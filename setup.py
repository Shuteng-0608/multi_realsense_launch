# from setuptools import find_packages, setup

# package_name = 'dual_realsense_launch'

# setup(
#     name=package_name,
#     version='0.0.0',
#     packages=find_packages(exclude=['test']),
#     data_files=[
#         ('share/ament_index/resource_index/packages',
#             ['resource/' + package_name]),
#         ('share/' + package_name, ['package.xml']),
#     ],
#     install_requires=['setuptools'],
#     zip_safe=True,
#     maintainer='stw',
#     maintainer_email='stw@todo.todo',
#     description='TODO: Package description',
#     license='TODO: License declaration',
#     extras_require={
#         'test': [
#             'pytest',
#         ],
#     },
#     entry_points={
#         'console_scripts': [
#         ],
#     },
# )

from glob import glob
from setuptools import setup

package_name = 'dual_realsense_launch'

setup(
    name=package_name,
    version='0.0.1',
    packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages',
         ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        ('share/' + package_name + '/launch',
         glob('launch/*.launch.py')),
        ('share/' + package_name + '/config',
         glob('config/*')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='stw',
    maintainer_email='stw@local',
    description='Dual RealSense (D405 + D455) launch',
    license='Apache-2.0',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [],
    },
)
