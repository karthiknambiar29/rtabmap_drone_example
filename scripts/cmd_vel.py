#!/usr/bin/env python3.8
import rospy
import math
import numpy as np
from geometry_msgs.msg import  Twist
from mavros_msgs.msg import State, ManualControl, OverrideRCIn
from mavros_msgs.srv import CommandBool, SetMode, SetModeRequest



class Controller:
    def __init__(self):
        rospy.init_node("controller", anonymous=True)
        # Parameters for the differential drive rover
        self.MAX_PWM = 1900
        self.MIN_PWM = 1100
        self.STOP_PWM = 1500
        self.MAX_LINEAR_VEL = 1.0  # Maximum linear velocity (m/s)
        self.MAX_ANGULAR_VEL = 1.0  # Maximum angular velocity (rad/s)
        self.rate = rospy.Rate(100)
        self.current_state = State()
        self.subscriber = rospy.Subscriber('/cmd_vel', Twist, self.callback)

        self.manual_pub = rospy.Publisher(
            "/mavros/manual_control/send", ManualControl, queue_size=10
        )
        self.arming_client = rospy.ServiceProxy("/mavros/cmd/arming", CommandBool)
        self.set_mode_client = rospy.ServiceProxy("/mavros/set_mode", SetMode)
        self.rc_pub = rospy.Publisher(
            "/mavros/rc/override", OverrideRCIn, queue_size=10
        )

        self.current_state.connected = False
        self.current_state.armed = False
        self.current_state.mode = "MANUAL"
        
    def callback(self, data):
        # Extract linear and angular velocities from cmd_vel
        linear_vel_x = data.linear.x
        # linear_vel_y = msg.linear.y
        # linear_vel_z = msg.linear.z
        
        angular_vel = data.angular.z

        # Convert velocities to PWM values
        throttle, steering = controller.map_velocity_to_pwm(linear_vel_x, angular_vel)
        print(throttle, steering)
        controller.RC_channel_override(steering, throttle)
      
        # Process data received from input_topic
        # self.send_manual_control(data.linear.x, data.linear.y, data.linear.z, data.angular.z)


    def connect(self):
        print(self.current_state)
        rospy.loginfo("Waiting for FCU connection...")
        while not self.current_state.connected:
            self.rate.sleep()
        rospy.loginfo("Connected")

    def arm(self):
        rospy.loginfo("Arming...")
        while not self.current_state.armed:
            self.arming_client(True)
            self.rate.sleep()
        rospy.loginfo("Armed")

    def state_cb(self, msg):
        self.current_state.connected = msg.connected
        self.current_state.armed = msg.armed
        self.current_state.mode = msg.mode

    def send_manual_control(self, x, y, z, r):
        msg = ManualControl()
        msg.x = np.clip(-x*11000, -1100, 1100)
        msg.y = np.clip(-y*11000, -1100, 1100)
        msg.z = np.clip(-z*11000, -1100, 1100)
        msg.r = np.clip(-r*11000, -1100, 1100)
        rospy.loginfo(f"{msg.x}, {msg.y}, {msg.z}, {msg.r}")
        self.manual_pub.publish(msg)

    def RC_channel_override(self, left, right):
        msg = OverrideRCIn()
        # make all channels 2000

        for i in range(0, 16):
            msg.channels[i] = 65535
        msg.channels[0] = left
        msg.channels[1] = 65535
        msg.channels[2] = right
        msg.channels[3] = 65535

        self.rc_pub.publish(msg)

    def map_velocity_to_pwm(self, linear_vel, angular_vel):
        if linear_vel > 0:
            throttle_pwm = self.STOP_PWM + (linear_vel / self.MAX_LINEAR_VEL) * (self.MAX_PWM - self.STOP_PWM)
        else:
            throttle_pwm = self.STOP_PWM + (linear_vel / self.MAX_LINEAR_VEL) * (self.STOP_PWM - self.MIN_PWM)
        throttle_pwm = int(max(self.MIN_PWM, min(self.MAX_PWM, throttle_pwm)))
        steering_pwm = self.STOP_PWM + (angular_vel / self.MAX_ANGULAR_VEL) * (self.MAX_PWM - self.STOP_PWM)
        steering_pwm = int(max(self.MIN_PWM, min(self.MAX_PWM, steering_pwm)))
        return throttle_pwm, steering_pwm
    def convert_velocity_yaw_to_pwm(forward_velocity, yaw_rate, base_pwm=1900, k=800, pwm_min=1100, pwm_max=1900):
        """
        Convert forward velocity and yaw rate to PWM values for left and right motors.

        Parameters:
        forward_velocity (float): Forward velocity (V) of the robot.
        yaw_rate (float): Yaw rate (ω) of the robot.
        base_pwm (int, optional): Base PWM value for straight movement. Default is 1900.
        k (int, optional): Scaling factor for converting yaw rate to PWM difference. Default is 800.
        pwm_min (int, optional): Minimum PWM value. Default is 1100.
        pwm_max (int, optional): Maximum PWM value. Default is 1900.

        Returns:
        tuple: PWM values for the left and right motors.
        """
        # Calculate PWM values based on forward velocity and yaw rate
        left_pwm = base_pwm - k * yaw_rate
        right_pwm = base_pwm + k * yaw_rate

        # Ensure PWM values are within the allowed range
        left_pwm = max(pwm_min, min(left_pwm, pwm_max))
        right_pwm = max(pwm_min, min(right_pwm, pwm_max))

        return int(left_pwm), int(right_pwm)


if __name__ == "__main__":
    rospy.init_node("controller", anonymous=True)
    # set rate
    rate = rospy.Rate(100)
    controller = Controller()
    rospy.Subscriber("/mavros/state", State, controller.state_cb)

    print("Waiting for FCU connection...")

    controller.connect()
    # controller.RC_channel_override(1900, 1900)
    
    # controller.send_manual_control(0, 0, 0, 0)
    

    controller.set_mode_client(0, "MANUAL")
    print("Arming...")
    controller.arm()

    while not rospy.is_shutdown():
        # throttle, steering = controller.map_velocity_to_pwm(-1, 1)
        # controller.RC_channel_override(steering, throttle)
        # if controller.current_state.mode != "STABILIZED":
        #     print(contr)
        #     if controller.set_mode_client.call(SetModeRequest(custom_mode="STABILIZED")).mode_sent:
        #         rospy.loginfo("STABILIZED enabled")
        # controller/annel_override(1900, 1900)
        
        controller.rate.sleep()


