import argparse
import sqlite3
import struct
import wave
import os
import time
import subprocess
import json

import paho.mqtt.publish as publish
from _picovoice import Picovoice
from pvrecorder import PvRecorder
from pixels import pixels
import atexit
import pro_sound

    
def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        '--access_key',
        help='AccessKey obtained from Picovoice Console (https://console.picovoice.ai/)')

    parser.add_argument(
        '--keyword_path',
        help="Absolute path to a Porcupine keyword file.")
    
    # parser.add_argument(
    #     '--wav_path',
    #     help='Absolute path to input audio file.',
    #     required=True)

    parser.add_argument(
        '--context_path',
        help="Absolute path to a Rhino context file.")

#--porcupine_library_path
    parser.add_argument(
        '--porcupine_library_path',
        help="Absolute path to Porcupine's dynamic library.")

#--porcupine_model_path
    parser.add_argument(
        '--porcupine_model_path',
        help="Absolute path to Porcupine's model file.")

    parser.add_argument(
        '--porcupine_sensitivity',
        help="Sensitivity for detecting wake word. Each value should be a number within [0, 1]. A higher sensitivity "
             "results in fewer misses at the cost of increasing the false alarm rate.",
        type=float,
        default=0.5)

#--rhino_library_path
    parser.add_argument(
        '--rhino_library_path',
        help="Absolute path to Rhino's dynamic library.")

#--rhino_model_path
    parser.add_argument(
        '--rhino_model_path',
        help="Absolute path to Rhino's model file.")

    parser.add_argument(
        '--rhino_sensitivity',
        help="Inference sensitivity. It should be a number within [0, 1]. A higher sensitivity value results in fewer "
             "misses at the cost of (potentially) increasing the erroneous inference rate.",
        type=float,
        default=0.5)

    parser.add_argument(
        '--endpoint_duration_sec',
        help="Endpoint duration in seconds. An endpoint is a chunk of silence at the end of an utterance that marks "
             "the end of spoken command. It should be a positive number within [0.5, 5]. A lower endpoint duration "
             "reduces delay and improves responsiveness. A higher endpoint duration assures Rhino doesn't return "
             "inference pre-emptively in case the user pauses before finishing the request.",
        type=float,
        default=1.)

    parser.add_argument(
        '--require_endpoint',
        help="If set to `True`, Rhino requires an endpoint (a chunk of silence) after the spoken command. If set to "
             "`False`, Rhino tries to detect silence, but if it cannot, it still will provide inference regardless. "
             "Set to `False` only if operating in an environment with overlapping speech (e.g. people talking in the "
             "background).",
        default='True',
        choices=['True', 'False'])

    parser.add_argument('--audio_device_index', help='index of input audio device', type=int, default=-1)

    parser.add_argument('--output_path', help='Absolute path to recorded audio for debugging.', default=None)

    parser.add_argument('--show_audio_devices', action='store_true')

    args = parser.parse_args()

    if args.require_endpoint.lower() == 'false':
        require_endpoint = False
    else:
        require_endpoint = True

    if args.show_audio_devices:
        for i, device in enumerate(PvRecorder.get_available_devices()):
            print('Device %d: %s' % (i, device))
        return

    if not args.access_key or not args.keyword_path or not args.context_path:
        print('--access_key, --keyword_path and --context_path are required.')
        return
    

    def exit_handler():
        pixels.off()
    atexit.register(exit_handler)

    def wake_word_callback():
        print('[wake word]\n')
        pixels.wakeup()
        
    # Play the audio file using aplay
 
        
