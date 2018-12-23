# audio_server.py
# Created by: VectorHax
# Created on: December 23, 2018

# The audio server that handles sending out audio packets to connected clients

import sys

try:
  # The global native libs
  import datetime
  import multiprocessing
  import queue
  import socket
  import threading
  import time

  # Imports brought in via pip
  import pydub

  # The local imports
  import constants
  import util_func


except Exception as import_error:
  print("Audio Server failed to import: ", import_error)

class AudioServer(multiprocessing.Process):
  CLIENT_SOCKET_TIMEOUT = .2
  CLIENT_SOCKET_BACKLOG = 5

  SERVER_SOCKET_TIMEOUT = .2
  SERVER_SOCKET_BACKLOG = 5

  FRAMES_PER_PACKET = 10
  SEND_FRAME_SIZE = FRAMES_PER_PACKET * constants.AUDIO_BYTE_FRAME_SIZE

  def __init__(self):
    multiprocessing.Process.__init__(self)

    self._server_status_queue = multiprocessing.Queue()

    self._client_thread_list = []

    self._server_ip = ""
    self._server_socket = None

    self._audio_data_queue = multiprocessing.Queue()
    self._audio_data_thread = None
    return

  def __del__(self):

    return

  def run(self):
    self._init_data_thread()
    while self._server_status_queue.empty():
      if not self._server_socket:
        self._init_server_socket()
      else:
        self._accept_clients()

    self._audio_data_thread.join()

    while not self._server_status_queue.empty():
      self._server_status_queue.get()

    while not self._audio_data_queue.empty():
      self._audio_data_queue.get()

    print("Closed Audio Server loop")
    return

  def stop(self):
    self._server_status_queue.put(constants.PROCESS_KILL_WORD)
    return

  def load_audio_data(self, file_location):
    try:
      audio_file = pydub.AudioSegment.from_wav(file_location)
      audio_data = audio_file.raw_data
      prev_audio_index = 0
      current_audio_index = self.SEND_FRAME_SIZE

      while current_audio_index < len(audio_data)/10:
        audio_data_chunk = audio_data[prev_audio_index:current_audio_index]
        
        prev_audio_index = current_audio_index
        current_audio_index += self.SEND_FRAME_SIZE
        #print("Adding audio data onto the queue")
        self._audio_data_queue.put(audio_data_chunk)

    except Exception as load_audio_error:
      print("Failed to load the audio: ", load_audio_error)
    return

  def _init_data_thread(self):
    self._audio_data_thread = threading.Thread(target=self._data_thread_func,
                                               args=())
    self._audio_data_thread.start()
    return

  def _data_thread_func(self):
    while self._server_status_queue.empty():
      if not self._audio_data_queue.empty():
        audio_data = self._audio_data_queue.get()
        self._handle_audio_data(audio_data)
        self._wait_until_client_ready()

    while not self._audio_data_queue.empty():
      self._audio_data_queue.get()
      time.sleep(.01)

    for client_thread in self._client_thread_list:
      client_thread.stop()
      client_thread.join()
      print("Closed a client thread")

    print("Left the data thread func")
    return

  def _handle_audio_data(self, audio_data):
    try:
      for client_thread in self._client_thread_list:
        if client_thread.is_ready():
          #current_time = datetime.datetime.now()
          packet_message = {constants.AUDIO_PAYLOAD_STR: list(audio_data)}
          #packet_message.update({constants.TIMESTAMP_STR: current_time})
          client_thread.add_packet_message(packet_message)
        else:
          pass
          #print("Client wasn't ready")
    
    except Exception as handle_data_error:
      print("Got the error handling data: ", handle_data_error)
    return

  def _wait_until_client_ready(self):
    for client_thread in self._client_thread_list:
      if client_thread.is_alive():
        while (not client_thread.is_ready()) and client_thread.is_alive():
          pass
      else:
        self._client_thread_list.remove(client_thread)

  def _init_server_socket(self):
    try:
      self._server_ip = util_func.get_own_ip()

      self._server_socket = socket.socket()
      self._server_socket.settimeout(self.SERVER_SOCKET_TIMEOUT)
      self._server_socket.bind((self._server_ip, constants.AUDIO_CLIENT_PORT))
      self._server_socket.listen(self.SERVER_SOCKET_BACKLOG)

    except Exception as server_socket_error:
      self._close_server_socket()

    return

  def _close_server_socket(self):
    if self._server_socket:
      self._server_socket.close()
    
    self._server_socket = None
    return

  def _accept_clients(self):
    try:
      # TODO: Want to design the client map for more features
      client_socket, client_address = self._server_socket.accept()
      client_thread = ClientThread(client_socket)
      client_thread.start()
      self._client_thread_list.append(client_thread)

    except socket.timeout:
      pass
    except Exception as accept_client_error:
      print("Got the unhandled error of: ", accept_client_error)

    return

