from flask import render_template, request, redirect, url_for, flash, g, Blueprint
from app import app
from .db import get_db, init_db
import random
import json
from .modem import modem_init, play_audio_on_phone, record_audio_from_phone
from datetime import datetime
import os, stat
import subprocess
import threading
import time
from sqlite3 import IntegrityError

NUMBER_PLACEHOLDER_1800 = "800"
DTMF_PASSWORD = "1234"

RINGTONES_FOLDER = os.path.expanduser("~/phonebot/answermator-app/ringtones/")
DEFAULT_RINGTONE = "marimba"

DTMF_SCRIPT_FOLDER=os.path.expanduser("~/answermator-dtmf")
VOICEMAIL_FOLDER=os.path.expanduser("~/answermator-voicemail")
JSON_CONFIG_FILE = os.path.expanduser("~/config.json")

json_settings = {}

if not os.path.isfile(JSON_CONFIG_FILE):
    #default settings
    json_settings = {
        "dont_disturb": False,
        "allow_faves": True,
        "faves_bypass": True,
        "anyone_bypass": False,
        "block1800": False,
        "dtmf_scripts": {},
        "owner_number": ""
    }
    #create a new json file
    with open(JSON_CONFIG_FILE, "w") as f:
        f.write(json.dumps(json_settings, indent=4))
else:
    with open(JSON_CONFIG_FILE) as f:
        json_settings = json.load(f)


def save_json_settings():
    global json_settings
    with open(JSON_CONFIG_FILE, "w") as f:
        f.write(json.dumps(json_settings, indent=4))

@app.route('/console')
def console0():
    return render_template("console.html", ip_addr=get_ip_addr())


bash_proc = subprocess.Popen(['/bin/bash'], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True, bufsize=1)
reset_console = False

console_output = ""

def read_console():
    global console_output, reset_console
    while 1:
        line = bash_proc.stdout.readline()
        if reset_console:
            reset_console = False
        else:
            console_output += line

read_console_thread = threading.Thread(target=read_console)
read_console_thread.start()

@app.route("/console_reset", methods=('POST',))
def console_reset():
    global bash_proc, reset_console
    bash_proc.kill()
    reset_console = True
    console_output = ""
    bash_proc = subprocess.Popen(['/bin/bash'], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True, bufsize=1)
    return ""

@app.route('/console_run', methods=('POST',))
def console_run0():
    global bash_proc, console_output
    data = request.json
    print("data:", data)
    if "command" in data:
        console_command = data["command"]
        console_output += "$ " + console_command + "\n"
        bash_proc.stdin.write(console_command+"\n"); bash_proc.stdin.flush()
        time.sleep(0.25)
        # try:
        # print("command:", data["command"])
        # bash_output = app.config['bash_proc'].communicate(data["command"])
        # except:
            # app.config['bash_proc'].kill()
            # app.config['bash_proc'] = subprocess.Popen(['/bin/bash'], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    console_output_copy = console_output[:]
    console_output = ""
    print(console_output_copy)
    return console_output_copy


@app.route('/dont_disturb', methods=('POST',))
def dont_disturb0():
    global json_settings
    data = request.json
    if data["dontdisturb"] == 1:
        json_settings["dont_disturb"] = True
    else:
        json_settings["dont_disturb"] = False
    save_json_settings()
    print("don't disturb:" + str(json_settings["dont_disturb"]))
    return ""

@app.route('/allow_faves', methods=('POST',))
def allow_faves0():
    global json_settings
    data = request.json
    if data["allowfaves"] == 1:
        json_settings["allow_faves"] = True
    else:
        json_settings["allow_faves"] = False
    save_json_settings()
    print("allow faves:" + str(json_settings["allow_faves"]))
    return ""

@app.route('/faves_bypass', methods=('POST',))
def faves_bypass0():
    global json_settings
    data = request.json
    if data["faves_bypass"] == 1:
        json_settings["faves_bypass"] = True
    else:
        json_settings["faves_bypass"] = False
    save_json_settings()
    print("faves_bypass:" + str(json_settings["faves_bypass"]))
    return ""

