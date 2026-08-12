from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.actions import TimerAction

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
    name_arg = DeclareLaunchArgument(
        "name",
        default_value="Meca500PLC",
        description="Name of the Beckhoff ros2_control system",
    )

    beckhoff_robot_description_content = Command(
        [
            FindExecutable(name="xacro"),
            " ",
            PathJoinSubstitution(
                [
                    FindPackageShare("meca500_description"),
                    "urdf",
                    "meca500_beckhoff.urdf.xacro",
                ]
            ),
            " ",
            "name:=",
            LaunchConfiguration("name"),
        ]
    )
    beckhoff_robot_description = ParameterValue(beckhoff_robot_description_content, value_type=str)

    beckhoff_controller_manager = Node(
        package="controller_manager",
        executable="ros2_control_node",
        name="beckhoff_controller_manager",
        output="both",
        remappings=[("robot_description", "/beckhoff_robot_description")],
        parameters=[
            {"robot_description": beckhoff_robot_description},
            PathJoinSubstitution(
                [
                    FindPackageShare("meca500_bringup"),
                    "config",
                    "meca500_beckhoff_controllers.yaml",
                ]
            ),
        ],
    )

    # Publish a dedicated robot_description topic for the Beckhoff controller manager
    # to avoid consuming the simulation robot description from /robot_description.
    beckhoff_robot_description_publisher = Node(
        package="robot_state_publisher",
        executable="robot_state_publisher",
        name="beckhoff_robot_description_publisher",
        output="both",
        remappings=[("robot_description", "/beckhoff_robot_description")],
        parameters=[{"robot_description": beckhoff_robot_description}],
    )

    # beckhoff_gpio_controller = Node(
    #     package="controller_manager",
    #     executable="spawner",
    #     arguments=["gpio_controller", "--controller-manager", "/beckhoff_controller_manager"],
    #     output="screen",
    # )

    # beckhoff_gpio_state_broadcaster = Node(
    #     package="controller_manager",
    #     executable="spawner",
    #     arguments=["gpio_state_broadcaster", "--controller-manager", "/beckhoff_controller_manager"],
    #     output="screen",
    # )

    return LaunchDescription([
        name_arg,
        beckhoff_robot_description_publisher,
        beckhoff_controller_manager,
        # TimerAction(period=2.0, actions=[beckhoff_gpio_controller, beckhoff_gpio_state_broadcaster]),
    ])