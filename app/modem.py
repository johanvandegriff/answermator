import serial
import time
import threading
import atexit
import sys
import re
import wave
from datetime import datetime
# import pyaudio
import os


analog_modem = serial.Serial()
analog_modem.port = "/dev/ttyACM0"
analog_modem.baudrate = 57600 #9600
analog_modem.bytesize = serial.EIGHTBITS #number of bits per bytes
analog_modem.parity = serial.PARITY_NONE #set parity check: no parity
analog_modem.stopbits = serial.STOPBITS_ONE #number of stop bits
analog_modem.xonxoff = False     #disable software flow control
analog_modem.rtscts = False     #disable hardware (RTS/CTS) flow control
analog_modem.dsrdtr = False      #disable hardware (DSR/DTR) flow control
analog_modem.timeout = 3            #non-block read
analog_modem.writeTimeout = 3     #timeout for write


# Used in global event listener
disable_modem_event_listener = True
RINGS_BEFORE_AUTO_ANSWER = 2
RINGS_BEFORE_VOICEMAIL = 5
REC_VM_MAX_DURATION = 120  # Time in Seconds

SAMPLING_RATE1 = 8000
VSM_COMMAND1 = "AT+VSM=128,"+str(SAMPLING_RATE1)

SAMPLING_RATE2 = 8000
VSM_COMMAND2 = "AT+VSM=128,"+str(SAMPLING_RATE2)
# AT+VSM=?
# 128,"8-BIT LINEAR",(7200,8000,11025)
# 129,"16-BIT LINEAR",(7200,8000,11025)
# 130,"8-BIT ALAW",(8000)
# 131,"8-BIT ULAW",(8000)
# 132,"IMA ADPCM",(7200,8000,11025)

# OK


#=================================================================
# Initialize Modem
#=================================================================
def init_modem_settings():
    # Opean Serial Port
    try:
        analog_modem.open()
    except:
        print "Error: Unable to open the Serial Port."
        sys.exit()


    # Initialize
    try:
        analog_modem.flushInput()
        analog_modem.flushOutput()

        # Test Modem connection, using basic AT command.
        if not exec_AT_cmd("AT"):
            print "Error: Unable to access the Modem"

        # reset to factory default.
        if not exec_AT_cmd("ATZ3"):
            print "Error: Unable reset to factory default"            
            
        # Display result codes in verbose form     
        if not exec_AT_cmd("ATV1"):
            print "Error: Unable set response in verbose form"    

        # Enable Command Echo Mode.
        if not exec_AT_cmd("ATE1"):
            print "Error: Failed to enable Command Echo Mode"        

        # Enable formatted caller report.
        if not exec_AT_cmd("AT+VCID=1"):
            print "Error: Failed to enable formatted caller report."

        # Enable formatted caller report.
        #if not exec_AT_cmd("AT+FCLASS=8"):
        #    print "Error: Failed to enable formatted caller report."


        analog_modem.flushInput()
        analog_modem.flushOutput()

    except:
        print "Error: unable to Initialize the Modem"
        sys.exit()
#=================================================================



#=================================================================
# Execute AT Commands on the Modem
#=================================================================
def exec_AT_cmd(modem_AT_cmd):
    try:
        global disable_modem_event_listener
        disable_modem_event_listener = True

        cmd = modem_AT_cmd + "\r"
        analog_modem.writeTimeout = 3
        analog_modem.write(cmd.encode())

        analog_modem.timeout = 3
        modem_response = analog_modem.readline()
        modem_response = modem_response + analog_modem.readline()

        print modem_response

        disable_modem_event_listener = False

        if ((modem_AT_cmd in ("AT+VTX", "AT+VRX", "AT+VTR"))) and ("CONNECT" in modem_response):
            # modem in TAD mode
            return True
        elif "OK" in modem_response:
            # Successful command execution
            return True
        else:
            # Failed command execution
            return False

    except:
        disable_modem_event_listener = False
        print "Error: unable to write AT command to the modem..."
        return()
#=================================================================



#=================================================================
# Recover Serial Port
#=================================================================
def recover_from_error():
    try:
        exec_AT_cmd("ATH")
    except:
        pass

    analog_modem.close()
    init_modem_settings()

    try:
        analog_modem.close()
    except:
        pass

    try:
        init_modem_settings()
    except:
        pass

    try:
        exec_AT_cmd("ATH")
    except:
        pass

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


