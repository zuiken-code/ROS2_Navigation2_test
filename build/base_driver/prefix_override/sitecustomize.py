import sys
if sys.prefix == '/usr':
    sys.real_prefix = sys.prefix
    sys.prefix = sys.exec_prefix = '/home/zuiken/Documents/ROS2_Navigation2_test/install/base_driver'
