from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch_ros.actions import Node
from launch.substitutions import Command, PathJoinSubstitution, LaunchConfiguration
from launch_ros.substitutions import FindPackageShare

def generate_launch_description():
    
    # Declare launch arguments
    robot_ip_arg = DeclareLaunchArgument(
        "robot_ip",
        default_value="192.168.0.100",
        description="IP address of the Meca500 robot"
    )
    
    sim_mode_arg = DeclareLaunchArgument(
        "sim_mode",
        default_value="false",
        description="Simulation mode: true for simulation, false for real hardware"
    )
    
    alone_arg = DeclareLaunchArgument(
        "alone",
        default_value="true",
        description="Robot standalone (true) or connected to PLC (false)"
    )
    
    # 1. Process the URDF/Xacro (Simplified to avoid the TextSubstitution error)
    robot_description_content = Command([
        "xacro ",
        PathJoinSubstitution([FindPackageShare("meca500_description"), "urdf", "meca500.urdf.xacro"]),
        " robot_ip:=", LaunchConfiguration("robot_ip"),
        " sim_mode:=", LaunchConfiguration("sim_mode"),
        " alone:=", LaunchConfiguration("alone"),
    ])
    robot_description = {"robot_description": robot_description_content}

    # 2. Path to the controller parameters
    robot_controllers = PathJoinSubstitution([
        FindPackageShare("meca500_bringup"), "config", "meca500_controllers.yaml"
    ])

    # 3. Start the ROS 2 Controller Manager
    control_node = Node(
        package="controller_manager",
        executable="ros2_control_node",
        parameters=[robot_description, robot_controllers],
        output="both",
    )

    # 4. Start the Robot State Publisher
    robot_state_pub_node = Node(
        package="robot_state_publisher",
        executable="robot_state_publisher",
        output="both",
        parameters=[robot_description],
    )

    # 5. Spawn the Joint State Broadcaster
    joint_state_broadcaster_spawner = Node(
        package="controller_manager",
        executable="spawner",
        arguments=["joint_state_broadcaster", "--controller-manager", "/controller_manager"],
    )

    # 6. Spawn your custom Velocity Controller
    meca_velocity_controller_spawner = Node(
        package="controller_manager",
        executable="spawner",
        arguments=["meca_velocity_controller", "--controller-manager", "/controller_manager"],
    )

    return LaunchDescription([
        robot_ip_arg,
        sim_mode_arg,
        alone_arg,
        control_node,
        robot_state_pub_node,
        joint_state_broadcaster_spawner,
        meca_velocity_controller_spawner,
    ])