def pick_up_phone():
    # Put Modem into Voice Mode
    if not exec_AT_cmd("AT+FCLASS=8"):
        print("Error: Failed to put modem into Voice Mode...")

    # Enable silence detection.
    # Select normal silence detection sensitivity 
    # and a silence detection interval of 10 s.
    # Call will be dropped on Silce Detection
    # Change the code logic if required
    if not exec_AT_cmd("AT+VSD=120,20"):
    # if not exec_AT_cmd("AT+VSD=128,100"):
        print("Error: Failed tp enable silence detection.")
        return

    # Compression Method and Sampling Rate Specifications
    # Compression Method: 8-bit linear / Sampling Rate: 8000MHz
    if not exec_AT_cmd(VSM_COMMAND1):
        print "Error: Failed to set compression method and sampling rate specifications."
        return

    # Put Modem into TAD Mode
    if not exec_AT_cmd("AT+VLS=1"):
        print("Error: Unable to answer the call...")

def hang_up():
    os.system("killall paplay") #stop ringing
    # Hangup the Call
    if not exec_AT_cmd("ATH"):
        print("Error: Unable to hang-up the call")
    else:
        print("\nAction: Call Terminated...")

def go_offHook_and_wait_for_emergency_and_hang_up(call_record):
    number = call_record['NMBR']
    print("\n-------------------------------------------")
    print("Going Off-Hook...\n")

    pick_up_phone()
    
    # Disable global event listener
    global disable_modem_event_listener
    disable_modem_event_listener = True


    try:
        data_buffer = ""

        code_entered = ""

        # startTime = time.time()

        timeout = time.time() + 10 #10 seconds to enter the emergency code

        ringTimer = time.time()+100
        ringModeTimer = time.time()-100
        disableVoicemail = False
        while 1:
            # Read data from the Modem
            analog_modem.timeout = 3
            data_buffer = data_buffer + analog_modem.read()
            print(data_buffer)

            # Check if <DLE>b is in the stream
            if ((chr(16)+chr(98)) in data_buffer):
                print("\nNew Event: Busy Tone... (Call will be disconnected)")
                hang_up()
                break

            # Check if <DLE>s is in the stream
            if ((chr(16)+chr(115)) in data_buffer):
                print("\nNew Event: Silence Detected... (Call will be disconnected)")
                hang_up()
                break

            # Check if <DLE><ETX> is in the stream
            if (("<DLE><ETX>").encode() in data_buffer):
                print("\nNew Event: <DLE><ETX> Char Recieved... (Call will be disconnected)")
                hang_up()
                break

            # Parse DTMF Digits, if found in the Modem Data
            if len(re.findall('/(.+?)~', data_buffer)) > 0:
                digit_list = re.findall('/(.+?)~', data_buffer)
                for d in digit_list:
                    print("\nNew Event: DTMF Digit Detected: " + d[1])
                    code_entered += d[1]
                    print(code_entered, d)
                data_buffer = ""
                if code_entered == "999":
                    print("emergency ring-thru code was entered")
                    if emergency_bypass_callback(number):
                        print("number ringing thru")
                        ringModeTimer = time.time() + 13
                        ringtone_callback(number)
                        ringTimer = time.time() + 6
                        disableVoicemail = True
                    else:
                        print("number not allowed to ring thru")

            ringMode = time.time() <= ringModeTimer

            # print (time.time() - startTime, ringModeTimer - startTime, ringTimer - startTime, ringMode)

            if ringMode:
                if time.time() > ringTimer:
                    ringtone_callback(number)
                    ringTimer = time.time() + 6
            if not disableVoicemail and time.time() > timeout:
                #instead of hanging up, record voicemail
                record_voicemail(call_record)
                hang_up()
                break

        data_buffer = ""

    finally:
        # Enable global event listener
        disable_modem_event_listener = False
        print("-------------------------------------------")

def go_offHook_and_hang_up():
    print("\n-------------------------------------------")
    print("Going Off-Hook...\n")

    # Put Modem into Voice Mode
    if not exec_AT_cmd("AT+FCLASS=8"):
        print("Error: Failed to put modem into Voice Mode...")

    # Compression Method and Sampling Rate Specifications
    # Compression Method: 8-bit linear / Sampling Rate: 8000MHz
    if not exec_AT_cmd(VSM_COMMAND1):
        print "Error: Failed to set compression method and sampling rate specifications."
        return

    # Put Modem into TAD Mode
    if not exec_AT_cmd("AT+VLS=1"):
        print("Error: Unable to answer the call...")
    
    # Hangup the Call
    if not exec_AT_cmd("ATH"):
        print("Error: Unable to hang-up the call")
    else:
        print("\nAction: Call Terminated...")

