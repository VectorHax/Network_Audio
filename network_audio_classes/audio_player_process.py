# audio_player_process.py
# Created by: VectorHax
# Created on: January 12th, 2020

# A process that will manage playing audio

# **********************************Import*********************************** #

# The global native python imports
import time
import ctypes
import multiprocessing

# The imports brought in via pip
import pydub
import pyaudio

# The local libraries
from network_audio_classes import constants


# ***********************Audio Player Thread Class************************** #

class AudioPlayer(multiprocessing.Process):
    PROCESS_NAME: str = "Audio Player"

    # Class wide static variables
    AUDIO_REQUEST_ASSERT: str = "Audio Request must be a dict"
    LOCATION_ASSERT: str = "Location must be a float"
    AUDIO_DATA_ASSERT: str = "Audio Data must be bytes"

    LOCATION_MIN: float = -1.0
    LOCATION_MAX: float = 1.0

    AUDIO_ARRAY_LEN: int = 10
    AUDIO_ARRAY_SIZE: int = AUDIO_ARRAY_LEN * constants.AUDIO_BYTE_FRAME_SIZE

    AUDIO_STEP_BUFFER: int = 5

    def __init__(self):
        multiprocessing.Process.__init__(self, name=self.PROCESS_NAME)

        self._speaker_location = multiprocessing.Value(ctypes.c_float, 0.0)

        self._audio_data_index = multiprocessing.Value(ctypes.c_ubyte, 0)
        self._playback_data_index = multiprocessing.Value(ctypes.c_ubyte, 0)
        self._audio_data_array = multiprocessing.Array(ctypes.c_ubyte,
                                                       self.AUDIO_ARRAY_SIZE)

        self._audio_data_requested = multiprocessing.Value(ctypes.c_ulong, 0)
        self._audio_data_played = multiprocessing.Value(ctypes.c_ulong, 0)

        self._audio_player_running = multiprocessing.Value(ctypes.c_bool, True)

        self._debug_mode = multiprocessing.Value(ctypes.c_bool, False)
        return

    def run(self):
        audio_frame_size = constants.AUDIO_FRAME_SIZE

        audio_player: pyaudio.PyAudio = pyaudio.PyAudio()

        audio_streamer = audio_player.open(format=constants.AUDIO_FORMAT,
                                           channels=constants.AUDIO_CHANNELS,
                                           rate=constants.AUDIO_RATE,
                                           frames_per_buffer=audio_frame_size,
                                           output=True,
                                           stream_callback=self._audio_callback)

        audio_streamer.start_stream()

        while self._audio_player_running.value:
            time.sleep(.001)

        audio_streamer.stop_stream()
        audio_streamer.close()

        audio_player.terminate()
        return

    def stop(self):
        self._audio_player_running.value = False
        self.join()
        return

    def add_audio_data(self, audio_data: bytes) -> None:
        audio_seg: pydub.AudioSegment = self._create_audio_segment(audio_data)

        # noinspection PyUnresolvedReferences
        panned_audio_segment = audio_seg.pan(self._speaker_location.value)
        panned_audio_data: bytes = panned_audio_segment.raw_data

        self._set_audio_data(self._audio_data_index.value, panned_audio_data)

        self._increase_data_index(self._audio_data_index)

        self._audio_data_requested.value += 1
        return

    def set_speaker_location(self, location: float) -> None:
        assert isinstance(location, float), self.LOCATION_ASSERT

        if location < self.LOCATION_MIN:
            self._speaker_location.value = self.LOCATION_MIN
        elif location > self.LOCATION_MAX:
            self._speaker_location.value = self.LOCATION_MAX
        else:
            self._speaker_location.value = location

        return

    def wait_for_audio_player(self) -> None:
        while self.audio_data_delta >= self.AUDIO_STEP_BUFFER:
            time.sleep(.001)
        return

    def enable_debug_mode(self) -> None:
        self._debug_mode.value = True
        return

    def disable_debug_mode(self) -> None:
        self._debug_mode = False
        return

    @property
    def audio_data_requested(self) -> int:
        return self._audio_data_requested.value

    @property
    def audio_data_played(self) -> int:
        return self._audio_data_played.value

    @property
    def audio_data_delta(self) -> int:
        data_delta: int = 0
        if self.audio_data_played > self.audio_data_requested:
            # This is the case of audio data overflowed
            data_played_max_value: int = 2 ** 64 - 1
            data_delta = data_played_max_value - self.audio_data_played
            data_delta -= self.audio_data_requested
        else:
            data_delta = self.audio_data_requested - self.audio_data_played
        return data_delta

    @property
    def debug_mode(self) -> bool:
        return self._debug_mode.value

    @staticmethod
    def _create_audio_segment(data: bytes = bytes()) -> pydub.AudioSegment:
        audio_seg = pydub.AudioSegment(data=data,
                                       sample_width=constants.AUDIO_SEG_WIDTH,
                                       frame_rate=constants.AUDIO_RATE,
                                       channels=constants.AUDIO_CHANNELS)
        return audio_seg

    @staticmethod
    def _get_start_stop_points(index: int) -> (int, int):
        array_start_point = index * constants.AUDIO_BYTE_FRAME_SIZE
        array_end_point = array_start_point + constants.AUDIO_BYTE_FRAME_SIZE
        return array_start_point, array_end_point

    def _get_audio_data(self, index: int) -> bytes:
        array_start_point, array_end_point = self._get_start_stop_points(index)
        audio_data = self._audio_data_array[array_start_point: array_end_point]
        return bytes(audio_data)

    def _set_audio_data(self, index: int, audio_data: bytes) -> None:
        array_start_point, array_end_point = self._get_start_stop_points(index)
        self._audio_data_array[array_start_point: array_end_point] = audio_data
        return

    def _increase_data_index(self, data_index: multiprocessing.Value) -> None:
        if (data_index.value + 1) == self.AUDIO_ARRAY_LEN:
            data_index.value = 0
        else:
            data_index.value += 1
        return

    def _audio_callback(self, in_data, frame_count, time_info, status):

        if self._playback_data_index.value != self._audio_data_index.value:
            playback_index = self._playback_data_index.value
            audio_data = self._get_audio_data(playback_index)

            self._increase_data_index(self._playback_data_index)

            self._audio_data_played.value += 1

        else:
            playback_index = self._playback_data_index.value
            audio_data = self._get_audio_data(playback_index)

        if self._debug_mode.value:
            print("Audio_Callback in_data:", in_data, "frame_count:",
                  frame_count, "time_info:", time_info, "status:", status)

        return audio_data, pyaudio.paContinue
