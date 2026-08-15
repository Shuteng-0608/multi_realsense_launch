# Dual RealSense Launch

这是一个用于同时启动 Intel RealSense D405 和 D455 的 ROS 2 Humble
启动包。当前配置发布 640×480、30 Hz 的彩色图和深度图，并通过
`compressed_image_transport` 提供 JPEG 压缩彩色图像。

## 当前相机配置

| 相机 | 序列号 | 彩色图配置 | 深度图配置 |
| --- | --- | --- | --- |
| D405 | `260322275294` | RGB8，640×480@30 Hz | Z16，640×480@30 Hz |
| D455 | `261822304024` | RGB8，640×480@30 Hz | Z16，640×480@30 Hz |

主要彩色图话题：

```text
/d405/d405/color/image_raw
/d405/d405/color/image_raw/compressed
/d455/d455/color/image_raw
/d455/d455/color/image_raw/compressed
```

压缩话题的消息类型为 `sensor_msgs/msg/CompressedImage`。当前插件默认使用
JPEG、质量 95，发布端 QoS 为 Best Effort/Volatile。实测两路压缩彩色图均可
稳定达到约 30 Hz，解码后的尺寸为 640×480×3。

> JPEG 是有损压缩。解码后图像尺寸仍为 640×480，但像素值不会与原始
> RGB 图像逐像素完全一致。

## 推荐运行环境

- Ubuntu 22.04
- ROS 2 Humble
- `realsense2_camera` 4.58.2
- `librealsense` 2.58.2
- `compressed_image_transport` 2.5.5
- Fast DDS（Humble 默认 RMW 实现）

其他版本不一定不能使用，但 RealSense Wrapper 的参数名称和 DDS 行为可能存在
差异，迁移后应重新检查话题、QoS 和频率。

本文采用的安装路线与当前机器一致：

1. 在 Ubuntu 22.04 上通过 Debian 包安装 ROS 2 Humble；
2. RealSense 官方安装说明 Step 2 选择 **Option 2: Install librealsense2
   (without graphical tools and examples) debian package from ROS servers**；
3. Step 3 选择 **Option 1: Install debian package from ROS servers**；
4. 额外安装 JPEG 压缩图像传输插件；
5. 只编译本项目，不从源码重复编译 librealsense 或 RealSense ROS Wrapper。

对应的官方说明：