@app.route('/anyone_bypass', methods=('POST',))
def anyone_bypass0():
    global json_settings
    data = request.json
    if data["anyone_bypass"] == 1:
        json_settings["anyone_bypass"] = True
    else:
        json_settings["anyone_bypass"] = False
    save_json_settings()
    print("anyone_bypass:" + str(json_settings["anyone_bypass"]))
    return ""


@app.route('/block1800', methods=('POST',))
def block1800_func():
    global json_settings
    data = request.json
    if data["block1800"] == 1:
        json_settings["block1800"] = True
    else:
        json_settings["block1800"] = False
    save_json_settings()
    print("block1800:" + str(json_settings["block1800"]))
    return ""


@app.route('/owner_number', methods=('POST',))
def owner_number_func():
    global json_settings
    data = request.json
    json_settings["owner_number"] = data["owner_number"]
    save_json_settings()
    print("owner_number:" + str(json_settings["owner_number"]))
    return ""

@app.route('/script_enable_disable', methods=('POST',))
def script_enable_disable():
    global json_settings
    dtmf_scripts = json_settings["dtmf_scripts"]

    data = request.json
    #script_id = "music.sh:1234"
    script_id = data["script_id"]
    isEnabled = data["isEnabled"] == 1
    
    script, code = script_id.split(":")

    if not code in dtmf_scripts[script]:
        print("code not found in script")
        return "fail"
    else:
        dtmf_scripts[script][code]["isEnabled"] = isEnabled
        print("script "+script+", "+code+":" + str(isEnabled))
        print(dtmf_scripts)

        json_settings["dtmf_scripts"] = dtmf_scripts
        save_json_settings()
        return "success"

@app.route('/voicemail')
def voicemail_func():
    id = request.args["id"]
    voicemail_file = VOICEMAIL_FOLDER + "/" + str(id) + ".wav"
    if os.path.isfile(voicemail_file):
        with open(voicemail_file, "r") as f:
            return f.read()
    return ""

@app.route('/check_call_log', methods=('POST',))
def check_call_log():
    data = request.json

    call_records = getCallRecords()
    num_calls_have = data["num_calls"]
    num_calls = len(call_records)

    num_voicemail_have = data["num_voicemail"]
    num_voicemail = 0
    for call_record in call_records:
        if call_record["Has_Voicemail"]:
            num_voicemail += 1

    print("num_voicemail:", num_voicemail, "num_voicemail_have:", num_voicemail_have)
    if num_voicemail != num_voicemail_have or num_calls != num_calls_have:
        return "new"
    return ""

@app.route('/delete_voicemail', methods=('POST',))
def delete_voicemail_func():
    data = request.json
    id = data["id"]
    
    voicemail_file = VOICEMAIL_FOLDER + "/" + str(id) + ".wav"

    print("deleting voicemail", id, " ", voicemail_file)

    if os.path.isfile(voicemail_file):
        os.remove(VOICEMAIL_FOLDER+"/"+str(id)+".wav")
    
    with app.app_context():
        contact = get_db().execute(
            "UPDATE call_log SET Has_Voicemail = 0 where S_No = ?"
            , [id]
        )
        get_db().commit()
    return ""

@app.route('/')
@app.route('/index')
def index():
    global json_settings
    dtmf_scripts = json_settings["dtmf_scripts"]
    contacts = getContacts()
    # scripts = [{"name": "a", "id": "88", "checked": "checked"}]
    scripts = []
    for script in dtmf_scripts:
        if len(dtmf_scripts[script]) == 0:
            scripts.append({"name": script + " (error)", "id": script+":", "checked": "disabled"})
        for code in dtmf_scripts[script]:
            isEnabled = dtmf_scripts[script][code]["isEnabled"]
            deSCRIPTion = dtmf_scripts[script][code]["description"]
            if len(deSCRIPTion) > 0:
                deSCRIPTion = ": " + deSCRIPTion
            checked = ""
            if isEnabled:
                checked = "checked"
            scripts.append({"name": script + " " + code + deSCRIPTion, "id": script+":"+code, "checked": checked})
    return render_template('index.html', contacts=getContacts(), call_records=getCallRecords(), scripts=scripts,
                    json_settings=json_settings, DTMF_PASSWORD=DTMF_PASSWORD, ringtones=getRingtones())

