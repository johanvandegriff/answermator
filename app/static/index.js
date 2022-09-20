function get(id) {
    return document.getElementById(id);
}

function addContact() {
    const request = new XMLHttpRequest();
    request.open('POST', "/create");
    request.setRequestHeader('Content-Type', 'application/json');
    favoriteValue = get("favorite").checked ? 1 : 0;
    blockedValue = get("blocked").checked ? 1 : 0;
    var data = {};
    data['name'] = get("name").value;
    data['phone'] = get("phone").value;
    data['favorite'] = favoriteValue;
    data['blocked'] = blockedValue;
    data['ringtone'] = current_ringtone.innerText;
    request.onreadystatechange = function() {
        if (request.readyState == XMLHttpRequest.DONE) {
            console.log(">" + request.responseText + "<")
            if (request.responseText == "success") {
                window.location.reload();
            } else {
                alert("duplicate number in phonebook");
            }
        }
    }
    request.send(JSON.stringify(data));
}

var isEditing = false;
var editID = 0;

document.getElementById("save").addEventListener("click", function (event) {
    event.preventDefault();
    console.log("addContact isEditing", isEditing);
    if (isEditing) {
        editContact(editID);
    } else {
        addContact();
    }
});

document.getElementById("addnewcontact").addEventListener("click", function (event) {
    isEditing = false;
    ringtone_dropdown.style["display"] = "none";
    console.log("isEditing", isEditing);
});

function editContact(id) {
    const request = new XMLHttpRequest();
    const str = "/update/" + id;
    request.open('POST', str);
    request.setRequestHeader('Content-Type', 'application/json');
    favoriteValue = get("favorite").checked ? 1 : 0;
    blockedValue = get("blocked").checked ? 1 : 0;
    var data = {};
    data['name'] = get("name").value;
    data['phone'] = get("phone").value;
    data['favorite'] = favoriteValue;
    data['blocked'] = blockedValue;
    data['ringtone'] = current_ringtone.innerText;
    request.onreadystatechange = function() {
        window.location.reload();
    };
    request.send(JSON.stringify(data));
}

edits = document.getElementsByClassName("btn btn-sm btn-success editcontact");
for (i=0; i<edits.length; i++) {
    edits[i].addEventListener("click", function (event) {
        event.preventDefault();
        isEditing = true;
        ringtone_dropdown.style["display"] = "none";
        console.log("isEditing", isEditing);
        editID = this.id;
        document.getElementById("name").value = this.parentElement.parentElement.children[0].innerText;
        document.getElementById("phone").value = this.parentElement.parentElement.children[1].innerText;

        document.getElementById("favorite").checked = this.parentElement.parentElement.children[2].innerText != "";
        document.getElementById("blocked").checked = this.parentElement.parentElement.children[3].innerText != "";

        current_ringtone.innerText = this.parentElement.parentElement.children[5].value;
    });
}

dontdisturb = document.getElementById("flexSwitchCheckDefault");
dontdisturb.addEventListener("click", function (event) {
    // event.preventDefault();
    console.log("dontdisturb.checked: " + dontdisturb.checked);

    if (dontdisturb.checked) {
        allowfaves.disabled = false;
        faves_bypass.disabled = anyone_bypass.checked;
        anyone_bypass.disabled = false;
    } else {
        allowfaves.disabled = true;
        faves_bypass.disabled = true;
        anyone_bypass.disabled = true;
    }
    set_dontdisturb_message();

    const request = new XMLHttpRequest();
    request.open('POST', "/dont_disturb");
    request.setRequestHeader('Content-Type', 'application/json');
    request.send(JSON.stringify({"dontdisturb": dontdisturb.checked ? 1 : 0}));
});

allowfaves = document.getElementById("flexSwitchCheckChecked");
allowfaves.addEventListener("click", function (event) {
    // event.preventDefault();
    console.log("allowfaves.checked: " + allowfaves.checked);
    set_dontdisturb_message();

    const request = new XMLHttpRequest();
    request.open('POST', "/allow_faves");
    request.setRequestHeader('Content-Type', 'application/json');
    request.send(JSON.stringify({"allowfaves": allowfaves.checked ? 1 : 0}));
});


faves_bypass = document.getElementById("flexSwitchCheckChecked1");
faves_bypass.addEventListener("click", function (event) {
    // event.preventDefault();
    console.log("faves_bypass.checked: " + faves_bypass.checked);
    set_dontdisturb_message();

    const request = new XMLHttpRequest();
    request.open('POST', "/faves_bypass");
    request.setRequestHeader('Content-Type', 'application/json');
    request.send(JSON.stringify({"faves_bypass": faves_bypass.checked ? 1 : 0}));
});

