# pro_sound.py
# Xử lý âm thanh trước khi được gọi qua en_picovoice.py
import os
import subprocess
import threading
import time

class SoundPlayer:
    def __init__(self):
        self.play_event = threading.Event()

    def play_audio(self, audio_data):
        try:
            with open("/home/pi/picovoice/audio/en/yessir.wav", "wb") as temp_wav:
                temp_wav.write(audio_data)

            subprocess.Popen(["aplay", "-D", "plughw:0,0", "/home/pi/picovoice/audio/en/yessir.wav"])
            self.play_event.set()  # Đánh dấu rằng âm thanh đã được phát
        except Exception as e:
            print(f"Error playing audio: {str(e)}")

    def wait_for_playback(self):
        self.play_event.wait()  # Đợi cho đến khi âm thanh hoàn tất phát
        self.play_event.clear()  # Đặt lại sự kiện cho lần tiếp theo

sound_player = SoundPlayer()

def play_audio(audio_data):
    sound_player.play_audio(audio_data)
    time.sleep(1)  # Đợi 1 giây để âm thanh hoàn tất phát

if __name__ == '__main__':
    audio_file_path = "/home/pi/picovoice/audio/en/yessir.wav"
    if os.path.exists(audio_file_path):
        with open(audio_file_path, "rb") as audio_file:
            audio_data = audio_file.read()
            play_thread = threading.Thread(target=play_audio, args=(audio_data,))
            play_thread.start()
            play_thread.join()  # Đợi thread phát âm thanh hoàn tất
            sound_player.wait_for_playback()
