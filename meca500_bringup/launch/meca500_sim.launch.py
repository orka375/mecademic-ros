from launch import LaunchDescription
from launch.actions import (
    DeclareLaunchArgument,
    ExecuteProcess,
    RegisterEventHandler,
    TimerAction,
)
from launch.event_handlers import OnProcessExit
from launch.substitutions import Command, FindExecutable, LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():

    world_arg = DeclareLaunchArgument(
        "world",
        default_value="empty.sdf",
        description="Gazebo world file to load",
    )
    
    alone_arg = DeclareLaunchArgument(
        "alone",
        default_value="true",
        description="Robot standalone (true) or connected to PLC (false)"
    )

    # Robot description built with simulation hardware plugin selected
    robot_description_content = Command([
        FindExecutable(name="xacro"), " ",
        PathJoinSubstitution(
            [FindPackageShare("meca500_description"), "urdf", "meca500.urdf.xacro"]
        ),
        " sim_mode:=true",
        " alone:=", LaunchConfiguration("alone"),
    ])
    robot_description = {
        "robot_description": ParameterValue(robot_description_content, value_type=str)
    }

    # 1. Start Gazebo Ignition (server-only mode to avoid GUI library conflicts)
    gazebo = ExecuteProcess(
        cmd=["gz", "sim", "-s", LaunchConfiguration("world"), "-r"],
        output="screen",
    )

    # 2. Gazebo-ROS bridge for clock synchronization
    clock_bridge = Node(
        package="ros_gz_bridge",
        executable="parameter_bridge",
        arguments=["/clock@rosgraph_msgs/msg/Clock[gz.msgs.Clock"],
        output="screen",
        parameters=[{"use_sim_time": True}],
    )

    # 3. Robot state publisher (uses sim time from /clock)
    robot_state_publisher = Node(
        package="robot_state_publisher",
        executable="robot_state_publisher",
        output="both",
        parameters=[robot_description, {"use_sim_time": True}],
    )

    # 4. Spawn robot entity; Gazebo converts /robot_description URDF → SDF automatically
    spawn_robot = Node(
        package="ros_gz_sim",
        executable="create",
        arguments=["-name", "meca500", "-topic", "robot_description"],
        output="screen",
    )

    # 5. Controller spawners — delayed until spawn_robot exits (robot loaded into sim)
    #    An extra 2 s timer gives the embedded gz_ros2_control plugin time to initialise
    #    the controller_manager before the spawners try to connect.
    joint_state_broadcaster_spawner = Node(
        package="controller_manager",
        executable="spawner",
        arguments=[
            "joint_state_broadcaster",
            "--controller-manager", "/controller_manager",
        ],
        parameters=[{"use_sim_time": True}],
    )

    velocity_controller_spawner = Node(
        package="controller_manager",
        executable="spawner",
        arguments=[
            "meca_velocity_controller",
            "--controller-manager", "/controller_manager",
        ],
        parameters=[{"use_sim_time": True}],
    )

    spawn_controllers = RegisterEventHandler(
        event_handler=OnProcessExit(
            target_action=spawn_robot,
            on_exit=[
                TimerAction(
                    period=2.0,
                    actions=[joint_state_broadcaster_spawner],
                )
            ],
        )
    )

    spawn_velocity_controller = RegisterEventHandler(
        event_handler=OnProcessExit(
            target_action=joint_state_broadcaster_spawner,
            on_exit=[velocity_controller_spawner],
        )
    )

    return LaunchDescription([
        world_arg,
        alone_arg,
        gazebo,
        clock_bridge,
        robot_state_publisher,
        spawn_robot,
        spawn_controllers,
        spawn_velocity_controller,
    ])
