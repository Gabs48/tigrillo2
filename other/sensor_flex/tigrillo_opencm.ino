/* Tigrillo_openCM
 
 This script implements the basic functions to interface sensors and actuators over the UART 
 so that they can be used on another board. No major computation or logi is done here.
 
 Created on September 11th 2017
 
 Gabriel Urbain <gabriel.urbain@ugent.be>
 Copyright 2017, Human Brain Projet, SP10
 */

/* -------- Global Variables and Preprocessor Commands -------- */

// Includes
#include "tigrillo_opencm.h"

#include <errno.h>
#include <string.h>
#include <stdio.h>


// Declare library objects
Dynamixel Dxl(UART_3);
HardwareTimer Timer(TIMER_1);

// Sensors variables
long sens_period = DEF_SENS_READ_TIME;
long sens_timestamp = 0;
int sens_val[SENS_NUM];

// Actuators variables
long act_timestamp = 0;

// UART
char rx_buffer[BUFF_SIZE] = {0,};
volatile unsigned int buffer_idx = 0;
int bus_mutex = 0;

/* -------- OpenCM Required Functions -------- */

void setup() {

	// Setup Serial2 to transmit messages
	Serial2.begin(BAUDRATE_UART_921600);
	
	// Setup Interuption for received UART USB message
	SerialUSB.begin();
	SerialUSB.attachInterrupt(processRx);

	// Setup Dynamixel protocol
	Dxl.begin(BAUDRATE_SERVO_115200);
	Dxl.jointMode(ACT_ID_FL);
	Dxl.jointMode(ACT_ID_FR);
	Dxl.jointMode(ACT_ID_BL);
	Dxl.jointMode(ACT_ID_BR);

	// Setup Timer 1 for periodic sensor reading
	Timer.pause();
	Timer.setPeriod(sens_period);
	Timer.setMode(TIMER_CH1, TIMER_OUTPUT_COMPARE);
	Timer.setCompare(TIMER_CH1, 1);
	Timer.attachInterrupt(TIMER_CH1, readSensors);
	Timer.refresh();
	Timer.resume();


	// Init sensor PINs
	pinMode(SENS_PIN_FL, INPUT_ANALOG);
	pinMode(SENS_PIN_FR, INPUT_ANALOG);
	pinMode(SENS_PIN_BR, INPUT_ANALOG);
	pinMode(SENS_PIN_BL, INPUT_ANALOG);

}


void loop() {

	// Nothing to do in the main loop
	delay(10);

}

/* -------- Custom Processing Functions -------- */

void processRx(byte* buffer, byte size) {

	// Ensure buffer is clean by setting next address value to 0 (not always true but don't know why)
  	buffer[size] = '\0';

	// Process received instruction
	char instruction = (char)buffer[0];
	switch (instruction) {
	
	case 'A':
		if (size > 1) {
			int act_leg[MAX_ARG_SIZE];
			int res = str2i((char*)(buffer+1), act_leg, ACT_NUM);
			// if (res != 0) {
			// 	wait4Bus();
			// 	if  (res == -1)
			// 		Serial2.println("{'ACK': {'Instruction': 'A', 'Data': 'Error: Too few numbers in argument list!'}}");
			// 	else if (res == -2)
			// 		Serial2.println("{'ACK': {'Instruction': 'A', 'Data': 'Error: Too many numbers in argument list!'}}");
			// 	else if (res == -3)
			// 		Serial2.println("{'ACK': {'Instruction': 'A', 'Data': 'Error: Wrong character in argument list!'}}");
			// 	else if (res == -4)
			// 		Serial2.println("{'ACK': {'Instruction': 'A', 'Data': 'Error: Unknown!'}}");
			// 	freeBus();
			// 	break; 
			// }
			updateMotors(act_leg);
			//wait4Bus();
			//char text[120];
			// sprintf(text, "{'ACK': {'Instruction': 'A', 'Data': 'Success: %i %i %i %i !'}}", act_leg[0], act_leg[1], act_leg[2], act_leg[3]);
			// Serial2.println(text);
			//freeBus();
		} //else {
		// 	wait4Bus();
		// 	Serial2.println("{'ACK': {'Instruction': 'A', 'Data': 'Error: Too few arguments!'}}");
		// 	freeBus();
		// }
		break;
		
	//case 'R':
		//resetSensors();
		// wait4Bus();
		// Serial2.println("{'ACK': {'Instruction': 'R', 'Data': 'Success!'}}");
		// freeBus();
		//break;
		
	case 'F':
		if (size > 1) {
			int period[1] = {DEF_SENS_READ_TIME};
			int res1 = str2i((char*)(buffer+1), period, 1);
			// if (res1 != 0) {
			// 	wait4Bus();
			// 	if  (res1 == -1)
			// 		Serial2.println("{'ACK': {'Instruction': 'F', 'Data': 'Error: Too few numbers in argument list!'}}");
			// 	else if (res1 == -2)
			// 		Serial2.println("{'ACK': {'Instruction': 'F', 'Data': 'Error: Too many numbers in argument list!'}}");
			// 	else if (res1 == -3)
			// 		Serial2.println("{'ACK': {'Instruction': 'A', 'Data': 'Error: Wrong character in argument list!'}}");
			// 	else if (res1 == -4)
			// 		Serial2.println("{'ACK': {'Instruction': 'A', 'Data': 'Error: Unknown!'}}");
			// 	freeBus();
			// 	break; 
			// }
			int res2 = changePeriod(period[0]);
			// wait4Bus();
			// if (res2 == 0) {
			// 	char text[120];
			// 	sprintf(text, "{'ACK': {'Instruction': 'F', 'Data': 'Success: Sensor reading period changed to %i microseconds!'}}", period[0]);
			// 	Serial2.println(text);
			// }
			// else {
			// 	char text[120];
			// 	sprintf(text, "{'ACK': {'Instruction': 'F', 'Data': 'Error: Period is too short. Please, use higher than %i microseconds!'}}", MIN_SENS_READ_TIME);
			// 	Serial2.println(text);
			// }
			// freeBus();
		} //else {
		// 	wait4Bus();
		// 	Serial2.println("{'ACK': {'Instruction': 'F', 'Data': 'Error: Too few arguments!'}}");
		// 	freeBus();
		// }
		break;
		
	default:
		// wait4Bus();
		// Serial2.println("{'ACK': {'Instruction': 'D', 'Data': 'Error: Instruction not recognised!'}}");
		// freeBus();
		break;
	}

  	// WARNING: Empty buffer after each usage
  	emptyStr((char*)buffer, MAX_ARG_SIZE);

}


