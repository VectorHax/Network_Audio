import pyaudio
import pydub
import wave
import sys
import numpy
import time
import queue


wf = wave.open("audio/sample.wav", 'rb')
wf_audio_data = wf.readframes(1)

file_location = "audio/sample.wav"
audio_file = pydub.AudioSegment.from_wav(file_location)
audio_data = audio_file.raw_data
prev_audio_index = 0
current_audio_index = 4
audio_data_chunk = audio_data[prev_audio_index:current_audio_index]

print(wf_audio_data)
print(audio_data_chunk)