- [RealSense ROS Wrapper：Installation on Ubuntu](https://github.com/realsenseai/realsense-ros#installation-on-ubuntu)
- [ROS 2 Humble：Ubuntu Debian 包安装](https://docs.ros.org/en/humble/Installation/Ubuntu-Install-Debs.html)

> RealSense 官方明确要求：librealsense 的 RealSense 软件源 Debian 包、ROS
> 软件源 Debian 包和源码编译三种方式只能选择一种。本文使用 ROS 软件源中的
> `ros-humble-librealsense2*`，不要再安装另一份 RealSense 软件源版本，也不要
> 在工作空间里再次编译 librealsense，否则容易产生版本和工作空间冲突。

## 从一台全新的 Ubuntu 22.04 开始安装

### 第 1 步：安装 ROS 2 Humble

本项目选用：

- 操作系统：Ubuntu 22.04；
- ROS 版本：ROS 2 Humble。

ROS 2 的安装请直接按照官方文档完成：

- [ROS 2 Humble：Ubuntu Debian 包安装](https://docs.ros.org/en/humble/Installation/Ubuntu-Install-Debs.html)

### 第 2 步：从 ROS 软件源安装 librealsense2

这是 RealSense 官方安装页面 Step 2 的 Option 2。官方页面将该选项描述为
“without graphical tools and examples”：

```bash
sudo apt update
sudo apt install 'ros-humble-librealsense2*'
```

不同时间构建的 ROS Debian 包内容可能不同。当前测试环境中的
`ros-humble-librealsense2` 2.58.2 实际提供了 `realsense-viewer`，可以这样
确认：

```bash
command -v realsense-viewer
```

如果能找到，可以按需运行 `realsense-viewer` 检查设备、USB 连接和图像流；如果
找不到，也不影响本项目启动。本项目不依赖该 GUI，可以使用
`rs-enumerate-devices`、ROS 2 话题和节点日志完成全部必要检查。

> 使用 GUI 检查完毕后必须关闭 `realsense-viewer`，再启动 ROS 2 相机节点。
> 两者同时占用同一台相机时，ROS Wrapper 可能报告设备忙或无法启动数据流。

### 第 3 步：从 ROS 软件源安装 RealSense ROS 2 Wrapper

这是 RealSense 官方安装页面 Step 3 的 Option 1：

```bash
sudo apt install 'ros-humble-realsense2-*'
```

该命令会安装 ROS Wrapper、消息包和相机描述包，不需要再把
`realsense-ros` 仓库克隆到本工作空间中编译。

确认软件包可被 ROS 2 找到：

```bash
source /opt/ros/humble/setup.bash
ros2 pkg prefix realsense2_camera
ros2 pkg prefix realsense2_camera_msgs
```

正常情况下两条命令均应输出 `/opt/ros/humble`。

### 第 4 步：安装压缩图像和本项目所需依赖

```bash
sudo apt update
sudo apt install \
  ros-humble-image-transport \
  ros-humble-compressed-image-transport \
  ros-humble-tf2-ros \
  python3-colcon-common-extensions
```

确认压缩传输插件已经加载：

```bash
source /opt/ros/humble/setup.bash
ros2 run image_transport list_transports
```

输出中应同时包含：

```text
image_transport/compressed
image_transport/raw
```

如果缺少 `image_transport/compressed`，RealSense 节点仍能发布原始
`sensor_msgs/Image`，但不会生成 `/compressed` 话题。

### 第 5 步：连接并检查两台相机

连接 D405 和 D455 后，加载 ROS 环境并枚举设备：

```bash
source /opt/ros/humble/setup.bash
rs-enumerate-devices | grep -E "Name|Serial Number|Usb Type Descriptor"
```

应能看到两台相机，并且序列号与本项目配置一致：

```text
D405: 260322275294
D455: 261822304024
```

如果提示没有权限或找不到设备，先重新插拔相机，再确认安装命令没有报错。还可以
用下面的命令检查 Linux 是否已经识别 USB 设备：

```bash
lsusb
lsusb -t
```

两台相机都应工作在 `5000M` 或更高的 USB 3.x 链路，而不是 `480M`。

### 第 6 步：放置并构建本项目

将本包放入 ROS 2 工作空间的 `src` 目录，然后执行：

```bash
mkdir -p ~/tianji_ws/src
# 将 dual_realsense_launch 整个目录复制到 ~/tianji_ws/src/ 下
cd ~/tianji_ws
source /opt/ros/humble/setup.bash
colcon build --symlink-install --packages-select dual_realsense_launch
source install/setup.bash
```

启动文件通过 `FindPackageShare` 查找 Fast DDS 配置，不依赖当前用户名或固定的
工作空间绝对路径。

确认 ROS 2 找到的是刚刚构建的包：

```bash
ros2 pkg prefix dual_realsense_launch
```

输出应指向当前工作空间，例如：

```text
/home/<用户名>/tianji_ws/install/dual_realsense_launch
```

### 第 7 步：设置 ROS 2 通信环境

本项目当前约定使用 Domain ID 42：

```bash
export ROS_DOMAIN_ID=42
export ROS_LOCALHOST_ONLY=0
```

单机使用时也建议保持相同配置；跨机器通信时，两台电脑必须设置完全相同的
`ROS_DOMAIN_ID`。

如果这台电脑没有主动安装其他 RMW，ROS 2 Humble 默认使用 Fast DDS。不要在
启动前加载未经确认的其他 Fast DDS XML。

### 第 8 步：启动两台相机

先确认 `realsense-viewer` 和其他相机程序已经关闭，然后执行：

```bash
source /opt/ros/humble/setup.bash
source ~/tianji_ws/install/setup.bash
export ROS_DOMAIN_ID=42
export ROS_LOCALHOST_ONLY=0
ros2 launch dual_realsense_launch dual_rs.launch.py
```

启动后，日志中应该分别出现 D455 和 D405 的设备信息，并显示彩色图与深度图以
640×480@30 Hz 启动。D405 会在 D455 之后延迟 3 秒启动，这是正常行为。

### 第 9 步：验证话题、类型和帧率

保留相机启动终端，在另一个终端执行：

```bash
source /opt/ros/humble/setup.bash
source ~/tianji_ws/install/setup.bash
export ROS_DOMAIN_ID=42
export ROS_LOCALHOST_ONLY=0

ros2 topic type /d405/d405/color/image_raw/compressed
ros2 topic type /d455/d455/color/image_raw/compressed
```

两条命令都应输出：

```text
sensor_msgs/msg/CompressedImage
```

继续检查帧率：

```bash
ros2 topic hz /d405/d405/color/image_raw/compressed
ros2 topic hz /d455/d455/color/image_raw/compressed
```

每个命令持续观察至少 20～30 秒，平均频率应接近 30 Hz。两条 `hz` 命令需要在
两个不同终端中同时运行，才能检查两路压缩传输并发时的实际表现。

检查 QoS：

```bash
ros2 topic info /d405/d405/color/image_raw/compressed -v
ros2 topic info /d455/d455/color/image_raw/compressed -v
```

发布端应显示 `BEST_EFFORT` 和 `VOLATILE`。完成以上步骤后，两路相机即已成功
启动并以 JPEG 压缩格式发布彩色图像。

## 迁移到另一台电脑

### 1. 检查相机序列号

启动文件按照序列号绑定相机：

```python
D405_SERIAL = "_260322275294"
D455_SERIAL = "_261822304024"
```

如果搬过去的仍是同一对物理相机，无需调整。换成其他相机时，必须查询并更新
序列号：

```bash
rs-enumerate-devices | grep -E "Name|Serial Number"
```

序列号前面的下划线用于确保 ROS 2 将参数解析为字符串。

### 2. 检查 USB 连接速率

```bash
lsusb -t
```

两台相机都应显示在 `5000M` 或更高的 USB 3.x 链路上。如果显示为 `480M`，
说明相机工作在 USB 2.0，可能无法稳定发布当前配置的两路图像。

常见原因包括：

- 使用了只支持 USB 2.0 的 Type-C 线；
- 接入了 USB 2.0 接口；
- 使用了带宽不足或供电不稳定的 Hub；
- 两台相机共享带宽不足的上游 USB 控制器；
- USB autosuspend 或其他省电设置干扰设备。

### 3. 统一 ROS Domain

当前系统使用 `ROS_DOMAIN_ID=42`。参与通信的所有电脑必须使用相同的 Domain
ID，并允许非本机通信：

```bash
export ROS_DOMAIN_ID=42
export ROS_LOCALHOST_ONLY=0
```

这些变量没有写死在启动文件中，需要在每台电脑的终端、启动脚本或 shell 配置
中统一设置。如果一台机器使用 42、另一台使用默认值 0，双方看不到彼此的话题。

### 4. 检查 RMW 和 Fast DDS 环境变量

本包的 `config/fastdds_large_data.xml` 是 Fast DDS 配置。如果另一台电脑使用
Cyclone DDS，这份 XML 不会生效：

```bash
echo "$RMW_IMPLEMENTATION"
```

还应检查是否遗留了其他 Fast DDS 配置：

```bash
env | grep -E \
  '^(RMW_IMPLEMENTATION|RMW_FASTRTPS_USE_QOS_FROM_XML|FASTRTPS_DEFAULT_PROFILES_FILE|FASTDDS_DEFAULT_PROFILES_FILE)='
```

特别注意 `RMW_FASTRTPS_USE_QOS_FROM_XML=1`。它可能让外部 XML 中的 QoS 配置
影响 ROS 2 的话题行为。不要在未确认内容的情况下全局加载其他 Fast DDS XML。

### 5. 检查网络

跨机器传输建议使用千兆有线网络，并检查：

- 两台电脑处于同一网段；
- 防火墙允许 DDS 使用的 UDP 和组播通信；
- 交换机没有启用客户端隔离或组播隔离；
- VPN、Wi-Fi 和虚拟网卡没有让 DDS 选择错误的网络接口；
- 两端的 `ROS_DOMAIN_ID` 相同；
- `ROS_LOCALHOST_ONLY` 为 0。

可以使用 `iperf3` 检查两台电脑之间的实际带宽：

```bash
# 电脑 A
iperf3 -s

# 电脑 B
iperf3 -c <电脑A的IP地址> -t 20
```

千兆链路通常可以达到约 900～940 Mbit/s。还应交换客户端和服务端角色，检查
反方向带宽。

### 6. 检查 UDP 缓冲上限

Fast DDS XML 请求 1 MiB UDP 收发缓冲，但操作系统可能设置了更低的上限：

```bash
sysctl net.core.rmem_max
sysctl net.core.wmem_max
```

当前两路 JPEG 压缩彩色图载荷合计约 53 Mbit/s，通常不需要很大的缓冲；但在
恢复 raw 图像、提高分辨率、增加相机或网络产生突发流量时，较低的系统上限可能
导致 UDP 丢包。XML 中的请求值不会突破 Linux 的系统上限。

## QoS 要求

彩色图和压缩彩色图使用 Sensor Data QoS：

```text
Reliability: BEST_EFFORT
Durability: VOLATILE
```

远端自定义订阅节点也应使用 Best Effort/Sensor Data QoS。如果订阅端强制要求
Reliable，可能出现“能看到话题名称，但收不到任何消息”的现象。

检查发布端和订阅端 QoS：

```bash
ros2 topic info /d405/d405/color/image_raw/compressed -v
ros2 topic info /d455/d455/color/image_raw/compressed -v
```

ROS 2 Humble 自带的以下命令默认使用 Reliable 订阅，和当前压缩发布端不兼容：

```bash
ros2 run image_transport republish compressed raw
```

如果需要把压缩图重新发布为普通 `sensor_msgs/Image`，接收节点必须以 Best
Effort QoS 订阅 `CompressedImage`，再通过 `cv_bridge` 解码。例如：

```python
image = bridge.compressed_imgmsg_to_cv2(
    msg,
    desired_encoding="bgr8",
)
```

解码得到的 OpenCV 图像仍为 640×480。需要重新发布时，可以再通过
`cv_bridge.cv2_to_imgmsg()` 转成 `sensor_msgs/msg/Image`。

## 频率检查

启动相机后分别检查两路压缩彩色图：

```bash
ros2 topic hz /d405/d405/color/image_raw/compressed
ros2 topic hz /d455/d455/color/image_raw/compressed
```

注意：`ros2 topic hz` 显示的是测试进程实际收到的频率，可能受测试电脑 CPU、
网络、DDS 和 QoS 影响，不一定等同于相机发布端的真实频率。

如果本机是 30 Hz、远端只有约 10 Hz，按以下顺序排查：

1. 确认远端订阅的是 `/compressed`，不是 `/image_raw`；
2. 检查远端订阅 QoS 是否为 Best Effort；
3. 确认两端 `ROS_DOMAIN_ID` 相同；
4. 使用 `iperf3` 双向测试网络；
5. 检查防火墙、组播、VPN 和虚拟网卡；
6. 检查两端 Fast DDS/RMW 环境变量；
7. 检查 UDP 缓冲上限和系统负载。

## 已知限制

- 当前 `package.xml` 尚未完整声明 `ament_python`、`launch`、`launch_ros` 和
  `compressed_image_transport` 等依赖，因此新电脑不能只依赖 `rosdep` 自动补齐
  全部运行环境，应先按本文“安装依赖”章节安装相关 Debian 包；
- `setup.py` 与 `package.xml` 中的版本号、许可证和描述元数据尚未完全统一；
- 相机序列号、图像配置和启动延迟目前写在启动文件中，没有提供 launch
  arguments；
- D405 使用固定 3 秒延迟启动，但该延迟不会主动判断 D455 是否已经完成初始化；
- `wait_for_device_timeout` 为 10 秒，启动时设备长时间未出现，节点可能退出；
- 相机节点没有启用进程级 `respawn`，节点异常退出后不会由 launch 自动重启；
- 原始 `/image_raw` 话题仍然存在，远端误订阅 raw 会显著增加网络流量；
- JPEG 格式和质量 95 当前来自压缩插件默认值，没有在启动文件中显式固定；
- diagnostics 默认关闭，以减少查询对双相机稳定性的潜在影响；
- 相机安装 TF 默认关闭，必须完成实际外参标定后才能启用。

## 快速迁移检查表

- [ ] Ubuntu 22.04 和 ROS 2 Humble 已安装；
- [ ] `realsense2_camera` 与 `librealsense` 版本兼容；
- [ ] `compressed_image_transport` 已安装并可被发现；
- [ ] 相机序列号与启动文件一致；
- [ ] 两台相机均工作在 USB 3.x；
- [ ] 工作空间已重新构建并 source `install/setup.bash`；
- [ ] 所有电脑均使用 `ROS_DOMAIN_ID=42`；
- [ ] `ROS_LOCALHOST_ONLY=0`；
- [ ] 没有意外加载其他 Fast DDS XML；
- [ ] 防火墙、组播、VPN 和虚拟网卡已检查；
- [ ] 远端订阅 `/compressed` 并使用 Best Effort QoS；
- [ ] 两个压缩彩色图话题均实测接近 30 Hz。