def getRingtones():
    ringtones = [x.split(".")[0] for x in os.listdir(RINGTONES_FOLDER)]
    if DEFAULT_RINGTONE in ringtones:
        del ringtones[ringtones.index(DEFAULT_RINGTONE)]
        ringtones2 = [DEFAULT_RINGTONE]
        ringtones2.extend(ringtones)
        ringtones = ringtones2
    return ringtones

@app.route('/script', methods=('GET',))
def script_page():
    data = request.args
    print(data)
    if data is None:
        return "tmp"
    if "script_name" in data:
        script_name = data["script_name"]
    elif "script_id" in data:
        script_name = data["script_id"].split(":")[0]
    else:
        return "error, no script name provided"

    script_file = DTMF_SCRIPT_FOLDER+"/"+script_name

    script_text = """
#!/bin/bash
if [[ "$1" == "register" ]]; then
    echo "5555:description,5556:description"
elif [[ "$1" == "run" ]]; then
    echo "shell script activated, args: $@"
    if [[ "$3" == "True" ]]; then
        if [[ "$2" == 5555 ]]; then
            echo "(shell script) put your code here (5555)"
        else
            echo "(shell script) put your code here (5556)"
        fi
    else
        echo "(shell script) not logged in"
    fi
fi
"""
    if os.path.isfile(script_file):
        with open(script_file, "r") as f:
            script_text = f.read()

    return render_template('script.html', script_name=script_name, script_text=script_text)

@app.route('/script_rescan', methods=('POST',))
def script_rescan():
    scan_for_dtmf_scripts()
    return ""

@app.route('/script_save', methods=('POST',))
def script_save():
    data = request.json
    script_name = data["script_name"]
    script_text = data["script_text"]
    print("saving script", script_name, script_text)
    with open(DTMF_SCRIPT_FOLDER+"/"+script_name, "w") as f:
        f.write(script_text)
    os.chmod(DTMF_SCRIPT_FOLDER+"/"+script_name, stat.S_IREAD|stat.S_IWRITE|stat.S_IEXEC)
    scan_for_dtmf_scripts()
    return ""

@app.route('/script_delete', methods=('POST',))
def script_delete():
    data = request.json
    script_name = data["script_name"]
    print("deleting script", script_name)
    os.remove(DTMF_SCRIPT_FOLDER+"/"+script_name)
    scan_for_dtmf_scripts()
    return ""

@app.route('/script_run', methods=('POST',))
def script_run():
    data = request.json
    print("id:", data["script_id"])
    script_name, code = data["script_id"].split(":")

    print("running script", script_name)
    run_script(script_name, code, True)
    
    return ""

# Creates a new contact and inserts it into the Phonebook table.
@app.route('/create', methods=('POST',))
def create():
    if request.method == 'POST':
        
        data = request.json

        contact_name = data["name"]
        contact_number = data["phone"]
        ringtone = data["ringtone"]
        favorite = data["favorite"]
        blocked = data["blocked"]
       
        db = get_db()
        sql = "INSERT INTO phonebook (contact_name, contact_number, ringtone, favorite, blocked) VALUES (?,?,?,?,?)"
        val = (contact_name, contact_number, ringtone, favorite, blocked)

        try:
            db.execute(sql,val)
            db.commit()
        except IntegrityError:
            return "error"
        return "success" #redirect(url_for('index'))


# Edits the information for the contact in Phonebook specified by contact_id.
@app.route('/update/<int:contactID>', methods=('POST',))
def update(contactID):
    if request.method == 'POST':
        
        data = request.json

        name = data["name"]
        num = data["phone"]
        ring = data["ringtone"]
        fav = data["favorite"]
        block = data["blocked"]

        db = get_db()
        db.execute('''
            UPDATE phonebook
            SET contact_name = ?, contact_number = ?, ringtone = ?, favorite = ?, blocked = ?
            WHERE id = ?
        ''', [name, num, ring, fav, block, contactID])
        
        db.commit()
        return redirect(url_for('index'))