#=================================================================
# Go Off-Hook and Detect Events
#=================================================================
def go_offHook():
    print("\n-------------------------------------------")
    print("Going Off-Hook...\n")

    pick_up_phone()

    # # Put modem into TAD Mode
    # if not exec_AT_cmd("AT+VTX"):
    #     print "Error: Unable put modem into TAD mode."
    #     return

    # time.sleep(1)

    # # Disable global event listener
    # global disable_modem_event_listener
    # disable_modem_event_listener = True

    # wf = wave.open('/home/answermator/Answermator/play_audio_over_phone_line/sample.wav','rb')
    # chunk = 1024

    # data = wf.readframes(chunk)
    # while data != '':
    #     analog_modem.write(data)
    #     data = wf.readframes(chunk)
    #     # You may need to change this sleep interval to smooth-out the audio
    #     time.sleep(.12)
    # wf.close()

    # # 2 Min Time Out
    # timeout = time.time() + 60*2 
    # while 1:
    #     modem_data = analog_modem.readline()
    #     if "OK" in modem_data:
    #         break
    #     if time.time() > timeout:
    #         break

    # disable_modem_event_listener = False
    # print "Play Audio Msg - END"
    # return


    # Disable global event listener
    global disable_modem_event_listener
    disable_modem_event_listener = True


    try:
        data_buffer = ""
        data_buffer_for_hangup = ""

        start_time = time.time()
        hasReset = False
        while 1:
            # Read data from the Modem
            analog_modem.timeout = 3
            new_data = analog_modem.read()
            data_buffer += new_data
            data_buffer_for_hangup += new_data

            if time.time() > start_time + 5:
                if not hasReset:
                    data_buffer_for_hangup = ""
                    hasReset = True

                # Check if <DLE>b is in the stream
                if ((chr(16)+chr(98)) in data_buffer_for_hangup):
                    print("\nNew Event: Busy Tone... (Call will be disconnected)")
                    break

                # Check if <DLE>s is in the stream
                if ((chr(16)+chr(115)) in data_buffer_for_hangup):
                    print("\nNew Event: Silence Detected... (Call will be disconnected)")
                    break

                # Check if <DLE><ETX> is in the stream
                if (("<DLE><ETX>").encode() in data_buffer_for_hangup):
                    print("\nNew Event: <DLE><ETX> Char Recieved... (Call will be disconnected)")
                    break

            # Parse DTMF Digits, if found in the Modem Data
            if len(re.findall('/(.+?)~', data_buffer)) > 0:
                doHangup = dtmf_digits(data_buffer)
                data_buffer = ""
                data_buffer_for_hangup = ""
                if doHangup:
                    break

        data_buffer = ""

        # Hangup the Call
        if not exec_AT_cmd("ATH"):
            print("Error: Unable to hang-up the call")
        else:
            print("\nAction: Call Terminated...")
    finally:
        # Enable global event listener
        disable_modem_event_listener = False
        print("-------------------------------------------")
    
#=================================================================


#=================================================================
# Play wav file
#=================================================================
def play_audio():
    print "Play Audio Msg - Start"

    # Enter Voice Mode
    if not exec_AT_cmd("AT+FCLASS=8"):
        print "Error: Failed to put modem into voice mode."
        return

    # Compression Method and Sampling Rate Specifications
    # Compression Method: 8-bit linear / Sampling Rate: 8000MHz
    if not exec_AT_cmd(VSM_COMMAND1):
        print "Error: Failed to set compression method and sampling rate specifications."
        return

    # Put modem into TAD Mode
    if not exec_AT_cmd("AT+VLS=1"):
        print "Error: Unable put modem into TAD mode."
        return

    # Put modem into TAD Mode
    if not exec_AT_cmd("AT+VTX"):
        print "Error: Unable put modem into TAD mode."
        return

    time.sleep(1)

    # Play Audio File

    global disable_modem_event_listener
    disable_modem_event_listener = True

    wf = wave.open('sample.wav','rb')
    chunk = 1024

    analog_modem.writeTimeout = 3
    data = wf.readframes(chunk)
    while data != '':
        analog_modem.write(data)
        data = wf.readframes(chunk)
        # You may need to change this sleep interval to smooth-out the audio
        time.sleep(.12)
    wf.close()

    #analog_modem.flushInput()
    #analog_modem.flushOutput()

    cmd = "<DLE><ETX>" + "\r"
    analog_modem.write(cmd.encode())

    # 2 Min Time Out
    timeout = time.time() + 60*2 
    while 1:
        analog_modem.timeout = 3
        modem_data = analog_modem.readline()
        if "OK" in modem_data:
            break
        if time.time() > timeout:
            break

    disable_modem_event_listener = False

    cmd = "ATH" + "\r"
    analog_modem.write(cmd.encode())

    print "Play Audio Msg - END"
    return
