from setuptools import find_packages, setup
import glob

package_name = 'base_driver'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        ('share/' + package_name + '/urdf',   glob.glob('urdf/*')),
        ('share/' + package_name + '/config', glob.glob('config/*')),
        ('share/' + package_name + '/map',    glob.glob('map/*')),   # ← map追加
        ('share/' + package_name + '/launch', glob.glob('launch/*')), # ← launchは1行だけ
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='zuiken',
    maintainer_email='zuiken2022robo@gmail.com',
    description='ROS2 Nav2 base driver',
    license='MIT',
    entry_points={
        'console_scripts': [
            'base_driver  = base_driver.driver:main',
            'encoder_odom = base_driver.encoder:main',
        ],
    },
)