# audio_player.py
# Created by: Dale Best
# Created on: December 22nd, 2018

import sys

try:
  # The global native python imports
  import datetime
  import math
  import queue
  import threading
  import time
  import wave

  # The imports brought in via pip
  import pyaudio
  import pydub

  # The local imports
  import constants

except Exception as import_error:
  print("Audio Player faield to import: ", import_error)
  sys.exit()


class AudioPlayer(threading.Thread):
  # Class wide static variables
  AUDIO_REQUEST_ASSERT = "Audio Request must be a dict"
  LOCATION_ASSERT = "Location must be a float"
  AUDIO_DATA_ASSERT = "Audio Data must be bytes"

  REQUEST_BUFFER_LIMIT = 5
  AUDIO_BUFFER_LIMIT = 3

  # __init(self): The class initilizer which takes no variables
  # Allocates the various audio player parameter and settings
  def __init__(self):
    threading.Thread.__init__(self)

    self._audio_player, self._audio_streamer = self._init_audio_player()
    self._temp_audio_segment = self._create_empty_audio_segment()

    self._audio_status_queue = queue.Queue()
    self._audio_request_queue = queue.Queue()
    self._audio_data_queue = queue.Queue()

    self._blank_audio_data = self._create_empty_audio_data()
    self._speaker_location = constants.STARTING_LOCATION

    self._audio_player_running = False
    return

  # __del__(self): The deallocater for the class which is called when freed
  def __del__(self):
    if self._audio_player_running:
      self.stop()
    return

  # run(self): The function that is called when the thread starts
  # will loop processing audio request messages until it receives a
  # message on the class status queue
  def run(self):
    print("Starting the audio player")
    self._audio_player_running = True
    self._audio_streamer.start_stream()

    while self._audio_status_queue.empty():
      while not self._audio_request_queue.empty():
        audio_data_packet = self._audio_request_queue.get()
        self._handle_audio_packet(audio_data_packet)

    self._empty_audio_queues()
    self._stop_audio_player()
    print("Finished running the audio player")
    return

  # stop(self): Called to stop the class by putting a kill message on
  # the internal status queue
  def stop(self):
    self._audio_status_queue.put(constants.PROCESS_KILL_WORD)
    self._audio_player_running = False
    return

  # add_audio_request(self, audio_request): Adds a dict message onto the 
  # audio request queue to update various parameters of the audio player
  # Speaker_Location: <float> between -1 and 1 to set left/right speaker
  # Audio_Payload: <bytes> the byte array of audio data
  def add_audio_request(self, audio_request):
    assert isinstance(audio_request,dict), AUDIO_REQUEST_ASSERT
    self._audio_request_queue.put(audio_request)
    return

  # set_speaker_location(self, location): Takes in a float value for location
  # between -1.0 and 1.0 that sets how left/right the position of the speaker
  def set_speaker_location(self, location):
    assert isinstance(location, float), LOCATION_ASSERT
    
    if location < constants.LOCATION_MIN:
      self._speaker_location = constants.LOCATION_MIN
    elif location > constants.LOCATION_MAX:
      self._speaker_location = constants.LOCATION_MAX
    else:
      self._speaker_location = location

    return

  # set_audio_data(self, audio_data): Takes in a byte array that is of size
  # multiple of 4096 and splices into frames to be put onto the audio playback
  def set_audio_data(self, audio_data):
    assert isinstance(audio_data,bytes), AUDIO_DATA_ASSERT

    audio_start_index = 0
    audio_end_index = constants.AUDIO_BYTE_FRAME_SIZE
    audio_frame_count = int(len(audio_data)/constants.AUDIO_BYTE_FRAME_SIZE)

    for audio_frame in range(audio_frame_count):
      frame_audio_data = audio_data[audio_start_index:audio_end_index]

      self._temp_audio_segment._data = frame_audio_data
      output_audio_data = self._get_output_audio()

      audio_start_index = audio_end_index
      audio_end_index += constants.AUDIO_BYTE_FRAME_SIZE

      #TODO: Might want to look into having a queue depth
      self._audio_data_queue.put(output_audio_data.raw_data)

    return

  # audio_player_ready(self): A non-blocking call that will return if the audio
  # player is ready for more packets, it should be used to handle getting
  # smooth playback
  def audio_player_ready(self):
    audio_player_status = True

    if self._audio_request_queue.qsize() > self.REQUEST_BUFFER_LIMIT:
      audio_player_status = False
    elif self._audio_data_queue.qsize() > self.AUDIO_BUFFER_LIMIT:
      audio_player_status = False

    return audio_player_status

  # wait_for_audio_player(self): A blocking call that will wait until the audio
  # player is ready to continue before returning
  def wait_for_audio_player(self):
    while not self.audio_player_ready():
      pass
    return

  # Private functions for the audio_player

  def _init_audio_player(self):
    audio_player = pyaudio.PyAudio()

    audio_streamer = audio_player.open(format=constants.AUDIO_FORMAT,
                                       channels=constants.AUDIO_CHANNELS,
                                       rate=constants.AUDIO_RATE,
                                       output=True,
                                       stream_callback=self._audio_callback)
    return audio_player, audio_streamer

  def _create_empty_audio_segment(self):
    audio_segment = pydub.AudioSegment(data=bytes(),
                                       sample_width=constants.AUDIO_SEG_WIDTH,
                                       frame_rate=constants.AUDIO_RATE,
                                       channels=constants.AUDIO_CHANNELS)
    return audio_segment

  def _create_empty_audio_data(self):
    empty_audio_array = constants.EMPTY_BYTE * constants.AUDIO_BYTE_FRAME_SIZE
    return bytes(empty_audio_array)

  def _get_output_audio(self):
    panned_audio = self._temp_audio_segment.pan(self._speaker_location)
    return panned_audio

  def _audio_callback(self, in_data, frame_count, time_info, status):
    audio_data = None

    if self._audio_data_queue.empty():
      audio_data = self._blank_audio_data
    else:
      audio_data = self._audio_data_queue.get()

    self._frame_count = frame_count

    return (audio_data, pyaudio.paContinue)

  def _handle_audio_packet(self, audio_data_packet):
    try:
      speaker_location = audio_data_packet.get(constants.SPEAKER_LOC_STR)
      new_audio_data   = audio_data_packet.get(constants.AUDIO_PAYLOAD_STR)
      timestamp_data   = audio_data_packet.get(constants.TIMESTAMP_STR)

      if speaker_location:
        self.set_speaker_location(speaker_location)

      if new_audio_data:
        self.set_audio_data(new_audio_data)

      if timestamp_data:
        self._process_timestamp(timestamp_data)

    except Exception as audio_packet_error:
      print("Got the error with the handle audio packet: ", audio_packet_error)

    return

  def _process_timestamp(self, timestamp_data):
    assert isinstance(timestamp_data,datetime.datetime)
    current_time = datetime.datetime.now()
    delta_time = current_time - timestamp_data
    #TODO: Figure out what to do with timestamp
    return

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

  #Test 1: Setting the location
  ap.set_speaker_location(0.0)

  #Test 2: Loading audio data from a file
  file_location = "audio/test.wav"
  audio_file = pydub.AudioSegment.from_wav(file_location)
  audio_data = audio_file.raw_data

  playback_len = int(len(audio_data)/10)


  prev_audio_index = 0
  current_audio_index = constants.AUDIO_BYTE_FRAME_SIZE

  while current_audio_index < playback_len:
    audio_data_chunk = audio_data[prev_audio_index:current_audio_index]

    ap.add_audio_request({constants.AUDIO_PAYLOAD_STR: audio_data_chunk,
                           constants.TIMESTAMP_STR: datetime.datetime.now()})

    prev_audio_index = current_audio_index
    current_audio_index += constants.AUDIO_BYTE_FRAME_SIZE
    
    ap.wait_for_audio_player()

  print("Finished playback")
  ap.stop()
  ap.join()

  print("Closing")
