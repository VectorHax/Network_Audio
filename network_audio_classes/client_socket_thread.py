# client_socket_thread.py
# Created by: VectorHax
# Created on: June 1st, 2019

# A thread class that handles client socket communication of JSON messages

# **********************************Import*********************************** #
import sys

try:
    # The global libraries built into python
    import json
    import queue
    import socket
    import threading

except Exception as import_failure:
    print("Client Socket Thread failed to import: ", str(import_failure))
    sys.exit()

# ***********************Client Socket Thread Class************************** #


class ClientSocketThread(threading.Thread):
    THREAD_NAME = "Client Socket Thread"

    SOCKET_TIMEOUT = 2.0

    QUEUE_DEPTH = 10

    def __init__(self, client_socket):
        threading.Thread.__init__(self, name=self.THREAD_NAME)

        self._incoming_message_queue = queue.Queue(self.QUEUE_DEPTH)
        self._outgoing_message_queue = queue.Queue(self.QUEUE_DEPTH)

        self._client_socket = client_socket
        self._client_socket.settimeout(self.SOCKET_TIMEOUT)

        self._current_message = {}

        self._thread_running = True
        self._client_connected = True

        self._outgoing_thread = None

        return

    def __del__(self):
        if self._client_socket is not None:
            self._client_socket.close()
        self._client_socket = None
        return

    def run(self):

        self._start_outgoing_thread()

        while self._thread_running:
            try:
                incoming_message = self._socket_json_receive()

                if self._incoming_message_queue.full():
                    self._incoming_message_queue.get()

                if incoming_message is not None:
                    self._incoming_message_queue.put_nowait(incoming_message)
                else:
                    self._close_client_socket()

            except socket.timeout:
                pass

            except socket.error:
                self._close_client_socket()

            except Exception as loop_err:
                print("Client socket thread got unhandled error: ", loop_err)

        self._close_client_socket()
        self._empty_queues()
        return

    def add_outgoing_message(self, outgoing_message, nowait=False):
        if nowait:
            self._outgoing_message_queue.put(outgoing_message)
        else:
            self._outgoing_message_queue.put(outgoing_message)
        return

    def get_incoming_message(self, timeout=1.0):
        assert isinstance(timeout, float) or isinstance(timeout, int)
        return self._incoming_message_queue.get(True, timeout)

    def stop(self):
        self._thread_running = False
        self.join()
        return

    @property
    def client_connected(self):
        return self._client_connected

    @property
    def thread_running(self):
        return self._thread_running

    @property
    def pending_incoming_messages(self):
        return self._incoming_message_queue.qsize()

    def _start_outgoing_thread(self):
        self._outgoing_thread = threading.Thread(target=self._out_thread_func,
                                                 args=())
        self._outgoing_thread.start()
        return

    def _out_thread_func(self):
        while self._thread_running:
            try:
                outgoing_message = self._outgoing_message_queue.get(True, 1.0)
                self._socket_json_send(outgoing_message)

            except queue.Empty:
                pass

            except socket.timeout:
                pass

            except Exception as out_thread_err:
                print("Got unhandled cst out thread error: ", out_thread_err)
                self._close_client_socket()
        return

    def _socket_json_send(self, payload):
        serialized_data = json.dumps(payload)
        send_string = serialized_data
        len_string = str('%d\n' % len(send_string))
        final_send_string = len_string + serialized_data
        self._client_socket.sendall(final_send_string.encode())
        return

    def _socket_json_receive(self):
        receive_message = None
        length_str = ""
        message_buffer = ""

        read_char = self._client_socket.recv(1)
        if read_char != b'':
            while (read_char != b'\n') and (read_char != b''):
                length_str += read_char.decode()
                read_char = self._client_socket.recv(1)

            length_int = int(length_str)
            pending_bytes = length_int

            while pending_bytes > 0:
                temp_buffer = self._client_socket.recv(pending_bytes)
                message_buffer += temp_buffer.decode()
                pending_bytes -= len(temp_buffer)

            receive_message = json.loads(message_buffer)
        return receive_message

    def _close_client_socket(self):
        if self._client_socket is not None:
            self._client_socket.close()

        self._client_connected = False
        self._thread_running = False
        return

    def _empty_queues(self):
        while not self._outgoing_message_queue.empty():
            self._outgoing_message_queue.get()

        while not self._incoming_message_queue.empty():
            self._incoming_message_queue.get()
        return
