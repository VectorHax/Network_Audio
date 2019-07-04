# audio_server_application.py
# Created by: Vectorhax
# Created on: June 2nd, 2019

# The audio client server application
# **********************************Import*********************************** #

import sys

try:
    # The global libraries built into python
    import time
    import queue
    import socket
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

except Exception as import_failure:
    print("Audio Server Application failed to import: ", str(import_failure))
    sys.exit()


# *************************Audio Server Application************************** #

class AudioServerApplication(multiprocessing.Process):
    PROCESS_NAME = "Audio Server Application"

    def __init__(self, audio_location):
        multiprocessing.Process.__init__(self, name=self.PROCESS_NAME)

        self._audio_location = audio_location
        self._audio_file = pydub.AudioSegment.from_wav(self._audio_location)
        self._audio_data = self._audio_file.raw_data

        self._prev_audio_index = 0
        self._current_audio_index = constants.AUDIO_BYTE_FRAME_SIZE

        self._network_process = None

        self._server_running = multiprocessing.Value("b", True)
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
                    audio_data_chunk = self._audio_data[self._prev_audio_index:
                                                        self._current_audio_index]
                    audio_message = {constants.AUDIO_PAYLOAD_STR:
                                     list(audio_data_chunk)}
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
