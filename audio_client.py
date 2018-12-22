# The client side code for the Network audio

import audio_player

import multiprocessing
import pyaudio
import pydub
import socket
import time
import util_func
import threading


class AudioClient(multiprocessing.Process):
    AUDIO_FORMAT = 8
    AUDIO_CHANNELS = 2
    AUDIO_RATE = 44100
    AUDIO_OUTPUT = True

    CLIENT_PORT = 1250
    CLIENT_TIMEOUT = .05

    def __init__(self, host_ip):
        multiprocessing.Process.__init__(self)

        self._client_status_queue = multiprocessing.Queue()
        self._audio_data_queue = multiprocessing.Queue()

        self._audio_player = None
        self._client_socket = None
        self._host_ip = host_ip

        self._client_running = False
        return

    def __del__(self):
        if self._client_running:
            self.stop()
        return

    def run(self):
        print("Starting up the client loop")
        self._start_audio_player()

        while self._client_status_queue.empty():
            try:
                if self._client_socket:
                    self.get_packet_from_server()
                else:
                    self.connect_to_server()

            except Exception as client_loop_error:
                print("The client got the following error: ", client_loop_error)
                if self._client_socket:
                    self._client_socket.close()
                self._client_socket = None

        self._client_status_queue.get()
        self._audio_player.stop()
        return

    def stop(self):
        self._client_status_queue.put("KILL")
        self._client_running = False
        return

    def client_audio_request(self, audio_request):
        self._audio_data_queue.put(audio_request)
        return

    def connect_to_server(self):
        try:
            self._client_socket = socket.socket()
            self._client_socket.connect((self._host_ip, self.CLIENT_PORT))
            self._client_socket.settimeout(self.CLIENT_TIMEOUT)
            print("Client connected")
        except Exception as connect_to_server_issue:
            self._client_socket = None
        return

    def get_packet_from_server(self):
        try:
            client_json_message = util_func.receive_json_socket(self._client_socket)
            if client_json_message:
                self._audio_data_queue.put(client_json_message)
        except socket.timeout:
            pass
        return

    def _start_audio_player(self):
        self._audio_player = audio_player.AudioPlayer()
        self._audio_player.start()
        self._client_running = True

        self._audio_unload_thread = threading.Thread(target=self._unload_audio_packet_thread,
                                                     args=())
        self._audio_unload_thread.start()
        return

    def _unload_audio_packet_thread(self):
        while self._client_status_queue.empty():
            audio_request = {}
            while not self._audio_data_queue.empty():
                audio_request = self._audio_data_queue.get()
                self._audio_player.add_audio_request(audio_request)

        while not self._audio_data_queue.empty():
            self._audio_data_queue.get()
            time.sleep(.01)

        print("Finished the side thread")
        return

#TODO: Create a function that returns if ready to accept next packet

if __name__ == "__main__":
    CHUNK_SIZE = 4 * 1024
    SENT_CHUNKS = 5
    AUDIO_CHUNK_SIZE = SENT_CHUNKS * CHUNK_SIZE
    AUDIO_RATE = 44100
    CHUNK_TIMEOUT = 1024/AUDIO_RATE
    AUDIO_TIMEOUT = SENT_CHUNKS * CHUNK_TIMEOUT

    test_audio_client = AudioClient(util_func.get_own_ip())
    test_audio_client.start()

    time.sleep(3)

    file_location = "audio/sample.wav"
    audio_file = pydub.AudioSegment.from_wav(file_location)
    audio_data = audio_file.raw_data
    prev_audio_index = 0
    current_audio_index = AUDIO_CHUNK_SIZE

    while current_audio_index < len(audio_data)/5:
      audio_data_chunk = audio_data[prev_audio_index:current_audio_index]
      prev_audio_index = current_audio_index
      current_audio_index += AUDIO_CHUNK_SIZE
      test_audio_client.client_audio_request({"audio_payload":list(audio_data_chunk)})
      time.sleep(AUDIO_TIMEOUT)

    time.sleep(5)
    print("Stopping")
    print("Done")
    test_audio_client.stop()
