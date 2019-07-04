# audio_server_test.py
# Created by: Vectorhax
# Created on: July 3rd, 2019

import time

from network_audio_classes import util_func
from audio_client_application import AudioClientApplication
from audio_server_application import AudioServerApplication


if __name__ == '__main__':

    current_ip = util_func.get_own_ip()

    test_server = AudioServerApplication("audio/sample.wav")
    test_server.start()

    time.sleep(2)

    test_client = AudioClientApplication(current_ip)
    test_client.start()

    time.sleep(10)

    test_server.stop()
    print("Server closed")

    time.sleep(5)

    print("Starting the server again")
    test_server = AudioServerApplication("audio/sample.wav")
    test_server.start()

    time.sleep(10)

    print("CLOSING")

    test_client.stop()
    print("Client closed")
    test_server.stop()
    print("Server closed")
