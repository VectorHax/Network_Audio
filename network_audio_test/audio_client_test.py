# audio_client_test.py
# Created by: Vectorhax
# Created on: June 2nd, 2019

import time
import socket

import pydub

from network_audio_classes import constants
from network_audio_classes.client_socket_thread import ClientSocketThread
from audio_client_application import AudioClientApplication


if __name__ == '__main__':

    server_socket = socket.socket()
    server_socket.settimeout(2.0)
    server_socket.bind(("localhost", constants.AUDIO_CLIENT_PORT))
    server_socket.listen(5)

    test_client = AudioClientApplication("localhost")
    test_client.start()

    time.sleep(2.0)

    client_connection, client_ip = server_socket.accept()
    server_socket_thread = ClientSocketThread(client_connection)
    server_socket_thread.start()

    file_location = "audio/sample.wav"
    audio_file = pydub.AudioSegment.from_wav(file_location)
    audio_data = audio_file.raw_data

    playback_len = int(len(audio_data) / 10)

    prev_audio_index = 0
    current_audio_index = constants.AUDIO_BYTE_FRAME_SIZE

    while current_audio_index < playback_len:
        audio_data_chunk = audio_data[prev_audio_index:current_audio_index]
        audio_message = {constants.AUDIO_PAYLOAD_STR: list(audio_data_chunk)}
        server_socket_thread.add_outgoing_message(audio_message)

        prev_audio_index = current_audio_index
        current_audio_index += constants.AUDIO_BYTE_FRAME_SIZE

        time.sleep(constants.AUDIO_SLEEP_TIME)

    time.sleep(10)
    print("Stopping")
    test_client.stop()
    server_socket_thread.stop()

    print("DONE")