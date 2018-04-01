#!/usr/bin/python
from __future__ import print_function
import time
from digi.xbee.models.status import NetworkDiscoveryStatus
from digi.xbee.devices import XBeeDevice
from digi.xbee.io import IOLine,IOMode,IOValue
import serial
import threading


import datetime
import sys
import os
import traceback
import cloud4rpi

DEVICE_TOKEN='73EvUkG9rjfRnV7yBLTWjNzAq'

temperature = 0.0
volt = 0.0
_64bitaddr = ' '
_16bitaddr = ' '

def gettemp():
	global temperature
	return temperature

def getvolt():
	global volt
	return volt

def get64bitaddr():
	global _64bitaddr
	return str(_64bitaddr)

def get16bitaddr():
	global _16bitaddr
	return str(_16bitaddr)


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
diagnostics = {
	'64 bit address': get64bitaddr,
	'16 bit address': get16bitaddr
	}

clouddevice = cloud4rpi.connect(DEVICE_TOKEN)
clouddevice.declare(variables)
clouddevice.declare_diag(diagnostics)

clouddevice.publish_config()
time.sleep(1)

def print_data(data):
    logerror("Data received: %s " & str(data))

def logerror(msg):
    g=open('/usr/local/bin/xbeetemp/xbeerelayerror.txt', 'a')
    n=datetime.datetime.now()
    s=str(n)
    g.write(s + ': ')
    print(str(msg))
    g.write(str(msg) + '\n')
    g.close()
    return

def analog_to_celsius(analog):
	return (analog/1023.0*1.20-0.5)*100

def analog_to_volt(analog):
	return (((1200*analog)+512)/1024)/1000

def io_sample_callback(io_sample,remote_xbee,send_time):
	global temperature
	global volt
	global _64bitaddr
	global _16bitaddr

	_64bitaddr = remote_xbee.get_64bit_addr()
	_16bitaddr = remote_xbee.get_16bit_addr()
	
	logerror("IO sample received at time %s." % datetime.datetime.fromtimestamp(send_time))
	logerror("Xbee %s %s" % (_64bitaddr,_16bitaddr))
	logerror("IO sample:")
	logerror(str(io_sample))
	analog = io_sample.get_analog_value(IOLine.DIO3_AD3)
	analogvolt = io_sample.power_supply_value
	logerror("Temp reading: %s" % analog)
	logerror("Power Supply: %s" % analogvolt)
	temperature = analog_to_celsius(analog)
	logerror("Temp in celsius %.1f" % temperature)
	volt = analog_to_volt(analogvolt)
	logerror("Volt %.2f" % volt)
	return

def toggle_led(device):
	logerror("Device %s " % device)
	value = device.get_dio_value(IOLine.DIO1_AD1)
	if value == IOValue.HIGH:
		device.set_dio_value(IOLine.DIO1_AD1,IOValue.LOW)
	else:
		device.set_dio_value(IOLine.DIO1_AD1,IOValue.HIGH)
	return

logerror('Service started')
xbee = XBeeDevice("/dev/ttyUSB0",9600)
xbee.open()

xnet = xbee.get_network()


xnet.set_discovery_timeout(5)

logerror("Starting network discovery")
xnet.start_discovery_process()
while xnet.is_discovery_running():
	time.sleep(0.5)
	logerror("...")

devices = xnet.get_devices()
for device in devices:
	toggle_led(device)

xbee.add_io_sample_received_callback(io_sample_callback)
    
try:
	data_timer = 0
	diag_timer = 0
	while True:
		try:
			if getvolt() > 0: 
				if data_timer <= 0:
					clouddevice.publish_data()
					data_timer = 30
					logerror("Data published")

				if diag_timer <= 0:
					clouddevice.publish_diag()
					logerror("Diagnostics published")
					diag_timer = 60
			
				time.sleep(1)
				data_timer -= 1
				diag_timer -= 1

		except KeyboardInterrupt:
			break
except:
	logerror("Main loop exception: %s" % e)

for device in devices:
	toggle_led(device)

xbee.close()

logerror('Service stopped')
