import os
from launch import LaunchDescription
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory

def generate_launch_description():
    pkg_dir     = get_package_share_directory('base_driver')
    params_file = os.path.join(pkg_dir, 'config', 'nav2_params.yaml')
    urdf_file   = os.path.join(pkg_dir, 'urdf', 'robot.urdf.xml')
    map_file    = os.path.join(pkg_dir, 'map', 'empty_map.yaml')

    return LaunchDescription([

        # モーター制御
     #    Node(package='base_driver', executable='base_driver',
     #         name='base_driver', output='screen'),

     #    # エンコーダーオドメトリ
     #    Node(package='base_driver', executable='encoder_odom',
     #         name='encoder_odom_node', output='screen',
     #         parameters=[{'ticks_per_rev': 40.0,
     #                      'wheel_radius': 0.030,
     #                      'wheel_separation': 0.10}]),

        # URDF → TF
        Node(package='robot_state_publisher',
             executable='robot_state_publisher',
             parameters=[{'robot_description': open(urdf_file).read(),
                          'use_sim_time': False}]),

          # Node(package='joint_state_publisher',
          # executable='joint_state_publisher',
          # name='joint_state_publisher'),

        # ★ map→odom を静的TFで固定（AMCLの代替）
        Node(package='base_driver', executable='static_tf_pub',
             name='static_map_odom_tf', output='screen'),

        # 地図サーバー
        Node(package='nav2_map_server', executable='map_server',
             name='map_server', output='screen',
             parameters=[params_file,
                         {'yaml_filename': map_file}]),

        # プランナー
        Node(package='nav2_planner', executable='planner_server',
             name='planner_server', output='screen',
             parameters=[params_file]),

        # コントローラー
        Node(package='nav2_controller', executable='controller_server',
             name='controller_server', output='screen',
             parameters=[params_file]),

        # スムーザー
        Node(package='nav2_smoother', executable='smoother_server',
             name='smoother_server', output='screen',
             parameters=[params_file]),

        # ビヘイビア（スピン・バックアップ等）
        Node(package='nav2_behaviors', executable='behavior_server',
             name='behavior_server', output='screen',
             parameters=[params_file]),

        # BTナビゲーター
        Node(package='nav2_bt_navigator', executable='bt_navigator',
             name='bt_navigator', output='screen',
             parameters=[params_file]),

        # Waypointフォロワー
        Node(package='nav2_waypoint_follower',
             executable='waypoint_follower',
             name='waypoint_follower', output='screen',
             parameters=[params_file]),

        # 速度スムーザー
        Node(package='nav2_velocity_smoother',
             executable='velocity_smoother',
             name='velocity_smoother', output='screen',
             parameters=[params_file]),

        # ライフサイクルマネージャー（localization）: AMCLなし・map_serverのみ
        Node(package='nav2_lifecycle_manager',
             executable='lifecycle_manager',
             name='lifecycle_manager_localization',
             output='screen',
             parameters=[{'autostart': True,
                          'node_names': ['map_server']}]),

        # ライフサイクルマネージャー（navigation）
        Node(package='nav2_lifecycle_manager',
             executable='lifecycle_manager',
             name='lifecycle_manager_navigation',
             output='screen',
             parameters=[{'autostart': True,
                          'node_names': [
                              'controller_server',
                              'smoother_server',
                              'planner_server',
                              'behavior_server',
                              'bt_navigator',
                              'waypoint_follower',
                              'velocity_smoother',
                          ]}]),
    ])