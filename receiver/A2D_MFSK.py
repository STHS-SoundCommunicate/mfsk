import argparse
import librosa
import numpy as np
import sounddevice as sd
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from const import *

N = int(sampling_rate * signal_ms / 1000) # 1シンボルあたりのサンプル数(882サンプル)
# 50%オーバーラップ時のホップ幅
HALF_N = N // 2

"""""
#goertzelアルゴリズムによる周波数成分の強さの計算

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
"""

#FFTによる周波数成分の強さの計算
def fft_power(samples: np.ndarray, target_freq: float, sample_rate: int) -> float:
    n = len(samples)

    windowed = samples * np.hanning(n)  #窓関数によるデータ修正
    spectrum = np.fft.rfft(windowed)  #実数FFT
    freqs = np.fft.rfftfreq(n, d=1 / sample_rate)  #各FFTビンの周波数
    idx = np.argmin(np.abs(freqs - target_freq))  #target_freq に一番近いビンを探す
    return float(np.abs(spectrum[idx]) ** 2)  #その周波数成分の強さを返す

def detect_symbol(samples: np.ndarray) -> int:
    powers = [fft_power(samples, f, sampling_rate) for f in signal_freqs]
    return int(np.argmax(powers))



def decode_symbols_to_text(payload_symbols: list[int]) -> str: #ペイロードのシンボル列をテキストに変換
    #シンボル列をビット列に変換
    bits: list[int] = []
    for s in payload_symbols:
        for i in range(bits_per_signal - 1, -1, -1): #3から0桁までのビットを取り出す
            bits.append((s >> i) & 1) #1とand演算した物をリストに追加
    # ビット列をバイト列に変換
    byte_array = list()
    for i in range(0, len(bits) - 7, 8): #各バイト列の先頭を取得
        b = 0
        for bit in bits[i:i + 8]: #8ビット分のビットを取り出しbに追加
            b = (b << 1) | bit
        byte_array.append(b)
    return bytes(byte_array).decode("utf-8", errors="replace")#utf-8でデコード


def read_symbol(read_samples) -> int: #1シンボル分のサンプル読み取り
    data = read_samples(N)
    if len(data) < N:
        raise EOFError("symbol read requires more samples") #シンボル長よりサンプルが少ない時にエラー出力(ファイル入力時用)
    return detect_symbol(data)


def decode_framed(read_samples) -> str: #同期前は0.5シンボル単位で読み取り(精度向上のため)
    buf = np.zeros(N, dtype="float32") #シンボル長分のバッファを生成
    recent: list[int] = []

    print("プリアンブル待機中...")
    pre_len = len(preamble)
    k = 0
    while True:
        chunk = read_samples(HALF_N) #0.5シンボル分のサンプルを読み取る(同期ずれを防ぐため)
        if len(chunk) < HALF_N: #ファイル読み取り時にプリアンブル前に終了したときにエラー
            raise EOFError("preamble not found before end of input")
        buf = np.concatenate([buf[HALF_N:], chunk]) #バッファを更新
        sym = detect_symbol(buf) #シンボル検出
        recent.append(sym) #recentに追加(recentがプリアンブルと一致したら同期)
        k += 1 #n番目のシンボルを検出したかのループカウンタ
        print(f"[preamble] K={k:3d} sym={sym:2d} recent={recent[-8:]}") #デバッグ用
        if len(recent) >= pre_len * 2:
            window = recent[-pre_len * 2:] #recentの末尾から直近4シンボル(半シンボル8)を取り出す
            if window[::2] == preamble or window[1::2] == preamble: #多少位相がずれていても検出できるように奇数と偶数の並びがプリアンブルと一致するかを確認
                break
    print(f"プリアンブル検出  K={k} sym={sym:2d} recent={recent[-8:]}")

    #ヘッダ情報受信    
    #payload length: 2シンボル
    pl_hi = read_symbol(read_samples)
    pl_lo = read_symbol(read_samples)
    payload_length = (pl_hi << 4) | pl_lo
    # message ID: 2シンボル
    mi_hi = read_symbol(read_samples)
    mi_lo = read_symbol(read_samples)
    message_id = (mi_hi << 4) | mi_lo
    # CRC8: 2シンボル
    c8_hi = read_symbol(read_samples)
    c8_lo = read_symbol(read_samples)
    crc8 = (c8_hi << 4) | c8_lo
    print(f"payload length={payload_length} message_id={message_id} crc8={crc8}")
    #ペイロード受信
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
    with sd.InputStream(samplerate=sampling_rate, channels=1, dtype="float32") as stream: #ファイル的な感じでマイク入力ストリームを開く
        def read_samples(count: int) -> np.ndarray: #マイクストリームを読み取る
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