anyone_bypass = document.getElementById("flexSwitchCheckChecked2");
anyone_bypass.addEventListener("click", function (event) {
    // event.preventDefault();
    console.log("anyone_bypass.checked: " + anyone_bypass.checked);
    set_dontdisturb_message();

    if (anyone_bypass.checked) {
        if (!faves_bypass.checked) {
            faves_bypass.click();
        }
        faves_bypass.disabled = true;
    } else {
        faves_bypass.disabled = false;
    }

    const request = new XMLHttpRequest();
    request.open('POST', "/anyone_bypass");
    request.setRequestHeader('Content-Type', 'application/json');
    request.send(JSON.stringify({"anyone_bypass": anyone_bypass.checked ? 1 : 0}));
});


block1800 = document.getElementById("block1800");
block1800.addEventListener("click", function (event) {
    // event.preventDefault();
    console.log("block1800.checked: " + block1800.checked);

    const request = new XMLHttpRequest();
    request.open('POST', "/block1800");
    request.setRequestHeader('Content-Type', 'application/json');
    request.send(JSON.stringify({"block1800": block1800.checked ? 1 : 0}));
});





if (dontdisturb.checked) {
    allowfaves.disabled = false;
    faves_bypass.disabled = anyone_bypass.checked;
    anyone_bypass.disabled = false;
} else {
    allowfaves.disabled = true;
    faves_bypass.disabled = true;
    anyone_bypass.disabled = true;
}

dontdisturb_message = function () {
    if (!dontdisturb.checked) {
        return "The phone will ring when anyone calls.";
    } else {
        if (!allowfaves.checked && !anyone_bypass.checked && !faves_bypass.checked) {
            return "Nobody is allowed to ring through.";
        } else if (!allowfaves.checked && !anyone_bypass.checked && faves_bypass.checked) {
            return "Only favorites can ring through by calling and dialing 999.";
        } else if (!allowfaves.checked && anyone_bypass.checked) {
            return "Anyone can ring through by calling and dialing 999.";
        } else if (allowfaves.checked && !anyone_bypass.checked) {
            return "Only favorites will ring through.";
        } else if (allowfaves.checked && anyone_bypass.checked) {
            return "Favorites will ring through, and others can ring through by calling and dialing 999.";
        }
    }  
}

set_dontdisturb_message = function() {
    get("dontdisturb_message").innerText = dontdisturb_message();
}

set_dontdisturb_message();




scripts = document.getElementsByClassName("form-check-input script_class");
for (i=0; i<scripts.length; i++) {
    scripts[i].addEventListener("click", function (event) {
        // event.preventDefault();

        console.log(this.id + ".checked: " + this.checked);

        const request = new XMLHttpRequest();
        request.open('POST', "/script_enable_disable");
        request.setRequestHeader('Content-Type', 'application/json');
        request.send(JSON.stringify({"isEnabled": this.checked ? 1 : 0, "script_id": this.id}));
    });
}

owner_number = document.getElementById("owner_number");
owner_number.addEventListener("change", function (event) {
    // event.preventDefault();
    console.log("owner_number.value: " + owner_number.value);

    const request = new XMLHttpRequest();
    request.open('POST', "/owner_number");
    request.setRequestHeader('Content-Type', 'application/json')
    request.send(JSON.stringify({"owner_number": owner_number.value}));
});

script_edits = document.getElementsByClassName("script_edit");
for (i=0; i<script_edits.length; i++) {
    script_edits[i].addEventListener("click", function (event) {
        // event.preventDefault();
        id = this.parentElement.children[2].id; //id from the checkbox element
        console.log(id)
        window.location = "/script?script_id="+id;
        // const request = new XMLHttpRequest();
        // request.open('POST', "/script");
        // request.setRequestHeader('Content-Type', 'application/json')
        // request.send(JSON.stringify({"script_id": id}));
    });
}

script_runs = document.getElementsByClassName("script_run");
for (i=0; i<script_runs.length; i++) {
    script_runs[i].addEventListener("click", function (event) {
        // event.preventDefault();
        id = this.parentElement.children[2].id; //id from the checkbox element
        console.log(id)
        // window.location = "/script?script_id="+id;
        const request = new XMLHttpRequest();
        request.open('POST', "/script_run");
        request.setRequestHeader('Content-Type', 'application/json')
        request.send(JSON.stringify({"script_id": id}));
    });
}

script_rescan = document.getElementById("script_rescan");
script_rescan.addEventListener("click", function (event) {
    // event.preventDefault();
    const request = new XMLHttpRequest();
    request.open('POST', "/script_rescan");
    request.setRequestHeader('Content-Type', 'application/json')
    request.onreadystatechange = function() {
        window.location.reload();
    };
    request.send(JSON.stringify({}));
});

function playAudio(url) {
    var audio = new Audio(url);  
    audio.type = 'audio/wav';
  
    var playPromise = audio.play();
  
    if (playPromise !== undefined) {
        playPromise.then(function () {
            console.log('Playing....');
        }).catch(function (error) {
            console.log('Failed to play....' + error);
        });
    }
    audio.addEventListener("ended", function(){
        audio.currentTime = 0;
        console.log("ended");
        end_func();
    });
    return audio;
  }

