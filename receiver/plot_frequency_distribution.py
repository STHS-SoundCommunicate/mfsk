import argparse
from pathlib import Path

import librosa
import matplotlib.pyplot as plt
import numpy as np

from const import sampling_rate, signal_ms


def extract_strongest_frequencies(
    wav_path: Path, sr: int, symbol_ms: float
) -> tuple[np.ndarray, np.ndarray]:
    wav, loaded_sr = librosa.load(str(wav_path), sr=sr, mono=True)

    frame_samples = int(loaded_sr * (symbol_ms / 1000))
    if frame_samples <= 0:
        raise ValueError("symbol_ms must create at least 1 sample per frame")

    stft_result = librosa.stft(
        wav,
        n_fft=frame_samples,
        hop_length=frame_samples,
        window="boxcar",
        center=False,
    )
    abs_result = np.abs(stft_result)

    max_indices = np.argmax(abs_result, axis=0)
    frequencies = librosa.fft_frequencies(sr=loaded_sr, n_fft=frame_samples)
    strongest_frequencies = frequencies[max_indices]
    return strongest_frequencies, wav


def main() -> None:
    default_wav = Path(__file__).with_name(".test.wav")
    parser = argparse.ArgumentParser(
        description="WAVからフレームごとの主成分周波数を抽出し、分布を可視化する"
    )
    parser.add_argument("wav_path", nargs="?", type=Path, default=default_wav)
    parser.add_argument("--sr", type=int, default=sampling_rate)
    parser.add_argument("--symbol-ms", type=float, default=signal_ms)
    parser.add_argument("--bins", type=int, default=120)
    parser.add_argument(
        "--save",
        type=Path,
        default=None,
        help="保存先PNGパス。未指定ならウィンドウ表示。",
    )
    args = parser.parse_args()

    if not args.wav_path.exists():
        raise FileNotFoundError(f"WAV file not found: {args.wav_path}")

    strongest_freqs, wav = extract_strongest_frequencies(
        args.wav_path, args.sr, args.symbol_ms
    )
    frame_sec = (args.symbol_ms / 1000.0)
    times = np.arange(len(strongest_freqs)) * frame_sec

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8))
    fig.suptitle(f"Frequency distribution: {args.wav_path.name}")

    ax1.hist(strongest_freqs, bins=args.bins, color="#4F81BD", edgecolor="black")
    ax1.set_title("Histogram of strongest frequencies")
    ax1.set_xlabel("Frequency [Hz]")
    ax1.set_ylabel("Count")
    ax1.grid(alpha=0.25)

    ax2.plot(times, strongest_freqs, ".", markersize=3, color="#C0504D")
    ax2.set_title("Strongest frequency per frame")
    ax2.set_xlabel("Time [s]")
    ax2.set_ylabel("Frequency [Hz]")
    ax2.grid(alpha=0.25)

    plt.tight_layout()

    if args.save is not None:
        args.save.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(args.save, dpi=150)
        print(f"Saved: {args.save}")
        return

    plt.show()


if __name__ == "__main__":
    main()
