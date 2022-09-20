DROP TABLE IF EXISTS phonebook;
DROP TABLE IF EXISTS voicemail;
DROP TABLE IF EXISTS call_log;

CREATE TABLE phonebook (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    contact_name TEXT,
    contact_number INTEGER UNIQUE NOT NULL,
    ringtone TEXT,
    favorite BIT,
    blocked BIT
);

-- CREATE TABLE voicemail (
--     id INTEGER PRIMARY KEY AUTOINCREMENT,
--     contact_number INTEGER NOT NULL,
--     mail TEXT UNIQUE NOT NULL
-- );

CREATE TABLE call_log (
    S_No INTEGER PRIMARY KEY AUTOINCREMENT,
    Phone_Number TEXT,
    Modem_Date TEXT,
    Modem_Time TEXT,
    System_Date_Time TEXT,
    Has_Voicemail, BIT
);