# Deletes the specified contact from the Phonebook table.
@app.route('/delete/<int:contactID>')
def delete(contactID):
    db = get_db()
    sql = "DELETE FROM phonebook WHERE id = ?"
    c = (contactID, )
    db.execute(sql, c)
    db.commit()
    return redirect(url_for('index'))


def getContacts():
    db = get_db()
    db_records = db.execute(
        'SELECT id, contact_name, contact_number, ringtone, favorite, blocked'
        ' FROM phonebook'
        ' WHERE blocked != 2'
        ' ORDER BY contact_name ASC'
    ).fetchall()

    contacts = []
    for record in db_records:
        contacts.append(dict(contact_id=record[0], contact_name=record[1], contact_number=record[2], ringtone=record[3], favorite=record[4], blocked=record[5]))

    return contacts


# Returns the contact specified by contact_id.
def get_contact(contact_id):

    contact = get_db().execute(
        'SELECT contact_name, contact_number, ringtone, favorite, blocked'
        ' FROM phonebook'
        ' WHERE id = ?'
        , contact_id
    ).fetchone()

    if contact is None:
        abort(404, "Contact ID {0} doesn't exist.".format(contact_id))

    return contact


def getCallRecords():
    query = 'select S_No, Phone_Number, Modem_Date, Modem_Time, System_Date_Time, Has_Voicemail from call_log order by datetime(System_Date_Time) DESC'

    db = get_db()
    db_records = db.execute(query).fetchall()

    call_records = []
    for record in db_records:
        call_records.append(dict(S_No=record[0], Phone_Number=record[1], Modem_Date=record[2], Modem_Time=record[3], System_Date_Time=record[4], Has_Voicemail=record[5]))
    
    return call_records

digits = ""
isLoggedIn = False

#=================================================================
# Save Call Details in Database
#=================================================================
def call_details_logger(call_record):
    global digits, isLoggedIn
    digits = ""
    isLoggedIn = False
    with app.app_context():
        
        query = 'INSERT INTO call_log(Phone_Number, Modem_Date, Modem_Time, System_Date_Time, Has_Voicemail) VALUES(?,?,?,?,0)'
        arguments = [call_record['NMBR'], datetime.strptime(call_record['DATE'],'%m%d').strftime('%d-%b'), datetime.strptime(call_record['TIME'],'%H%M').strftime('%I:%M %p'), (datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3])]
        db = get_db()


        cursor=db.cursor()
        cursor.execute(query, arguments)

        # db.execute(query, arguments)
        db.commit()
        # insert_record(query, arguments)
        print("New record added")
        print("cursor.lastrowid:", cursor.lastrowid)
        return cursor.lastrowid
#=================================================================

#=================================================================
# DTMF code applied to the Answermator
    # Incoming call logger recognizes the owner's phone number and 
    # calls this function to wait for a dialtone before proceeding
#=================================================================
# def dtmf_control(modem_data):
#     digit_list = re.findall('/(.+?)~', modem_data)
#     db_path = "data.db" #Believe it is one database for phonebook and voicemail
#                         #Might need something like this: r"C:\sqlite\db\pythonsqlite.db"
#     conn = create_connection(db_path) #create connection to the database
#     if (d[1] == 0):
#         # Enter home automation/user interaction phase
#         print "You have entered home automation mode"
#         print "You can press 1 to..."
#     else if (d[1] == 1): 
#         # Access voicemail by querying the database
#         print "You have entered voicemail mode"
#         print "You can press 1 to listen to your most recent voicemail"
#         select_all_voicemail(conn) #select all voicemail in database
#         if (d[1] == 1):
#             # Sequence 11 (should it be d[2] == 1?)
#     else if (d[1] == 2): 
#         # Access phonebook by querying the database (contacts, blocked, etc.)
#         # Listing contacts/blocked/favorites
#         print "You have entered phonebook mode"
#         select_all_phonebook(conn)
#         if (d[1] == 1):
#             #sequence 2, 1 should print all of the blocked phone numbers from the phonebook
#             cur = conn.cursor()
#             cur.execute("SELECT * FROM phonebook WHERE blocked=1", (blocked,)) #check this
#             rows = cur.fetchall()
#             for row in rows:
#                 print(row)
#     else:
#         # default action
#         print "No event associated with that dial tone." 
#         # Give chance to enter another digit
#=================================================================


