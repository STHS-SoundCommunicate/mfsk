# transmitter.py
import sys, os
import numpy as np
import wave

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from const import *
from D2A_MFSK import *


def generate_full_signal(message_str: str) -> tuple[np.ndarray, float]:
    """
    文字列からヘッダー（プリアンブル含む）とデータ部をすべて結合した
    一連の音声信号（波形データ）を生成します。
    """
    bits = str2bits(message_str)
    payload_indices = bits2index(bits)

    # ヘッダーとペイロードをドッキングしたすべてのシンボル列
    full_indices = genheader(payload_indices) + payload_indices

    waves = []
    phase = 0.0
    for idx in full_indices:
        wave_temp, phase = gen_wave(idx, phase)
        waves.append(wave_temp)

    combined_signal = np.concatenate(waves).astype(np.float32)

    # 💡 追加ポイント: 受信側が数サンプル余分に読み込んでも落ちないよう、末尾に0.2秒の無音を足す
    silence = np.zeros(int(sampling_rate * 0.2), dtype=np.float32)
    combined_signal = np.concatenate([combined_signal, silence])

    # 時間測定用：ヘッダー（プリアンブル含む）が何秒間あるかを計算
    header_length_symbols = len(preamble) + 6
    header_duration = header_length_symbols * (signal_ms / 1000.0)

    return combined_signal, header_duration


def create_transmission_file(filename: str, message_str: str) -> float:
    """
    指定された文字列から送信用信号を作ってWAVファイルに保存し、
    解析のヒントとなるヘッダーの長さを返します。
    """
    signal_data, header_duration = generate_full_signal(message_str)

    # 32bit PCM 整数フォーマットに変換して保存
    pcm = (signal_data * np.iinfo(np.int32).max).astype(np.int32)

    with wave.open(filename, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(4)  # 32bit (4バイト)
        wf.setframerate(sampling_rate)
        wf.writeframes(pcm.tobytes())

    return header_duration
