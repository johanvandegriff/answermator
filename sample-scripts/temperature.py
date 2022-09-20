#!/usr/bin/python2
import sys

action = sys.argv[1]
digits = sys.argv[2]
isLoggedIn = sys.argv[3] == "True"

if action == "register":
    print("7760:60F,7770:70F,7780:80F")
if action == "run":
    if not isLoggedIn:
        print("not logged in, access denied to temperature")
    else:
        if digits == "7760":
            print("(python script) set temperature to 60 degrees F")
        elif digits == "7770":
            print("(python script) set temperature to 70 degrees F")
        elif digits == "7780":
            print("(python script) set temperature to 80 degrees F")
