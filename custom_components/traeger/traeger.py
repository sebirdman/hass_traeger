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
TIMEOUT = 60


_LOGGER: logging.Logger = logging.getLogger(__package__)

class traeger:
    def __init__(self, username, password, hass, request_library):
        self.username = username
        self.password = password
        self.mqtt_uuid = str(uuid.uuid1())
        self.mqtt_thread_running = False
        self.mqtt_thread_refreshing = False
        self.hass = hass
        self.loop = hass.loop
        self.task = None
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
            request_time = time.time()
            response = await self.do_cognito()
            self.token_expires = response["AuthenticationResult"]["ExpiresIn"] + request_time
            self.token = response["AuthenticationResult"]["IdToken"]

    async def get_user_data(self):
        await self.refresh_token()
        return await self.api_wrapper("get", "https://1ywgyc65d1.execute-api.us-west-2.amazonaws.com/prod/users/self",
                                   headers={'authorization': self.token})

    async def send_command(self, thingName, command):
        _LOGGER.debug("Send Command Topic: %s, Send Command: %s", thingName, command)
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

    async def set_probe_temperature(self, thingName, temp):
        await self.send_command(thingName, "14,{}".format(temp))

    async def set_switch(self, thingName, switchval):
        await self.send_command(thingName, str(switchval))

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

    def grill_subscribe(self, client, userdata, mid, granted_qos):
        for grill in self.grills:
            grill_id = grill["thingName"]
            if grill_id in self.grill_status:
                del self.grill_status[grill_id]
            self.update_state(grill_id)

    async def refresh_mqtt_url(self):
        await self.refresh_token()
        if self.mqtt_url_remaining() < 60:
            try:
                mqtt_request_time = time.time()
                json = await self.api_wrapper("post", "https://1ywgyc65d1.execute-api.us-west-2.amazonaws.com/prod/mqtt-connections",
                                           headers={'Authorization': self.token})
                self.mqtt_url_expires = json["expirationSeconds"] + \
                    mqtt_request_time
                self.mqtt_url = json["signedUrl"]
            except KeyError as exception:
                _LOGGER.error(
                    "Key Error Failed to Parse MQTT URL %s - %s",
                    json,
                    exception,
                )
            except Exception as exception:
                _LOGGER.error(
                    "Other Error Failed to Parse MQTT URL %s - %s",
                    json,
                    exception,
                )
        _LOGGER.debug(f"MQTT URL:{self.mqtt_url} Expires @:{self.mqtt_url_expires}")

    def _mqtt_connect_func(self):
        if self.mqtt_client != None:
            _LOGGER.debug(f"Start MQTT Loop Forever")
            while self.mqtt_thread_running:
                self.mqtt_client.loop_forever()
                while (self.mqtt_url_remaining() < 60 or self.mqtt_thread_refreshing) and self.mqtt_thread_running:
                    time.sleep(1)
        _LOGGER.debug(f"Should be the end of the thread.")

    async def get_mqtt_client(self, on_connect, on_message, on_log, on_subscribe):
        if self.mqtt_client == None:
            await self.refresh_mqtt_url()
            mqtt_parts = urllib.parse.urlparse(self.mqtt_url)
            self.mqtt_client = mqtt.Client(transport="websockets")
            self.mqtt_client.on_connect = on_connect
            self.mqtt_client.on_message = on_message
            self.mqtt_client.on_subscribe = on_subscribe
            self.mqtt_client.on_log = on_log   #Only need this for troubleshooting
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
            _LOGGER.debug(f"Thread Active Count:{threading.active_count()}")
            if self.mqtt_thread_running == False:
                self.mqtt_thread = threading.Thread(target=self._mqtt_connect_func)
                self.mqtt_thread_running = True
                self.mqtt_thread.start()
        return self.mqtt_client

    def grill_message(self, client, userdata, message):
        _LOGGER.info("grill_message: message.topic = %s, message.payload = %s", message.topic, message.payload)
        _LOGGER.debug(f"Token Time Remaining:{self.token_remaining()} MQTT Time Remaining:{self.mqtt_url_remaining()}")
        if message.topic.startswith("prod/thing/update/"):
            grill_id = message.topic[len("prod/thing/update/"):]
            self.grill_status[grill_id] = json.loads(message.payload)
            if grill_id in self.grill_callbacks:
                for callback in self.grill_callbacks[grill_id]:
                    callback()

    def grill_connect(self, client, userdata, flags, rc):
        _LOGGER.info("Grill Connected")
        for grill in self.grills:
            grill_id = grill["thingName"]
            if grill_id in self.grill_status:
                del self.grill_status[grill_id]
            client.subscribe(
                ("prod/thing/update/{}".format(grill_id), 1))
            self.update_state(grill_id)

    def mqtt_log(self, client, userdata, level, buf):
        _LOGGER.debug("MQTT Log Level: %s, MQTT Log BUF: %s", level, buf)

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

    def get_features_for_device(self, thingName):
        if thingName not in self.grill_status:
            return None
        return self.grill_status[thingName]["features"]

    def get_cloudconnect(self, thingName):
        if thingName not in self.grill_status:
            return False
        return self.mqtt_thread_running

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
        if state is None:
            return None
        for accessory in state["acc"]:
            if accessory["uuid"] == accessory_id:
                return accessory
        return None

    async def start(self):
        await self.update_grills()
        await self.get_mqtt_client(self.grill_connect, self.grill_message, self.mqtt_log, self.grill_subscribe)
        delay = 30
        _LOGGER.info(f"Call_Later in: {delay} seconds")
        self.task = self.loop.call_later(delay, self.syncmain)

    def syncmain(self):
        _LOGGER.debug(f"@Call_Later SyncMain CreatingTask for async Main.")
        self.hass.async_create_task(self.main())

    async def main(self):
        _LOGGER.info(f"Current Main Loop Time: {time.time()}")
        _LOGGER.info(f"MQTT Logger Token Time Remaining:{self.token_remaining()} MQTT Time Remaining:{self.mqtt_url_remaining()}")
        if self.mqtt_url_remaining() < 60 and self.mqtt_thread_running:
            self.mqtt_thread_refreshing = True
            self.mqtt_client.disconnect()
            self.mqtt_client = None
            await self.get_mqtt_client(self.grill_connect, self.grill_message, self.mqtt_log, self.grill_subscribe)
            self.mqtt_thread_refreshing = False
        _LOGGER.info(f"Call_Later @: {self.mqtt_url_expires}")
        delay = self.mqtt_url_remaining()
        if delay < 30:
            delay = 30
        self.task = self.loop.call_later(delay, self.syncmain)

    async def kill(self):
        if self.mqtt_thread_running:
            _LOGGER.info(f"Killing Task")
            _LOGGER.debug(f"Task Info: {self.task}")
            self.task.cancel()
            _LOGGER.debug(f"TaskCancelled Status: {self.task.cancelled()}")
            _LOGGER.debug(f"Task Info: {self.task}")
            self.task = None
            _LOGGER.debug(f"Task Info: {self.task}")
            self.mqtt_thread_running = False
            self.mqtt_client.disconnect()
            self.mqtt_client = None
            self.mqtt_url_expires = time.time()
            for grill in self.grills:
                grill_id = grill["thingName"]
                for callback in self.grill_callbacks[grill_id]:
                    callback()
        else:
            _LOGGER.info(f"Task Already Dead")

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