playing = undefined;
audio = undefined;
end_func = undefined;
stop = undefined;

play_voicemail_buttons = document.getElementsByClassName("play_voicemail_button");
for (i=0; i<play_voicemail_buttons.length; i++) {
    play_voicemail_buttons[i].addEventListener("click", function (event) {
        // event.preventDefault();
        icon = this.children[0];
        if(icon.className == "fas fa-play") {
            icon.className = "fas fa-pause";
            id = this.id.split("_")[0]; //get just the number part of the ID
            console.log(id);
            if(playing != id) {
                if (stop != undefined) {
                    stop.style["display"] = "none";
                }
                //stop the old one
                if (audio != undefined) {
                    audio.pause();
                    audio.currentTime = 0;
                }
                if (playing != undefined) {
                    get(playing+"_play").children[0].className = "fas fa-play";
                }
                if (end_func != undefined) {
                    end_func();
                }
                icon.className = "fas fa-pause";
                audio = undefined;
                playing = undefined;
                audio = undefined;
                end_func = undefined;
                stop = undefined;
                
                stop = get(id+"_stop");
                stop.style["display"] = "inline";
                playing = id;
                end_func = function(){
                    icon.className = "fas fa-play";
                    stop.style["display"] = "none";
                    audio = undefined;
                    playing = undefined;
                    audio = undefined;
                    end_func = undefined;
                    stop = undefined;
                }
                
                audio = playAudio('/voicemail?id='+id);
            } else {
                audio.play();
            }
        } else {
            icon.className = "fas fa-play";
            if (audio != undefined) {
                audio.pause();
            }
        }
    });
}


stop_voicemail_buttons = document.getElementsByClassName("stop_voicemail_button");
for (i=0; i<stop_voicemail_buttons.length; i++) {
    stop_voicemail_buttons[i].addEventListener("click", function (event) {
        if (audio != undefined) {
            audio.pause();
            audio.currentTime = 0;
        }

        this.style["display"] = "none";
        if (end_func != undefined) {
            end_func();
        }

        audio = undefined;
        playing = undefined;
        audio = undefined;
        end_func = undefined;
        stop = undefined;
        
    });
}


delete_voicemail_buttons = document.getElementsByClassName("delete_voicemail_button");
for (i=0; i<delete_voicemail_buttons.length; i++) {
    delete_voicemail_buttons[i].addEventListener("click", function (event) {
        id = this.id.split("_")[0]; //get just the number part of the ID
        console.log(id)
        const request = new XMLHttpRequest();
        request.open('POST', "/delete_voicemail");
        request.setRequestHeader('Content-Type', 'application/json')
        request.onreadystatechange = function() {
            window.location.reload();
        };
        request.send(JSON.stringify({"id": id}));
    });
}



current_ringtone = document.getElementById("current_ringtone");
ringtone_dropdown_toggle = document.getElementById("ringtone_dropdown_toggle");
ringtone_dropdown = document.getElementById("ringtone_dropdown");
ringtone_options = document.getElementsByClassName("ringtone_dropdown_option");

ringtone_dropdown_toggle_func = function (event) {
    if (ringtone_dropdown.style["display"] == "none") {
        ringtone_dropdown.style["display"] = "block";
    } else {
        ringtone_dropdown.style["display"] = "none";
    }
}

current_ringtone.addEventListener("click", ringtone_dropdown_toggle_func);
ringtone_dropdown_toggle.addEventListener("click", ringtone_dropdown_toggle_func);

for (i=0; i<ringtone_options.length; i++) {
    ringtone_options[i].addEventListener("click", function (event) {
        current_ringtone.innerText = this.innerText;
        ringtone_dropdown.style["display"] = "none";
    });
}



get("favorite").addEventListener("click", function (event) {
    if (this.checked) {
        current_ringtone.innerText = "ouverture";
    } else {
        current_ringtone.innerText = "marimba";
    }
});


check_call_log = function () {
    const request = new XMLHttpRequest();
    request.open('POST', "/check_call_log");
    request.setRequestHeader('Content-Type', 'application/json');
    request.onreadystatechange = function() {
        if (request.readyState == XMLHttpRequest.DONE) {
            if (request.responseText == "new") {
                console.log("new voicemail")
                window.location.reload();
            }
        }
    }

    num_voicemail = 0;
    calls = get("call_log_table_body").children;
    for (i=0; i<calls.length; i++) {
        if (calls[i].children[2].children.length > 0) {
            num_voicemail++;
        }
    }

    request.send(JSON.stringify({"num_voicemail": num_voicemail, "num_calls": calls.length}));
}
var t=setInterval(check_call_log,5000); //check_call_log every 5 seconds
