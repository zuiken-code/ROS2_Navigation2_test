import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
from gpiozero import Motor

RIGHT_MOTOR_PINS = (18, 17)
LEFT_MOTOR_PINS = (23, 22)

GAIN_LINEAR = 1.0
GAIN_ANGULAR = 1.0

class BaseDriver(Node):
    def __init__(self):
        super().__init__('base_driver')
        
        self.subscription = self.create_subscription(
            Twist,
            'cmd_vel',
            self.listener_callback,
            10)
            
        self.left_motor = Motor(forward=LEFT_MOTOR_PINS[0], backward=LEFT_MOTOR_PINS[1])
        self.right_motor = Motor(forward=RIGHT_MOTOR_PINS[0], backward=RIGHT_MOTOR_PINS[1])
        
        # --- 追加: タイムアウト監視用のタイマー ---
        # 0.1秒ごとにチェックし、最後にデータを受信してから0.5秒経っていたら止める
        self.last_received_time = self.get_clock().now()
        self.timer = self.create_timer(0.1, self.check_timeout)
        
        self.get_logger().info('GPIOZero Motor Driver with Timeout Started!')

    def listener_callback(self, msg):
        # データを受け取った時刻を更新
        self.last_received_time = self.get_clock().now()
        
        self.get_logger().info(f'Received - Linear: {msg.linear.x:.2f}, Angular: {msg.angular.z:.2f}')
        
        v = msg.linear.x * GAIN_LINEAR
        w = msg.angular.z * GAIN_ANGULAR
        
        left_speed = v - w
        right_speed = v + w
        
        left_output = max(min(left_speed, 1.0), -1.0)
        right_output = max(min(right_speed, 1.0), -1.0)
        
        self.drive(left_output, right_output)

    def check_timeout(self):
        # 現在時刻と最後に受信した時刻の差を計算
        elapsed_time = self.get_clock().now() - self.last_received_time
        
        # 0.5秒以上データが来なければ停止
        if elapsed_time.nanoseconds > 0.5 * 1e9:
            self.stop_motors()

    def drive(self, left_val, right_val):
        """モーターを動かす共通処理"""
        if left_val >= 0:
            self.left_motor.forward(left_val)
        else:
            self.left_motor.backward(abs(left_val))
            
        if right_val >= 0:
            self.right_motor.forward(right_val)
        else:
            self.right_motor.backward(abs(right_val))

    def stop_motors(self):
        # 停止中であることをログに出さない（ログが埋まるため）
        self.left_motor.stop()
        self.right_motor.stop()

def main(args=None):
    rclpy.init(args=args)
    node = BaseDriver()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.stop_motors()
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
