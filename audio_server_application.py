# audio_server_application.py
# Created by: Vectorhax
# Created on: June 2nd, 2019

# The audio client server application
# **********************************Import*********************************** #

# The global libraries built into python
import time
import queue
import ctypes
import socket
import datetime
import threading
import multiprocessing
from threading import Thread

# The brought in libraries via pip
import pydub

# The local libraries
from network_audio_classes import constants
from network_audio_classes import util_func
from network_audio_classes.audio_player_process import AudioPlayer
from network_audio_classes.client_socket_thread import ClientSocketThread
from network_audio_classes.server_network_process import ServerNetworkProcess


# *************************Audio Server Application************************** #

class AudioServerApplication(multiprocessing.Process):
    PROCESS_NAME: str = "Audio Server Application"

    def __init__(self):
        multiprocessing.Process.__init__(self, name=self.PROCESS_NAME)

        self._audio_location: str = ""

        self._audio_file: pydub.AudioSegment
        self._audio_file = None

        self._audio_data: bytes = bytes([])

        self._prev_audio_index = 0
        self._current_audio_index = constants.AUDIO_BYTE_FRAME_SIZE

        self._network_process: ServerNetworkProcess
        self._network_process = None

        self._server_running = multiprocessing.Value(ctypes.c_bool, True)
        return

    def run(self):
        self._network_process = ServerNetworkProcess()
        self._network_process.start()

        first_client_connected = False

        while self._server_running.value:
            if not first_client_connected:
                if self._network_process.clients_connected > 0:
                    first_client_connected = True
                else:
                    pass

            else:
                try:
                    current_time = datetime.datetime.now()

                    audio_data_chunk = self._audio_data[self._prev_audio_index:
                                                        self._current_audio_index]
                    audio_message = {constants.AUDIO_PAYLOAD_STR:
                                     list(audio_data_chunk)}
                    audio_message.update({constants.TIMESTAMP_STR:
                                          current_time.strftime("%Y-%m-%d %H:%M:%S.%f")})
                    self._network_process.add_audio_packet(audio_message, True)

                    self._prev_audio_index = self._current_audio_index
                    self._current_audio_index += constants.AUDIO_BYTE_FRAME_SIZE

                except queue.Full:
                    pass

            time.sleep(constants.AUDIO_SLEEP_TIME)

        print("Stopping audio server application")
        self._network_process.stop()
        print("Server network process stopped")
        return

    def stop(self):
        print("Stopping Server application")
        self._server_running.value = False
        self.join()
        return
