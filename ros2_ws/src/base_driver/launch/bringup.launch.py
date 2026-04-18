import os
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory

def generate_launch_description():
    pkg_dir      = get_package_share_directory('base_driver')
    nav2_bringup = get_package_share_directory('nav2_bringup')
    params_file  = os.path.join(pkg_dir, 'config', 'nav2_params.yaml')
    urdf_file    = os.path.join(pkg_dir, 'urdf', 'robot.urdf.xml')
    map_file     = os.path.join(pkg_dir, 'map', 'empty_map.yaml')

    return LaunchDescription([

        Node(
            package='base_driver',
            executable='base_driver',
            name='base_driver',
            output='screen',
        ),

        Node(
            package='base_driver',
            executable='encoder_odom',
            name='encoder_odom_node',
            output='screen',
            parameters=[{
                'ticks_per_rev':    40.0,
                'wheel_radius':     0.030,
                'wheel_separation': 0.10,
            }]
        ),

        Node(
            package='robot_state_publisher',
            executable='robot_state_publisher',
            parameters=[{
                'robot_description': open(urdf_file).read(),
                'use_sim_time': False,
            }]
        ),

        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(
                os.path.join(nav2_bringup, 'launch', 'bringup_launch.py')
            ),
            launch_arguments={
                'params_file': params_file,
                'use_sim_time': 'false',
                'map': map_file,
            }.items()  # ★ .items() が必要！
        ),
    ])