void readSensors(void) {

	// Get time and check with previous timestamp
	long current_timestamp = micros();

	// Get sensors values
	sens_val[0] = analogRead(SENS_PIN_FL);
	sens_val[1] = analogRead(SENS_PIN_FR);
	sens_val[2] = analogRead(SENS_PIN_BL);
	sens_val[3] = analogRead(SENS_PIN_BR);

	// Send over USB serial the sensors and timing information
	char text[300];
	long operation_time = micros();
	sprintf(text, "{'DATA': {'Sensors values': {'Front Left': %i, 'Front Right': %i, 'Back Left': %i,  'Back Right': %i}, 'Time Stamp': %ld, 'Previous Time Stamp': %ld, 'End of Reading Time Stamp': %ld}}", 
			sens_val[0], sens_val[1], sens_val[2] , sens_val[3], current_timestamp, sens_timestamp, operation_time);
	Serial2.println(text);
	sens_timestamp = current_timestamp;
}


void updateMotors(int act_leg[]) {
	
	int mi = SERVO_MIN_LIM;
	int ma = SERVO_MAX_LIM;
	int in = SERVO_MAX_LIM - SERVO_MIN_LIM;
	int ra = SERVO_RANGE;
	
	// Right legs
	Dxl.writeWord(ACT_ID_FR, GOAL_POS_ADDR, (mi + act_leg[ACT_ID_FR-1] * in / ra));
	Dxl.writeWord(ACT_ID_BR, GOAL_POS_ADDR, (mi + act_leg[ACT_ID_BR-1] * in / ra));
	
	// Left legs
	Dxl.writeWord(ACT_ID_FL, GOAL_POS_ADDR, (ma - act_leg[ACT_ID_FL-1] * in / ra));
	Dxl.writeWord(ACT_ID_BL, GOAL_POS_ADDR, (ma - act_leg[ACT_ID_BL-1] * in / ra));

}


int changePeriod(int period) {

	// Pause timer and change timer frequency
	if (period > MIN_SENS_READ_TIME) {  
		sens_period = period;
		Timer.pause();
		Timer.setPeriod(sens_period);
		Timer.refresh();
		Timer.resume();
		return 0;
	} else {
		return -1;
	}

}

/* -------- Custom Utils Functions -------- */

void printTab(int* tab, int size) {
	 
	// Only for debugging purpose
	Serial2.print("[ ");
	for (int i = 0; i < size; i++) {
		Serial2.print(tab[i]);
		Serial2.print(" ");
	}
	Serial2.println("]");
	
}


void initTab(int* tab, int size) {

	for (int i = 0; i < size; i++) {
		tab[i] = 0;
	}

}


void emptyStr(char* tab, int size) {

	for (int i = 0; i < size; i++) {
		tab[i] = '\0';
	}

}


int str2i(char* str, int* tab, int size) {
	
	char *end = str;
	int index = 0;

	// Split srting with symbol "," and convert to integer value 
	while(*end) {
		errno = 0;
		int n = strtol(str, &end, 10);
		if (str == end)
			return -3;
		else if (errno != 0 && n == 0)
			return -4;
		
		tab[index] = n;
		while (*end == ',') {
			end++;
		}
		str = end;
		index ++;
	}
		
	// Check the number of integer in the array
	if (index < size) {
		return -1;
	} else if (index > size) {
		return -2;
	} else {
		return 0;
	}

}


void wait4Bus(void) {

	while (bus_mutex == 1) {
		delay_us(100);
	}

}


void freeBus(void) {

	bus_mutex = 0;

}
