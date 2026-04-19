import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
from gpiozero import Motor

RIGHT_MOTOR_PINS = (18, 17)
LEFT_MOTOR_PINS  = (23, 22)
GAIN_LINEAR  = 5.0
GAIN_ANGULAR = 0.5

class BaseDriver(Node):
    def __init__(self):
        super().__init__('base_driver')
        self.left_motor  = Motor(forward=LEFT_MOTOR_PINS[0],  backward=LEFT_MOTOR_PINS[1])
        self.right_motor = Motor(forward=RIGHT_MOTOR_PINS[0], backward=RIGHT_MOTOR_PINS[1])
        self.subscription = self.create_subscription(
            Twist, 'cmd_vel', self.listener_callback, 10)
        self.last_received_time = self.get_clock().now()
        self.create_timer(0.1, self.check_timeout)
        self.get_logger().info('GPIOZero Motor Driver Started!')

    def listener_callback(self, msg):
        self.last_received_time = self.get_clock().now()
        v = msg.linear.x  * GAIN_LINEAR
        w = msg.angular.z * GAIN_ANGULAR
        left  = max(min(v - w, 1.0), -1.0)
        right = max(min(v + w, 1.0), -1.0)
        self.get_logger().info(f'cmd_vel → L:{left:.2f} R:{right:.2f}')
        self.drive(left, right)

    def drive(self, left_val, right_val):
        if left_val >= 0:
            self.left_motor.forward(left_val)
        else:
            self.left_motor.backward(abs(left_val))
        if right_val >= 0:
            self.right_motor.forward(right_val)
        else:
            self.right_motor.backward(abs(right_val))

    def check_timeout(self):
        elapsed = self.get_clock().now() - self.last_received_time
        if elapsed.nanoseconds > 0.5 * 1e9:
            self.stop_motors()

    def stop_motors(self):
        self.left_motor.stop()
        self.right_motor.stop()

    def destroy_node(self):
        self.stop_motors()
        super().destroy_node()

def main(args=None):
    rclpy.init(args=args)
    node = BaseDriver()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()