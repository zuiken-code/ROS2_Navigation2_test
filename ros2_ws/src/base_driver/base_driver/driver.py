import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
from nav_msgs.msg import Odometry
from gpiozero import Motor


RIGHT_MOTOR_PINS = (18, 17)
LEFT_MOTOR_PINS = (23, 22)


def clamp(value, low, high):
    return max(min(value, high), low)


class WheelPid:
    def __init__(self, kp, ki, kd, i_limit):
        self.kp = kp
        self.ki = ki
        self.kd = kd
        self.i_limit = abs(i_limit)
        self.integral = 0.0
        self.prev_error = 0.0
        self.has_prev_error = False

    def reset(self):
        self.integral = 0.0
        self.prev_error = 0.0
        self.has_prev_error = False

    def update(self, error, dt):
        self.integral += error * dt
        self.integral = clamp(self.integral, -self.i_limit, self.i_limit)

        derivative = 0.0
        if self.has_prev_error and dt > 0.0:
            derivative = (error - self.prev_error) / dt

        self.prev_error = error
        self.has_prev_error = True
        return self.kp * error + self.ki * self.integral + self.kd * derivative


class BaseDriver(Node):
    def __init__(self):
        super().__init__('base_driver')

        self.declare_parameter('wheel_separation', 0.10)
        self.declare_parameter('control_period', 0.05)
        self.declare_parameter('cmd_timeout', 0.5)
        self.declare_parameter('odom_timeout', 0.5)
        self.declare_parameter('target_deadband', 0.001)
        self.declare_parameter('ff_output', 0.25)
        self.declare_parameter('max_output', 1.0)
        self.declare_parameter('kp', 2.0)
        self.declare_parameter('ki', 0.0)
        self.declare_parameter('kd', 0.0)
        self.declare_parameter('i_limit', 0.3)

        self.wheel_separation = self.get_parameter('wheel_separation').value
        self.control_period = self.get_parameter('control_period').value
        self.cmd_timeout = self.get_parameter('cmd_timeout').value
        self.odom_timeout = self.get_parameter('odom_timeout').value
        self.target_deadband = self.get_parameter('target_deadband').value
        self.ff_output = self.get_parameter('ff_output').value
        self.max_output = self.get_parameter('max_output').value

        kp = self.get_parameter('kp').value
        ki = self.get_parameter('ki').value
        kd = self.get_parameter('kd').value
        i_limit = self.get_parameter('i_limit').value
        self.left_pid = WheelPid(kp, ki, kd, i_limit)
        self.right_pid = WheelPid(kp, ki, kd, i_limit)

        self.left_motor = Motor(
            forward=LEFT_MOTOR_PINS[0],
            backward=LEFT_MOTOR_PINS[1],
        )
        self.right_motor = Motor(
            forward=RIGHT_MOTOR_PINS[0],
            backward=RIGHT_MOTOR_PINS[1],
        )

        self.target_left = 0.0
        self.target_right = 0.0
        self.actual_left = 0.0
        self.actual_right = 0.0

        now = self.get_clock().now()
        self.last_cmd_time = now
        self.last_odom_time = now
        self.last_control_time = now

        self.cmd_sub = self.create_subscription(
            Twist, 'cmd_vel', self.cmd_vel_callback, 10)
        self.odom_sub = self.create_subscription(
            Odometry, 'odom', self.odom_callback, 10)
        self.create_timer(self.control_period, self.control_loop)

        self.get_logger().info('GPIOZero motor driver started with velocity PID')

    def cmd_vel_callback(self, msg):
        self.last_cmd_time = self.get_clock().now()
        v = msg.linear.x
        w = msg.angular.z
        self.target_left = v - (w * self.wheel_separation / 2.0)
        self.target_right = v + (w * self.wheel_separation / 2.0)

    def odom_callback(self, msg):
        self.last_odom_time = self.get_clock().now()
        v = msg.twist.twist.linear.x
        w = msg.twist.twist.angular.z
        self.actual_left = v - (w * self.wheel_separation / 2.0)
        self.actual_right = v + (w * self.wheel_separation / 2.0)

    def control_loop(self):
        now = self.get_clock().now()
        dt = (now - self.last_control_time).nanoseconds / 1e9
        self.last_control_time = now
        if dt <= 0.0:
            return

        cmd_age = (now - self.last_cmd_time).nanoseconds / 1e9
        odom_age = (now - self.last_odom_time).nanoseconds / 1e9
        if cmd_age > self.cmd_timeout or odom_age > self.odom_timeout:
            self.stop_motors()
            return

        left_output = self.wheel_output(
            self.target_left,
            self.actual_left,
            self.left_pid,
            dt,
        )
        right_output = self.wheel_output(
            self.target_right,
            self.actual_right,
            self.right_pid,
            dt,
        )
        self.drive(left_output, right_output)

    def wheel_output(self, target, actual, pid, dt):
        if abs(target) < self.target_deadband:
            pid.reset()
            return 0.0

        error = target - actual
        pid_output = pid.update(error, dt)
        ff_output = self.ff_output if target > 0.0 else -self.ff_output
        return clamp(ff_output + pid_output, -self.max_output, self.max_output)

    def drive(self, left_value, right_value):
        self.drive_motor(self.left_motor, left_value)
        self.drive_motor(self.right_motor, right_value)

    def drive_motor(self, motor, value):
        value = clamp(value, -self.max_output, self.max_output)
        if value > 0.0:
            motor.forward(value)
        elif value < 0.0:
            motor.backward(abs(value))
        else:
            motor.stop()

    def stop_motors(self):
        self.target_left = 0.0
        self.target_right = 0.0
        self.left_pid.reset()
        self.right_pid.reset()
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
