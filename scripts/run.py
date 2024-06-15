#!/usr/bin/env python3.8

import rospy
from geometry_msgs.msg import Twist, PoseStamped, Point, Pose, Quaternion
from tf.transformations import euler_from_quaternion
import tf.transformations as tf
from visualization_msgs.msg import Marker
import cv2

from car import Car
from draw import Draw
from controllers import PID, MPC
from utils import *
from parameters import *

def rotate_pose_stamped_90_degrees_clockwise(pose_stamped):
    # Define the 90 degrees rotation around z-axis (clockwise)
    angle = -1.5708  # -90 degrees in radians (clockwise)
    
    # Create a quaternion from the z-axis rotation
    q = tf.quaternion_from_euler(0, 0, angle)
    
    # Rotate the orientation
    original_orientation = [
        pose_stamped.pose.orientation.x, 
        pose_stamped.pose.orientation.y, 
        pose_stamped.pose.orientation.z, 
        pose_stamped.pose.orientation.w
    ]
    new_orientation = tf.quaternion_multiply(q, original_orientation)
    
    # Rotate the position
    rotation_matrix = tf.quaternion_matrix(q)
    original_position = [
        pose_stamped.pose.position.x, 
        pose_stamped.pose.position.y, 
        pose_stamped.pose.position.z, 
        1.0
    ]
    new_position = rotation_matrix.dot(original_position)
    
    # Create a new PoseStamped with the rotated orientation and position
    rotated_pose_stamped = PoseStamped()
    rotated_pose_stamped.header = pose_stamped.header  # Keep the same header
    rotated_pose_stamped.pose.position.x = new_position[0]
    rotated_pose_stamped.pose.position.y = new_position[1]
    rotated_pose_stamped.pose.position.z = new_position[2]
    rotated_pose_stamped.pose.orientation = Quaternion(*new_orientation)
    
    return rotated_pose_stamped


def publish_waypoints_as_line():
    marker = Marker()
    marker.header.frame_id = "map"
    marker.header.stamp = rospy.Time.now()
    marker.ns = "waypoints"
    marker.id = 0
    marker.type = Marker.LINE_STRIP
    marker.action = Marker.ADD

    marker.scale.x = 0.1  # Line width

    marker.color.r = 1.0
    marker.color.g = 0.0
    marker.color.b = 0.0
    marker.color.a = 1.0
    pose = Pose()
    pose.position.x = 0
    pose.position.y = 0
    pose.position.z = 0
    pose.orientation.x = 0
    pose.orientation.y = 0
    pose.orientation.z = 0
    pose.orientation.w = 1
    marker.pose = pose
    point = Point()
    point.x = 0
    point.y = 0
    point.z = 0

    marker.points.append(point)
    for wp in way_points:
        
        point = Point()
        point.x = wp[0]
        point.y = wp[1]
        point.z = 0

        marker.points.append(point)
    
    marker_pub.publish(marker)

def goal_callback(pose):
    global way_points
    if pose.header.frame_id != 'camera_link':
        data = rotate_pose_stamped_90_degrees_clockwise(pose)
    else:
        data = pose
    x = data.pose.position.x
    y = data.pose.position.y
    orientation = data.pose.orientation
    orientation_list = [orientation.x, orientation.y, orientation.z, orientation.w]
    _, _, yaw = euler_from_quaternion(orientation_list)
    way_points.append([x, y, yaw])
    # rospy.loginfo(f"Received new goal: ({x}, {y}), {yaw}")

if __name__ == "__main__":
    # Initialize the ROS node
    rospy.init_node('car_controller', anonymous=True)
    cmd_vel_pub = rospy.Publisher('/cmd_vel', Twist, queue_size=10)
    marker_pub = rospy.Publisher('/waypoints_marker', Marker, queue_size=10)



    controller_name = "PID"

    if controller_name not in ["PID", "MPC"]:
        print("Invalid controller used. Available controllers: MPC and PID.")
        exit()

    print(f"Using {controller_name} Controller.")

    way_points = []
    # Subscribe to the /move_base_simple/goal topic
    rospy.Subscriber('/move_base_simple/goal', PoseStamped, goal_callback)
    # def add_waypoint(event, x, y, flags, param):
    #     global way_points
    #     if event == cv2.EVENT_LBUTTONDOWN:
    #         way_points.append([x, y])
    #     if event == cv2.EVENT_RBUTTONDOWN:
    #         way_points.pop()

    # draw = Draw(VIEW_W, VIEW_H, window_name="Canvas", mouse_callback=add_waypoint)

    car = Car(50, 50)

    if controller_name == "PID":
        controller = PID(kp_linear=0.5, kd_linear=0.1, ki_linear=0,
                        kp_angular=3, kd_angular=0.1, ki_angular=0)
    if controller_name == "MPC":
        controller = MPC(horizon=MPC_HORIZON)

    lw = 0
    rw = 0
    current_idx = 0
    linear_v = 0
    angular_v = 0
    car_path_points = []

    while not rospy.is_shutdown():
        # draw.clear()
        # draw.add_text("Press the right click to place a way point, press the left click to remove a way point", 
        #               color=(0, 0, 0), fontScale=0.5, thickness=1, org=(5, 20))
        # if len(way_points) > 0:
        #     draw.draw_path(way_points, color=(200, 200, 200), thickness=1)

        # if len(car_path_points) > 0:
        #     draw.draw_path(car_path_points, color=(255, 0, 0), thickness=1, dotted=True)

        # draw.draw(car.get_points(), color=(255, 0, 0), thickness=1)
        
        # k = draw.show()

        x, _ = car.get_state()
        if len(way_points) > 0 and current_idx != len(way_points):
            # print(way_points)
            # rospy.loginfo(way_points[current_idx])
            car_path_points.append([int(x[0, 0]), int(x[1, 0])])
            goal_pt = way_points[current_idx]

            if controller_name == "PID":
                linear_v, angular_v = controller.get_control_inputs(x, goal_pt, car.get_points()[2], current_idx)
            
            if controller_name == "MPC":
                linear_v, angular_v = controller.optimize(car=car, goal_x=goal_pt)
            
            dist = get_distance(x[0, 0], x[1, 0], goal_pt[0], goal_pt[1])
            print(dist)
            if dist < 0.1:
                print("Reached")
                current_idx += 1
        else:
            linear_v = 0
            angular_v = 0
        
        car.set_robot_velocity(linear_v, angular_v)
        # car.update(DELTA_T)

        # Publish linear_v and angular_v to /cmd_vel
        twist_msg = Twist()
        twist_msg.linear.x = linear_v
        twist_msg.angular.z = angular_v
        cmd_vel_pub.publish(twist_msg)
        publish_waypoints_as_line()

        # if k == ord("q"):
        #     break

        rospy.Rate(100).sleep()  # Loop at 10 Hz

