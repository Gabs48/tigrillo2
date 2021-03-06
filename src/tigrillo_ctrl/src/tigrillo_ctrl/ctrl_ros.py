
import json
import rospy as ros
import time
from std_msgs.msg import String
from std_srvs.srv import Trigger
#from sensor_msgs.msg import Imu

from tigrillo_ctrl.srv import Frequency, FrequencyResponse
from tigrillo_ctrl.msg import Sensors, Motors, Imu
from tigrillo_ctrl import utils


__author__ = "Gabriel Urbain" 
__copyright__ = "Copyright 2017, Human Brain Projet, SP10"

__license__ = "MIT" 
__version__ = "2.0" 
__maintainer__ = "Gabriel Urbain"
__email__ = "gabriel.urbain@ugent.be" 
__status__ = "Research" 
__date__ = "November 25th, 2017"



class CTRLROS():

    def __init__(self):
        
        self.node_name = "tigrillo"
        self.uart_pub_name = "tigrillo_rob/uart_actuators"
        self.uart_sub_name = "tigrillo_rob/uart_sensors"
        self.sim_imu_name = "tigrillo_rob/sim_imu_sensors"
        self.i2c_sub_name = "tigrillo_rob/i2c_sensors"
        self.i2c_srv_freq_name = "i2c_set_sens_freq"
        self.i2c_srv_cal_name = "i2c_save_cal"
        self.uart_srv_freq_name = "uart_set_sens_freq"
        self.uart_srv_cal_name = "i2c_save_cal"

        self.queue_size = utils.ROS_QUEUE_SIZE

        self.uart_pub = None
        self.uart_sub = None
        self.i2c_sub = None
        self.i2c_srv_freq = None
        self.i2c_srv_cal = None
        self.uart_srv_freq = None
        self.uart_srv_cal = None
        self.imu_sub = None

        self.uart_sensors = dict()
        self.uart_actuators = dict()
        self.i2c_sensors = dict()
        self.sensors = dict()

    def update_actuators(self, update, t_run):

        ros.logdebug("UART actuator update sent: " + str(update))

        self.uart_pub.publish(run_time=t_run, FL=update[0], FR=update[1], BL=update[2], BR=update[3])

    def get_last_sensors(self):

        if "Run Time" in self.uart_sensors:
            self.uart_sensors["UART Run Time"] = self.uart_sensors["Run Time"]
            del self.uart_sensors["Run Time"]
        if "Run Time" in self.i2c_sensors:
            self.i2c_sensors["I2C Run Time"] = self.i2c_sensors["Run Time"]
            del self.i2c_sensors["Run Time"]

        self.sensors = self.uart_sensors.copy()
        self.sensors.update(self.i2c_sensors)

        return self.sensors 

    def reset_sensor_calibration(self):

        try:
            ack_cal_i2c = self.i2c_srv_cal()
            ack_cal_uart = self.uart_srv_cal()

            if  ack_cal_i2c["success"] and ack_cal_uart["success"]:
                ros.logwarn("UART and I2C sensors properly calibrated!")
            else:
                ros.logerr("Sensors calibration failed with UART message: " + ack_cal_uart["msg"] +
                           " and I2C message: " + ack_cal_i2c["msg"])

        except ros.ServiceException as exc:
            ros.logerr("Service did not process request: " + str(exc))
            pass

    def set_sensors_frequency(self, frequency):

        try:
            ack_freq_uart = self.uart_srv_freq(frequency)
            ack_freq_i2c = self.i2c_srv_freq(frequency)

            if ack_freq_i2c.success and ack_freq_uart.success:
                ros.logwarn("UART and I2C sensors frequency properly changed!")
            else:
                ros.logerr("Setting sensors frequency failed with UART message: " + ack_freq_uart.msg +
                           " and I2C message: " + ack_freq_i2c.msg)

        except ros.ServiceException as exc:
            ros.logerr("Service did not process request: " + str(exc))
            pass

    def __uart_ros_sub(self, msg):

        self.uart_sensors = {"Front Right": msg.FR, "Front Left": msg.FL, "Back Right": msg.BR, 
                             "Back Left": msg.BL, "Run Time": msg.run_time, "UART IO Time": msg.io_time,
                             "UART Loop Time": msg.loop_time, "UART Time Stamp": msg.ocm_time}

        ros.logdebug("UART sensor update received: " + str(self.uart_sensors))

    def __i2c_ros_sub(self, msg):

        self.i2c_sensors =  {"Acc X": msg.acc_x, "Acc Y": msg.acc_y, "Acc Z": msg.acc_z, 
                             "Grav X": msg.grav_x, "Grav Y": msg.grav_y, "Grav Z": msg.grav_z,
                             "H": msg.h, "R": msg.r,  "P": msg.p, "Cal Sys": msg.cal_sys,
                             "Cal Acc": msg.cal_acc, "Cal Gyro": msg.cal_gyro, "Cal Mag": msg.cal_mag,  
                             "I2C IO Time": msg.io_time, "Run Time": msg.run_time, "I2C Timestamp": msg.time_stamp}

        ros.logdebug("I2C sensor update received: " + str(self.i2c_sensors))


    def __imu_ros_sub(self, msg):

        self.i2c_sensors =  {"Acc X": msg.linear_acceleration.x, "Acc Y": msg.linear_acceleration.y, 
                             "Acc Z": msg.linear_acceleration.z, "H": msg.orientation.x, 
                             "R": msg.orientation.y,  "P": msg.orientation.z,  
                             "Run Time": msg.header.stamp.secs}

        ros.logdebug("I2C sensor update received: " + str(self.i2c_sensors))

    def start(self):

        ros.init_node(self.node_name, log_level=ros.INFO)
        self.uart_pub = ros.Publisher(self.uart_pub_name, Motors, queue_size=self.queue_size)
        self.uart_sub = ros.Subscriber(self.uart_sub_name, Sensors, callback=self.__uart_ros_sub, queue_size=self.queue_size)

        # Comment one of the two for simulation or real robot
        self.i2c_sub = ros.Subscriber(self.i2c_sub_name, Imu, callback=self.__i2c_ros_sub, queue_size=self.queue_size)
        #self.mu_sub = ros.Subscriber(self.sim_imu_name, Imu, callback=self.__imu_ros_sub, queue_size=self.queue_size)

        # try:
        #     ros.wait_for_service(self.i2c_srv_freq_name, timeout=2)
        #     ros.wait_for_service(self.i2c_srv_cal_name, timeout=2)
        #     ros.wait_for_service(self.uart_srv_freq_name, timeout=2)
        #     ros.wait_for_service(self.uart_srv_cal_name, timeout=2)

        # except ros.exceptions.ROSException as exc:
        #     ros.logerr(str(exc) + " ! Please, check that the UART and I2C nodes are started on the ROS network")
        #     pass

        self.i2c_srv_freq = ros.ServiceProxy(self.i2c_srv_freq_name, Frequency)
        self.i2c_srv_cal = ros.ServiceProxy(self.i2c_srv_cal_name, Trigger)
        self.uart_srv_freq = ros.ServiceProxy(self.uart_srv_freq_name, Frequency)
        self.uart_srv_cal = ros.ServiceProxy(self.uart_srv_cal_name, Trigger)


if __name__ == '__main__':

    c = CTRLROS()
    c.start()