class ClientThread(threading.Thread):
  INVALID_PACKET_TYPE = "The packet type must be a dict"

  def __init__(self, client_socket):
    threading.Thread.__init__(self)

    self._client_socket = client_socket

    self._status_queue = queue.Queue()
    self._packet_queue = queue.Queue()

    self._client_ready = True
    return

  def __del__(self):
    return

  def run(self):
    print("Client Thread starting")
    while self._status_queue.empty():
      if not self._packet_queue.empty():
        packet_message = self._packet_queue.get()
        self._handle_packet_message(packet_message)


    self._client_ready = False
    self._close_client_socket()

    while not self._status_queue.empty():
      self._status_queue.get()

    while not self._packet_queue.empty():
      self._packet_queue.get()

    print("Closed Client Thread")
    return

  def stop(self):
    self._stop_thread()
    return

  def is_ready(self):
    client_thread_status = self._client_ready
    return client_thread_status

  def add_packet_message(self, packet_message):
    assert isinstance(packet_message, dict), self.INVALID_PACKET_TYPE
    self._packet_queue.put(packet_message)
    return

  def _handle_packet_message(self, packet_message):
    self._client_ready = False
    self._send_packet_message(packet_message)
    #start_time = datetime.datetime.now()
    self._get_ready_response()
    #end_time = datetime.datetime.now()
    #delta_time = (end_time - start_time).total_seconds()
    #print("Took: ", delta_time, " seconds for ready")

    self._client_ready = True

    return

  def _send_packet_message(self, packet_message):
    if self._client_socket:
      try:
        util_func.send_json_socket(self._client_socket, packet_message)
      except Exception as send_packet_error:
        print("Had an error sending the packet: ", send_packet_error)
        self._stop_thread()
    return

  def _get_ready_response(self):
    if self._client_socket:
      try:
        ready_message = util_func.receive_json_socket(self._client_socket)

        if not ready_message:
          print("Never got a ready message")
          self._stop_thread()

      except Exception as ready_message_error:
        print("Got the ready message error: ", ready_message_error)
        self._stop_thread()

    return

  def _stop_thread(self):
    self._status_queue.put(constants.PROCESS_KILL_WORD)
    self._close_client_socket()
    return

  def _close_client_socket(self):
    if self._client_socket:
      self._client_socket.shutdown(socket.SHUT_RDWR)
      self._client_socket.close()
    self._client_socket = None
    return


if __name__ == '__main__':
  import audio_client

  print("Creating the server")
  test_audio_server = AudioServer()
  test_audio_server.start()

  time.sleep(1)

  print("Creating a client")
  test_audio_client = audio_client.AudioClient(util_func.get_own_ip())
  test_audio_client.start()

  time.sleep(5)
  print("Sending out audio data")
  test_audio_server.load_audio_data("audio/test.wav")


  time.sleep(5)

  print("Closing")
  test_audio_client.stop()
  test_audio_client.join()
  print("Client Closed")
  test_audio_server.stop()
  test_audio_server.join()
  print("ALL DONE")
