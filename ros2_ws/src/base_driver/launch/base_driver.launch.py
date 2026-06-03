from launch import LaunchDescription
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory
import os

joy_config = os.path.join(
    get_package_share_directory('base_driver'),
    'config',
    'joy.yaml'
)


def generate_launch_description():
    wheel_params = {
        'ticks_per_rev': 40.0,
        'wheel_radius': 0.030,
        'wheel_separation': 0.10,
    }
    pid_params = {
        'wheel_separation': 0.10,
        'control_period': 0.05,
        'cmd_timeout': 0.5,
        'odom_timeout': 0.5,
        'ff_output': 0.25,
        'kp': 2.0,
        'ki': 0.0,
        'kd': 0.0,
        'i_limit': 0.3,
    }

    joy_teleop_node = Node(
        package='teleop_twist_joy',
        executable='teleop_node',
        name='teleop_twist_joy_node',
        remappings=[
            ('/cmd_vel', '/turtle1/cmd_vel')
            ],
        parameters=[joy_config],
        output='screen',
        )

    joy_node = Node(
    package='joy',
    executable='joy_node',
    name='joy_node',
    output='screen',
)
    motor_node = Node(
        package='base_driver',
        executable='base_driver',
        name='motor_driver',
        remappings=[('/cmd_vel', '/turtle1/cmd_vel')],
        parameters=[pid_params],
        output='screen',
    )

    odom_node = Node(
        package='base_driver',
        executable='encoder_odom',
        name='encoder_odom_node',
        remappings=[('/cmd_vel', '/turtle1/cmd_vel')],
        parameters=[wheel_params],
        output='screen',
    )

    static_tf_node = Node(
        package='tf2_ros',
        executable='static_transform_publisher',
        name='static_tf_pub',
        arguments=['0', '0', '0', '0', '0', '0', 'map', 'odom'],
    )

    rviz_node = Node(
        package='rviz2',
        executable='rviz2',
        name='rviz2',
        output='screen',
    )

    dashboard_node = Node(
        package='base_driver',
        executable='web_dashboard',
        name='web_dashboard',
        parameters=[{
            'host': '0.0.0.0',
            'port': 5800,
            'wheel_separation': 0.10,
        }],
        output='screen',
    )

    return LaunchDescription([
        motor_node,
        odom_node,
        dashboard_node,
        static_tf_node,
        rviz_node,
        joy_teleop_node,
        joy_node,
    ])
