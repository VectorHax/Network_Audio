# client_socket_thread.py
# Created by: VectorHax
# Created on: April 15th, 2019

# A thread class that handles client socket communication with JSON messages

# **********************************Import*********************************** #

# The global libraries built into python
import time
import json
import queue
import socket
import threading
import multiprocessing
import multiprocessing.queues
from ast import literal_eval

# ************************Client Socket Thread Func************************** #


class ClientSocketThread(threading.Thread):
    THREAD_NAME: str = "Client Socket Thread"

    SOCKET_TIMEOUT: float = .5
    TERMINATING_CHARS: list = [b'\n', b'}', b'']
    STATUS_KEY: str = "Network_Alive"
    RESPONSE_MSG: dict = {"Network_Alive": True}

    def __init__(self,
                 client_socket: socket.socket,
                 in_message_queue: queue.Queue = queue.Queue(),
                 status_message: dict = None):
        assert isinstance(client_socket, socket.socket)

        threading.Thread.__init__(self, name=self.THREAD_NAME)

        if isinstance(in_message_queue, queue.Queue):
            self._incoming_message_queue = in_message_queue

        elif isinstance(in_message_queue, multiprocessing.queues.Queue):
            self._incoming_message_queue = in_message_queue

        else:
            self._incoming_message_queue = queue.Queue()

        self._outgoing_message_queue: queue.Queue = queue.Queue()

        self._client_socket: socket.socket = client_socket

        if self._client_socket.gettimeout() is None:
            self._client_socket.settimeout(self.SOCKET_TIMEOUT)

        self._thread_running: bool = True

        self._thread_running: bool = True
        self._client_connected: bool = True

        self._status_message: dict = {}

        if isinstance(status_message, dict):
            self._status_message.update(status_message)
        else:
            self._status_message.update(self.RESPONSE_MSG)

        self._incoming_thread: threading.Thread
        self._outgoing_thread: threading.Thread

        self._incoming_thread = threading.Thread(target=self._receive_messages)
        self._outgoing_thread = threading.Thread(target=self._send_messages)

        return

    def run(self):
        self._incoming_thread.start()
        self._outgoing_thread.start()

        while self._thread_running:
            time.sleep(self.SOCKET_TIMEOUT)

        self._incoming_thread.join()
        self._outgoing_thread.join()

        self._close_client_socket()

        self._empty_outgoing_queue()
        return

    def stop(self) -> None:
        self._thread_running = False
        self.join()
        return

    def pending_incoming_message(self) -> bool:
        return not self._incoming_message_queue.empty()

    def get_incoming_message(self) -> dict:
        return self._incoming_message_queue.get_nowait()

    def add_outgoing_message(self, outgoing_message: dict) -> None:
        assert isinstance(outgoing_message, dict)
        self._outgoing_message_queue.put(outgoing_message)
        return

    def update_status_message(self, status_message: dict) -> None:
        assert isinstance(status_message, dict)
        self._status_message.update(status_message)
        return

    @property
    def client_connected(self) -> bool:
        return self._client_connected

    @property
    def thread_running(self) -> bool:
        return self._thread_running

    def _socket_json_receive(self) -> dict:
        receive_message = None
        length_str = ""
        message_buffer = ""

        read_char = self._client_socket.recv(1)

        if read_char == b'{':
            message_buffer += read_char.decode()

            while read_char not in self.TERMINATING_CHARS:
                read_char = self._client_socket.recv(1)
                message_buffer += read_char.decode()

            receive_message = literal_eval(message_buffer)

        elif read_char != b'':
            length_str += read_char.decode()

            while read_char not in self.TERMINATING_CHARS:
                read_char = self._client_socket.recv(1)
                length_str += read_char.decode()

            try:
                length_int = int(length_str)
                pending_bytes = length_int

                while pending_bytes > 0:
                    temp_buffer = self._client_socket.recv(pending_bytes)
                    message_buffer += temp_buffer.decode()
                    pending_bytes -= len(temp_buffer)

                receive_message = json.loads(message_buffer)

            except (socket.error, json.JSONDecodeError):
                receive_message = literal_eval(message_buffer)
                if not isinstance(receive_message, dict):
                    receive_message = None

            except ValueError:
                receive_message = None

        return receive_message

    def _socket_json_send(self, payload: dict, with_len: bool = True) -> None:
        assert isinstance(self._client_socket, socket.socket)
        serialized_data = json.dumps(payload)
        len_string = str('%d\n' % len(serialized_data))
        final_send_string = len_string + serialized_data
        if with_len:
            self._client_socket.sendall(final_send_string.encode())
        else:
            self._client_socket.sendall(serialized_data.encode())
        return

    def _receive_messages(self) -> None:
        while self._thread_running:
            try:
                incoming_message = self._socket_json_receive()

                if incoming_message is None:
                    self._thread_running = False

                elif incoming_message.get(self.STATUS_KEY):
                    self._socket_json_send(self._status_message, False)

                else:
                    self._incoming_message_queue.put(incoming_message)

            except socket.timeout:
                pass

            except socket.error:
                self._thread_running = False

            except Exception as recv_error:
                print("Client Socket had unhandled recv error:", recv_error)
                self._thread_running = False

        return

    def _send_messages(self) -> None:
        while self._thread_running:
            try:
                outgoing_message = self._outgoing_message_queue.get(True, .5)
                self._socket_json_send(outgoing_message)

            except socket.error:
                self._thread_running = False

            except queue.Empty:
                pass

            except Exception as send_error:
                print("Client Socket had unhandled send error:", send_error)
                self._thread_running = False

        return

    def _close_client_socket(self) -> None:
        self._client_socket.shutdown(socket.SHUT_RDWR)
        self._client_socket.close()
        self._client_connected = False
        self._thread_running = False
        return

    def _empty_outgoing_queue(self) -> None:
        while not self._outgoing_message_queue.empty():
            self._outgoing_message_queue.get()
        return
