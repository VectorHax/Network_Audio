# The new audio player with call back

import queue
import pyaudio
import pydub
import time
import datetime
import wave
import threading
import math

class AudioPlayer(threading.Thread):
    FORMAT = 8
    CHANNELS = 2
    RATE = 44100
    OUTPUT = True

    EMPTY_AUDIO_BIT = [0]
    BYTES_PER_FRAME = 4
    FRAME_SIZE = 1024
    BYTE_FRAME_SIZE = BYTES_PER_FRAME * FRAME_SIZE

    STARTING_LOCATION = 0.0
    LOCATION_MAX =  1.0
    LOCATION_MIN = -1.0

    SEGMENT_WIDTH = 2

    AUDIO_QUEUE_DEPTH = 3
    AUDIO_READY_DEPTH = 3

    SPEAKER_LOC_STR = "speaker_location"
    AUDIO_PAYLOAD_STR = "audio_payload"

    def __init__(self):
        threading.Thread.__init__(self)
        self._audio_player = pyaudio.PyAudio()

        self._audio_streamer = self._audio_player.open(format=self.FORMAT,
                                                       channels=self.CHANNELS,
                                                       rate=self.RATE,
                                                       output=self.OUTPUT,
                                                       stream_callback=self._callback)

        self._current_audio_segment = pydub.AudioSegment(data=bytes(),
                                                         sample_width= self.SEGMENT_WIDTH,
                                                         frame_rate=self.RATE,
                                                         channels=self.CHANNELS)

        self._audio_status_queue = queue.Queue()
        self._audio_request_queue = queue.Queue()
        self._audio_data_queue = queue.Queue(self.AUDIO_QUEUE_DEPTH)

        self._blank_audio_data = bytes(self.EMPTY_AUDIO_BIT * self.BYTE_FRAME_SIZE)

        self._speaker_location = self.STARTING_LOCATION

        self._player_blocking = False
        self._audio_player_running = False
        return

    def __del__(self):
        if self._audio_player_running:
            self.stop()
        return

    def run(self):
        print("Starting the audio player")
        self._audio_player_running = True
        self._audio_streamer.start_stream()

        while self._audio_status_queue.empty():
            if not self._audio_request_queue.empty():
                audio_data_packet = self._audio_request_queue.get()
                self._handle_audio_packet(audio_data_packet)

        self._empty_audio_queues()
        self._stop_audio_player()
        print("Finished running the audio player")
        return

    def add_audio_request(self, audio_request):
        if isinstance(audio_request, dict):
            self._audio_request_queue.put(audio_request)
        return

    def set_speaker_location(self, location):
        if isinstance(location, float):
            if location < self.LOCATION_MIN:
                self._speaker_location = self.LOCATION_MIN
            elif location > self.LOCATION_MAX:
                self._speaker_location = self.LOCATION_MAX
            else:
                self._speaker_location = location
        return

    def set_audio_data(self, audio_data):
        try:
            audio_start_index = 0
            audio_end_index = self.BYTE_FRAME_SIZE
            audio_frame_count = int(len(audio_data)/self.BYTE_FRAME_SIZE)

            byte_audio_data = bytes(audio_data)
            
            for audio_frame in range(audio_frame_count):
                frame_audio_data = byte_audio_data[audio_start_index:audio_end_index]
                
                self._current_audio_segment._data = frame_audio_data
                output_audio_data = self._get_output_audio()
                self._audio_data_queue.put(output_audio_data.raw_data)

                audio_start_index = audio_end_index
                audio_end_index += self.BYTE_FRAME_SIZE


            pass
        except Exception as set_audio_error:
            print("Set audio data got the error of: ", set_audio_error)
        return

    def add_data_to_queue(self, audio_data):
        self._audio_data_queue.put(bytes(audio_data))
        return

    def stop(self):
        self._audio_status_queue.put("KILL")
        self._audio_player_running = False
        return

    def _callback(self, in_data, frame_count, time_info, status):
        data = None

        if self._audio_data_queue.empty():
            data = self._blank_audio_data
        else:
            data = self._audio_data_queue.get()

        self._player_blocking = False
        return (data, pyaudio.paContinue)

    def _handle_audio_packet(self, audio_data_packet):
        try:
            speaker_location = audio_data_packet.get(self.SPEAKER_LOC_STR)
            audio_data = audio_data_packet.get(self.AUDIO_PAYLOAD_STR)
            timestamp_data = audio_data_packet.get("Timestamp")

            if speaker_location:
                self.set_speaker_location(speaker_location)

            if audio_data:
                self.set_audio_data(audio_data)

            if timestamp_data:
                #print("Message time of: ", str(datetime.datetime.now()),timestamp_data)
                pass

        except Exception as audio_packet_error:
            print("Got the error with _handle_audio_packet: ", audio_packet_error)
        return

    def _get_output_audio(self):
        return self._current_audio_segment.pan(self._speaker_location)

    def _empty_audio_queues(self):
        while not self._audio_status_queue.empty():
            self._audio_status_queue.get()

        while not self._audio_request_queue.empty():
            self._audio_request_queue.get()

        while not self._audio_data_queue.empty():
            self._audio_data_queue.get()

        return

    def _stop_audio_player(self):
        self._audio_streamer.stop_stream()
        self._audio_streamer.close()
        self._audio_player.terminate()
        return

if __name__ == '__main__':

    ap = AudioPlayer()
    ap.start()
    ap.set_speaker_location(0.0)

    time.sleep(2)

    file_location = "audio/test.wav"
    audio_file = pydub.AudioSegment.from_wav(file_location)
    audio_data = audio_file.raw_data
    prev_audio_index = 0
    current_audio_index = 4 * 1024

    while current_audio_index < len(audio_data)/10:
      audio_data_chunk = audio_data[prev_audio_index:current_audio_index]
      prev_audio_index = current_audio_index
      current_audio_index += 4 * 1024
      ap.add_audio_request({ap.AUDIO_PAYLOAD_STR:audio_data_chunk})

    print("Finished playback")

    time.sleep(5)

    ap.stop()

    ap.join()

    print("DONE")