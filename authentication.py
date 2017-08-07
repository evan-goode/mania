import getpass
import argparse
from gmusicapi import Mobileclient
import json

def authenticate (config):
	username = config["username"] or input("Username: ")
	password = config["password"] or getpass.getpass("Password: ")
	android_id= config["android-id"] or Mobileclient.FROM_MAC_ADDRESS
	client = Mobileclient(debug_logging=config["debug-logging"])
	logged_in = client.login(
		username,
		password,
		android_id,
	)
	if not logged_in:
		raise Exception("Authentication failed.")
	return client
