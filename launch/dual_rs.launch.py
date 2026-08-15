#!/usr/bin/env python3

"""
D405 + D455 dual-camera launch.

Design:
1. Start D455 immediately.
2. Start D405 after a short delay to avoid simultaneous USB initialization.
3. Bind each node by serial number.
4. Keep point cloud, depth alignment and IMU disabled by default.
5. Optionally publish calibrated camera mount transforms.

Recommended filename:
    dual_realsense.launch.py
"""

from typing import Any

from launch import LaunchDescription
from launch.actions import SetEnvironmentVariable, TimerAction
from launch.substitutions import PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


# ---------------------------------------------------------------------------
# Device configuration
# ---------------------------------------------------------------------------

D405_SERIAL = "_260322275294"
D455_SERIAL = "_261822304024"

D405_NAMESPACE = "d405"
D405_NAME = "d405"

D455_NAMESPACE = "d455"
D455_NAME = "d455"

# Start the wrist camera after the global camera is fully initialized.
D405_START_DELAY_SECONDS = 3.0


# ---------------------------------------------------------------------------
# Stream configuration
# ---------------------------------------------------------------------------

DEPTH_PROFILE = "640x480x30"
COLOR_PROFILE = "640x480x30"

ENABLE_DEPTH = True
ENABLE_COLOR = True

# Enable these only after both raw camera streams are confirmed stable.
ENABLE_POINTCLOUD = False
ENABLE_ALIGN_DEPTH = False

# D455 has an IMU, but it is disabled here to reduce initialization complexity.
ENABLE_D455_IMU = False

# Keep periodic device diagnostics disabled during normal streaming. Querying
# every option on two devices can disturb frame delivery on some systems.
DIAGNOSTICS_PERIOD = 0.0


# ---------------------------------------------------------------------------
# Camera installation TF configuration
# ---------------------------------------------------------------------------

# Keep this False until the transforms below are replaced by calibrated values.
PUBLISH_CAMERA_MOUNT_TF = False

# Static transform:
#     robot_base_frame -> d455_link
#
# The D455 is assumed to be a fixed/global camera.
D455_PARENT_FRAME = "base_link"
D455_MOUNT_XYZ_RPY = {
    "x": 0.0,
    "y": 0.0,
    "z": 0.0,
    "roll": 0.0,
    "pitch": 0.0,
    "yaw": 0.0,
}

# Static transform:
#     robot_tool_frame -> d405_link
#
# The D405 is assumed to be mounted on the robot wrist/end effector.
# The dynamic base_link -> tool0 transform should normally come from
# robot_state_publisher.
D405_PARENT_FRAME = "tool0"
D405_MOUNT_XYZ_RPY = {
    "x": 0.0,
    "y": 0.0,
    "z": 0.0,
    "roll": 0.0,
    "pitch": 0.0,
    "yaw": 0.0,
}


def make_realsense_node(
    *,
    camera_name: str,
    camera_namespace: str,
    serial_no: str,
    device_type: str,
    camera_parameters: dict[str, Any],
) -> Node:
    """Create one independently configured RealSense ROS 2 node."""
    common_parameters: dict[str, Any] = {
        # These parameters are used internally by the wrapper when constructing
        # frame IDs. Do not rely only on the ROS node name.
        "camera_name": camera_name,
        "camera_namespace": camera_namespace,

        # Device binding.
        "serial_no": serial_no,
        "device_type": device_type,

        # Basic image streams.
        "enable_depth": ENABLE_DEPTH,
        "enable_color": ENABLE_COLOR,
        "enable_infra": False,
        "enable_infra1": False,
        "enable_infra2": False,

        # Motion streams.
        "enable_accel": False,
        "enable_gyro": False,
        "enable_motion": False,
        "unite_imu_method": 0,

        # Processing blocks.
        "pointcloud.enable": ENABLE_POINTCLOUD,
        "align_depth.enable": ENABLE_ALIGN_DEPTH,
        "colorizer.enable": False,
        "spatial_filter.enable": False,
        "temporal_filter.enable": False,
        "decimation_filter.enable": False,
        "hole_filling_filter.enable": False,

        # Stream synchronization.
        "enable_sync": False,

        # Image topics are high-bandwidth sensor streams. Avoid the DDS system
        # default here: on Fast DDS it may resolve to RELIABLE/TRANSIENT_LOCAL,
        # which can back-pressure a camera publisher when a subscriber cannot
        # keep up. SENSOR_DATA is BEST_EFFORT/VOLATILE with a small queue.
        "color_qos": "SENSOR_DATA",
        "color_info_qos": "SENSOR_DATA",
        "depth_qos": "SENSOR_DATA",
        "depth_info_qos": "SENSOR_DATA",

        # Device lifecycle and reconnect behavior.
        #
        # Avoid initial_reset=True for both devices because simultaneous USB
        # resets can make enumeration less predictable.
        "initial_reset": False,
        "wait_for_device_timeout": 10.0,
        "reconnect_timeout": 6.0,

        # RealSense sensor-tree TFs, such as:
        # d405_link -> d405_depth_frame -> d405_depth_optical_frame
        "publish_tf": True,
        "tf_publish_rate": 0.0,

        # Diagnostics.
        "diagnostics_period": DIAGNOSTICS_PERIOD,
    }

    common_parameters.update(camera_parameters)

    return Node(
        package="realsense2_camera",
        executable="realsense2_camera_node",
        namespace=camera_namespace,
        name=camera_name,
        output="screen",
        emulate_tty=True,
        parameters=[common_parameters],
    )


