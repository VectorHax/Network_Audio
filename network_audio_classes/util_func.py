# util_func.py
# Created by: VectorHax
# Created on: Dec 22nd, 2018

import socket


IP_TEST_ADDRESS = "10.255.255.255"
IP_TEST_PORT = 1
IP_TEST_INDEX = 0
IP_DEFAULT_ADDRESS = "127.0.0.1"


def get_own_ip() -> str:
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
