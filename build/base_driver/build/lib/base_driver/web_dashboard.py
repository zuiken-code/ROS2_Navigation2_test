import json
import math
import mimetypes
import os
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import unquote

import rclpy
from action_msgs.msg import GoalStatus, GoalStatusArray
from ament_index_python.packages import get_package_share_directory
from geometry_msgs.msg import PoseStamped, Twist
from nav_msgs.msg import Odometry
from rclpy.node import Node


STATUS_TEXT = {
    GoalStatus.STATUS_UNKNOWN: 'unknown',
    GoalStatus.STATUS_ACCEPTED: 'accepted',
    GoalStatus.STATUS_EXECUTING: 'executing',
    GoalStatus.STATUS_CANCELING: 'canceling',
    GoalStatus.STATUS_SUCCEEDED: 'succeeded',
    GoalStatus.STATUS_CANCELED: 'canceled',
    GoalStatus.STATUS_ABORTED: 'aborted',
}


def yaw_from_quaternion(q):
    siny_cosp = 2.0 * (q.w * q.z + q.x * q.y)
    cosy_cosp = 1.0 - 2.0 * (q.y * q.y + q.z * q.z)
    return math.atan2(siny_cosp, cosy_cosp)


class DashboardStore:
    def __init__(self):
        self._lock = threading.Lock()
        self._values = {}
        self._sources = {}
        self._widgets = []

    def add_source(self, name, label, unit='', kind='number', precision=3):
        source = {
            'name': name,
            'label': label,
            'unit': unit,
            'kind': kind,
            'precision': precision,
        }
        with self._lock:
            self._sources[name] = source
            self._values.setdefault(name, {
                'value': None,
                'time': None,
            })
        return source

    def add_widget(self, source, widget='value', size='medium'):
        with self._lock:
            self._widgets.append({
                'source': source,
                'widget': widget,
                'size': size,
            })

    def set_value(self, name, value, stamp_sec):
        with self._lock:
            self._values[name] = {
                'value': value,
                'time': stamp_sec,
            }

    def snapshot(self):
        with self._lock:
            return {
                'sources': list(self._sources.values()),
                'widgets': list(self._widgets),
                'values': dict(self._values),
            }


class DashboardNode(Node):
    def __init__(self):
        super().__init__('web_dashboard')
        self.declare_parameter('host', '0.0.0.0')
        self.declare_parameter('port', 5800)
        self.declare_parameter('wheel_separation', 0.10)

        self.store = DashboardStore()
        self.wheel_separation = self.get_parameter('wheel_separation').value
        self.static_dir = os.path.join(
            get_package_share_directory('base_driver'),
            'web',
        )

        self.configure_sources()
        self.create_subscription(Twist, 'cmd_vel', self.cmd_vel_callback, 10)
        self.create_subscription(Odometry, 'odom', self.odom_callback, 10)
        self.create_subscription(PoseStamped, 'goal_pose', self.goal_pose_callback, 10)
        self.create_subscription(
            GoalStatusArray,
            'navigate_to_pose/_action/status',
            self.goal_status_callback,
            10,
        )

        host = self.get_parameter('host').value
        port = self.get_parameter('port').value
        self.httpd = self.start_http_server(host, port)
        self.get_logger().info(f'Web dashboard listening on http://{host}:{port}')

    def configure_sources(self):
        self.add_value('cmd.linear_x', 'cmd_vel linear x', 'm/s')
        self.add_value('cmd.angular_z', 'cmd_vel angular z', 'rad/s')
        self.add_value('odom.linear_x', 'Current linear speed', 'm/s')
        self.add_value('odom.angular_z', 'Current angular speed', 'rad/s')
        self.add_value('wheel.left_speed', 'Left wheel speed', 'm/s')
        self.add_value('wheel.right_speed', 'Right wheel speed', 'm/s')
        self.add_value('goal.x', 'Goal x', 'm')
        self.add_value('goal.y', 'Goal y', 'm')
        self.add_value('goal.yaw', 'Goal yaw', 'rad')
        self.add_value('goal.status', 'Goal status', '', 'text', 0)
        self.add_value('goal.reached', 'Goal reached', '', 'boolean', 0)

        for source in [
            'cmd.linear_x',
            'cmd.angular_z',
            'odom.linear_x',
            'odom.angular_z',
            'wheel.left_speed',
            'wheel.right_speed',
            'goal.status',
            'goal.reached',
        ]:
            self.store.add_widget(source)

    def add_value(self, name, label, unit='', kind='number', precision=3):
        return self.store.add_source(name, label, unit, kind, precision)

    def set_value(self, name, value):
        stamp = self.get_clock().now().nanoseconds / 1e9
        self.store.set_value(name, value, stamp)

    def cmd_vel_callback(self, msg):
        self.set_value('cmd.linear_x', msg.linear.x)
        self.set_value('cmd.angular_z', msg.angular.z)

    def odom_callback(self, msg):
        v = msg.twist.twist.linear.x
        w = msg.twist.twist.angular.z
        half_track = self.wheel_separation / 2.0
        self.set_value('odom.linear_x', v)
        self.set_value('odom.angular_z', w)
        self.set_value('wheel.left_speed', v - (w * half_track))
        self.set_value('wheel.right_speed', v + (w * half_track))

    def goal_pose_callback(self, msg):
        pose = msg.pose
        self.set_value('goal.x', pose.position.x)
        self.set_value('goal.y', pose.position.y)
        self.set_value('goal.yaw', yaw_from_quaternion(pose.orientation))
        self.set_value('goal.status', 'accepted')
        self.set_value('goal.reached', False)

    def goal_status_callback(self, msg):
        if not msg.status_list:
            return

        status = msg.status_list[-1].status
        status_text = STATUS_TEXT.get(status, f'status_{status}')
        self.set_value('goal.status', status_text)
        self.set_value('goal.reached', status == GoalStatus.STATUS_SUCCEEDED)

    def start_http_server(self, host, port):
        node = self

        class DashboardHandler(BaseHTTPRequestHandler):
            def do_GET(self):
                path = unquote(self.path.split('?', 1)[0])
                if path == '/api/state':
                    self.write_json(node.store.snapshot())
                    return
                if path == '/':
                    path = '/index.html'
                self.serve_static(path)

            def serve_static(self, path):
                relative_path = path.lstrip('/')
                if '..' in relative_path.split('/'):
                    self.send_error(404)
                    return

                file_path = os.path.join(node.static_dir, relative_path)
                if not os.path.isfile(file_path):
                    self.send_error(404)
                    return

                content_type = mimetypes.guess_type(file_path)[0] or 'application/octet-stream'
                with open(file_path, 'rb') as file:
                    body = file.read()

                self.send_response(200)
                self.send_header('Content-Type', content_type)
                self.send_header('Cache-Control', 'no-store')
                self.send_header('Content-Length', str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def write_json(self, payload):
                body = json.dumps(payload).encode('utf-8')
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Cache-Control', 'no-store')
                self.send_header('Content-Length', str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, fmt, *args):
                return

        httpd = ThreadingHTTPServer((host, port), DashboardHandler)
        thread = threading.Thread(target=httpd.serve_forever, daemon=True)
        thread.start()
        return httpd

    def destroy_node(self):
        self.httpd.shutdown()
        self.httpd.server_close()
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = DashboardNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()
