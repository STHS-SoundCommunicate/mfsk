import numpy as np
import librosa

file_name = ""
wav, sr = librosa.load(file_name, sr = 44100)

signal_ms = 20 # 単位はms
signal_freq_start = 15000
signal_freq_width = 125
signal_freqs = []
channel = 16

def detect_index(signal_freqs: np.ndarray) -> list[int]:
    index = []
    for f in signal_freqs:
        for i in range(channel):
            if (f >= signal_freqs[i] and f < signal_freqs[i] + signal_freq_width):
                index.append(i)
    return index

def index_to_string(index: list) -> list[int]:
    binary = []
    for i in index:
        b = bin(i)
        for char in b:
            binary.append(int(char))
    return binary   

for i in range(channel):
    signal_freqs.append(signal_freq_start + i * signal_freq_width)

def audio_to_freqs() -> np.ndarray:
    length = int(sr * (signal_ms / 1000)) # 882

    stft_result = librosa.stft(wav, n_fft=1024, hop_length=length)
    abs_result = np.abs(stft_result)

    max_indices = np.argmax(abs_result, axis=0)

    frequencies = librosa.fft_frequencies(sr=sr, n_fft=1024)
    strongest_frequencies = frequencies[max_indices]
    
    return strongest_frequencies

if __name__ == "__main__":