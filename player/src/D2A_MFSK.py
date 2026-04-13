import numpy as np
import sounddevice as sd

channels = 16 #16チャンネル使用
bits_per_signal = 4
bps = 200 #200bpsを目標
sampling_rate = 44100 #44100hzで通信
signal_ms = 1 / bps * bits_per_signal * 1000
baud_rate = 1000 / signal_ms #分解能は12.5hz
signal_freq_start = 15000
signal_freq_width = 125

signal_freqs = []
for i in range (channels):
    signal_freqs.append(signal_freq_start + i * signal_freq_width)

def str2bits(s: str) -> list[int]:
    result = []
    for byte in s.encode("utf-8"):
        for i in range (7,-1,-1): #下位ビットから出力するとクッソ読みにくい
            result.append((byte >> i) & 1)
    print(result) #デバッグ用
    return result

def pad_bits(bits: list[int]) -> list[int]:
    r = len(bits) % bits_per_signal
    if r != 0:
        bits += [0] * (bits_per_signal - r)
    return bits

def bits2index(bits: list[int]) -> list[int]:
    result = []
    for i in range(0, len(bits), bits_per_signal):
        groupe = bits[i:i + bits_per_signal] #いい変数名募集
        index = 0
        for bit in groupe:
            index = (index << 1) | bit
        result.append(index)
    return result

def gen_wave(index: int) -> np.ndarray:
    freq = signal_freqs[index]
    n_signals = int(sampling_rate * signal_ms / 1000)
    t = np.arange(n_signals) / sampling_rate
    return np.sin(2 * np.pi * freq * t)

def play(data: np.ndarray):
    sd.play(data.astype(np.float32), samplerate = sampling_rate)
    sd.wait()

if __name__ == "__main__":
    send_data = "test"
    bits = pad_bits(str2bits(send_data))
    value = bits2index(bits) #いい変数名募集(2回目)
    waves = []
    for i in value:
        waves.append(gen_wave(i))
    waves = np.concatenate(waves)
    
    print(bits)
    print(value)
    
    play(waves)