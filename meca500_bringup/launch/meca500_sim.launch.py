import os

from ament_index_python.packages import get_package_share_directory

from launch import LaunchDescription
from launch.actions import (
    DeclareLaunchArgument,
    ExecuteProcess,
    IncludeLaunchDescription,
)
from launch.conditions import UnlessCondition
from launch.actions import ExecuteProcess
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.event_handlers import OnProcessExit
from launch.actions import RegisterEventHandler, TimerAction

from launch.substitutions import (
    Command,
    FindExecutable,
    LaunchConfiguration,
    PathJoinSubstitution,
)

from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    meca500_description_share = get_package_share_directory("meca500_description")
    meca500_description_parent = os.path.dirname(meca500_description_share)

    world_arg = DeclareLaunchArgument(
        "world",
        default_value="empty.sdf",
        description="Gazebo world file",
    )

    alone_arg = DeclareLaunchArgument(
        "alone",
        default_value="true",
        description=(
                "false = Robot + Beckhoff PLC"
        ),
    )

    gz_sim_resource_path = os.pathsep.join(
        filter(None, [meca500_description_parent, os.environ.get("GZ_SIM_RESOURCE_PATH", "")])
    )

    ign_gazebo_resource_path = os.pathsep.join(
        filter(None, [meca500_description_parent, os.environ.get("IGN_GAZEBO_RESOURCE_PATH", "")])
    )

    gz_sim_system_plugin_path = os.pathsep.join(
        filter(None, ["/opt/ros/kilted/lib", os.environ.get("GZ_SIM_SYSTEM_PLUGIN_PATH", "")])
    )

    ign_gazebo_system_plugin_path = os.pathsep.join(
        filter(None, ["/opt/ros/kilted/lib", os.environ.get("IGN_GAZEBO_SYSTEM_PLUGIN_PATH", "")])
    )

    robot_description_content = Command([FindExecutable(name="xacro")," ",
            PathJoinSubstitution([
                    FindPackageShare("meca500_description"),
                    "urdf",
                    "meca500.urdf.xacro",])," ","sim_mode:=true"," ","name:=DummyBot",])
    robot_description = {"robot_description": ParameterValue(robot_description_content, value_type=str)}



    gazebo = ExecuteProcess(
        cmd=["gz", "sim", "-s", LaunchConfiguration("world"), "-r"],
        output="screen",
        additional_env={
            "GZ_SIM_RESOURCE_PATH": gz_sim_resource_path,
            "IGN_GAZEBO_RESOURCE_PATH": ign_gazebo_resource_path,
            "GZ_SIM_SYSTEM_PLUGIN_PATH": gz_sim_system_plugin_path,
            "IGN_GAZEBO_SYSTEM_PLUGIN_PATH": ign_gazebo_system_plugin_path,
        },
    )

    clock_bridge = Node(
        package="ros_gz_bridge",
        executable="parameter_bridge",
        arguments=["/clock@rosgraph_msgs/msg/Clock[gz.msgs.Clock"],
        output="screen",
        parameters=[{"use_sim_time": True}],
    )

    robot_state_publisher = Node(
        package="robot_state_publisher",
        executable="robot_state_publisher",
        name="meca500_state_publisher",
        output="both",
        parameters=[robot_description, {"use_sim_time": True}],
    )

    spawn_robot = Node(
        package="ros_gz_sim",
        executable="create",
        arguments=["-name", "meca500", "-topic", "robot_description"],
        output="screen",
    )

    sim_joint_state_broadcaster = Node(
        package="controller_manager",
        executable="spawner",
        arguments=["joint_state_broadcaster", "--controller-manager", "/sim_controller_manager"],
        parameters=[{"use_sim_time": True}],
        output="screen",
    )

    sim_velocity_controller = Node(
        package="controller_manager",
        executable="spawner",
        arguments=["meca_velocity_controller", "--controller-manager", "/sim_controller_manager"],
        parameters=[{"use_sim_time": True}],
        output="screen",
    )

    spawn_sim_controllers = RegisterEventHandler(
        event_handler=OnProcessExit(
            target_action=spawn_robot,
            on_exit=[TimerAction(period=2.0, actions=[sim_joint_state_broadcaster])],
        )
    )

    spawn_sim_velocity_controller = RegisterEventHandler(
        event_handler=OnProcessExit(
            target_action=sim_joint_state_broadcaster,

            on_exit=[
                sim_velocity_controller,
            ],
        )
    )

    beckhoff_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            PathJoinSubstitution(
                [
                    FindPackageShare("meca500_bringup"),
                    "launch",
                    "meca500_beckhoff.launch.py",
                ]
            )
        ),
        condition=UnlessCondition(LaunchConfiguration("alone")),
        launch_arguments={"name": "Meca500PLC"}.items(),
    )

    return LaunchDescription([
        world_arg,
        alone_arg,
        gazebo,
        clock_bridge,
        robot_state_publisher,
        spawn_robot,
        spawn_sim_controllers,
        spawn_sim_velocity_controller,
        beckhoff_launch,
    ])