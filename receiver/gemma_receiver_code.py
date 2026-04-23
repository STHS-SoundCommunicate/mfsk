import argparse

import librosa
import numpy as np
import sounddevice as sd

from const import bits_per_signal, preamble, sampling_rate, signal_ms, signal_freqs

N = int(sampling_rate * signal_ms / 1000) # 1シンボルあたりのサンプル数(882サンプル)
# 50%オーバーラップ時のホップ幅
HALF_N = N // 2


def goertzel(samples: np.ndarray, target_freq: float, sample_rate: int) -> float: #goertzelアルゴリズムというものがあるらしい...
    n = len(samples)
    k = int(0.5 + n * target_freq / sample_rate)
    w = 2 * np.pi * k / n
    coeff = 2 * np.cos(w)
    s0, s1, s2 = 0.0, 0.0, 0.0
    for sample in samples:
        s0 = sample + coeff * s1 - s2
        s2 = s1
        s1 = s0
    return s1 * s1 + s2 * s2 - coeff * s1 * s2


def detect_symbol(samples: np.ndarray) -> int: #16チャネルのうちどの周波数が最も強いかを検出する
    powers = [goertzel(samples, f, sampling_rate) for f in signal_freqs]
    return int(np.argmax(powers))


def decode_symbols_to_text(payload_symbols: list[int]) -> str: #ペイロードのシンボル列をテキストに変換
    #シンボル列をビット列に変換
    bits: list[int] = []
    for s in payload_symbols:
        for i in range(bits_per_signal - 1, -1, -1):
            bits.append((s >> i) & 1)

    # ビット列 → バイト列
    byte_arr = bytearray()
    for i in range(0, len(bits) - 7, 8):
        b = 0
        for bit in bits[i:i + 8]:
            b = (b << 1) | bit
        byte_arr.append(b)

    # 末尾パディング除去 → UTF-8デコード
    return byte_arr.rstrip(b"\x00").decode("utf-8", errors="replace")


def read_symbol(read_samples) -> int: #1シンボル分のサンプル読み取り
    data = read_samples(N)
    if len(data) < N:
        raise EOFError("symbol read requires more samples")
    return detect_symbol(data)


def decode_framed(read_samples) -> str: #同期前は0.5シンボル単位で読み取り(精度向上のため)
    buf = np.zeros(N, dtype="float32")
    recent: list[int] = []

    print("プリアンブル待機中...")
    pre_len = len(preamble)
    while True:
        chunk = read_samples(HALF_N)
        if len(chunk) < HALF_N:
            raise EOFError("preamble not found before end of input")
        buf = np.concatenate([buf[HALF_N:], chunk])
        sym = detect_symbol(buf)
        recent.append(sym)
        if len(recent) >= pre_len * 2:
            window = recent[-pre_len * 2:]
            if window[::2] == preamble or window[1::2] == preamble:
                break
    print("プリアンブル検出")
    """
    #無音区間ののちにindex15の音を1ms単位で読み取って同期を行う
    sync_count = 0
    while True:
        ms_sample = sampling_rate // 1000
        chunk = read_samples(ms_sample) #1ms分のサンプルを読み取る
        buf = np.concatenate([buf[ms_sample:], chunk])
        sym = detect_symbol(buf)
        if sym == 15:
            sync_count += 1
        if sync_count > 18: #20ms以上連続でindex15が続いたら同期確立とみなす
            break
    """
        
    print("同期確立 --- ヘッダー受信中...")
    #payload length: 2シンボル
    pl_hi = read_symbol(read_samples)
    pl_lo = read_symbol(read_samples)
    payload_length = (pl_hi << 4) | pl_lo
    # message ID
    read_symbol(read_samples)
    read_symbol(read_samples)
    # CRC8: 2シンボル
    read_symbol(read_samples)
    read_symbol(read_samples)
    # --- ペイロード受信 ---
    payload_symbols = [read_symbol(read_samples) for _ in range(payload_length,)]
    print(payload_symbols)
    return decode_symbols_to_text(payload_symbols)


def decode_raw(wav: np.ndarray) -> str:
    symbols: list[int] = []
    for i in range(0, len(wav) - N + 1, N):
        symbols.append(detect_symbol(wav[i:i + N]))
    return decode_symbols_to_text(symbols)


def file_reader_factory(wav: np.ndarray):
    cursor = 0

    def read_samples(count: int) -> np.ndarray:
        nonlocal cursor
        chunk = wav[cursor:cursor + count]
        cursor += len(chunk)
        return chunk

    return read_samples


def decode_from_file(file_path: str, mode: str) -> str:
    wav, sr = librosa.load(file_path, sr=sampling_rate, mono=True)
    wav = wav.astype("float32")

    if mode == "raw":
        return decode_raw(wav)

    if mode == "framed":
        return decode_framed(file_reader_factory(wav))

    # auto
    try:
        return decode_framed(file_reader_factory(wav))
    except EOFError:
        return decode_raw(wav)


def decode_from_mic() -> str:
    with sd.InputStream(samplerate=sampling_rate, channels=1, dtype="float32") as stream:
        def read_samples(count: int) -> np.ndarray:
            data, _ = stream.read(count)
            return data[:, 0]

        return decode_framed(read_samples)


def main() -> None:
    parser = argparse.ArgumentParser(description="MFSK receiver")
    parser.add_argument(
        "--input",
        type=str,
        default=None,
        help="ローカル音声ファイルへのパス。未指定時はマイク入力",
    )
    parser.add_argument(
        "--mode",
        choices=["auto", "framed", "raw"],
        default="auto",
        help="復調モード (auto/framed/raw)",
    )
    args = parser.parse_args()

    if args.input:
        text = decode_from_file(args.input, args.mode)
    else:
        text = decode_from_mic()

    
    print(text)

if __name__ == "__main__":
    main()