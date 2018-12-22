# The entry point for the application

import time
import audio_server
import audio_client
import util_func


if __name__ == '__main__':
    test_audio_server = audio_server.AudioServer()
    test_audio_server.start()
    test_audio_server.load_audio_data("audio/sample.wav")

    time.sleep(3)
    test_audio_client = audio_client.AudioClient(util_func.get_own_ip())
    test_audio_client.start()


    time.sleep(10)

    print("Stopping the client")
    test_audio_client.stop()
    test_audio_client.join(timeout=5)

    print("Stopping the server")
    test_audio_server.stop_server_running()
    test_audio_server.join(timeout=5)

    print("Fully done")