import numpy as np
import librosa

file_name = ""
wav, sr = librosa.load(file_name, sr = 44100)

signal_ms = 20 # 単位はms
signal_freq_start = 15000
signal_freq_width = 125
signal_freqs = []

for i in range(16):
    signal_freqs.append(signal_freq_start + i * signal_freq_width)
    
length = int(sr * (signal_ms / 1000)) # 882

stft_result = librosa.stft(wav, n_fft=1024, hop_length=length)
abs_result = np.abs(stft_result)

max_indices = np.argmax(abs_result, axis=0)

frequencies = librosa.fft_frequencies(sr=sr, n_fft=1024)
strongest_frequencies = frequencies[max_indices]


for f in strongest_frequencies:
    
