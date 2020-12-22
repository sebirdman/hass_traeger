"""
Library to interact with traeger grills

Copyright 2020 by Keith Baker All rights reserved.
This file is part of the traeger python library,
and is released under the "GNU GENERAL PUBLIC LICENSE Version 2".
Please see the LICENSE file that should have been included as part of this package.
"""

import time
import ssl
import paho.mqtt.client as mqtt
import requests
import uuid
import urllib
import json
import threading
import datetime

CLIENT_ID = "2fuohjtqv1e63dckp5v84rau0j"


class traeger:
    def __init__(self, username, password,):
        self.username = username
        self.password = password
        self.mqtt_uuid = str(uuid.uuid1())
        self.mqtt_url = None
        self.mqtt_client = None
        self.grill_status = {}
        self.access_token = None
        self.token = None
        self.token_expires = 0
        self.mqtt_url_expires = 0
        self.grill_callbacks = {}

    def token_remaining(self):
        return self.token_expires - time.time()

    def refresh_token(self):
        if self.token_remaining() < 60:
            request_time = time.time()
            t = datetime.datetime.utcnow()
            amzdate = t.strftime('%Y%m%dT%H%M%SZ')
            r = requests.post("https://cognito-idp.us-west-2.amazonaws.com/",
                              json={
                                  "ClientMetadata": {},
                                  "AuthParameters": {
                                      "PASSWORD": self.password,
                                      "USERNAME": self.username,
                                  },
                                  "AuthFlow": "USER_PASSWORD_AUTH",
                                  "ClientId": CLIENT_ID
                              },
                              headers={'Content-Type': 'application/x-amz-json-1.1',
                                       'X-Amz-Date': amzdate,
                                       'X-Amz-Target': 'AWSCognitoIdentityProviderService.InitiateAuth'})
            response = r.json()
            self.token_expires = response["AuthenticationResult"]["ExpiresIn"] + request_time
            self.token = response["AuthenticationResult"]["IdToken"]

    def get_user_data(self):
        self.refresh_token()
        r = requests.get("https://1ywgyc65d1.execute-api.us-west-2.amazonaws.com/prod/users/self",
                         headers={'authorization': self.token})
        json = r.json()
        return json

    def send_command(self, thingName, command):
        self.refresh_token()
        requests.post("https://1ywgyc65d1.execute-api.us-west-2.amazonaws.com/prod/things/{}/commands".format(thingName),
                      json={
            'command': command
        },
            headers={
            'Authorization': self.token,
            "Content-Type": "application/json",
            "Accept-Language": "en-us",
            "User-Agent": "Traeger/11 CFNetwork/1209 Darwin/20.2.0",
        })

    def update_state(self, thingName):
        self.send_command(thingName, "90")

    def set_temperature(self, thingName, temp):
        self.send_command(thingName, "11,{}".format(temp))

    def shutdown_grill(self, thingName):
        self.send_command(thingName, "17")

    def set_timer_sec(self, thingName, time_s):
        self.send_command(thingName, "12,{}".format(time_s))

    def update_grills(self):
        json = self.get_user_data()
        self.grills = json["things"]

    def get_grills(self):
        return self.grills

    def set_callback_for_grill(self, grill_id, callback):
        self.grill_callbacks[grill_id] = callback

    def mqtt_url_remaining(self):
        return self.mqtt_url_expires - time.time()

    def refresh_mqtt_url(self):
        self.refresh_token()
        if self.mqtt_url_remaining() < 60:
            mqtt_request_time = time.time()
            r = requests.post("https://1ywgyc65d1.execute-api.us-west-2.amazonaws.com/prod/mqtt-connections",
                              headers={'Authorization': self.token})
            json = r.json()
            self.mqtt_url_expires = json["expirationSeconds"] + \
                mqtt_request_time
            self.mqtt_url = json["signedUrl"]

    def _mqtt_connect_func(self):
        while True:
            self.mqtt_client.loop_forever()

    def get_mqtt_client(self, on_connect, on_message):
        if self.mqtt_client == None:
            self.refresh_mqtt_url()
            mqtt_parts = urllib.parse.urlparse(self.mqtt_url)
            self.mqtt_client = mqtt.Client(transport="websockets")
            self.mqtt_client.on_connect = on_connect
            self.mqtt_client.on_message = on_message
            headers = {
                "Host": "{0:s}".format(mqtt_parts.netloc),
            }
            self.mqtt_client.ws_set_options(path="{}?{}".format(
                mqtt_parts.path, mqtt_parts.query), headers=headers)
            context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
            self.mqtt_client.tls_set_context(context)
            self.mqtt_client.connect(mqtt_parts.netloc, 443)
            x = threading.Thread(target=self._mqtt_connect_func)
            x.start()
        return self.mqtt_client

    def grill_message(self, client, userdata, message):
        if message.topic.startswith("prod/thing/update/"):
            grill_id = message.topic[len("prod/thing/update/"):]
            self.grill_status[grill_id] = json.loads(message.payload)
            if grill_id in self.grill_callbacks:
                self.grill_callbacks[grill_id]()

    def grill_connect(self, client, userdata, flags, rc):
        pass

    def subscribe_to_grill_status(self):
        client = self.get_mqtt_client(self.grill_connect, self.grill_message)
        for grill in self.grills:
            if grill["thingName"] in self.grill_status:
                del self.grill_status[grill["thingName"]]
            client.subscribe(
                ("prod/thing/update/{}".format(grill["thingName"]), 1))

    def get_state_for_device(self, thingName):
        if thingName not in self.grill_status:
            return None
        return self.grill_status[thingName]["status"]

    def get_state_for_device(self, thingName):
        if thingName not in self.grill_status:
            return None
        return self.grill_status[thingName]["status"]

    def get_limits_for_device(self, thingName):
        if thingName not in self.grill_status:
            return None
        return self.grill_status[thingName]["limits"]

    def start(self):
        self.update_grills()
        self.subscribe_to_grill_status() 
