# audio_client_application.py
# Created by: Vectorhax
# Created on: June 2nd, 2019

# The audio client application

# **********************************Import*********************************** #
# The global libraries built into python
import time
import json
import queue
import ctypes
import socket
import datetime
import threading
import multiprocessing

# The local libraries
from network_audio_classes import constants
from network_audio_classes.audio_player_process import AudioPlayer
from network_audio_classes.client_socket_thread import ClientSocketThread

# *************************Audio Client Application************************** #

class AudioClientApplication(multiprocessing.Process):
    PROCESS_NAME: str = "Audio Client Application"

    # TODO: Want to have a way for the client to auto find the server
    def __init__(self, host_ip: str):
        multiprocessing.Process.__init__(self, name=self.PROCESS_NAME)

        self._audio_player: AudioPlayer
        self._audio_player = None

        self._client_socket: socket.socket
        self._client_socket = None
        

        self._host_ip: str = host_ip

        self._socket_thread: threading.Thread
        self._socket_thread = None

        self._client_connected = multiprocessing.Value(ctypes.c_bool, False)

        self._client_running = multiprocessing.Value(ctypes.c_bool, True)

        self._client_location = multiprocessing.Value(ctypes.c_float, 0.0)

        self._latency_list: list = []
        self._average_latency = multiprocessing.Value(ctypes.c_float, 0.0)

        return

    def run(self):
        self._audio_player = AudioPlayer()
        self._audio_player.start()

        self._start_socket_thread()

        while self._client_running.value:
            try:
                if self._socket_thread.pending_incoming_message():
                    incoming_message = self._socket_thread.get_incoming_message()
                    self._handle_incoming_message(incoming_message)

                self._audio_player.set_speaker_location(self._client_location.value)
                time.sleep(.001)

            except queue.Empty:
                pass

            except Exception as unhandled_error:
                print("Got unhandled error: ", unhandled_error)

        self._audio_player.stop()
        self._close_client_socket()
        return

    def stop(self):
        self._client_running.value = False
        self.join()
        return

    @property
    def average_latency(self) -> float:
        return self._average_latency.value

    @property
    def client_connected(self) -> bool:
        return self._client_connected.value

    def set_location(self, location: float) -> None:
        self._client_location.value = location
        return

    def _start_socket_thread(self) -> None:
        try:
            client_info = (self._host_ip, constants.AUDIO_CLIENT_PORT)

            self._client_socket = socket.socket()
            self._client_socket.connect(client_info)

            self._client_connected.value = True

            self._socket_thread = ClientSocketThread(self._client_socket)
            self._socket_thread.start()

        except socket.error:
            self._close_client_socket()

        return

    def _close_client_socket(self) -> None:
        if self._client_socket is not None:
            self._client_socket.close()

        if self._socket_thread is not None:
            self._socket_thread.stop()

        self._client_socket = None
        self._socket_thread = None
        self._client_connected.value = False
        return

    def _handle_incoming_message(self, incoming_message: dict) -> None:
        assert isinstance(incoming_message, dict)
        message_time = datetime.datetime.now()
        audio_payload = incoming_message.get(constants.AUDIO_PAYLOAD_STR)
        audio_timestamp_str = incoming_message.get(constants.TIMESTAMP_STR)

        if audio_payload is not None:
            byte_payload = bytes(audio_payload)
            incoming_message.update({constants.AUDIO_PAYLOAD_STR: byte_payload})
            self._audio_player.add_audio_request(incoming_message)

        if audio_timestamp_str is not None:
            audio_timestamp = datetime.datetime.strptime(audio_timestamp_str,
                                                         "%Y-%m-%d %H:%M:%S.%f")
            audio_time_delta = (message_time - audio_timestamp).total_seconds()

            self._latency_list.append(audio_time_delta)

            if len(self._latency_list) > 1000:
                self._latency_list = self._latency_list[:500]

            self._average_latency.value = sum(self._latency_list)/len(self._latency_list)
        return


if __name__ == '__main__':

    try:
        ip = sys.argv[1]
        print("Connecting to server at: ", ip)
    except Exception as invalid_ip:
        print("Using default IP")
        ip = "localhost"

    test_client = AudioClientApplication(ip)
    test_client.start()

    try:
        while True:
            pass
    except Exception as app_break:
        pass

    test_client.stop()
