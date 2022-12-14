import sys
import serial
import threading
import atexit
from datetime import datetime
import subprocess
import time
import re
import wave
import os
import fcntl

#=================================================================
# Global Variables
#=================================================================
# USB Modem Name/Manufacturer as shown in "lsusb" command
MODEM_NAME = 'U.S. Robotics'   

# Global Modem Object
analog_modem = serial.Serial()

# Used in global event listener
disable_modem_event_listener = True

#DTMF variables
RINGS_BEFORE_AUTO_ANSWER = 2 #Must be greater than 1
MODEM_RESPONSE_READ_TIMEOUT = 120  #Time in Seconds (Default 120 Seconds)

#=================================================================
# Set COM Port settings
#=================================================================
def set_COM_port_settings(com_port):
    analog_modem.port = com_port
    analog_modem.baudrate = 57600 #9600
    analog_modem.bytesize = serial.EIGHTBITS #number of bits per bytes
    analog_modem.parity = serial.PARITY_NONE #set parity check: no parity
    analog_modem.stopbits = serial.STOPBITS_ONE #number of stop bits
    analog_modem.timeout = 3            #non-block read
    analog_modem.xonxoff = False     #disable software flow control
    analog_modem.rtscts = False     #disable hardware (RTS/CTS) flow control
    analog_modem.dsrdtr = False      #disable hardware (DSR/DTR) flow control
    analog_modem.writeTimeout = 3     #timeout for write
#=================================================================



#=================================================================
# Detect Modem COM Port
#=================================================================
def detect_COM_port(com_port_to_use=None):

    if com_port_to_use is not None:
        com_ports_list = [com_port_to_use]
    else:
        # List all the Serial COM Ports on Raspberry Pi
        proc = subprocess.Popen(['ls /dev/tty[A-Za-z]*'], shell=True, stdout=subprocess.PIPE)
        com_ports = proc.communicate()[0]
        com_ports_list = com_ports.split('\n')

    print(com_ports_list)

    # Find the right port associated with the Voice Modem
    for com_port in com_ports_list:
        if 'tty' in com_port:
            #Try to open the COM Port and execute AT Command
            try:
                # Set the COM Port Settings
                set_COM_port_settings(com_port)
                analog_modem.open()
            except:
                print("Unable to open COM Port: " + com_port)
                pass
            else:
                #Try to put Modem in Voice Mode
                if not exec_AT_cmd("AT+FCLASS=8", "OK"):
                    print("Error: Failed to put modem into voice mode.")
                    if analog_modem.isOpen():
                        analog_modem.close()
                else:
                    # Found the COM Port exit the loop
                    print("Modem COM Port is: " + com_port)
                    analog_modem.flushInput()
                    analog_modem.flushOutput()
                    break
#=================================================================



#=================================================================
# Initialize Modem
#=================================================================
def init_modem_settings(com_port_to_use=None):
    
    # Detect and Open the Modem Serial COM Port
    try:
        detect_COM_port(com_port_to_use)
    except:
        print("Error: Unable to open the Serial Port.")
        sys.exit()

    # Initialize the Modem
    try:
        # Flush any existing input outout data from the buffers
        analog_modem.flushInput()
        analog_modem.flushOutput()

        # Test Modem connection, using basic AT command.
        if not exec_AT_cmd("AT"):
            print("Error: Unable to access the Modem")

        # reset to factory default.
        if not exec_AT_cmd("ATZ3"):
            print("Error: Unable reset to factory default")
            
        # Display result codes in verbose form  
        if not exec_AT_cmd("ATV1"):
            print("Error: Unable set response in verbose form")

        # Enable Command Echo Mode.
        if not exec_AT_cmd("ATE1"):
            print("Error: Failed to enable Command Echo Mode")

        # Enable formatted caller report.
        if not exec_AT_cmd("AT+VCID=1"):
            print("Error: Failed to enable formatted caller report.")
            
        # Flush any existing input outout data from the buffers
        analog_modem.flushInput()
        analog_modem.flushOutput()

    except:
        print("Error: unable to Initialize the Modem")
        sys.exit()
