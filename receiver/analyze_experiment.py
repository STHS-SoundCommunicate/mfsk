# analyze_experiment.py
import argparse
import librosa
import sounddevice as sd
import numpy as np
import sys, os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import const
import receiver_test as rx


def decode_from_file(file_path: str) -> tuple[str, float, float]:
    """WAVファイルを読み込んで、時間付きでデコードを行います。"""
    wav_data, sr = librosa.load(file_path, sr=const.sampling_rate, mono=True)
    wav_data = wav_data.astype("float32")
    reader, get_pos = rx.file_reader_factory(wav_data)
    return rx.decode_framed_with_time(reader, get_pos)


def decode_from_mic() -> tuple[str, float, float]:
    """マイクからリアルタイムにストリームを入力し、時間付きでデコードを行います。"""
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

        return rx.decode_framed_with_time(read_samples, get_pos)


def main() -> None:
    parser = argparse.ArgumentParser(description="MFSK Time-Measurement Receiver")
    parser.add_argument(
        "--input",
        type=str,
        default=None,
        help="録音した音声ファイル(.wav)へのパス。未指定時はマイク入力でリアルタイム計測",
    )
    args = parser.parse_args()

    print("=== [受信解析スタート] ===")
    if args.input:
        text, t1, t2 = decode_from_file(args.input)
    else:
        print("※マイク入力待ちです。送信側から音波を流してください。")
        text, t1, t2 = decode_from_mic()

    # 実験結果の出力
    print("\n==============================")
    print("       🎉 実験解析結果 🎉     ")
    print("==============================")
    print(f" 📝 復調メッセージ : {text}")
    print(f" 📈 送信開始時刻(t1): {t1:.4f} 秒の位置")
    print(f" 🏁 受信完了時刻(t2): {t2:.4f} 秒の位置")
    print("------------------------------")

    total_communication_time = t2 - t1
    print(f" ⏱️ 送信開始〜受信完了の総時間: {total_communication_time:.4f} 秒")
    print("==============================")


if __name__ == "__main__":
    main()