def scan_for_dtmf_scripts():
    global json_settings
    dtmf_scripts = json_settings["dtmf_scripts"]

    print("old:", dtmf_scripts)

    if not os.path.isdir(DTMF_SCRIPT_FOLDER):
        os.makedirs(DTMF_SCRIPT_FOLDER)
    scripts = os.listdir(DTMF_SCRIPT_FOLDER)

    new_dtmf_scripts = {}
    for script in scripts:
        # script = DTMF_SCRIPT_FOLDER+"/"+script
        print "Adding script:", script
        new_dtmf_scripts[script] = {}
        try:
            codes = subprocess.check_output([DTMF_SCRIPT_FOLDER+"/"+script, "register", "", ""]).strip()
            for code in codes.split(","):
                description = ""
                if ":" in code:
                    code, description = code.split(":")
                isEnabled = True
                if script in dtmf_scripts and code in dtmf_scripts[script]:
                    isEnabled = dtmf_scripts[script][code]["isEnabled"]
                new_dtmf_scripts[script][code] = {"isEnabled": isEnabled, "description": description}
        except OSError:
            print("error running script, make sure it is executable with chmod +x " + script)
        except subprocess.CalledProcessError:
            print("script returned error")

    json_settings["dtmf_scripts"] = new_dtmf_scripts
    save_json_settings()
    print("new:", new_dtmf_scripts)


def run_script(script, code, isLoggedIn):
    try:
        output = subprocess.check_output([DTMF_SCRIPT_FOLDER+"/"+script, "run", code, str(isLoggedIn)])
        print("script output:")
        print(output)
    except subprocess.CalledProcessError:
        print("script returned error")

def dtmf_callback(digit):
    global digits, isLoggedIn, json_settings
    dtmf_scripts = json_settings["dtmf_scripts"]
    print("dtmf_callback: " + digit)
    digits += str(digit)
    print("all digits: " + digits)
    print("isLoggedIn: " + str(isLoggedIn))
    if digits == DTMF_PASSWORD:
        digits = ""
        isLoggedIn = True
        print("password entered, owner logged in")
    if digits == "0": #PHONE CALL
        ring("marimba")
        digits = ""
        # play_audio_on_phone(os.path.expanduser('~/phonebot/answermator-app/sample.wav'))
        # record_audio_from_phone(os.path.expanduser('~/record_output.wav'))
        # phone_call_audio(os.path.expanduser('~/phonebot/answermator-app/sample.wav'), os.path.expanduser('~/record_output.wav'))
    if digit == "#":
        print("# pressed, clearing digits")
        digits = ""
    if digit == "*":
        print("* pressed, hanging up")
        return True #hang up
    for script in dtmf_scripts:
        if digits in dtmf_scripts[script]:
            print("script code detected for:", script)
            if not dtmf_scripts[script][digits]["isEnabled"]:
                print("script not enabled")
            else:
                run_script(script, digits, isLoggedIn)
                print("clearing digits")
                digits = ""
    return False #don't hang up


