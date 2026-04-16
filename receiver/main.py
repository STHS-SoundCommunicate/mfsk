import numpy as np
import librosa

file_name = ".test.wav"

signal_ms = 20 # 単位はms
signal_freq_start = 15000
signal_freq_width = 125
signal_freqs = []
channel = 16

def detect_index(freqs: np.ndarray) -> list[int]:
    index = []
    for f in freqs:
        for i in range(channel):
            if (f < 15000 or f > signal_freq_start + channel * signal_freq_width):
                index.append(-1)
            elif (f >= signal_freqs[i] and f < signal_freqs[i] + signal_freq_width):
                index.append(i)
    return index

def index_to_string(index: list) -> list[int]:
    binary = []
    for i in index:
        if (i == -1): ## エラー処理
            print("Panic: index is -1")
            return []
        b = bin(i)
        for char in b[2:]: # 先頭の'0b'を除く
            binary.append(int(char))
    return binary   

for i in range(channel):
    signal_freqs.append(signal_freq_start + i * signal_freq_width)

def audio_to_freqs() -> np.ndarray:
    wav, sr = librosa.load(file_name, sr = 44100)
    length = int(sr * (signal_ms / 1000)) # 882

    stft_result = librosa.stft(wav, n_fft=1024, hop_length=length)
    abs_result = np.abs(stft_result)

    max_indices = np.argmax(abs_result, axis=0)

    frequencies = librosa.fft_frequencies(sr=sr, n_fft=1024)
    strongest_frequencies = frequencies[max_indices]
    
    return strongest_frequencies

if __name__ == "__main__":
    freqs = audio_to_freqs()
    index = detect_index(freqs)
    binary = index_to_string(index)
    print(binary)