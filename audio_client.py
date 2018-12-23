# audio_client.py
# Created by: Dale Best
# Created on: December 22nd, 2018

import sys

try:
  # The global native python libraries
  import multiprocessing
  import socket
  import threading
  import time

  # The imports brought in via pip

  # The imports brought in locally
  import audio_player
  import constants
  import util_func

except Exception as import_error:
  print("Audio Client failed to import: ", import_error)
  sys.exit()


class AudioClient(multiprocessing.Process):
  # Class wide static variables
  INVALID_HOST_STRING = "host_ip must be a string"

  CLIENT_TIMEOUT = .2

  # __init__(self, host_ip): The class initilizer which takes a host_ip string
  # of the ip address of the audio server in which it will spin up to connect
  # and collect audio packets to play through it's audio player
  def __init__(self, host_ip):
    assert isinstance(host_ip,str), self.INVALID_HOST_STRING
    multiprocessing.Process.__init__(self)

    self._client_status_queue = multiprocessing.Queue()
    self._audio_data_queue = multiprocessing.Queue()

    self._audio_player = None
    self._client_socket = None
    self._host_ip = host_ip

    self._audio_thread = None

    self._client_running = False
    return

  # __del__(self): The deallocater for the class which is called when freed
  def __del__(self):
    if self._client_running:
      self.stop()
    return

  # run(self): The function that is called when the thread starts and has
  # the attempt to connect to the server and when connected it will keep
  # collecting packets to be put onto the audio player
  def run(self):
    self._client_running = True

    self._start_audio_player()
    self._create_audio_thread()

    while self._client_status_queue.empty():
      if self._client_socket:
        self._get_packet_from_server()
      else:
        self._connect_to_server()

    self._audio_player.stop()
    return

  # stop(self): Called to stop the class by putting a kill message on the
  # internal status queue signalling all process to stop
  def stop(self):
    self._client_status_queue.put(constants.PROCESS_KILL_WORD)
    
    self._client_running = False
    return

  # client_audio_request(self, audio_request): Takes in a dict audio_request
  # that will then be put onto the audio player
  # It is meant to be a debug function
  def client_audio_request(self, audio_request):
    self._audio_data_queue.put(audio_request)
    return

  # The class private functions

  def _start_audio_player(self):
    self._audio_player = audio_player.AudioPlayer()
    self._audio_player.start()
    return

  def _create_audio_thread(self):
    self._audio_thread = threading.Thread(target=self._handle_packet_thread,
                                           args=())
    self._audio_thread.start()
    return

  def _handle_packet_thread(self):
    audio_request = {}
    while self._client_status_queue.empty():

      if not self._audio_data_queue.empty():
        audio_request = self._audio_data_queue.get()
        self._audio_player.add_audio_request(audio_request)
        self._audio_player.wait_for_audio_player()
        self._send_ready_message()

    while not self._audio_data_queue.empty():
      self._audio_data_queue.get()
      time.sleep(.01)

    return

  def _get_packet_from_server(self):
    try:
      client_json_message = util_func.receive_json_socket(self._client_socket)
      if client_json_message:
        self._audio_data_queue.put(client_json_message)
      else:
        self._close_client_socket()

    except socket.timeout:
      pass

    except Exception as get_packet_error:
      print("Got the unhandled error of: ", get_packet_error)
      self._close_client_socket()
    return

  def _close_client_socket(self):
    if self._client_socket:
      self._client_socket.close()

    self._client_socket = None
    return

  def _connect_to_server(self):
    try:
      self._client_socket = socket.socket()
      self._client_socket.settimeout(self.CLIENT_TIMEOUT)
      self._client_socket.connect((self._host_ip,constants.AUDIO_CLIENT_PORT))
      print("Client Connected")
    except Exception as server_connect_error:
      self._close_client_socket()
    return

  def _send_ready_message(self):
    if self._client_socket:
      try:
        ready_message = {constants.CLIENT_READY_STR: True}
        util_func.send_json_message(self._client_socket, ready_message)
      except Exception as ready_send_error:
        self._close_client_socket()

    return

if __name__ == '__main__':
  import pydub

  CHUNK_SIZE = 4 * 1024
  SENT_CHUNKS = 5
  AUDIO_CHUNK_SIZE = SENT_CHUNKS * CHUNK_SIZE
  AUDIO_RATE = 44100
  CHUNK_TIMEOUT = 1024/AUDIO_RATE
  AUDIO_TIMEOUT = SENT_CHUNKS * CHUNK_TIMEOUT

  test_audio_client = AudioClient(util_func.get_own_ip())
  test_audio_client.start()

  time.sleep(3)

  file_location = "audio/test.wav"
  audio_file = pydub.AudioSegment.from_wav(file_location)
  audio_data = audio_file.raw_data
  prev_audio_index = 0
  current_audio_index = AUDIO_CHUNK_SIZE

  while current_audio_index < len(audio_data)/20:
    audio_data_chunk = audio_data[prev_audio_index:current_audio_index]
    prev_audio_index = current_audio_index
    current_audio_index += AUDIO_CHUNK_SIZE
    test_audio_client.client_audio_request({"Audio_Payload":bytes(audio_data_chunk)})

  time.sleep(5)
  print("Stopping")
  test_audio_client.stop()
  print("Done")
