#!/usr/bin/python2
from __future__ import print_function
import time
from xbee import XBee, ZigBee
import serial


import datetime
import sys
import httplib2
import os
import traceback
import cloud4rpi


flags = None

# If modifying these scopes, delete your previously saved credentials
# at ~/.credentials/sheets.googleapis.com-python-quickstart.json
SCOPES = 'https://www.googleapis.com/auth/spreadsheets'
CLIENT_SECRET_FILE = 'client_secret.json'
APPLICATION_NAME = 'Temperature'
DEVICETOKEN = '73EvUkG9rjfRnV7yBLTWjNzAq'
temperature = 0
voltage = 0
led_on = 0

def gettemp():
	global temperature
	return temperature

def getvolt():
	global volt
	return volt

variables = {
	'Temperatur':{
		'type':'numeric',
		'bind': gettemp
	},
	'Volt':{
		'type':'numeric',
		'bind': getvolt
	}
}
device = cloud4rpi.connect(DEVICETOKEN)
device.declare(variables)
device.publish_config()


def tocloud4rpi(t,v):
	global temperature
	global voltage
	temperature = t
	volt = v
	logerror('tocloud4rpi')
	device.publish_data()
	logerror('pubslished to cloudp4rpi')

serial_port = serial.Serial(
        "/dev/ttyUSB0",
        baudrate=9600)


def logerror(msg):
	g=open('/usr/local/bin/xbeetemp/xbeetemperror.txt', 'a')
	n=datetime.datetime.now()
	s=str(n)
	g.write(s + ': ')
	print(str(msg))
	g.write(str(msg) + '\n')
	g.close()
	return

long_dest_addr='\x00\x13\xA2\x00\x40\xB9\x6D\x8E'
addr='\x9F\xB3'

def read_led_state():
	result = xbee.remote_at(
		dest_addr_long=long_dest_addr,
		dest_addr=addr,
		command='D1')
	logerror('Led state %s' % result)

def toggle_led():
	led_state = '\x05'
	global led_on
	logerror('Toggling led %s' % led_on)
	if led_on == 1:
		led_on = 0
		led_state = '\x04'
		logerror('Setting LED off')
	else:
		led_on = 1
		led_state = '\x05'
		logerror('Setting LED on')

	xbee.remote_at(
		dest_addr_long=long_dest_addr,
		dest_addr=addr,
		options='\x02',
		command='D1',
		parameter=led_state)

	time.sleep(2)
	logerror('Done sleeping')

def print_data(data):
	"""
	This method is called whenever data is received
	from the associated XBee device. Its first and
	only argument is the data contained within the
	frame.
	"""
	global temperature
	global volt
	global xbee
	
	try:
		toggle_led()
		logerror('print_data')
		if "samples" not in data: 
			logerror(data)
			return
		logerror(data["samples"])
		logerror(data["samples"][0])
		logerror(data["samples"][0]["adc-3"])
		analogReading=data["samples"][0]["adc-3"]
		voltageReading=data["samples"][0]["adc-7"]
		temp=(analogReading/1023.0*1.25-0.5)*100
		volt=float(((1200*voltageReading)+512)/1024)/1000
		strTemp="%.1f" % temp
		strVolt="%.2f" % volt
		logerror('Temperature %.1f' % temp)
		logerror('Volt %.2f' % volt)
		temperature = temp
		voltage = volt
		tocloud4rpi(temperature,volt)
	except:
		e = sys.exc_info()[0]
		logerror('Error: %s' % e)
		logerror(str(traceback.format_exc()))
	return
    

logerror('Service started')
xbee = ZigBee(serial_port, callback=print_data)

toggle_led()

try:
    while True:
        try:
            time.sleep(0.001)
        except KeyboardInterrupt:
            break
except:
    logerror('Main loop exception: %s' % e)
    
xbee.halt()
serial_port.close()
logerror('Service stopped')