#=================================================================



#=================================================================
# Modem Data Listener
#=================================================================
def read_data():
    global disable_modem_event_listener
    ring_data = ""

    call_record = {}

    #timer to detect the end of RING events
    last_ring_time = -100
    isRinging = False

    while 1:
        if not disable_modem_event_listener:
            # print("isRinging:", isRinging)
            if time.time() > last_ring_time + 8: #hasn't ringed for 8 seconds
                isRinging = False
                call_record = {}
                ring_data = ""
                # print("stopped ringing, clearing call_record")
            analog_modem.timeout = 3
            modem_data = analog_modem.readline()
            if (modem_data != "") and (modem_data != (chr(13)+chr(10))) :
                print("\n-------------------------------------------")
                print("New Event: " + modem_data.strip())
                #print "ASCII Values of Modem Data: " + (' '.join(str(ord(c)) for c in modem_data))

                if "b" in modem_data.strip(chr(16)):
                    print "b in modem data"
                    print "b count:"
                    print ((modem_data.strip(chr(16))).count("b"))
                    print "total length:"
                    print len(modem_data.strip(chr(16)))
                    print modem_data
                    
                    if ((modem_data.strip(chr(16))).count("b")) == len(modem_data.strip(chr(16))):
                        print "all Bs in mode data"
                        #Terminate the call
                        if not exec_AT_cmd("ATH"):
                            print "Error: Busy Tone - Failed to terminate the call"
                            print "Trying to revoer the serial port"
                            recover_from_error()
                        else:
                            print "Busy Tone: Call Terminated"

                if "s" == modem_data.strip(chr(16)):
                    #Terminate the call
                    if not exec_AT_cmd("ATH"):
                        print "Error: Silence - Failed to terminate the call"
                        print "Trying to revoer the serial port"
                        recover_from_error()
                    else:
                        print "Silence: Call Terminated"

                if ("DATE" in modem_data):
                    call_record['DATE'] = (modem_data[5:]).strip(' \t\n\r')
                if ("TIME" in modem_data):
                    call_record['TIME'] = (modem_data[5:]).strip(' \t\n\r')
                if ("NMBR" in modem_data):
                    call_record['NMBR'] = (modem_data[5:]).strip(' \t\n\r')
                    # Call call details logger
                    print(call_record)
                    call_record["id"] = call_details_logger(call_record)

                if "RING" in modem_data.strip(chr(16)):
                    print("Event Detail: RING detected on phone line...")
                    isRinging = True
                    last_ring_time = time.time()
                    ring_data = ring_data + modem_data
                    ring_count = ring_data.count("RING")
                
                    if ring_count >= RINGS_BEFORE_AUTO_ANSWER:
                        # ring_data = ""
                        if 'NMBR' in call_record:
                            #Go off-hook and detect DTMF Digits
                            isNumberBlocked = number_block_filter_callback(call_record['NMBR'])
                            isNumberOwner = number_owner_callback(call_record['NMBR'])
                            if isNumberOwner:
                                print("owner's number: " + str(call_record['NMBR']))
                                # ringtone_callback(call_record['NMBR'])
                                call_record = {}
                                ring_data = ""
                                go_offHook()
                                # play_audio()
                            elif isNumberBlocked == None: #blocked by do not disturb
                                go_offHook_and_wait_for_emergency_and_hang_up(call_record)
                                call_record = {}
                                ring_data = ""
                            elif isNumberBlocked:
                                print("number blocked: " + str(call_record['NMBR']))
                                call_record = {}
                                ring_data = ""
                                go_offHook_and_hang_up()
                            else:
                                print("number accepted: " + str(call_record['NMBR']))
                                ringtone_callback(call_record['NMBR'])
                                print("rings:", ring_count, " rings before voicemail:", RINGS_BEFORE_VOICEMAIL)                                
                                if ring_count >= RINGS_BEFORE_VOICEMAIL:
                                    ring_data = ""
                                    pick_up_phone()
                                    record_voicemail(call_record)
                                    call_record = {}
                        else:
                            print "number not received yet, waiting for next ring"
                # if ("RING" in modem_data) or ("DATE" in modem_data) or ("TIME" in modem_data) or ("NMBR" in modem_data):
                #     if "RING" in modem_data.strip(chr(16)):
                #         ring_data = ring_data + modem_data
                #         ring_count = ring_data.count("RING")
                #         if ring_count == 1:
                #             pass
                #             print modem_data
                #         elif ring_count == RINGS_BEFORE_AUTO_ANSWER:
                #             ring_data = ""
                #             play_audio()                            
