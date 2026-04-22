import rclpy
from rclpy.node import Node
from nav_msgs.msg import Odometry
from geometry_msgs.msg import TransformStamped, Quaternion, Twist
from tf2_ros import TransformBroadcaster, StaticTransformBroadcaster
import lgpio
import math

ENC_RIGHT = 10
ENC_LEFT  = 2

class EncoderOdomNode(Node):
    def __init__(self):
        super().__init__('encoder_odom_node')

        self.declare_parameter('ticks_per_rev',    40.0)
        self.declare_parameter('wheel_radius',     0.030)
        self.declare_parameter('wheel_separation', 0.10)
        self.ticks_per_rev    = self.get_parameter('ticks_per_rev').value
        self.wheel_radius     = self.get_parameter('wheel_radius').value
        self.wheel_separation = self.get_parameter('wheel_separation').value

        self.dir_r = 1
        self.dir_l = 1
        self.count_r = 0
        self.count_l = 0

        # lgpio 初期化
        self.h = lgpio.gpiochip_open(4)
        lgpio.gpio_claim_input(self.h, ENC_RIGHT, lgpio.SET_PULL_UP)
        lgpio.gpio_claim_input(self.h, ENC_LEFT,  lgpio.SET_PULL_UP)
        self.prev_r = lgpio.gpio_read(self.h, ENC_RIGHT)
        self.prev_l = lgpio.gpio_read(self.h, ENC_LEFT)

        self.x  = 0.0
        self.y  = 0.0
        self.th = 0.0
        self.prev_count_r = 0
        self.prev_count_l = 0
        self.last_time = self.get_clock().now()

        self.odom_pub       = self.create_publisher(Odometry, 'odom', 10)
        self.tf_broadcaster = TransformBroadcaster(self)

        static_broadcaster = StaticTransformBroadcaster(self)
        t = TransformStamped()
        t.header.stamp    = self.get_clock().now().to_msg()
        t.header.frame_id = 'base_footprint'
        t.child_frame_id  = 'base_link'
        t.transform.rotation.w = 1.0
        static_broadcaster.sendTransform(t)

        self.vel_sub = self.create_subscription(
            Twist, 'cmd_vel', self.cmd_vel_callback, 10)

        self.create_timer(0.002, self.poll_encoders)  # 500Hz ポーリング
        self.create_timer(0.1,   self.timer_callback) # 10Hz オドメトリ
        self.get_logger().info('EncoderOdom started!')

    def poll_encoders(self):
        cur_r = lgpio.gpio_read(self.h, ENC_RIGHT)
        cur_l = lgpio.gpio_read(self.h, ENC_LEFT)
        if cur_r != self.prev_r:
            self.count_r += self.dir_r
            self.prev_r = cur_r
        if cur_l != self.prev_l:
            self.count_l += self.dir_l
            self.prev_l = cur_l

    def cmd_vel_callback(self, msg):
        v = msg.linear.x
        w = msg.angular.z
        vel_r = v + (w * self.wheel_separation / 2.0)
        vel_l = v - (w * self.wheel_separation / 2.0)
        self.dir_r = -1 if vel_r < -0.001 else 1
        self.dir_l = -1 if vel_l < -0.001 else 1

    def euler_to_quaternion(self, yaw):
        return Quaternion(
            x=0.0, y=0.0,
            z=math.sin(yaw / 2),
            w=math.cos(yaw / 2)
        )

    def timer_callback(self):
        now = self.get_clock().now()
        dt  = (now - self.last_time).nanoseconds / 1e9
        if dt < 0.001:
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
        q = self.euler_to_quaternion(self.th)

        t = TransformStamped()
        t.header.stamp    = now.to_msg()
        t.header.frame_id = 'odom'
        t.child_frame_id  = 'base_footprint'
        t.transform.translation.x = self.x
        t.transform.translation.y = self.y
        t.transform.rotation      = q
        self.tf_broadcaster.sendTransform(t)

        odom = Odometry()
        odom.header.stamp       = now.to_msg()
        odom.header.frame_id    = 'odom'
        odom.child_frame_id     = 'base_footprint'
        odom.pose.pose.position.x  = self.x
        odom.pose.pose.position.y  = self.y
        odom.pose.pose.orientation = q
        odom.twist.twist.linear.x  = delta_dist / dt
        odom.twist.twist.angular.z = delta_th   / dt
        self.odom_pub.publish(odom)
        self.last_time = now

    def destroy_node(self):
        lgpio.gpiochip_close(self.h)
        super().destroy_node()

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