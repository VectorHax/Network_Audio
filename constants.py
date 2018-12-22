# constants.py
# Created by: Dale Best
# Created on: December 22nd, 2018

# A file to hold the constant values for the application

AUDIO_FORMAT = 8
AUDIO_CHANNELS = 2
AUDIO_SEG_WIDTH = 2
AUDIO_RATE = 44100

AUDIO_BYTE_PER_FRAME = 4
AUDIO_FRAME_SIZE = 1024
AUDIO_BYTE_FRAME_SIZE = AUDIO_BYTE_PER_FRAME * AUDIO_FRAME_SIZE

EMPTY_BYTE = [0]

STARTING_LOCATION = 0.0
LOCATION_MAX =  1.0 # The right most location
LOCATION_MIN = -1.0 # The left most location

FULL_RIGHT_LOCATION = LOCATION_MAX
FULL_LEFT_LOCATION = LOCATION_MIN

PROCESS_KILL_WORD = "KILL"


SPEAKER_LOC_STR = "Speaker_Location"
AUDIO_PAYLOAD_STR = "Audio_Payload"
TIMESTAMP_STR = "Timestamp"
