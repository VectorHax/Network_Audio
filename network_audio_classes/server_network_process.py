# server_network_process.py
# Created by: Vectorhax
# Created on: June 2nd, 2019

# A network process that handles finding clients and sending out packets

# **********************************Import*********************************** #

# The global libraries built into python
import time
import queue
import ctypes
import socket
import threading
import multiprocessing

# The local libraries
from network_audio_classes import constants
from network_audio_classes import util_func
from network_audio_classes.client_socket_thread import ClientSocketThread

# *************************Server Network Process*************************** #


class ServerNetworkProcess(multiprocessing.Process):
    PROCESS_NAME = "Server Network Process"

    QUEUE_DEPTH = 3

    def __init__(self):
        multiprocessing.Process.__init__(self, name=self.PROCESS_NAME)

        self._client_thread_list: list = []

        self._incoming_message_queue = multiprocessing.Queue(self.QUEUE_DEPTH)
        self._outgoing_message_queue = multiprocessing.Queue(self.QUEUE_DEPTH)

        self._server_ip: str = ""

        self._server_socket: socket.socket
        self._server_socket = None

        self._server_running = multiprocessing.Value(ctypes.c_bool, True)
        self._clients_connected = multiprocessing.Value(ctypes.c_uint64, 0)
        return

    def run(self):

        send_message_thread = threading.Thread(target=self._send_thread())
        send_message_thread.start()

        while self._server_running.value:
            self._check_for_new_clients()

            self._close_dead_client_threads()

        send_message_thread.join()

        self._close_dead_client_threads(force_close=True)
        self._clear_queues()
        return

    def stop(self):
        self._server_running.value = False
        self.join()
        return

    def add_audio_packet(self, audio_packet: dict, wait: bool = True) -> None:
        assert isinstance(wait, bool)
        assert isinstance(audio_packet, dict)

        if wait:
            self._outgoing_message_queue.put(audio_packet, True, 1.0)

        else:
            if self._outgoing_message_queue.full():
                self._outgoing_message_queue.get_nowait()

            self._outgoing_message_queue.put_nowait(audio_packet)

        return

    @property
    def clients_connected(self) -> bool:
        return self._clients_connected.value

    def _send_thread(self) -> None:

        while self._server_running.value:
            try:
                outgoing_message = self._outgoing_message_queue.get_nowait()

                for client_thread in self._client_thread_list:
                    try:
                        client_thread.add_outgoing_message(outgoing_message)

                    except queue.Full:
                        pass

            except queue.Empty:
                pass

            except Exception as send_err:
                print("Got an unhandled error in send thread: ", send_err)

        return

    def _check_for_new_clients(self) -> None:
        if self._server_socket is None:
            self._create_server_socket()
        else:
            self._accept_client()
        return

    def _create_server_socket(self) -> None:
        try:
            self._server_ip = util_func.get_own_ip()
            server_ip_info = (self._server_ip, constants.AUDIO_CLIENT_PORT)
            self._server_socket = socket.socket(socket.AF_INET,
                                                socket.SOCK_STREAM)
            self._server_socket.bind(server_ip_info)
            self._server_socket.listen(5)
            self._server_socket.settimeout(1.0)

        except Exception as create_err:
            print("Got an error creating server socket: ", create_err)
        return

    def _accept_client(self) -> None:
        try:
            new_client, client_address = self._server_socket.accept()
            client_thread = ClientSocketThread(new_client)
            client_thread.start()
            self._client_thread_list.append(client_thread)
            self._clients_connected.value += 1

        except socket.timeout:
            pass

        except Exception as accept_err:
            print("Had an issue with accepting client: ", accept_err)
        return

    def _close_dead_client_threads(self, force_close: bool = False) -> None:
        dead_client_list = []

        for client_thread in self._client_thread_list:
            if (not client_thread.thread_running) or force_close:
                client_thread.stop()
                dead_client_list.append(client_thread)

        for dead_client_list in dead_client_list:
            self._client_thread_list.remove(dead_client_list)
            self._clients_connected.value -= 1

        return

    def _clear_queues(self) -> None:
        self._outgoing_message_queue = multiprocessing.Queue(self.QUEUE_DEPTH)
        self._incoming_message_queue = multiprocessing.Queue(self.QUEUE_DEPTH)
        return