#=================================================================


#=================================================================
# Reset Modem
#=================================================================
def reset_USB_Device():

    # Close the COM Port if it's open
    try:
        if analog_modem.isOpen():
            analog_modem.close()
    except:
        pass

    # Equivalent of the _IO('U', 20) constant in the linux kernel.
    USBDEVFS_RESET = ord('U') << (4*2) | 20
    dev_path = ""

    # Bases on 'lsusb' command, get the usb device path in the following format - 
    # /dev/bus/usb/<busnum>/<devnum>
    proc = subprocess.Popen(['lsusb'], stdout=subprocess.PIPE)
    out = proc.communicate()[0]
    lines = out.split('\n')
    for line in lines:
        if MODEM_NAME in line:
            parts = line.split()
            bus = parts[1]
            dev = parts[3][:3]
            dev_path = '/dev/bus/usb/%s/%s' % (bus, dev)

    # Reset the USB Device
    fd = os.open(dev_path, os.O_WRONLY)
    try:
        fcntl.ioctl(fd, USBDEVFS_RESET, 0)
        print("Modem reset successful")
    finally:
        os.close(fd)

    # Re-initialize the Modem
    init_modem_settings()
#=================================================================


#=================================================================
# Execute AT Commands at the Modem
#=================================================================
def exec_AT_cmd(modem_AT_cmd, expected_response="OK"):
    
    global disable_modem_event_listener
    disable_modem_event_listener = True
    
    try:
        # Send command to the Modem
        analog_modem.write((modem_AT_cmd + "\r").encode())
        # Read Modem response
        execution_status = read_AT_cmd_response(expected_response)
        disable_modem_event_listener = False
        # Return command execution status
        return execution_status

    except:
        disable_modem_event_listener = False
        print("Error: Failed to execute the command")
        return False
#=================================================================


#=================================================================
# Read AT Command Response from the Modem
#=================================================================
def read_AT_cmd_response(expected_response="OK"):
    
    # Set the auto timeout interval
    start_time = datetime.now()

    try:
        while 1:
            # Read Modem Data on Serial Rx Pin
            modem_response = analog_modem.readline()
            print(modem_response)
            # Recieved expected Response
            if expected_response == modem_response.strip(' \t\n\r' + chr(16)):
                return True
            # Failed to execute the command successfully
            elif "ERROR" in modem_response.strip(' \t\n\r' + chr(16)):
                return False
            # Timeout
            elif (datetime.now()-start_time).seconds > MODEM_RESPONSE_READ_TIMEOUT:
                return False

    except:
        print("Error in read_modem_response function...")
        return False
#=================================================================


#=================================================================
# Recover Serial Port
#=================================================================
def recover_from_error():
    # Stop Global Modem Event listener
    global disable_modem_event_listener
    disable_modem_event_listener = True

    # Reset USB Device
    reset_USB_Device()

    # Start Global Modem Event listener
    disable_modem_event_listener = False
#=================================================================


#=================================================================
# Read DTMF Digits
#=================================================================
def dtmf_digits(modem_data):
    digit_list = re.findall('/(.+?)~', modem_data)
    doHangup = False
    for d in digit_list:
        print("\nNew Event: DTMF Digit Detected: " + d[1])
        if dtmf_callback(d[1]):
            doHangup = True
    return doHangup
#=================================================================


