import FHSS
import librosa
import numpy as np
from const import channels, sampling_rate, signal_freq_width, signal_ms

file_name = ".test.wav"
wav, sr = librosa.load(file_name, sr=sampling_rate)


def detect_index(freqs: np.ndarray) -> list[int]:
    index = []
    half_band = signal_freq_width / 2
    for symbol_index, f in enumerate(freqs):
        hop_freq = FHSS.return_fhss(symbol_index)
        base_freq = f - hop_freq
        nearest_channel = int(round(base_freq / signal_freq_width))
        nearest_center = nearest_channel * signal_freq_width
        if (
            0 <= nearest_channel < channels
            and abs(base_freq - nearest_center) <= half_band
        ):
            index.append(nearest_channel)
    return index


# def index_to_binary(index: list) -> list[int]:  ## テスト用
#     binary = []
#     for i in index:
#         bin = "{:04b}".format(i)
#         for b in bin:
#             binary.append(int(b))
#     return binary


def index_to_message(index: list[int]):
    # 例: 4bitシンボルを2つで1byte化している想定
    byte_values = []
    for i in range(0, len(index) - 1, 2):
        hi = index[i]
        lo = index[i + 1]
        byte_values.append((hi << 4) | lo)

    raw = bytes(byte_values)
    print("hex:", raw.hex(" "))
    return raw.decode("utf-8", errors="replace")  # 一時的にreplace


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
    print(test_index)
    test_message = index_to_message(test_index)
    print(test_message)