#=================================================================



#=================================================================
# Close the Serial Port
#=================================================================
def close_modem_port():
    try:
        exec_AT_cmd("ATH")
    except:
        pass

    try:
        if analog_modem.isOpen():
            analog_modem.close()
            print ("Serial Port closed...")
    except:
        print "Error: Unable to close the Serial Port."
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
    # if not exec_AT_cmd(VSM_COMMAND1):
    #     print "Error: Failed to set compression method and sampling rate specifications."
    #     return

    # # Put modem into TAD Mode
    # if not exec_AT_cmd("AT+VLS=1"):
    #     print "Error: Unable put modem into TAD mode."
    #     return

    # Put modem into TAD Mode
    if not exec_AT_cmd("AT+VTX"):
        print "Error: Unable put modem into TAD mode."
        return

    time.sleep(1)

    wf = wave.open(filename,'rb')
    chunk = 1024

    analog_modem.writeTimeout = 3
    data = wf.readframes(chunk)
    while data != '':
        analog_modem.write(data)
        data = wf.readframes(chunk)
        # You may need to change this sleep interval to smooth-out the audio
        analog_modem.flushInput()
        analog_modem.flushOutput()
        time.sleep(.12)
    wf.close()


def record_voicemail(call_record):
    os.system("killall paplay") #stop ringing
    # play_audio_on_phone(os.path.expanduser("~/phonebot/answermator-app/sample.wav"))
    voicemail_filename = database_voicemail_callback(call_record["id"])
    record_audio_from_phone(os.path.expanduser(voicemail_filename))

