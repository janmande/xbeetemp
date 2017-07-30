#!/usr/bin/python
from __future__ import print_function
import time
from xbee import XBee, ZigBee
import serial


import datetime
import sys
import httplib2
import os
import traceback

from apiclient import discovery
from oauth2client import client
from oauth2client import tools
from oauth2client.file import Storage

try:
    import argparse
    flags = argparse.ArgumentParser(parents=[tools.argparser]).parse_args()
except ImportError:
    flags = None

# If modifying these scopes, delete your previously saved credentials
# at ~/.credentials/sheets.googleapis.com-python-quickstart.json
SCOPES = 'https://www.googleapis.com/auth/spreadsheets'
CLIENT_SECRET_FILE = 'client_secret.json'
APPLICATION_NAME = 'Temperature'


def get_credentials():
    """
    Gets valid user credentials from storage.

    If nothing has been stored, or if the stored credentials are invalid,
    the OAuth2 flow is completed to obtain the new credentials.

    Returns:
        Credentials, the obtained credential.
    """
    logerror('get_credentials')
    home_dir = '/home/pi/'
    print('home_dir: %s' % home_dir)
    credential_dir = os.path.join(home_dir, '.credentials')
    print('Credential dir %s' % credential_dir)
    if not os.path.exists(credential_dir):
        os.makedirs(credential_dir)
    credential_path = os.path.join(
                credential_dir,
                'sheets.googleapis.com-python-quickstart.json')
    print('Credential path %s' % credential_path)
    store = Storage(credential_path)
    credentials = store.get()
    if not credentials or credentials.invalid:
        flow = client.flow_from_clientsecrets(CLIENT_SECRET_FILE, SCOPES)
        flow.user_agent = APPLICATION_NAME
        if flags:
            credentials = tools.run_flow(flow, store, flags)
        else:  # Needed only for compatibility with Python 2.6
            credentials = tools.run(flow, store)
        logerror('Storing credentials to ' + credential_path)

    return credentials


def write_google_sheets(temp, volt):
    """
    Creates a Sheets API service object to this sheet
    https://docs.google.com/spreadsheets/d/1fpZdczZuxoE4Q-9cygcttD9shcrwziQ8-MM58CO4k3E/edit
    """
    logerror('write_google_sheets')
    credentials = get_credentials()
    print('type(credentials) ' + type(credentials).__name__)
    if credentials is None:
        return
    http = credentials.authorize(httplib2.Http())
    discoveryUrl = ('https://sheets.googleapis.com/$discovery/rest?'
                    'version=v4')
    service = discovery.build(
        'sheets',
        'v4',
        http=http, discoveryServiceUrl=discoveryUrl)

    spreadsheet_id = '1fpZdczZuxoE4Q-9cygcttD9shcrwziQ8-MM58CO4k3E'
    value_input_option = 'USER_ENTERED'
    insert_data_option = 'INSERT_ROWS'
    range_name = 'A1'

    values = [
        [
            str(datetime.datetime.now()),
            temp,
            volt
        ]
    ]
    body = {
        'values': values
    }
    requests = []
    requests.append({
        'insertDimension': {
            'range': {
                'dimension': 'ROWS',
                'startIndex': 0,
                'endIndex': 1
            }
         }
    })
    requests.append({
        'deleteDimension': {
            'range': {
               'dimension': 'ROWS',
               'startIndex': 20000,
               'endIndex': 20001
        }
      }
    })
    body1 = {
        'requests': requests
    }
    print('Append data to sheet: %s' % spreadsheet_id)
    print('Adding row to start')
    result = service.spreadsheets().batchUpdate(
        spreadsheetId=spreadsheet_id,
        body=body1).execute()
    logerror('Updating data')
    result = service.spreadsheets().values().update(
        spreadsheetId=spreadsheet_id,
        range=range_name,
        valueInputOption=value_input_option,
        body=body).execute()

    return

serial_port = serial.Serial(
        "/dev/ttyUSB0",
        baudrate=9600)


def write_data(temp, volt):
    try:
        g = open(
                 '/var/www/data.json',
                 'w')
        g.write('{"temperature" : '+str(temp)+',"volt": '+str(volt)+',"time": "'+str(datetime.datetime.now())+'"}')
        g.close()
        write_google_sheets(
            temp,
            volt)
        logerror('Data written')
    except:  
        e=sys.exc_info()[0]
        logerror('Error: %s<' % e )
        logerror(traceback.format_exc())
    return


def logerror(msg):
    g=open('/var/www/xbeetemperror.txt', 'a')
    n=datetime.datetime.now()
    s=str(n)
    g.write(s + ': ')
    print(str(msg))
    g.write(str(msg) + '\n')
    g.close()
    return


def print_data(data):
    """
    This method is called whenever data is received
    from the associated XBee device. Its first and
    only argument is the data contained within the
    frame.
    """
    try:
        logerror('print_data')
        if "samples" not in data: 
            logerror(data)
            return
        logerror(data["samples"])
        print(data["samples"][0])
        print(data["samples"][0]["adc-3"])
        analogReading=data["samples"][0]["adc-3"]
        voltageReading=data["samples"][0]["adc-7"]
        temp=(analogReading/1023.0*1.25-0.5)*100
        volt=float(((1200*voltageReading)+512)/1024)/1000
        strTemp="%.1f" % temp
        strVolt="%.2f" % volt
        g=open('/var/www/temp.txt', 'w')
        g.write(strTemp)
        g.close()
        g=open('/var/www/volt.txt', 'w')
        g.write(strVolt)
        g.close()
        logerror('Temperature %.1f' % temp)
        logerror('Volt %.2f' % volt)
        write_data(temp, volt)
    except:
        e = sys.exc_info()[0]
        logerror('Error: %s' % e)
        logerror(str(traceback.format_exc()))
    return
    

logerror('Service started')
xbee = ZigBee(serial_port, callback=print_data)

while True:
    try:
        time.sleep(0.001)
    except KeyboardInterrupt:
        break

xbee.halt()
serial_port.close()
logerror('Service stopped')
