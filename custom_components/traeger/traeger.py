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
import asyncio
import socket
import logging
import async_timeout
import aiohttp
import homeassistant.const


CLIENT_ID = "2fuohjtqv1e63dckp5v84rau0j"
TIMEOUT = 10


_LOGGER: logging.Logger = logging.getLogger(__package__)

class traeger:
    def __init__(self, username, password, request_library):
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
        self.request = request_library
        self.grill_callbacks = {}

    def token_remaining(self):
        return self.token_expires - time.time()

    async def do_cognito(self):
        t = datetime.datetime.utcnow()
        amzdate = t.strftime('%Y%m%dT%H%M%SZ')
        return await self.api_wrapper("post", "https://cognito-idp.us-west-2.amazonaws.com/",
                                      data={
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

    async def refresh_token(self):
        if self.token_remaining() < 60:
            try:
                request_time = time.time()

                response = await self.do_cognito()

                self.token_expires = response["AuthenticationResult"]["ExpiresIn"] + request_time
                self.token = response["AuthenticationResult"]["IdToken"]
            except KeyError as exception:
                _LOGGER.error(
                    "Failed to login %s - %s",
                    response,
                    exception,
                )

    async def get_user_data(self):
        await self.refresh_token()
        return await self.api_wrapper("get", "https://1ywgyc65d1.execute-api.us-west-2.amazonaws.com/prod/users/self",
                                   headers={'authorization': self.token})

    async def send_command(self, thingName, command):
        await self.refresh_token()
        await self.api_wrapper("post_raw", "https://1ywgyc65d1.execute-api.us-west-2.amazonaws.com/prod/things/{}/commands".format(thingName),
                               data={
            'command': command
        },
            headers={
            'Authorization': self.token,
            "Content-Type": "application/json",
            "Accept-Language": "en-us",
            "User-Agent": "Traeger/11 CFNetwork/1209 Darwin/20.2.0",
        })

    async def update_state(self, thingName):
        self.grill_status = {}
        await self.send_command(thingName, "90")
        while not bool(self.grill_status):
            await asyncio.sleep(1)

    async def set_temperature(self, thingName, temp):
        await self.send_command(thingName, "11,{}".format(temp))

    async def shutdown_grill(self, thingName):
        await self.send_command(thingName, "17")

    async def set_timer_sec(self, thingName, time_s):
        await self.send_command(thingName, "12,{}".format(time_s))

    async def update_grills(self):
        json = await self.get_user_data()
        self.grills = json["things"]

    def get_grills(self):
        return self.grills

    def set_callback_for_grill(self, grill_id, callback):
        if grill_id not in self.grill_callbacks:
            self.grill_callbacks[grill_id] = []
        self.grill_callbacks[grill_id].append(callback)

    def mqtt_url_remaining(self):
        return self.mqtt_url_expires - time.time()

    async def refresh_mqtt_url(self):
        await self.refresh_token()
        if self.mqtt_url_remaining() < 60:
            mqtt_request_time = time.time()
            json = await self.api_wrapper("post", "https://1ywgyc65d1.execute-api.us-west-2.amazonaws.com/prod/mqtt-connections",
                                       headers={'Authorization': self.token})
            self.mqtt_url_expires = json["expirationSeconds"] + \
                mqtt_request_time
            self.mqtt_url = json["signedUrl"]

    def _mqtt_connect_func(self):
        while True:
            self.mqtt_client.loop_forever()

    async def get_mqtt_client(self, on_connect, on_message):
        if self.mqtt_client == None:
            await self.refresh_mqtt_url()
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
        _LOGGER.info("grill_message: message.topic = %s, message.payload = %s", message.topic, message.payload)
        if message.topic.startswith("prod/thing/update/"):
            grill_id = message.topic[len("prod/thing/update/"):]
            self.grill_status[grill_id] = json.loads(message.payload)
            if grill_id in self.grill_callbacks:
                for callback in self.grill_callbacks[grill_id]:
                    callback()

    def grill_connect(self, client, userdata, flags, rc):
        pass

    async def subscribe_to_grill_status(self):
        client = await self.get_mqtt_client(self.grill_connect, self.grill_message)
        for grill in self.grills:
            if grill["thingName"] in self.grill_status:
                del self.grill_status[grill["thingName"]]
            client.subscribe(
                ("prod/thing/update/{}".format(grill["thingName"]), 1))

    def get_state_for_device(self, thingName):
        if thingName not in self.grill_status:
            return None
        return self.grill_status[thingName]["status"]

    def get_details_for_device(self, thingName):
        if thingName not in self.grill_status:
            return None
        return self.grill_status[thingName]["details"]

    def get_limits_for_device(self, thingName):
        if thingName not in self.grill_status:
            return None
        return self.grill_status[thingName]["limits"]

    def get_settings_for_device(self, thingName):
        if thingName not in self.grill_status:
            return None
        return self.grill_status[thingName]["settings"]

    def get_units_for_device(self, thingName):
        state = self.get_state_for_device(thingName)
        if state is None:
            return homeassistant.const.TEMP_FAHRENHEIT
        if state["units"] == 0:
            return homeassistant.const.TEMP_CELSIUS
        else:
            return homeassistant.const.TEMP_FAHRENHEIT

    def get_details_for_accessory(self, thingName, accessory_id):
        state = self.get_state_for_device(thingName)
        for accessory in state["acc"]:
            if accessory["uuid"] == accessory_id:
                return accessory
        return None

    async def start(self):
        await self.update_grills()
        await self.subscribe_to_grill_status()

    async def api_wrapper(
        self, method: str, url: str, data: dict = {}, headers: dict = {}
    ) -> dict:
        """Get information from the API."""
        try:
            async with async_timeout.timeout(TIMEOUT, loop=asyncio.get_event_loop()):
                if method == "get":
                    response = await self.request.get(url, headers=headers)
                    data = await response.read()
                    return json.loads(data)

                if method == "post_raw":
                     await self.request.post(url, headers=headers, json=data)

                elif method == "post":
                    response = await self.request.post(url, headers=headers, json=data)
                    data = await response.read()
                    return json.loads(data)

        except asyncio.TimeoutError as exception:
            _LOGGER.error(
                "Timeout error fetching information from %s - %s",
                url,
                exception,
            )

        except (KeyError, TypeError) as exception:
            _LOGGER.error(
                "Error parsing information from %s - %s",
                url,
                exception,
            )
        except (aiohttp.ClientError, socket.gaierror) as exception:
            _LOGGER.error(
                "Error fetching information from %s - %s",
                url,
                exception,
            )
        except Exception as exception:  # pylint: disable=broad-except
            _LOGGER.error("Something really wrong happend! - %s", exception)
