from launch import LaunchDescription
from launch_ros.actions import Node

def generate_launch_description():
    # launchの構成を示すLaunchDescription型の変数の定義
    ld = LaunchDescription()

    # 1. モータードライバーノード (drive)
    motor_node = Node(
        package='base_driver',
        executable='drive',
        name='motor_driver',
        # turtle_teleop_keyのトピック名に合わせるためのリマップ
        remappings=[('/cmd_vel', '/turtle1/cmd_vel')],
        output='screen'
    )

    # 2. エンコーダーオドメトリノード (encoder_odom_node)
    odom_node = Node(
        package='base_driver',
        executable='encoder',
        name='encoder_odom',
        remappings=[('/cmd_vel', '/turtle1/cmd_vel')],
        output='screen'
    )

    # 3. 静的TF配信ノード (map -> odom)
    static_tf_node = Node(
        package='tf2_ros',
        executable='static_transform_publisher',
        name='static_tf_pub',
        arguments=['0', '0', '0', '0', '0', '0', 'map', 'odom']
    )

    # 4. RViz2ノード
    rviz_node = Node(
        package='rviz2',
        executable='rviz2',
        name='rviz2',
        output='screen'
    )
    # 5. keyboard操作のノードは自分で出す

    # LaunchDescriptionに、起動したいノードを追加する
    ld.add_action(motor_node)
    ld.add_action(odom_node)
    ld.add_action(static_tf_node)
    ld.add_action(rviz_node)

    # launch構成を返すようにする
    return ld