# Tiếp tục với các bước khởi tạo và vòng lặp ghi âm của bạn

    # Khai báo hàm inference_callback để xử lý kết quả nhận dạng từ Rhino
    def inference_callback(inference):
        global last_intent

        if inference.is_understood:

            last_intent = inference.intent  # Set the last_intent when understood
            intent = inference.intent
            mqtt_topic = "picovoice/intent"
            publish.single(mqtt_topic, intent, hostname="localhost")

            # Hiển thị thông tin intent và slots
            print('{')
            print("  intent : '%s'" % inference.intent)
            print('  slots : {')
            for slot, value in inference.slots.items():
                print("    %s : '%s'" % (slot, value))
            print('  }')
            print('}\n')
            
            # Tải dữ liệu từ tệp JSON
            with open('/home/pi/picovoice/json/changeLight.json', 'r') as json_file:
                json_data = json.load(json_file)

              # Connect db
            conn = sqlite3.connect('/home/pi/picovoice/database/ConnectLukatoWeb.db')
            cursor = conn.cursor()

            # Lặp qua từng phần tử trong danh sách JSON và kiểm tra khớp với kết quả nhận dạng từ Picovoice
            for item in json_data:
                if item.get("intent") == inference.intent and item.get("slots") == inference.slots:
                    print("Dữ liệu JSON khớp với kết quả nhận dạng từ Picovoice.")
                    
                    # Lấy danh sách các pin từ dữ liệu JSON và thực hiện gửi tin nhắn MQTT đến các pin tương ứng
                    if "pin" in item:
                        pins = item["pin"].split(", ")
                        for pin in pins:
                            mqtt_topic = "esp8266/" + pin
                            mqtt_message = "0" if inference.slots["state"] == "on" else "1"
                            publish.single(mqtt_topic, mqtt_message, hostname="localhost")

                        pin_numbers = item["pin"].split(", ")
                        state = True if inference.slots["state"] == "on" else False

                         # Cập nhật trạng thái và số chân pin trong cơ sở dữ liệu
                    for pin_number in pin_numbers:
                        cursor.execute("UPDATE LightControl SET status = ? WHERE pin_number = ? ;", (state, int(pin_number)))
                    print("Đã cập nhật dữ liệu mới")

                    # Lưu thay đổi và đóng kết nối
                    conn.commit()
                    conn.close()

                    # Phát tệp âm thanh "yes-sir.wav"
                    audio_file_path = "/home/pi/picovoice/audio/en/yes-sir.wav"
                    print("yes sir, I will do it right away.")
                    if os.path.exists(audio_file_path):
                        subprocess.Popen(["aplay", "-D", "plughw:0,0", audio_file_path])
                        time.sleep(1)  # Đợi 1 giây để âm thanh hoàn tất phát
                    else:
                        print("Audio file not found.")
                    return
            else:
                print("Picovoice inference does not match JSON data.\n")

                # Phát tệp âm thanh "try-again.wav"
                try_again_audio_file_path = "/home/pi/picovoice/audio/en/try-again.wav"
                print("Sorry, I don't understand what you mean. Please try again.")
                if os.path.exists(try_again_audio_file_path):
                    subprocess.Popen(["aplay", "-D", "plughw:0,0", try_again_audio_file_path])
                    time.sleep(1)  # Đợi 1 giây để âm thanh hoàn tất phát
                else:
                    print("Try-again audio file not found.")
        else:
            print("Didn't understand the command.\n")
            # Phát tệp âm thanh "try-again.wav"
            try_again_audio_file_path = "/home/pi/picovoice/audio/en/try-again.wav"
            print("Sorry, I don't understand what you mean. Please try again.")
            if os.path.exists(try_again_audio_file_path):
                subprocess.Popen(["aplay", "-D", "plughw:0,0", try_again_audio_file_path])
                time.sleep(1)  # Đợi 1 giây để âm thanh hoàn tất phát
            else:
                print("Try-again audio file not found.")
    
    try:
        # Khởi tạo Picovoice
        picovoice = Picovoice(            
            access_key=args.access_key,
            keyword_path=args.keyword_path,
            wake_word_callback=wake_word_callback,
            context_path=args.context_path,
            inference_callback=inference_callback,
            porcupine_library_path=args.porcupine_library_path,
            porcupine_model_path=args.porcupine_model_path,
            porcupine_sensitivity=args.porcupine_sensitivity,
            rhino_library_path=args.rhino_library_path,
            rhino_model_path=args.rhino_model_path,
            rhino_sensitivity=args.rhino_sensitivity,
            endpoint_duration_sec=args.endpoint_duration_sec,
            require_endpoint=require_endpoint
        )
    except PicovoiceInvalidArgumentError as e:
        print("One or more arguments provided to Picovoice is invalid: ", args)
        print("If all other arguments seem valid, ensure that '%s' is a valid AccessKey" % args.access_key)
        raise e
    except PicovoiceActivationError as e:
        print("AccessKey activation error")
        raise e
    except PicovoiceActivationLimitError as e:
        print("AccessKey '%s' has reached it's temporary device limit" % args.access_key)
        raise e
    except PicovoiceActivationRefusedError as e:
        print("AccessKey '%s' refused" % args.access_key)
        raise e
    except PicovoiceActivationThrottledError as e:
        print("AccessKey '%s' has been throttled" % args.access_key)
        raise e
    except PicovoiceError as e:
        print("Failed to initialize Picovoice")
        raise e

    # In ra phiên bản Picovoice và thông tin ngữ cảnh
    print('Picovoice version: %s' % picovoice.version)
    print('Context info: %s' % picovoice.context_info)

    # Khởi tạo và cấu hình recorder để ghi âm
    recorder = PvRecorder(
        frame_length=picovoice.frame_length,
        device_index=args.audio_device_index,
    )
    recorder.start()

    print('Listening ... (Press Ctrl+C to exit)\n')

    wav_file = None
    if args.output_path is not None:
        wav_file = wave.open(args.output_path, 'wb')
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(picovoice.sample_rate)

    try:
        while True:
            pcm = recorder.read()
            
            if wav_file is not None:
                wav_file.writeframes(struct.pack("h" * len(pcm), *pcm))

            # Xử lý âm thanh thông qua Picovoice
            picovoice.process(pcm)

    except KeyboardInterrupt:
        print('Stopping ...')
    finally:
        # Giải phóng tài nguyên khi thoát chương trình
        recorder.delete()
        picovoice.delete()
        pixels.off()
        if wav_file is not None:
            wav_file.close()
            
if __name__ == '__main__':
    main()