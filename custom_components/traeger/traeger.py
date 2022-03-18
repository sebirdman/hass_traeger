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
        self.grills_active = False
        self.hass = hass
        self.loop = hass.loop
        self.task = None
        self.mqtt_url = None
        self.mqtt_client = None
        self.grill_status = {}
        self.access_token = None
        self.token = None
        self.token_expires = 0
        self.mqtt_url_expires = time.time()
        self.request = request_library
        self.grill_callbacks = {}
        self.mqtt_client_inloop = False
        self.autodisconnect = True

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
        await self.send_command(thingName, "90")

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
                self.mqtt_client_inloop = True
                self.mqtt_client.loop_forever()
                self.mqtt_client_inloop = False
                while (self.mqtt_url_remaining() < 60 or self.mqtt_thread_refreshing) and self.mqtt_thread_running:
                    time.sleep(1)
        _LOGGER.debug(f"Should be the end of the thread.")

    async def get_mqtt_client(self):
        await self.refresh_mqtt_url()
        if self.mqtt_client != None:
            _LOGGER.debug(f"ReInit Client")
            #self.mqtt_client.reinitialise()                            #Reint doesn't accept Transport.
            #self.mqtt_client = mqtt.Client(transport="websockets")
        else:
            self.mqtt_client = mqtt.Client(transport="websockets")
            #self.mqtt_client.on_log = self.mqtt_onlog                  #logging passed via enable_logger this would be redundant.
            self.mqtt_client.on_connect = self.mqtt_onconnect
            self.mqtt_client.on_connect_fail = self.mqtt_onconnectfail
            self.mqtt_client.on_subscribe = self.mqtt_onsubscribe
            self.mqtt_client.on_message = self.mqtt_onmessage
            if _LOGGER.level <= 10:                                     #Add these callbacks only if our logging is Debug or less.
                self.mqtt_client.enable_logger(_LOGGER)
                self.mqtt_client.on_publish = self.mqtt_onpublish       #We dont Publish to MQTT
                self.mqtt_client.on_unsubscribe = self.mqtt_onunsubscribe
                self.mqtt_client.on_disconnect = self.mqtt_ondisconnect
                self.mqtt_client.on_socket_open = self.mqtt_onsocketopen
                self.mqtt_client.on_socket_close = self.mqtt_onsocketclose
                self.mqtt_client.on_socket_register_write = self.mqtt_onsocketregisterwrite
                self.mqtt_client.on_socket_unregister_write = self.mqtt_onsocketunregisterwrite
                context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
                context.check_hostname = False
                context.verify_mode = ssl.CERT_NONE
                self.mqtt_client.tls_set_context(context)
                self.mqtt_client.reconnect_delay_set(min_delay=10, max_delay=160)
        mqtt_parts = urllib.parse.urlparse(self.mqtt_url)
        headers = {
            "Host": "{0:s}".format(mqtt_parts.netloc),
        }
        self.mqtt_client.ws_set_options(path="{}?{}".format(
        mqtt_parts.path, mqtt_parts.query), headers=headers)     
        _LOGGER.info(f"Thread Active Count:{threading.active_count()}")
        self.mqtt_client.connect(mqtt_parts.netloc, 443, keepalive=300)
        if self.mqtt_thread_running == False:
            self.mqtt_thread = threading.Thread(target=self._mqtt_connect_func)
            self.mqtt_thread_running = True
            self.mqtt_thread.start()

