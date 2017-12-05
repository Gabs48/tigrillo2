 

"""
This file contains all other methods
"""

import ast
from collections import deque
import copy
import rospy as ros
import serial
import threading
import time


__author__ = "Gabriel Urbain" 
__copyright__ = "Copyright 2017, Human Brain Projet, SP10"

__license__ = "MIT" 
__version__ = "2.0" 
__maintainer__ = "Gabriel Urbain"
__email__ = "gabriel.urbain@ugent.be" 
__status__ = "Research" 
__date__ = "September 11th, 2017"


MAX_BUFFER_SIZE = 100


class UARTDaemon(threading.Thread):
    """
    This UART daemon monitors the use of a serial IO channel and store all receeeived
    data in a buffer for asynchronous usage
    """

    def __init__(self, port, baud):

        super(UARTDaemon, self).__init__()

        self.port = port
        self.baud = baud
        self.conn = None

        self.data_buffer = deque([])
        self.ack_buffer = deque([])

        self.stop = True
        self.read_period = 0.0001
        self.daemon = True

    def start(self):
        """ Initialize and configure serial port """

        self.conn = serial.Serial(self.port, self.baud)
        if not self.conn.isOpen():
            self.conn.open()

        self.stop = False
        super(UARTDaemon, self).start()

    def stop(self):
        """ Raise a stop flag to stop the daemon """

        self.stop = True
        self.conn.close()

    def _add_data(self, data):
        """ Add a data line in the uart buffer """
        print "aaaaa"

        if "Previous Time Stamp" and "Time Stamp" and "End of Reading Time Stamp" in data:
            ts = float(data["Time Stamp"]) / 1000000
            eor = float(data["End of Reading Time Stamp"]) / 1000000
            pts = float(data["Previous Time Stamp"]) / 1000000
            data["UART IO Time"] = eor - ts
            data["UART Time Stamp"] = ts
            data["UART Loop Time"] = ts - pts
            del data["End of Reading Time Stamp"]
            del data["Previous Time Stamp"]
            del data["Time Stamp"]

        self.data_buffer.append(data)
        if len(self.data_buffer) > MAX_BUFFER_SIZE:
            self.data_buffer.popleft()

    def _add_ack(self, ack):
        """ Add a ack line in the uart buffer """

        # TODO: PRINT IF ACK FAILED
        self.ack_buffer.append(ack)
        if len(self.ack_buffer) > MAX_BUFFER_SIZE:
            self.ack_buffer.popleft()

    def read_data(self):
        """ Read the last data line in the uart buffer """

        if self.data_buffer:
            return self.data_buffer.pop()

    def read_r_ack(self):
        """ Read the last rst ack line in the uart buffer """

        if self.ack_buffer:
            for a in self.ack_buffer:
                if a["Instruction"] == 'R':
                    ack = {"success": True, "msg": a["Data"]}
                    if not "success" in a["Data"].lower():
                        ack["success"] = False
                    self.ack_buffer.remove(a)
                    return ack
        else:
            return {"success": False, "msg": "No ACK reveived!"}

    def read_f_ack(self):
        """ Read the last frequency ack line in the uart buffer """

        print self.ack_buffer
        if self.ack_buffer:
            for a in self.ack_buffer:
                if a["Instruction"] == 'F':
                    ack = {"success": True, "msg": a["Data"]}
                    if not "success" in a["Data"].lower():
                        ack["success"] = False
                    self.ack_buffer.remove(a)
                    return ack
        else:
            return {"success": False, "msg": "No ACK reveived!"}

    def write(self, line):
        """ Write a line in the uart channel"""

        self.conn.write(line)
        self.conn.flush()

    def run(self):
        """ Read and populate the buffer"""

        while not self.stop:
            line = self.conn.readline()
            dico = dict()
            try:
                dico = ast.literal_eval(line)
            except SyntaxError or ValueError:
                ros.logwarn("Malformed UART packet. Ignoring!")
                pass;

            if "DATA" in dico:
                self._add_data(dico["DATA"])
            if "ACK" in dico:
                self._add_ack(dico["ACK"])
            time.sleep(self.read_period)


if __name__ == "__main__":

    uart = UARTDaemon("/dev/ttyS0", 57600)
    uart.start()
    uart.write("F50000\n\r")
    time.sleep(20)
