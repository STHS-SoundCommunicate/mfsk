import numpy as np
import sounddevice as sd
import wave　#test
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from const import *
from rs_codec import convert_text_to_fsk_symbols

signal_freqs = []
for i in range (channels):
    signal_freqs.append(signal_freq_start + i * signal_freq_width)

def str2bits(s: str) -> list[int]:
    result = []
    for byte in s.encode("utf-8"):
        for i in range (7,-1,-1): #下位ビットから出力するとクッソ読みにくい
            result.append((byte >> i) & 1)
    return result

def bits2index(bits: list[int]) -> list[int]:
    result = []
    for i in range(0, len(bits), bits_per_signal):
        groupe = bits[i:i + bits_per_signal] #いい変数名募集
        index = 0
        for bit in groupe:
            index = (index << 1) | bit
        result.append(index)
    return result

def crc8(data: list[int]) -> int: #ドキュメントを作成するのは厳しいので知恵袋に上げたサイトを適宜参照
    crc = 0
    for val in data: #0~15の整数値
        crc ^= val #XOR演算
        for _ in range(8): #_はループカウンタを使わないことを示す
            if crc & 0x80: #生成多項式を適用するかの判定
                crc = ((crc << 1) ^ 0x07) & 0xFF #0x07は生成多項式を表す 0xFFは8bitのマスク
            else:
                crc = (crc << 1) & 0xFF #生成多項式とXORしない場合でも8bitにマスク
    return crc  # 0〜255 (8bit)

def genheader(payload: list[int]) -> list[int]:
    if(len(payload) > 255):
        raise ValueError("うわーん!ペイロードがデカすぎます!")
    payload_length = len(payload)
    message_ID = 0 #実験用として0で固定
    payload_length_symbols = [payload_length >> 4, payload_length & 0xF]
    message_ID_symbols = [message_ID >> 4, message_ID & 0xF]
    header_symbols_info =payload_length_symbols + message_ID_symbols
    crc = crc8(header_symbols_info)
    print(f"info_data : {header_symbols_info}, crc : {crc}") #デバッグ用
    crc_symbols = [crc >> 4, crc & 0xF]
    header_symbols = preamble + header_symbols_info + crc_symbols
    return header_symbols

def gen_wave(index: int, phase: float) -> tuple[np.ndarray, float]:
    freq = signal_freqs[index]
    n_signals = int(sampling_rate * signal_ms / 1000)
    t = np.arange(n_signals) / sampling_rate
    duration = n_signals / sampling_rate
    phase_next = (phase + 2 * np.pi * freq * duration) % (2 * np.pi) #次のシンボルの開始時点での位相を計算
    return np.sin(2 * np.pi * freq * t + phase), phase_next

def play(data: np.ndarray):
    sd.play(data.astype(np.float32), samplerate = sampling_rate)
    sd.wait()

def save_wave(data: np.ndarray, filename :str):
    pcm = (data * np.iinfo(np.int32).max).astype(np.int32) #waveライブラリはpcm整数（16,32bitなどの整数）しか扱えないので変換
    with wave.open(filename, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(4) #1サンプル4バイト→32bitで表現
        wf.setframerate(sampling_rate)
        wf.writeframes(pcm.tobytes())

if __name__ == "__main__":
    print("送信するメッセージを入力")
    send_data = input()
    value = convert_text_to_fsk_symbols(
        send_data, 
        parity_symbols = 16
    )
    # bits =  str2bits(send_data)
    # value = bits2index(bits) #いい変数名募集(2回目)
    value = genheader(value) + value
    waves = []
    phase = 0
    for i in value:
        wave_temp, phase = gen_wave(i, phase)
        waves.append(wave_temp)
    waves = np.concatenate(waves)
    
    print(bits)
    print(value)
    save_wave(waves,".test.wav")
    play(waves)