def record_audio_from_phone(filename):
    # Play beep.
    if not exec_AT_cmd("AT+VTS=[933,900,100]"):
        print "Error: Failed to play 1.2 second beep."
        #return

    # Select voice receive mode
    if not exec_AT_cmd("AT+VRX"): #response: CONNECT
        print "Error: Unable put modem into voice receive mode."
        return
    
    # Record Audio File

    global disable_modem_event_listener
    disable_modem_event_listener = True

    # Set the auto timeout interval
    start_time = datetime.now()
    CHUNK = 1024
    audio_frames = []

    while 1:
        analog_modem.timeout = 3
        # Read audio data from the Modem
        audio_data = analog_modem.read(CHUNK)

        # Check if <DLE>b is in the stream
        if ((chr(16)+chr(98)) in audio_data):
            print "Busy Tone... Call will be disconnected."
            break

        # Check if <DLE>s is in the stream
        if ((chr(16)+chr(115)) in audio_data):
            print "Silence Detected... Call will be disconnected."
            break

        # Check if <DLE><ETX> is in the stream
        if (("<DLE><ETX>").encode() in audio_data):
            print "<DLE><ETX> Char Recieved... Call will be disconnected."
            break

        # # Check if <DLE>t is in the stream
        # if ((chr(16)+'t') in audio_data):
        #     print "(added) <DLE>t Char Recieved... Call will be disconnected."
        #     break

        # # Check if <DLE><ETX> is in the stream
        # if ((chr(16)+chr(3)) in audio_data):
        #     print "(added) <DLE><ETX> Char Recieved... Call will be disconnected."
        #     break

        # if ((chr(16)) in audio_data):
        #     print "(added) Char 16 Recieved..."
        #     locations = [i for i, ch in enumerate(audio_data) if ch == chr(16)]

        #     for i in locations:
        #         print "location: " + str(i)
        #         print "after char 16: " + str(ord(audio_data[i+1]))
        #         print "after char 16: " + str(ord(audio_data[i+2]))

        # if ((chr(76)) in audio_data):
        #     print "(added) Char 76 Recieved..."
        #     locations = [i for i, ch in enumerate(audio_data) if ch == chr(76)]

        #     for i in locations:
        #         print "location: " + str(i)
        #         print "after char 76: " + str(ord(audio_data[i+1]))
        #         print "after char 76: " + str(ord(audio_data[i+2]))

        # if ((chr(108)) in audio_data):
        #     print "(added) Char 108 Recieved..."
        #     locations = [i for i, ch in enumerate(audio_data) if ch == chr(108)]

        #     for i in locations:
        #         print "location: " + str(i)
        #         print "after char 108: " + str(ord(audio_data[i+1]))
        #         print "after char 108: " + str(ord(audio_data[i+2]))

        # if ((chr(3)) in audio_data):
        #     print "(added) Char 3 Recieved..."
        #     locations = [i for i, ch in enumerate(audio_data) if ch == chr(3)]

        #     for i in locations:
        #         print "location: " + str(i)
        #         print "after char 3: " + str(ord(audio_data[i+1]))
        #         print "after char 3: " + str(ord(audio_data[i+2]))

        if (("<DLE>").encode() in audio_data):
            print "(added) <DLE> Char Recieved..."

        # Timeout
        elif ((datetime.now()-start_time).seconds) > REC_VM_MAX_DURATION:
            print "Timeout - Max recording limit reached."
            break

        # Add Audio Data to Audio Buffer
        audio_frames.append(audio_data)

    # global audio_file_name

    # Save the Audio into a .wav file
    wf = wave.open(filename, 'wb')
    wf.setnchannels(1)
    wf.setsampwidth(1)
    wf.setframerate(SAMPLING_RATE1)
    wf.writeframes(b''.join(audio_frames))
    wf.close()

    # Reset Audio File Name
    # audio_file_name = ''


    # Send End of Voice Recieve state by passing "<DLE>!"
    if not exec_AT_cmd((chr(16)+chr(33))):
        print "Error: Unable to signal end of voice receive state"

    # Hangup the Call
    if not exec_AT_cmd("ATH"):
        print "Error: Unable to hang-up the call"

    # Enable global event listener
    disable_modem_event_listener = False

    print "Record Audio Msg - END"
    return


enable_audio_thread = False
wf = None
# audio_frames = []
# audio_frames2 = []


#recording from the mic and playing to the phone
def audio_thread_func():
    global enable_audio_thread
    global wf
    global data
    chunk = 1024
    while True:
        while not enable_audio_thread:
            time.sleep(0.1)
        
        # global audio_frames2
        # audio_frames2 = []
        data = wf.readframes(chunk)
        print "audio_thread_func 1"
        while True: #data != '':
            analog_modem.write(data)
            # if len(audio_frames2) > 0:
            #     analog_modem.write(audio_frames2.pop(0))
            print "audio_thread_func 2"
            # data = stream.read(chunk)
            # data = wf.readframes(chunk)

            # You may need to change this sleep interval to smooth-out the audio
            analog_modem.flushInput()
            analog_modem.flushOutput()
            time.sleep(.6)
        wf.close()
        enable_audio_thread = False

# def pyaudio_callback(in_data, frame_count, time_info, status):
#     global audio_frames, audio_frames2
#     audio_frames_copy = audio_frames[:]
#     audio_frames = []
#     audio_frames2.append(in_data)
#     return (b''.join(audio_frames_copy), pyaudio.paContinue)

