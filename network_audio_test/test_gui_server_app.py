
from network_audio_classes import util_func
from audio_client_application import AudioClientApplication
from audio_server_gui_app import AudioGUIServerApplication


if __name__ == '__main__':
    server_ip = util_func.get_own_ip()
    print("Starting server with ip of: ", server_ip)

    test_client = AudioClientApplication(server_ip)
    test_client.start()
    test_client.set_location(-1.0)

    #test_client_B = AudioClientApplication(server_ip)
    #test_client_B.start()
    #test_client_B.set_location(1.0)

    AudioGUIServerApplication()

    test_client.stop()
    #test_client_B.stop()
    print("DONE")