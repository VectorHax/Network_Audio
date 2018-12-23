#util_func.py
# Created by: VectorHax
# Created on: Dec 22nd, 2018

import sys

try:
  # The global native python imports
  import json
  import socket

except Exception as import_error:
  print("Util fun failed to import: ", import_error)
  sys.exit()


IP_TEST_ADDRESS = "10.255.255.255"
IP_TEST_PORT = 1
IP_TEST_INDEX = 0
IP_DEFAULT_ADDRESS = "127.0.0.1"

def receive_json_socket(sock):
    received_json = {}
    length_str = ""
    message_buffer = ""

    read_char = sock.recv(1)

    if read_char:
      while read_char != '\n'.encode():
        length_str += read_char.decode()
        read_char = sock.recv(1)

      length_int = int(length_str)
      pending_bytes = length_int

      while pending_bytes:
        temp_buffer = sock.recv(pending_bytes)
        message_buffer += temp_buffer.decode()
        pending_bytes -= len(temp_buffer)

      received_json = json.loads(message_buffer)

    return received_json


def send_json_socket(sock, data):
  serialized_data = json.dumps(data)
  len_string = str("%d\n" % len(serialized_data))
  send_string = len_string + serialized_data
  sock.sendall(send_string.encode())
  
  return


def get_own_ip():

    temp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    try:
        temp_socket.connect((IP_TEST_ADDRESS, IP_TEST_PORT))
        device_ip = temp_socket.getsockname()[IP_TEST_INDEX]
    except Exception as e:
        print("Had to default with finding the ip: ", e)
        device_ip = IP_DEFAULT_ADDRESS
    finally:
        temp_socket.close()
    return device_ip

