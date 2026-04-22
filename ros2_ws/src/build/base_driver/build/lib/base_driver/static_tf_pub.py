# base_driver/static_tf_pub.py
import rclpy
from rclpy.node import Node
from tf2_ros import StaticTransformBroadcaster
from geometry_msgs.msg import TransformStamped

class StaticMapOdomTF(Node):
    def __init__(self):
        super().__init__('static_map_odom_tf')
        self.broadcaster = StaticTransformBroadcaster(self)
        t = TransformStamped()
        t.header.stamp = self.get_clock().now().to_msg()
        t.header.frame_id = 'map'
        t.child_frame_id  = 'odom'
        t.transform.rotation.w = 1.0  # 回転なし・位置ずれなし
        self.broadcaster.sendTransform(t)
        self.get_logger().info('Static map->odom TF published!')

def main(args=None):
    rclpy.init(args=args)
    node = StaticMapOdomTF()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()