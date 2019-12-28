# audio_client_gui_application.py
# Created by: Vectorhax
# Created on: August 18th, 2019

import tkinter
import datetime

from tkinter import ttk
from tkinter import Tk, Label

from network_audio_classes import util_func
from network_audio_classes import constants
from audio_client_application import AudioClientApplication

class AudioGUIClientApplication:
    WINDOW_NAME = "Audio Client Application"

    def __init__(self):

        self._window = Tk()

        self._window.title(self.WINDOW_NAME)
        self._window.protocol("WM_DELETE_WINDOW", self._close_application)
        self._window.resizable(1, 1)

        current_ip = util_func.get_own_ip()
        self._audio_client = AudioClientApplication(current_ip)
        self._audio_client.start()

        self._latency_list = []

        self._build_window_space()

        self._window.after(20, self._update_loop)
        self._window.mainloop()
        return

    def _close_application(self):
        self._audio_client.stop()
        self._window.quit()
        return

    def _build_window_space(self):

        self._connected_text = tkinter.StringVar()
        self._connected_text.set("Disconnected")
        self._connected_label = Label(self._window,
                                      textvariable=self._connected_text)
        self._connected_label.grid(row=0, column=0)
        #self._connected_label.grid_configure("nsew")

        self._packet_latency_text = tkinter.StringVar()
        self._packet_latency_text.set("Average Packet Latency: ")
        self._packet_latency_label = Label(self._window,
                                           textvariable=self._packet_latency_text)
        self._packet_latency_label.grid(row=1, column=0)
        #self._packet_latency_label.grid_configure("nsew")

        self._window.grid_columnconfigure(0, weight=1)
        self._window.grid_rowconfigure(0, weight=1)
        self._window.grid_rowconfigure(1, weight=1)
        return

    def _update_loop(self):

        if self._audio_client.client_connected:
            self._connected_text.set("Connected")
        else:
            self._connected_text.set("Disconnected")

        self._packet_latency_text.set(str(self._audio_client.average_latency))

        self._window.after(20, self._update_loop)
        return

if __name__ == '__main__':
    AudioGUIClientApplication()