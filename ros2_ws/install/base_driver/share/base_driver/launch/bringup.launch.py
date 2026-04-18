import os
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory

def generate_launch_description():
    # パス設定
    pkg_dir      = get_package_share_directory('base_driver')
    nav2_bringup = get_package_share_directory('nav2_bringup')
    params_file  = os.path.join(pkg_dir, 'config', 'nav2_params.yaml')
    urdf_file    = os.path.join(pkg_dir, 'urdf', 'robot.urdf.xml')
    map_yaml     = os.path.join(pkg_dir, 'map', 'empty_map.yaml')

    # LaunchDescriptionのインスタンス作成
    ld = LaunchDescription()

    # 1. モーター制御ノード
    motor_node = Node(
        package='base_driver',
        executable='base_driver',
        name='base_driver',
        output='screen'
    )

    # 2. エンコーダーオドメトリノード
    odom_node = Node(
        package='base_driver',
        executable='encoder_odom',
        name='encoder_odom_node',
        output='screen',
        parameters=[{
            'ticks_per_rev':    40.0,
            'wheel_radius':     0.030,
            'wheel_separation': 0.10,
        }]
    )

    # 3. ロボット状態配信 (URDF -> TF)
    rsp_node = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        parameters=[{
            'robot_description': open(urdf_file).read(),
            'use_sim_time': False,
        }]
    )

    # 4. Nav2 Bringup (地図、AMCL、ナビゲーション一式)
    # Jazzyの型エラー回避のため、辞書をlist().items()で確実に変換して渡します
    nav2_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(nav2_bringup, 'launch', 'bringup_launch.py')
        ),
        launch_arguments=list({
            'params_file': params_file,
            'use_sim_time': 'false',
            'map': map_yaml,
        }.items())
    )

    # アクションの追加
    ld.add_action(motor_node)
    ld.add_action(odom_node)
    ld.add_action(rsp_node)
    ld.add_action(nav2_launch)

    return ld