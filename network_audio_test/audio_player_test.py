import pydub

from network_audio_classes.audio_player_process import AudioPlayer
from network_audio_classes import constants


if __name__ == '__main__':

    test_audio_player_left = AudioPlayer()
    test_audio_player_left.start()

    test_audio_player_right = AudioPlayer()
    test_audio_player_right.start()

    test_audio_player_left.set_speaker_location(1.0)
    test_audio_player_right.set_speaker_location(-1.0)

    file_location = "audio/sample.wav"
    audio_file = pydub.AudioSegment.from_mp3(file_location)
    audio_data = audio_file.raw_data

    playback_len = int(len(audio_data) / 10)

    prev_audio_index = 0
    current_audio_index = constants.AUDIO_BYTE_FRAME_SIZE
    previous_data_played = -1

    while current_audio_index < playback_len:
        left_data_played = test_audio_player_left.audio_data_played
        right_data_played = test_audio_player_right.audio_data_played

        if left_data_played == right_data_played:
            audio_data_chunk = audio_data[prev_audio_index:current_audio_index]
            test_audio_player_left.add_audio_data(audio_data_chunk)
            test_audio_player_right.add_audio_data(audio_data_chunk)

            prev_audio_index = current_audio_index
            current_audio_index += constants.AUDIO_BYTE_FRAME_SIZE

            test_audio_player_left.wait_for_audio_player()

        else:
            pass

    print("Left speaker packets played:",
          test_audio_player_left.audio_data_requested,
          "audio data played:",
          test_audio_player_left.audio_data_played)

    print("Right speaker packets played:",
          test_audio_player_right.audio_data_requested,
          "audio data played:",
          test_audio_player_right.audio_data_played)

    print("Finished playback")
    test_audio_player_left.stop()
    print("Left speaker stopped")
    test_audio_player_right.stop()
    print("Closing")