#returns:
#   True if the number is on the blocked list, or blocked by being a 1800 number if that is enabled (never ring thru)
#   None if the number is blocked by do not disturb (this one can be overridden by the ring thru code)
#   False if the number is not blocked
def number_block_filter_callback(number):
    global json_settings
    print("number_block_filter_callback: " + str(number))
    print("don't disturb:" + str(json_settings["dont_disturb"]))

    #block 1800 numbers
    if number[0:3] == NUMBER_PLACEHOLDER_1800 and json_settings["block1800"]:
        return True #blocked

    with app.app_context():
        
        contact = get_db().execute(
            '''SELECT contact_name, contact_number, ringtone, favorite, blocked
            FROM phonebook
            WHERE contact_number = ?'''
            , [number]
        ).fetchone()

        if contact is None:
            print(str(number) + " not in contacts")
            if json_settings["dont_disturb"]:
                return None #blocked by do not disturb
            else:
                return False #not blocked

        blocked = contact[4]
        favorite = contact[3]
        print("contact: ", contact, "favorite: ", favorite, "blocked: ", blocked)
        if blocked:
            return True #blocked

        if json_settings["dont_disturb"]:
            if favorite and json_settings["allow_faves"]:
                return False #not blocked
            else:
                return None #blocked by do not disturb


    return False #not blocked

def emergency_bypass_callback(number):
    global json_settings
    print("emergency_bypass_callback: " + str(number))

    # #block 1800 numbers
    # if number[0:3] == NUMBER_PLACEHOLDER_1800 and json_settings["block1800"]:
    #     return True #blocked

    if json_settings["anyone_bypass"]:
        return True #ring thru

    with app.app_context():
        
        contact = get_db().execute(
            '''SELECT contact_name, contact_number, ringtone, favorite, blocked
            FROM phonebook
            WHERE contact_number = ?'''
            , [number]
        ).fetchone()

        if contact is None:
            print(str(number) + " not in contacts")
            return False #dont ring thru

        favorite = contact[3]
        print("contact: ", contact, "favorite: ", favorite)


        if favorite and json_settings["faves_bypass"]:
            return True #ring thru
        else:
            return False #dont ring thru
    return False #dont ring thru


def ring(ringtone):
    os.system("paplay "+RINGTONES_FOLDER+ringtone+".ogg &")

# ringtones = {"default": "~/phonebot/answermator-app/ouverture.ogg", "favorite": "~/phonebot/answermator-app/marimba.ogg"}
# def ring(name):
#     os.system("paplay "+ringtones[name]+" &")


def ringtone_callback(number):
    print("ringtone_callback: " + str(number))

    with app.app_context():
        
        contact = get_db().execute(
            '''SELECT contact_name, contact_number, ringtone, favorite, blocked
            FROM phonebook
            WHERE contact_number = ?'''
            , [number]
        ).fetchone()

        if contact is None:
            print(str(number) + " not in contacts")
            ring("ouverture")
        else:
            print("contact: ", contact)
            ringtone = contact[2]
            ring(ringtone)
            # favorite = contact[3]
            # if favorite:
            #     ring("favorite")
            # else:
            #     ring("default")

def number_owner_callback(number):
    return str(number) == str(json_settings["owner_number"])

def database_voicemail_callback(id):
    with app.app_context():
        contact = get_db().execute(
            "UPDATE call_log SET Has_Voicemail = 1 where S_No = ?"
            , [id]
        )
        get_db().commit()

        if not os.path.isdir(VOICEMAIL_FOLDER):
            os.makedirs(VOICEMAIL_FOLDER)
        return VOICEMAIL_FOLDER + "/" + str(id) + ".wav"
    return ""


def get_ip_addr():
    return subprocess.check_output(["hostname", "-I"]).strip()

def speak_ip_address():
    print("playing bootup sound")
    os.system("paplay ~/phonebot/answermator-app/bootup.ogg")
    ip_addr = get_ip_addr()
    print("reading local IP address:", ip_addr)
    for digit in ip_addr:
        if digit in "0123456789":
            os.system("paplay ~/phonebot/answermator-app/digits/"+digit+".ogg")
        else:
            time.sleep(1.3)


#initialize the modem, giving it callback functions to save call logs to, dtmf tones, check for blocked numbers, etc.
modem_init(call_details_logger, dtmf_callback, number_block_filter_callback, ringtone_callback, number_owner_callback, database_voicemail_callback, emergency_bypass_callback)
scan_for_dtmf_scripts()

threading.Thread(target=speak_ip_address).start()