#=================================================================
# Go Off-Hook and Detect Events
#=================================================================
def go_offHook():
    print("\n-------------------------------------------")
    print("Going Off-Hook...\n")

    # Put Modem into Voice Mode
    if not exec_AT_cmd("AT+FCLASS=8"):
        print("Error: Failed to put modem into Voice Mode...")

    # Enable silence detection.
    # Select normal silence detection sensitivity 
    # and a silence detection interval of 10 s.
    # Call will be dropped on Silce Detection
    # Change the code logic if required
    # if not exec_AT_cmd("AT+VSD=129,35","OK"):
    # # if not exec_AT_cmd("AT+VSD=128,100","OK"):
    #     print("Error: Failed tp enable silence detection.")
    #     return

    # Compression Method and Sampling Rate Specifications
    # Compression Method: 8-bit linear / Sampling Rate: 8000MHz
    if not exec_AT_cmd("AT+VSM=128,8000"):
        print "Error: Failed to set compression method and sampling rate specifications."
        return

    # Put Modem into TAD Mode
    if not exec_AT_cmd("AT+VLS=1"):
        print("Error: Unable to answer the call...")

    # Put modem into TAD Mode
    if not exec_AT_cmd("AT+VTX"):
        print "Error: Unable put modem into TAD mode."
        return

    time.sleep(1)

    # Disable global event listener
    global disable_modem_event_listener
    disable_modem_event_listener = True

    wf = wave.open('/home/answermator/Answermator/play_audio_over_phone_line/sample.wav','rb')
    chunk = 1024

    data = wf.readframes(chunk)
    while data != '':
        analog_modem.write(data)
        data = wf.readframes(chunk)
        # You may need to change this sleep interval to smooth-out the audio
        time.sleep(.12)
    wf.close()

    # 2 Min Time Out
    timeout = time.time() + 60*2 
    while 1:
        modem_data = analog_modem.readline()
        if "OK" in modem_data:
            break
        if time.time() > timeout:
            break

    disable_modem_event_listener = False
    print "Play Audio Msg - END"
    return

    try:
        data_buffer = ""

        while 1:
            # Read data from the Modem
            data_buffer = data_buffer + analog_modem.read()

            # Check if <DLE>b is in the stream
            if ((chr(16)+chr(98)) in data_buffer):
                print("\nNew Event: Busy Tone... (Call will be disconnected)")
                break

            # Check if <DLE>s is in the stream
            if ((chr(16)+chr(115)) in data_buffer):
                print("\nNew Event: Silence Detected... (Call will be disconnected)")
                break

            # Check if <DLE><ETX> is in the stream
            if (("<DLE><ETX>").encode() in data_buffer):
                print("\nNew Event: <DLE><ETX> Char Recieved... (Call will be disconnected)")
                break

            # Parse DTMF Digits, if found in the Modem Data
            if len(re.findall('/(.+?)~', data_buffer)) > 0:
                doHangup = dtmf_digits(data_buffer)
                data_buffer = ""
                if doHangup:
                    break

        data_buffer = ""

        # Hangup the Call
        if not exec_AT_cmd("ATH","OK"):
            print("Error: Unable to hang-up the call")
        else:
            print("\nAction: Call Terminated...")
    finally:
        # Enable global event listener
        disable_modem_event_listener = False
        print("-------------------------------------------")
    
#=================================================================