#===========================Paho MQTT Functions=======================================================
    def mqtt_onlog(self, client, userdata, level, buf):
        _LOGGER.debug(f"OnLog Callback. Client:{client} userdata:{userdata} level:{level} buf:{buf}")
    def mqtt_onconnect(self, client, userdata, flags, rc):
        _LOGGER.info("Grill Connected")
        for grill in self.grills:
            grill_id = grill["thingName"]
            if grill_id in self.grill_status:
                del self.grill_status[grill_id]
            client.subscribe(
                ("prod/thing/update/{}".format(grill_id), 1))
    def mqtt_onconnectfail(self, client, userdata):
        _LOGGER.debug(f"Connect Fail Callback. Client:{client} userdata:{userdata}")
        _LOGGER.warning("Grill Connect Failed! MQTT Client Kill.")
        self.hass.async_create_task(self.kill())                    #Shutdown if we arn't getting anywhere.
    def mqtt_onsubscribe(self, client, userdata, mid, granted_qos):
        _LOGGER.debug(f"OnSubscribe Callback. Client:{client} userdata:{userdata} mid:{mid} granted_qos:{granted_qos}")
        for grill in self.grills:
            grill_id = grill["thingName"]
            if grill_id in self.grill_status:
                del self.grill_status[grill_id]
            #self.update_state(grill_id)
            self.hass.async_create_task(self.update_state(grill_id))
    def mqtt_onmessage(self, client, userdata, message):
        _LOGGER.debug("grill_message: message.topic = %s, message.payload = %s", message.topic, message.payload)
        _LOGGER.info(f"Token Time Remaining:{self.token_remaining()} MQTT Time Remaining:{self.mqtt_url_remaining()}")
        if message.topic.startswith("prod/thing/update/"):
            grill_id = message.topic[len("prod/thing/update/"):]
            self.grill_status[grill_id] = json.loads(message.payload)
            if grill_id in self.grill_callbacks:
                for callback in self.grill_callbacks[grill_id]:
                    callback()
            if self.grills_active == False:                         #Go see if any grills are doing work.
                for grill in self.grills:                           #If nobody is working next MQTT refresh
                    grill_id = grill["thingName"]                   #It'll call kill.
                    state = self.get_state_for_device(grill_id)     #Maybe should be moved to ASYNC.
                    if state == None:
                        return
                    if state["connected"]:
                        if 4 <= state["system_status"] <= 8:
                            self.grills_active = True
    def mqtt_onpublish(self, client, userdata, mid):
        _LOGGER.debug(f"OnPublish Callback. Client:{client} userdata:{userdata} mid:{mid}")
    def mqtt_onunsubscribe(self, client, userdata, mid):
        _LOGGER.debug(f"OnUnsubscribe Callback. Client:{client} userdata:{userdata} mid:{mid}")
    def mqtt_ondisconnect(self, client, userdata, rc):
        _LOGGER.debug(f"OnDisconnect Callback. Client:{client} userdata:{userdata} rc:{rc}")
    def mqtt_onsocketopen(self, client, userdata, sock):
        _LOGGER.debug(f"Sock.Open.Report...Client: {client} UserData: {userdata} Sock: {sock}")
    def mqtt_onsocketclose(self, client, userdata, sock):
        _LOGGER.debug(f"Sock.Clse.Report...Client: {client} UserData: {userdata} Sock: {sock}")
    def mqtt_onsocketregisterwrite(self, client, userdata, sock):
        _LOGGER.debug(f"Sock.Regi.Write....Client: {client} UserData: {userdata} Sock: {sock}")
    def mqtt_onsocketunregisterwrite(self, client, userdata, sock):
        _LOGGER.debug(f"Sock.UnRg.Write....Client: {client} UserData: {userdata} Sock: {sock}")
#===========================/Paho MQTT Functions=======================================================

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

    async def start(self, delay):
        await self.update_grills()
        self.grills_active = True
        _LOGGER.info(f"Call_Later in: {delay} seconds.")
        self.task = self.loop.call_later(delay, self.syncmain)

    def syncmain(self):
        _LOGGER.debug(f"@Call_Later SyncMain CreatingTask for async Main.")
        self.hass.async_create_task(self.main())

    async def main(self):
        _LOGGER.debug(f"Current Main Loop Time: {time.time()}")
        _LOGGER.debug(f"MQTT Logger Token Time Remaining:{self.token_remaining()} MQTT Time Remaining:{self.mqtt_url_remaining()}")
        if self.mqtt_url_remaining() < 60:
            self.mqtt_thread_refreshing = True
            if self.mqtt_thread_running:
                self.mqtt_client.disconnect()
                self.mqtt_client = None
            await self.get_mqtt_client()
            self.mqtt_thread_refreshing = False
        _LOGGER.debug(f"Call_Later @: {self.mqtt_url_expires}")
        delay = self.mqtt_url_remaining()
        if delay < 30:
            delay = 30
        self.task = self.loop.call_later(delay, self.syncmain)

    async def kill(self):
        if self.mqtt_thread_running:
            _LOGGER.info(f"Killing Task")
            _LOGGER.debug(f"Task Info: {self.task}")
            self.task.cancel()
            _LOGGER.debug(f"Task Info: {self.task} TaskCancelled Status: {self.task.cancelled()}")
            self.task = None
            self.mqtt_thread_running = False
            self.mqtt_client.disconnect()
            while self.mqtt_client_inloop:                  #Wait for disconnect to finish
                await asyncio.sleep(0.25)
            self.mqtt_url_expires = time.time()
            for grill in self.grills:                       #Mark the grill(s) disconnected so they report unavail.
                grill_id = grill["thingName"]               #Also hit the callbacks to update HA
                self.grill_status[grill_id]["status"]["connected"] = False
                for callback in self.grill_callbacks[grill_id]:
                    callback()
        else:
            _LOGGER.info(f"Task Already Dead")

    async def api_wrapper(
        self, method: str, url: str, data: dict = {}, headers: dict = {}
    ) -> dict:
        """Get information from the API."""
        try:
            async with async_timeout.timeout(TIMEOUT):
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
