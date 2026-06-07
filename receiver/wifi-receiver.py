# wifi_receiver.py
import socket
import threading
import sounddevice as sd
import numpy as np
import sys, os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import const
import receiver_test as rx

# Wi-Fi経由で合図を受け取った瞬間のサンプル位置を記録するグローバル変数
wifi_trigger_pos = -1


def start_wifi_server(get_pos_func):
    global wifi_trigger_pos
    host = "0.0.0.0"
    port = 50000

    def server_task():
        global wifi_trigger_pos
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind((host, port))
            s.listen(1)
            print(f"📡 [Wi-Fi待機中] 送信側からの接続を待っています (Port: {port})...")

            conn, addr = s.accept()
            with conn:
                print(f"🔗 {addr[0]} から接続されました！送信合図を待ちます。")
                data = conn.recv(1024)
                if b"START" in data:
                    # 合図を受け取った瞬間のマイクの録音位置を記録！
                    wifi_trigger_pos = get_pos_func()
                    print(
                        f"⚡ [Wi-Fiトリガー受信!] 現在のサンプル位置: {wifi_trigger_pos}"
                    )

    # マイク録音を止めないように、Wi-Fiの待ち受けは裏（別スレッド）で動かす
    thread = threading.Thread(target=server_task, daemon=True)
    thread.start()


def decode_from_mic_with_wifi() -> tuple[str, float, float, float]:
    global wifi_trigger_pos
    total_mic_samples = 0

    with sd.InputStream(
        samplerate=const.sampling_rate, channels=1, dtype="float32"
    ) as stream:

        def read_samples(count: int) -> np.ndarray:
            nonlocal total_mic_samples
            data, _ = stream.read(count)
            chunk = data[:, 0]
            total_mic_samples += len(chunk)
            return chunk

        def get_pos() -> int:
            return total_mic_samples

        # マイク起動直後にWi-Fiサーバーの待機をスタート
        start_wifi_server(get_pos)

        # 既存のデコード処理を実行
        text, t1, t2 = rx.decode_framed_with_time(read_samples, get_pos)

        # t1 は「録音開始からの秒数」なので、Wi-Fi合図からの秒数に変換する
        if wifi_trigger_pos != -1:
            wifi_trigger_time = wifi_trigger_pos / const.sampling_rate
        else:
            wifi_trigger_time = 0.0

        return text, t1, t2, wifi_trigger_time


def main():
    print("=== [Wi-Fi同期型] 受信解析スタート ===")
    print("※このPCのIPアドレスを調べて、送信側のプログラムに入力してください。")
    text, t1, t2, wifi_trigger_time = decode_from_mic_with_wifi()

    print("\n==============================")
    print("       🎉 実験解析結果 🎉     ")
    print("==============================")
    print(f" 📝 復調メッセージ : {text}")
    print("------------------------------")

    if wifi_trigger_time > 0:
        # Wi-Fi合図を0秒としたときの、音の到着時間
        acoustic_delay = t1 - wifi_trigger_time
        print(f" ⚡ Wi-Fi合図の受信時刻 : {wifi_trigger_time:.4f} 秒")
        print(f" 📈 音波(t1)の到着時刻  : {t1:.4f} 秒")
        print(f" ⏱️ 【測定結果】遅延時間 : {acoustic_delay:.4f} 秒")
    else:
        print(" ⚠️ Wi-Fiトリガーを受信できませんでした。")

    print("==============================")


if __name__ == "__main__":
    main()
