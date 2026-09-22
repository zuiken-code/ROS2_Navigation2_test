import os

from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory


def generate_launch_description():

    base_driver_dir = get_package_share_directory('base_driver')
    ydlidar_dir = get_package_share_directory('ydlidar_ros2_driver')
    slam_toolbox_dir = get_package_share_directory('slam_toolbox')

    urdf_file = os.path.join(
        base_driver_dir,
        'urdf',
        'robot.urdf.xml'
    )

    ydlidar_params = os.path.join(
        ydlidar_dir,
        'params',
        'Tmini-Plus-SH.yaml'
    )

    slam_params = os.path.join(
        slam_toolbox_dir,
        'config',
        'mapper_params_online_async.yaml'
    )

    # ============================================================
    # モーター制御
    # ============================================================

    motor_node = Node(
        package='base_driver',
        executable='base_driver',
        name='base_driver',
        output='screen',
        remappings=[
            ('/cmd_vel', '/turtle1/cmd_vel'),
        ],
        parameters=[{
            'wheel_separation': 0.14,
            'control_period': 0.05,
            'cmd_timeout': 0.5,
            'odom_timeout': 0.5,
            'ff_output': 0.25,
            'kp': 2.0,
            'ki': 0.0,
            'kd': 0.0,
            'i_limit': 0.3,
        }],
    )

    # ============================================================
    # エンコーダオドメトリ
    # ============================================================

    odom_node = Node(
        package='base_driver',
        executable='encoder_odom',
        name='encoder_odom_node',
        output='screen',
        parameters=[{
            'ticks_per_rev': 40.0,
            'wheel_radius': 0.035,
            'wheel_separation': 0.14,
        }],
    )

    # ============================================================
    # Web Dashboard
    # ============================================================

    dashboard_node = Node(
        package='base_driver',
        executable='web_dashboard',
        name='web_dashboard',
        output='screen',
        parameters=[{
            'host': '0.0.0.0',
            'port': 5800,
            'wheel_separation': 0.14,
        }],
    )

    # ============================================================
    # URDF -> TF
    # ============================================================

    robot_state_publisher = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        name='robot_state_publisher',
        output='screen',
        parameters=[{
            'robot_description': open(urdf_file).read(),
            'use_sim_time': False,
        }],
    )

    joint_state_publisher = Node(
        package='joint_state_publisher',
        executable='joint_state_publisher',
        name='joint_state_publisher',
        output='screen',
    )

    # ============================================================
    # YDLIDAR T-mini Plus
    # ============================================================

    lidar_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(
                ydlidar_dir,
                'launch',
                'ydlidar_launch.py'
            )
        ),
        launch_arguments={
            'params_file': ydlidar_params,
        }.items(),
    )

    # ============================================================
    # SLAM Toolbox
    # ============================================================

    slam_node = Node(
        package='slam_toolbox',
        executable='async_slam_toolbox_node',
        name='slam_toolbox',
        output='screen',
        parameters=[
            slam_params,
            {
                'use_sim_time': False,
            },
        ],
    )

    # ============================================================
    # RViz
    # ============================================================

    rviz_node = Node(
        package='rviz2',
        executable='rviz2',
        name='rviz2',
        output='screen',
    )

    return LaunchDescription([
        motor_node,
        odom_node,
        dashboard_node,

        robot_state_publisher,
        joint_state_publisher,

        lidar_launch,

        slam_node,

        rviz_node,
    ])
