# wifi_transmitter.py
import socket
import sounddevice as sd
import scipy.io.wavfile as wav
import time
import sys, os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import transmitter as tx


def main():
    # 1. 送信先（受信側PC）のIPアドレスを指定
    # ※ Windowsの場合はコマンドプロンプトで「ipconfig」と打ち、IPv4アドレスを確認してください
    receiver_ip = input("受信側PCのIPアドレスを入力してください (例: 192.168.1.10): ")
    port = 50000

    # 2. 送信用の音声ファイルを生成
    test_filename = "wifi_test_packet.wav"
    send_data = "qwertyuiop"
    print(f"\n音波データ '{send_data}' を生成中...")
    tx.create_transmission_file(test_filename, send_data)

    # 3. 音声をメモリに読み込んでおく（再生のタイムラグを無くすため）
    sr, wave_data = wav.read(test_filename)

    # 4. 受信側PCとWi-Fi接続
    print(f"\n{receiver_ip} に接続しています...")
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            # TCPの遅延アルゴリズムを無効化（即座にパケットを送るため）
            s.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            s.connect((receiver_ip, port))
            print("接続成功！Enterキーを押すと、Wi-Fi合図と同時に音波を発射します。")
            input()

            # 🚀 同時発射！
            s.sendall(b"START")  # Wi-Fiで合図を送る
            sd.play(wave_data, samplerate=sr)  # 同時にスピーカーから音を出す

            print("送信完了！音波の再生が終わるまで待機します...")
            sd.wait()

    except ConnectionRefusedError:
        print(
            "❌ 接続に失敗しました。受信側のプログラムが待機状態になっているか、IPアドレスが正しいか確認してください。"
        )


if __name__ == "__main__":
    main()
