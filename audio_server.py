# audio_server.py
# Create by: Dale Best
# October 27th, 2018

# The process that handles the audio server

import pydub
import util_func
import multiprocessing
import threading
import socket
import time
import datetime

class AudioServer(multiprocessing.Process):
    CLIENT_PORT = 1250

    SOCKET_TIMEOUT = 1
    SOCKET_BACKLOG = 5

    AUDIO_RATE = 44100
    AUDIO_BYTE_PER_FRAME = 4
    AUDIO_FRAME_SIZE = 1024
    CHUNKS_PER_SEND = 5
    AUDIO_CHUNK_SIZE = AUDIO_BYTE_PER_FRAME * AUDIO_FRAME_SIZE
    AUDIO_MESSAGE_SIZE = CHUNKS_PER_SEND * AUDIO_CHUNK_SIZE

    SPEAKER_LOC_STR = "speaker_location"
    AUDIO_PAYLOAD_STR = "audio_payload"

    def __init__(self):
        self._server_running = multiprocessing.Queue()
        self._client_thread_running = multiprocessing.Queue()

        self._client_list = []
        self._client_thread = None
        self._server_thread = None
        self._server_socket = None

        self._audio_file = None
        self._audio_data = multiprocessing.Queue()
        self._prev_audio_index = 0
        self._current_audio_index = 0

        multiprocessing.Process.__init__(self)
        return

    def __del__(self):
        return

    def run(self):

        self._init_server_socket()
        self.start_client_thread()

        while self._server_running.empty():
            try:
                if not self._server_socket:
                    self._init_server_socket()
                else:
                    self._send_package_to_client()

            except Exception as server_loop_error:
                print("Server loop ran into an error of : ", server_loop_error)

        self._server_running.get()
        self.stop_client_thread()
        while self._audio_data.qsize() > 0:
            try:
                self._audio_data.get()
            except Exception as get_error:
                print("Had the follow issues emptying: ", get_error)
                self._audio_data.close()
                break
        return

    def stop_server_running(self):
        self._server_running.put("KILL")
        return

    def load_audio_data(self, file_location):
        try:
            print("Loading the song data")
            audio_file = pydub.AudioSegment.from_wav(file_location)
            audio_data = audio_file.raw_data
            prev_audio_index = 0
            current_audio_index = self.AUDIO_MESSAGE_SIZE

            while current_audio_index < len(audio_data):
                audio_data_chunk = audio_data[prev_audio_index:current_audio_index]
                prev_audio_index = current_audio_index
                current_audio_index += self.AUDIO_MESSAGE_SIZE
                self._audio_data.put(audio_data_chunk)
            print("Done loading: ", self._audio_data.qsize())

        except Exception as load_audio_error:
            print("Failed to load the audio data because: ", load_audio_error)
        return

    def done_playing_audio(self):
        return self._prev_audio_index == self._current_audio_index

    def _init_server_socket(self):
        server_ip = util_func.get_own_ip()

        self._server_socket = socket.socket()
        self._server_socket.settimeout(self.SOCKET_TIMEOUT)
        self._server_socket.bind((server_ip, self.CLIENT_PORT))
        self._server_socket.listen(self.SOCKET_BACKLOG)
        print("Opened up the server port")
        return

    def _send_package_to_client(self):
        if self._audio_data.qsize() >= self.CHUNKS_SENT:
            for client in self._client_list:
                try:
                    audio_message_data = []
                    for index in range(self.CHUNKS_SENT):
                        audio_message_data.append(list(self._audio_data.get()))
                    util_func.send_json_socket(client, {self.AUDIO_PAYLOAD_STR: audio_message_data,
                                                        "Timestamp":str(datetime.datetime.now())})

                except Exception as client_send_error:
                    client.close()
                    self._client_list.remove(client)
                    print("Got the client send issue of :", client_send_error)
        return

    def start_client_thread(self):
        self._client_thread = threading.Thread(target=self._find_client_thread,
                                               args=())
        self._client_thread.start()
        return

    def _find_client_thread(self):
        while self._client_thread_running.empty():
            if self._server_socket:
                self._find_client()
            time.sleep(.5)

        self._client_thread_running.get()
        return

    def _find_client(self):
        try:
            client_socket, client_address = self._server_socket.accept()
            client_socket.settimeout(self.SOCKET_TIMEOUT)

            self._client_list.append(client_socket)
            print("Found a client")

        except socket.timeout:
            pass
        except Exception as find_client_error:
            print("Got the follow issue of: ", find_client_error)

        return

    def stop_client_thread(self):
        self._client_thread_running.put("KILL")
        self._client_thread.join()

        self.clear_client_list()
        return

    def clear_client_list(self):
        for client in self._client_list:
            client.close()
            self._client_list.remove(client)
        if self._server_socket:
            self._server_socket.close()
        return


if __name__ == '__main__':
    test_audio_server = AudioServer()
    test_audio_server.start()
    test_audio_server.load_audio_data("audio/sample.wav")

    time.sleep(10)
    print("Stopping")
    test_audio_server.stop_server_running()
    test_audio_server.join()

    time.sleep(3)
    print("Done")