#=================================================================
# Modem Data Listener / Monitor
#=================================================================
def read_data():
    global disable_modem_event_listener
    ring_data = ""

    call_record = {}

    while 1:

        if not disable_modem_event_listener:
            modem_data = analog_modem.readline()

            if (modem_data != "") and (modem_data != (chr(13)+chr(10))) :
                print("\n-------------------------------------------")
                print("New Event: " + modem_data.strip())
                #print "ASCII Values of Modem Data: " + (' '.join(str(ord(c)) for c in modem_data))

                # Busy Tone <DLE>b
                if (chr(16)+chr(98)) in modem_data:
                    print("Event Detail: Busy Tone Detected on phone line...")
                    #Terminate the call
                    if not exec_AT_cmd("ATH"):
                        print("Error: Busy Tone - Failed to terminate the call")
                        print("Trying to revoer the serial port")
                        recover_from_error()
                    else:
                        print("Action: Call Terminated (Busy Tone)...")
                
                # Silence <DLE>s
                if (chr(16)+chr(115)) == modem_data:
                    print("Event Detail: Silence detected on phone line...")
                    #Terminate the call
                    if not exec_AT_cmd("ATH"):
                        print("Error: Silence - Failed to terminate the call")
                        print("Trying to revoer the serial port")
                        recover_from_error()
                    else:
                        print("Action: Call Terminated (Silence)...")

                if ("DATE" in modem_data):
                    call_record['DATE'] = (modem_data[5:]).strip(' \t\n\r')
                if ("TIME" in modem_data):
                    call_record['TIME'] = (modem_data[5:]).strip(' \t\n\r')
                if ("NMBR" in modem_data):
                    call_record['NMBR'] = (modem_data[5:]).strip(' \t\n\r')
                    # Call call details logger
                    print(call_record)
                    call_details_logger(call_record)

                if "RING" in modem_data.strip(chr(16)):
                    # pass

                # if ("RING" in modem_data) or ("DATE" in modem_data) or ("TIME" in modem_data) or ("NMBR" in modem_data):
                #     if ("NMBR" in modem_data):
                #         print "Event Detail: Incomming call from phone number: " + (modem_data[5:]).strip()
                #     if ("DATE" in modem_data):
                #         print "Event Detail: Service provider date: " + (modem_data[5:]).strip()
                #     if ("TIME" in modem_data):
                #         print "Event Detail: Service provider time: " + (modem_data[5:]).strip() 
                #     if "RING" in modem_data.strip(chr(16)):
                    print("Event Detail: RING detected on phone line...")
                    ring_data = ring_data + modem_data
                    ring_count = ring_data.count("RING")
                
                    if ring_count == RINGS_BEFORE_AUTO_ANSWER:
                        ring_data = ""
                        #Go off-hook and detect DTMF Digits
                        isNumberBlocked = number_block_filter_callback(call_record['NMBR'])
                        if isNumberBlocked:
                            print("number blocked: " + str(call_record['NMBR']))
                        else:
                            print("number accepted: " + str(call_record['NMBR']))
                            go_offHook()

#=================================================================



#=================================================================
# Close the Serial Port
#=================================================================
def close_modem_port():

    # Try to close any active call
    try:
        exec_AT_cmd("ATH")
    except:
        pass

    # Close the Serial COM Port
    try:
        if analog_modem.isOpen():
            analog_modem.close()
            print("Serial Port closed...")
    except:
        print("Error: Unable to close the Serial Port.")
        sys.exit()
#=================================================================


def play_audio_on_phone(filename):
    #for now, just play audio on laptop
    # os.system("paplay sample.wav")

    # # Enter Voice Mode
    # if not exec_AT_cmd("AT+FCLASS=0"):
    #     print "Error: Failed to put modem into voice mode."
    #     return

    # # Enter Voice Mode
    # if not exec_AT_cmd("AT+FCLASS=8"):
    #     print "Error: Failed to put modem into voice mode."
    #     return

    # # Compression Method and Sampling Rate Specifications
    # # Compression Method: 8-bit linear / Sampling Rate: 8000MHz
    # if not exec_AT_cmd("AT+VSM=128,8000"):
    #     print "Error: Failed to set compression method and sampling rate specifications."
    #     return

    # # Put modem into TAD Mode
    # if not exec_AT_cmd("AT+VLS=1"):
    #     print "Error: Unable put modem into TAD mode."
    #     return

    # # Put modem into TAD Mode
    # if not exec_AT_cmd("AT+VTX"):
    #     print "Error: Unable put modem into TAD mode."
    #     return

    time.sleep(1)

    wf = wave.open(filename,'rb')
    chunk = 1024

    data = wf.readframes(chunk)
    while data != '':
        analog_modem.write(data)
        data = wf.readframes(chunk)
        # You may need to change this sleep interval to smooth-out the audio
        analog_modem.flushInput()
        analog_modem.flushOutput()
        time.sleep(.12)
    wf.close()




def modem_init(logger_callback_function0, dtmf_callback0, number_block_filter_callback0):
    global call_details_logger, dtmf_callback, number_block_filter_callback
    call_details_logger = logger_callback_function0
    dtmf_callback = dtmf_callback0
    number_block_filter_callback = number_block_filter_callback0
    # Main Function
    init_modem_settings("/dev/ttyACM0")
    #init_modem_settings()

    # Start a new thread to listen to modem data 
    data_listener_thread = threading.Thread(target=read_data)
    data_listener_thread.start()

    # Close the Modem Port when the program terminates
    atexit.register(close_modem_port)
