import numpy as np
import librosa

file_name = ".test.wav"

signal_ms = 20  # 単位はms
signal_freq_start = 15000
signal_freq_width = 125
signal_freqs = []
channel = 16

wav, sr = librosa.load(file_name, sr=44100)

for i in range(channel):
    signal_freqs.append(signal_freq_start + i * signal_freq_width)


def detect_index(freqs: np.ndarray) -> list[int]:
    index = []
    for f in freqs:
        for i in range(channel):
            if f >= signal_freqs[i] and f < signal_freqs[i] + signal_freq_width:
                index.append(i)
    return index


def index_to_binary(index: list) -> list[int]:  ## テスト用
    binary = []
    for i in index:
        bin = "{:04b}".format(i)
        for b in bin:
            binary.append(int(b))
    return binary


def audio_to_freqs() -> np.ndarray:
    n_fft = 882
    hop_length = int(sr * (signal_ms / 1000))  # 882

    stft_result = librosa.stft(
        wav, n_fft=n_fft, hop_length=hop_length, window="boxcar", center=False
    )
    abs_result = np.abs(stft_result)

    max_indices = np.argmax(abs_result, axis=0)

    frequencies = librosa.fft_frequencies(sr=sr, n_fft=n_fft)
    strongest_frequencies = frequencies[max_indices]

    return strongest_frequencies


## テスト
if __name__ == "__main__":
    test_freqs = audio_to_freqs()
    test_index = detect_index(test_freqs)
    test_binary = index_to_binary(test_index)
    print(test_binary)
