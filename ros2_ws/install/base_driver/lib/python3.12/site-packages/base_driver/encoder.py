import rclpy
from rclpy.node import Node
from nav_msgs.msg import Odometry
from geometry_msgs.msg import TransformStamped, Quaternion, Twist
from tf2_ros import TransformBroadcaster
from gpiozero import Button
import math
import numpy as np

class EncoderOdomNode(Node):
    def __init__(self):
        super().__init__('encoder_odom_node')

        # --- パラメータ設定 ---
        self.declare_parameter('ticks_per_rev', 20.0 * 2) # 20スリット * 2(両エッジ) = 40
        self.declare_parameter('wheel_radius', 0.030)    # 半径 (例: 65mmタイヤなら0.0325)
        self.declare_parameter('wheel_separation', 0.10)  # 車輪間隔 (例: 15cm)
        
        self.ticks_per_rev = self.get_parameter('ticks_per_rev').value
        self.wheel_radius = self.get_parameter('wheel_radius').value
        self.wheel_separation = self.get_parameter('wheel_separation').value

        # --- 方向制御用のフラグ (1: 前進, -1: 後退) ---
        self.dir_r = 1
        self.dir_l = 1

        # --- GPIO設定 ---
        # 右モータ (GPIO 10)
        self.enc_r = Button(10, pull_up=True)
        self.count_r = 0
        self.enc_r.when_pressed = self.enc_callback_r
        self.enc_r.when_released = self.enc_callback_r

        # 左モータ (GPIO 2)
        self.enc_l = Button(2, pull_up=True)
        self.count_l = 0
        self.enc_l.when_pressed = self.enc_callback_l
        self.enc_l.when_released = self.enc_callback_l

        # --- オドメトリ計算用変数 ---
        self.x = 0.0
        self.y = 0.0
        self.th = 0.0
        
        self.prev_count_r = 0
        self.prev_count_l = 0
        self.last_time = self.get_clock().now()

        # --- ROS 2 通信 ---
        self.odom_pub = self.create_publisher(Odometry, 'odom', 10)
        self.tf_broadcaster = TransformBroadcaster(self)

        # 【追加】cmd_velを購読して、回転方向を判断する
        self.vel_sub = self.create_subscription(Twist, 'cmd_vel', self.cmd_vel_callback, 10)

        # 0.1秒ごとにオドメトリ計算
        self.timer = self.create_timer(0.1, self.timer_callback)

    # --- cmd_vel を受け取って方向フラグを更新する ---
    def cmd_vel_callback(self, msg):
        linear = msg.linear.x
        angular = msg.angular.z
        
        # 差動二輪の運動学から左右の期待される速度方向を計算
        # 右車輪の速度 = v + (w * d / 2)
        # 左車輪の速度 = v - (w * d / 2)
        vel_r = linear + (angular * self.wheel_separation / 2.0)
        vel_l = linear - (angular * self.wheel_separation / 2.0)

        # 速度がマイナスならカウントを減らすモード(-1)にする
        # 0の場合は、とりあえず前の状態を維持するか、1(正転)とする
        if vel_r < -0.001: self.dir_r = -1
        else:              self.dir_r = 1
            
        if vel_l < -0.001: self.dir_l = -1
        else:              self.dir_l = 1

    # --- 割り込みコールバック (方向フラグを掛ける) ---
    def enc_callback_r(self):
        self.count_r += 1 * self.dir_r  # ここでプラスかマイナスか決まる

    def enc_callback_l(self):
        self.count_l += 1 * self.dir_l  # ここでプラスかマイナスか決まる

    def euler_to_quaternion(self, roll, pitch, yaw):
        qx = np.sin(roll/2) * np.cos(pitch/2) * np.cos(yaw/2) - np.cos(roll/2) * np.sin(pitch/2) * np.sin(yaw/2)
        qy = np.cos(roll/2) * np.sin(pitch/2) * np.cos(yaw/2) + np.sin(roll/2) * np.cos(pitch/2) * np.sin(yaw/2)
        qz = np.cos(roll/2) * np.cos(pitch/2) * np.sin(yaw/2) - np.sin(roll/2) * np.sin(pitch/2) * np.cos(yaw/2)
        qw = np.cos(roll/2) * np.cos(pitch/2) * np.cos(yaw/2) + np.sin(roll/2) * np.sin(pitch/2) * np.sin(yaw/2)
        return Quaternion(x=qx, y=qy, z=qz, w=qw)

    def timer_callback(self):
        current_time = self.get_clock().now()
        dt = (current_time - self.last_time).nanoseconds / 1e9
        
        if dt == 0: return

        delta_r = self.count_r - self.prev_count_r
        delta_l = self.count_l - self.prev_count_l
        
        self.prev_count_r = self.count_r
        self.prev_count_l = self.count_l

        # 距離計算
        dist_r = (2 * math.pi * self.wheel_radius) * (delta_r / self.ticks_per_rev)
        dist_l = (2 * math.pi * self.wheel_radius) * (delta_l / self.ticks_per_rev)

        delta_dist = (dist_r + dist_l) / 2.0
        delta_th = (dist_r - dist_l) / self.wheel_separation

        self.x += delta_dist * math.cos(self.th + delta_th / 2.0)
        self.y += delta_dist * math.sin(self.th + delta_th / 2.0)
        self.th += delta_th

        vx = delta_dist / dt
        vth = delta_th / dt

        q = self.euler_to_quaternion(0, 0, self.th)

        # TF配信
        t = TransformStamped()
        t.header.stamp = current_time.to_msg()
        t.header.frame_id = 'odom'
        t.child_frame_id = 'base_link'
        t.transform.translation.x = self.x
        t.transform.translation.y = self.y
        t.transform.translation.z = 0.0
        t.transform.rotation = q
        self.tf_broadcaster.sendTransform(t)

        # Odom配信
        odom = Odometry()
        odom.header.stamp = current_time.to_msg()
        odom.header.frame_id = 'odom'
        odom.child_frame_id = 'base_link'
        odom.pose.pose.position.x = self.x
        odom.pose.pose.position.y = self.y
        odom.pose.pose.orientation = q
        odom.twist.twist.linear.x = vx
        odom.twist.twist.angular.z = vth
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

if __name__ == '__main__':
    main()
