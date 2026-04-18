# encoder_odom.py（修正版）
import rclpy
from rclpy.node import Node
from nav_msgs.msg import Odometry
from geometry_msgs.msg import TransformStamped, Quaternion, Twist
from tf2_ros import TransformBroadcaster, StaticTransformBroadcaster  # StaticTF追加
from gpiozero import Button
import math
import numpy as np

class EncoderOdomNode(Node):
    def __init__(self):
        super().__init__('encoder_odom_node')

        self.declare_parameter('ticks_per_rev', 40.0)
        self.declare_parameter('wheel_radius', 0.030)
        self.declare_parameter('wheel_separation', 0.10)
        
        self.ticks_per_rev    = self.get_parameter('ticks_per_rev').value
        self.wheel_radius     = self.get_parameter('wheel_radius').value
        self.wheel_separation = self.get_parameter('wheel_separation').value

        self.dir_r = 1
        self.dir_l = 1

        self.enc_r = Button(10, pull_up=True)
        self.count_r = 0
        self.enc_r.when_pressed  = self.enc_callback_r
        self.enc_r.when_released = self.enc_callback_r

        self.enc_l = Button(2, pull_up=True)
        self.count_l = 0
        self.enc_l.when_pressed  = self.enc_callback_l
        self.enc_l.when_released = self.enc_callback_l

        self.x    = 0.0
        self.y    = 0.0
        self.th   = 0.0
        self.prev_count_r = 0
        self.prev_count_l = 0
        self.last_time = self.get_clock().now()

        self.odom_pub      = self.create_publisher(Odometry, 'odom', 10)
        self.tf_broadcaster = TransformBroadcaster(self)
        
        # ★ 追加: base_footprint → base_link の静的TF
        self.static_broadcaster = StaticTransformBroadcaster(self)
        self._publish_static_tf()

        self.vel_sub = self.create_subscription(
            Twist, 'cmd_vel', self.cmd_vel_callback, 10)
        self.timer = self.create_timer(0.1, self.timer_callback)
        self.get_logger().info('EncoderOdom started!')

    def _publish_static_tf(self):
        """base_footprint → base_link (高さ0なので完全に同じ位置でOK)"""
        t = TransformStamped()
        t.header.stamp    = self.get_clock().now().to_msg()
        t.header.frame_id = 'base_footprint'
        t.child_frame_id  = 'base_link'
        t.transform.translation.z = 0.0
        t.transform.rotation.w    = 1.0  # 回転なし
        self.static_broadcaster.sendTransform(t)

    def cmd_vel_callback(self, msg):
        linear  = msg.linear.x
        angular = msg.angular.z
        vel_r = linear + (angular * self.wheel_separation / 2.0)
        vel_l = linear - (angular * self.wheel_separation / 2.0)
        self.dir_r = -1 if vel_r < -0.001 else 1
        self.dir_l = -1 if vel_l < -0.001 else 1

    def enc_callback_r(self):
        self.count_r += self.dir_r

    def enc_callback_l(self):
        self.count_l += self.dir_l

    def euler_to_quaternion(self, roll, pitch, yaw):
        cy, sy = math.cos(yaw/2), math.sin(yaw/2)
        cp, sp = math.cos(pitch/2), math.sin(pitch/2)
        cr, sr = math.cos(roll/2), math.sin(roll/2)
        return Quaternion(
            x = sr*cp*cy - cr*sp*sy,
            y = cr*sp*cy + sr*cp*sy,
            z = cr*cp*sy - sr*sp*cy,
            w = cr*cp*cy + sr*sp*sy
        )

    def timer_callback(self):
        current_time = self.get_clock().now()
        dt = (current_time - self.last_time).nanoseconds / 1e9
        if dt == 0:
            return

        delta_r = self.count_r - self.prev_count_r
        delta_l = self.count_l - self.prev_count_l
        self.prev_count_r = self.count_r
        self.prev_count_l = self.count_l

        dist_r = (2 * math.pi * self.wheel_radius) * (delta_r / self.ticks_per_rev)
        dist_l = (2 * math.pi * self.wheel_radius) * (delta_l / self.ticks_per_rev)

        delta_dist = (dist_r + dist_l) / 2.0
        delta_th   = (dist_r - dist_l) / self.wheel_separation

        self.x  += delta_dist * math.cos(self.th + delta_th / 2.0)
        self.y  += delta_dist * math.sin(self.th + delta_th / 2.0)
        self.th += delta_th

        vx  = delta_dist / dt
        vth = delta_th   / dt
        q   = self.euler_to_quaternion(0, 0, self.th)

        # TF: odom → base_footprint
        t = TransformStamped()
        t.header.stamp    = current_time.to_msg()
        t.header.frame_id = 'odom'
        t.child_frame_id  = 'base_footprint'   # ★ base_link→base_footprintに変更
        t.transform.translation.x = self.x
        t.transform.translation.y = self.y
        t.transform.translation.z = 0.0
        t.transform.rotation      = q
        self.tf_broadcaster.sendTransform(t)

        # Odometry
        odom = Odometry()
        odom.header.stamp       = current_time.to_msg()
        odom.header.frame_id    = 'odom'
        odom.child_frame_id     = 'base_footprint'  # ★ 同様に変更
        odom.pose.pose.position.x    = self.x
        odom.pose.pose.position.y    = self.y
        odom.pose.pose.orientation   = q
        odom.twist.twist.linear.x    = vx
        odom.twist.twist.angular.z   = vth
        self.odom_pub.publish(odom)

        self.last_time = current_time

def main(args=None):
    rclpy.init(args=args)
    node = EncoderOdomNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()