def make_static_transform_node(
    *,
    node_name: str,
    parent_frame: str,
    child_frame: str,
    transform: dict[str, float],
) -> Node:
    """Create a static TF publisher using the current named-argument syntax."""
    return Node(
        package="tf2_ros",
        executable="static_transform_publisher",
        name=node_name,
        output="screen",
        arguments=[
            "--x",
            str(transform["x"]),
            "--y",
            str(transform["y"]),
            "--z",
            str(transform["z"]),
            "--roll",
            str(transform["roll"]),
            "--pitch",
            str(transform["pitch"]),
            "--yaw",
            str(transform["yaw"]),
            "--frame-id",
            parent_frame,
            "--child-frame-id",
            child_frame,
        ],
    )


def generate_launch_description() -> LaunchDescription:
    # A 640x480 RGB8 frame is 921,600 bytes, larger than Fast DDS 2.6's
    # default 512 KiB SHM segment. Give camera publishers enough shared memory
    # to transport several color/depth samples without falling back to UDP.
    fastdds_profile = SetEnvironmentVariable(
        name="FASTRTPS_DEFAULT_PROFILES_FILE",
        value=PathJoinSubstitution([
            FindPackageShare("dual_realsense_launch"),
            "config",
            "fastdds_large_data.xml",
        ]),
    )

    # -----------------------------------------------------------------------
    # D455: fixed/global camera
    # -----------------------------------------------------------------------

    d455_node = make_realsense_node(
        camera_name=D455_NAME,
        camera_namespace=D455_NAMESPACE,
        serial_no=D455_SERIAL,
        device_type="d455",
        camera_parameters={
            "depth_module.depth_profile": DEPTH_PROFILE,
            "depth_module.depth_format": "Z16",

            # D455 has a separate RGB camera.
            "rgb_camera.color_profile": COLOR_PROFILE,
            "rgb_camera.color_format": "RGB8",
            "rgb_camera.enable_auto_exposure": True,

            "enable_accel": ENABLE_D455_IMU,
            "enable_gyro": ENABLE_D455_IMU,
            "unite_imu_method": 2 if ENABLE_D455_IMU else 0,
        },
    )

    # -----------------------------------------------------------------------
    # D405: wrist camera
    # -----------------------------------------------------------------------

    d405_node = make_realsense_node(
        camera_name=D405_NAME,
        camera_namespace=D405_NAMESPACE,
        serial_no=D405_SERIAL,
        device_type="d405",
        camera_parameters={
            "depth_module.depth_profile": DEPTH_PROFILE,
            "depth_module.depth_format": "Z16",

            # D405 color is part of the depth module, not rgb_camera.
            "depth_module.color_profile": COLOR_PROFILE,
            "depth_module.color_format": "RGB8",
            "depth_module.enable_auto_exposure": True,
        },
    )

    delayed_d405_node = TimerAction(
        period=D405_START_DELAY_SECONDS,
        actions=[d405_node],
    )

    actions = [
        fastdds_profile,

        # Start D455 first.
        d455_node,

        # Start D405 after D455 initialization has settled.
        delayed_d405_node,
    ]

    # Do not publish fabricated zero transforms by default.
    # Enable only after replacing the XYZ/RPY values with calibration results.
    if PUBLISH_CAMERA_MOUNT_TF:
        d455_mount_tf = make_static_transform_node(
            node_name="base_to_d455_tf",
            parent_frame=D455_PARENT_FRAME,
            child_frame=f"{D455_NAME}_link",
            transform=D455_MOUNT_XYZ_RPY,
        )

        d405_mount_tf = make_static_transform_node(
            node_name="tool_to_d405_tf",
            parent_frame=D405_PARENT_FRAME,
            child_frame=f"{D405_NAME}_link",
            transform=D405_MOUNT_XYZ_RPY,
        )

        actions.extend([
            d455_mount_tf,
            d405_mount_tf,
        ])

    return LaunchDescription(actions)