"""
def phone_call_audio(filename_play, filename_record):
    # # Put modem into VLS Mode
    # if not exec_AT_cmd("AT+VLS=5"):
    #     print "Error: Unable put modem into VLS mode."
    #     return

    # Compression Method and Sampling Rate Specifications
    # Compression Method: 8-bit linear / Sampling Rate: 8000MHz
    if not exec_AT_cmd(VSM_COMMAND2):
        print "Error: Failed to set compression method and sampling rate specifications."
        return

    # Play beep.
    if not exec_AT_cmd("AT+VTS=[933,900,100]"):
        print "Error: Failed to play 1.2 second beep."
        #return

    # Put modem into VTR Mode
    if not exec_AT_cmd("AT+VTR"):
        print "Error: Unable put modem into VTR mode."
        return

    # # Select voice receive mode
    # if not exec_AT_cmd("AT+VRX"): #response: CONNECT
    #     print "Error: Unable put modem into voice receive mode."
    #     return

    # AT+VLS=?
    # 0,"",B0000000,B0000000,B0000000
    # 1,"T",0BC01800,0BC01800,0BC01800
    # 2,"L",00000000,00000000,B0000000
    # 3,"LT",0BC01800,0BC01800,0BC01800
    # 4,"S",00000000,00000000,B0000000
    # 5,"ST",0BC01800,0BC01800,0BC01800
    # 6,"M",00000000,00000000,B0000000
    # 7,"MST",0BC01800,0BC01800,0BC01800



    global disable_modem_event_listener
    disable_modem_event_listener = True

    # time.sleep(1)

    print "test1"

    # Record Audio File

    # Set the auto timeout interval
    start_time = datetime.now()
    # global audio_frames
    audio_frames = []

    global data
    global wf
    wf = wave.open(filename_play,'rb')
    chunk = 1024

    analog_modem.timeout = 3
    analog_modem.writeTimeout = 3

    p = pyaudio.PyAudio()

    stream = p.open(format=p.get_format_from_width(1),
                channels=1,
                rate=SAMPLING_RATE2,
                input=True,
                output=True,
                frames_per_buffer=chunk)
                # stream_callback=pyaudio_callback)

    global enable_audio_thread
    enable_audio_thread = True

    while enable_audio_thread:
        # analog_modem.write(data)
        # data = wf.readframes(chunk)


        # print "test2"

        # Read audio data from the Modem
        audio_data = analog_modem.read(chunk)
        data = stream.read(chunk)
        stream.write(audio_data, chunk)

        # # Timeout
        # if ((datetime.now()-start_time).seconds) > 10: #REC_VM_MAX_DURATION:
        #     print "Timeout - Max recording limit reached."
        #     break

        # Add Audio Data to Audio Buffer
        audio_frames.append(audio_data)


        # print len(audio_data)

        # You may need to change this sleep interval to smooth-out the audio
        # analog_modem.flushInput()
        # analog_modem.flushOutput()
        # time.sleep(.24)

    enable_audio_thread = False

    print "test3"

    # Save the Audio into a .wav file
    wf = wave.open(filename_record, 'wb')
    wf.setnchannels(1)
    wf.setsampwidth(1)
    wf.setframerate(SAMPLING_RATE2)
    wf.writeframes(b''.join(audio_frames))
    wf.close()

    print "test4"

    # cmd = "<DLE>^" + "\r"
    # analog_modem.write(cmd.encode())

    # # 2 Min Time Out
    # timeout = time.time() + 60*2 
    # while 1:
    #     analog_modem.timeout = 3
    #     modem_data = analog_modem.readline()
    #     print "test4.5"
    #     if "OK" in modem_data:
    #         break
    #     if time.time() > timeout:
    #         break


    # Send End of VTR by passing "<DLE>^"
    if not exec_AT_cmd((chr(16)+chr(94))):
        print "Error: Unable to signal end of VTR"

    print "test5"

    # Hangup the Call
    if not exec_AT_cmd("ATH"):
        print "Error: Unable to hang-up the call"

    print "test6"

    # Enable global event listener
    disable_modem_event_listener = False

    print "Play/Record Audio Msg - END"
"""



def modem_init(logger_callback_function0, dtmf_callback0, number_block_filter_callback0, ringtone_callback0, number_owner_callback0, database_voicemail_callback0, emergency_bypass_callback0):
    global call_details_logger, dtmf_callback, number_block_filter_callback, ringtone_callback, number_owner_callback, database_voicemail_callback, emergency_bypass_callback
    call_details_logger = logger_callback_function0
    dtmf_callback = dtmf_callback0
    number_block_filter_callback = number_block_filter_callback0
    ringtone_callback = ringtone_callback0
    number_owner_callback = number_owner_callback0
    database_voicemail_callback = database_voicemail_callback0
    emergency_bypass_callback = emergency_bypass_callback0

    # Main Function
    # init_modem_settings("/dev/ttyACM0")
    init_modem_settings()

    #Start a new thread to listen to modem data 
    data_listener_thread = threading.Thread(target=read_data)
    data_listener_thread.start()

    audio_thread = threading.Thread(target=audio_thread_func)
    audio_thread.start()

    # Close the Modem Port when the program terminates
    atexit.register(close_modem_port)






# def dummy_callback(arg):
#     return False

# modem_init(dummy_callback, dummy_callback, dummy_callback)