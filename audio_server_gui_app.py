# audio_server_gui.py
# Created by: VectorHax
# Created on: July 3rd, 2019

import os
import datetime
import tkinter
from tkinter import ttk
from tkinter import Tk, Label, Button, Entry, Listbox

import pydub

from network_audio_classes import constants
from network_audio_classes.server_network_process import ServerNetworkProcess


class AudioGUIServerApplication:
    WINDOW_NAME = "Audio Server Application"

    AUDIO_FOLDER_NAME = "audio"
    SUPPORTED_FORMATS = [".wav"]

    PROGRESS_BAR_SIZE = 200
    LOOP_FREQUENCY = 22

    def __init__(self):

        self._window = Tk()

        self._window.title(self.WINDOW_NAME)
        self._window.protocol("WM_DELETE_WINDOW", self._close_application)
        self._window.resizable(1, 1)

        self._audio_server = ServerNetworkProcess()
        self._audio_server.start()

        self._audio_file_list = []
        self._selected_audio_file = ""

        self._audio_playing = False
        self._audio_data = []
        self._prev_audio_index = 0
        self._current_audio_index = constants.AUDIO_BYTE_FRAME_SIZE

        self._build_window_space()

        self._window.after(20, self._update_loop)
        self._window.mainloop()

        return

    def __del__(self):
        return

    def _close_application(self):
        self._audio_server.stop()
        self._window.quit()
        return

    def _build_window_space(self):

        # On the left most side there should be a list of the songs
        self._audio_file_list = self._get_audio_file_list()

        self._file_list_box = Listbox(self._window)
        self._file_list_box.grid(row=0, column=0, sticky=tkinter.W, rowspan=3)
        self._file_list_box.grid_configure(sticky="nsew")

        for audio_file_name in self._audio_file_list:
            self._file_list_box.insert(tkinter.END, audio_file_name)

        # Then in the middle want to then have the current song playing listed
        self._song_playing_text = tkinter.StringVar()
        self._song_playing_text.set("Nothing")
        self._song_playing_label = Label(self._window,
                                         textvariable=self._song_playing_text)
        self._song_playing_label.grid(row=0, column=1, rowspan=2)
        self._song_playing_label.grid_configure(sticky="nsew")

        # Want to have below it a progress bar of where in the song it is
        self._song_progress_bar = ttk.Progressbar(self._window,
                                                  orient="horizontal",
                                                  length=self.PROGRESS_BAR_SIZE)
        self._song_progress_bar.grid(row=2, column=1)
        self._song_progress_bar.grid_configure(sticky="nsew")

        # Set so the window properly adjust on resize
        self._window.grid_columnconfigure(0, weight=1)
        self._window.grid_columnconfigure(1, weight=1)
        self._window.grid_rowconfigure(0, weight=1)
        self._window.grid_rowconfigure(1, weight=1)

        return

    def _get_audio_file_list(self):
        audio_files = []
        for file in os.listdir(self.AUDIO_FOLDER_NAME):
            for file_extension in self.SUPPORTED_FORMATS:
                if file.endswith(file_extension):
                    audio_files.append(file)

        return audio_files

    def _update_loop(self):
        loop_start_time = datetime.datetime.now()

        selected_file = self._file_list_box.get(tkinter.ANCHOR)
        if self._selected_audio_file != selected_file:
            self._song_playing_text.set(selected_file)
            self._selected_audio_file = selected_file
            self._start_playing_audio_file()

        if self._audio_playing:
            self._update_audio_playback()

        loop_end_time = datetime.datetime.now()
        loop_run_time = (loop_end_time - loop_start_time).total_seconds()
        loop_run_time_ms = int(loop_run_time * 1000)

        if loop_run_time_ms >= self.LOOP_FREQUENCY:
            self._window.after(1, self._update_loop)
        else:
            next_loop_time = self.LOOP_FREQUENCY - loop_run_time_ms
            self._window.after(next_loop_time, self._update_loop)
        return

    def _start_playing_audio_file(self):
        actual_audio_file = os.path.join(self.AUDIO_FOLDER_NAME,
                                         self._selected_audio_file)
        file_data = pydub.AudioSegment.from_file(actual_audio_file)
        self._audio_data = file_data.raw_data

        self._audio_playing = True
        self._prev_audio_index = 0
        self._current_audio_index = constants.AUDIO_BYTE_FRAME_SIZE
        return

    def _update_audio_playback(self):
        audio_time = datetime.datetime.now()
        audio_segment = self._audio_data[self._prev_audio_index:
                                         self._current_audio_index]
        audio_message = {constants.AUDIO_PAYLOAD_STR: list(audio_segment),
                         constants.TIMESTAMP_STR: str(audio_time)}

        self._audio_server.add_audio_packet(audio_message, nowait=True)

        self._prev_audio_index = self._current_audio_index
        self._current_audio_index += constants.AUDIO_BYTE_FRAME_SIZE

        if self._current_audio_index > len(self._audio_data):
            self._audio_playing = False
        else:
            self._update_progress_bar()

        return

    def _update_progress_bar(self):
        song_progress = self._current_audio_index/len(self._audio_data)
        progress_percent = song_progress * 100
        self._song_progress_bar["value"] = progress_percent
        return
