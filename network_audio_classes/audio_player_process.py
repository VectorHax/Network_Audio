# audio_player_process.py
# Created by: VectorHax
# Created on: June 1st

# A thread that will manage playing audio

# **********************************Import*********************************** #

# The global native python imports
import queue
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

    REQ_QUEUE_SIZE: int = 10
    AUDIO_QUEUE_SIZE: int = 30

    def __init__(self):
        multiprocessing.Process.__init__(self, name=self.PROCESS_NAME)

        self._audio_player: pyaudio.PyAudio
        self._audio_streamer: pyaudio.PyAudio

        self._audio_player = None
        self._audio_streamer = None

        self._temp_audio_segment = self._create_empty_audio_segment()

        self._audio_data_queue = multiprocessing.Queue(self.AUDIO_QUEUE_SIZE)
        self._audio_request_queue = multiprocessing.Queue(self.REQ_QUEUE_SIZE)

        self._blank_audio_data = self._create_empty_audio_data()
        self._speaker_location = multiprocessing.Value(ctypes.c_float, 0.0)

        self._audio_player_running = multiprocessing.Value(ctypes.c_bool, True)
        self._debug_flag = multiprocessing.Value(ctypes.c_bool, False)
        return

    def run(self):

        self._audio_player, self._audio_streamer = self._init_audio_player()
        self._audio_streamer.start_stream()

        while self._audio_player_running.value:
            try:
                audio_data_packet = self._audio_request_queue.get(True, 1.0)
                self._handle_audio_packet(audio_data_packet)

            except queue.Empty:
                pass

            except Exception as packet_handle_error:
                print("Got the error with packet: ", packet_handle_error)

        self._empty_audio_queues()
        self._stop_audio_player()
        return

    def stop(self):
        self._audio_player_running.value = False
        self.join()
        return

    def add_audio_request(self, audio_request: dict) -> None:
        assert isinstance(audio_request, dict), self.AUDIO_REQUEST_ASSERT
        self._audio_request_queue.put(audio_request)
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
        while self._audio_data_queue.full():
            pass
        return

    @property
    def pending_audio_buffers(self) -> int:
        return self._audio_data_queue.qsize()

    @property
    def pending_audio_requests(self) -> int:
        return self._audio_request_queue.qsize()

    def _init_audio_player(self):
        audio_player = pyaudio.PyAudio()

        audio_streamer = audio_player.open(format=constants.AUDIO_FORMAT,
                                           channels=constants.AUDIO_CHANNELS,
                                           rate=constants.AUDIO_RATE,
                                           output=True,
                                           stream_callback=self._audio_callback)
        return audio_player, audio_streamer

    def _audio_callback(self, in_data, frame_count, time_info, status):

        try:
            audio_data = self._audio_data_queue.get_nowait()

        except queue.Empty:
            audio_data = self._blank_audio_data

        if self._debug_flag.value:
            print("Audio Callback: ", in_data, frame_count, time_info, status)

        return audio_data, pyaudio.paContinue

    @staticmethod
    def _create_empty_audio_segment() -> pydub.AudioSegment:
        audio_seg = pydub.AudioSegment(data=bytes(),
                                       sample_width=constants.AUDIO_SEG_WIDTH,
                                       frame_rate=constants.AUDIO_RATE,
                                       channels=constants.AUDIO_CHANNELS)
        return audio_seg

    @staticmethod
    def _create_empty_audio_data() -> bytes:
        empty_audio_array = [1] * constants.AUDIO_BYTE_FRAME_SIZE
        return bytes(empty_audio_array)

    def _handle_audio_packet(self, audio_data_packet: dict) -> None:
        speaker_location = audio_data_packet.get(constants.SPEAKER_LOC_STR)
        new_audio_data = audio_data_packet.get(constants.AUDIO_PAYLOAD_STR)

        if speaker_location:
            self.set_speaker_location(speaker_location)

        if new_audio_data:
            self._set_audio_data(new_audio_data)

        return

    def _set_audio_data(self, audio_data: bytes) -> None:
        assert isinstance(audio_data, bytes), self.AUDIO_DATA_ASSERT

        audio_start_index = 0
        audio_end_index = constants.AUDIO_BYTE_FRAME_SIZE
        audio_frame_parts = len(audio_data) / constants.AUDIO_BYTE_FRAME_SIZE
        audio_frame_count = int(audio_frame_parts)

        for audio_frame in range(audio_frame_count):
            frame_audio_data = audio_data[audio_start_index:audio_end_index]

            self._temp_audio_segment._data = frame_audio_data
            pan_offset = self._speaker_location.value
            # noinspection PyUnresolvedReferences
            panned_audio = self._temp_audio_segment.pan(pan_offset)

            audio_start_index = audio_end_index
            audio_end_index += constants.AUDIO_BYTE_FRAME_SIZE

            self._audio_data_queue.put(panned_audio.raw_data)

        return

    def _empty_audio_queues(self) -> None:

        while not self._audio_request_queue.empty():
            self._audio_request_queue.get()

        while not self._audio_data_queue.empty():
            self._audio_data_queue.get()

        return

    def _stop_audio_player(self) -> None:
        self._audio_streamer.stop_stream()
        self._audio_streamer.close()
        self._audio_player.terminate()
        return
