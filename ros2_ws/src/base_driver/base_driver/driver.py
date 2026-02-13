import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
from gpiozero import Motor

LEFT_MOTOR_PINS = (18,17)
RIGHT_MOTOR_PINS = (23,22)

GAIN_LINEAR = 2.0
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
        
        self.get_logger().info('GPIOZero Motor Driver Started on Ubuntu!')

    def listener_callback(self, msg):
        v = msg.linear.x * GAIN_LINEAR
        w = msg.angular.z * GAIN_ANGULAR
        
        left_speed = v - w
        right_speed = v + w
        
        left_output = max(min(left_speed, 1.0), -1.0)
        right_output = max(min(right_speed, 1.0), -1.0)
        
        if left_output >= 0:
            self.left_motor.forward(left_output)
        else:
            self.left_motor.backward(abs(left_output))
            
        if right_output >= 0:
            self.right_motor.forward(right_output)
        else:
            self.right_motor.backward(abs(right_output))

    def stop_motors(self):
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
