import argparse
import librosa
import numpy as np
import sounddevice as sd
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from const import *
correct_data = "abcdefghijklmnopqrstuvwxyz1234567890!@#$%^&*()_+-=,./<>?;:'[]|`~"

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

def detect_symbol(samples: np.ndarray) -> int: #16チャネルのうちどの周波数が最も強いかを検出する
    powers = [goertzel(samples, f, sampling_rate) for f in signal_freqs]
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

def decode_framed(read_samples) -> str: #同期前は0.5シンボル単位で読み取り(精度向上のため)
    buf = np.zeros(N, dtype="float32") #シンボル長分のバッファを生成
    recent: list[int] = []
    recent_raw = np.zeros(HALF_N * 9, dtype="float32") #プリアンブル長と半シンボル分のバッファ

    print("プリアンブル待機中...")
    pre_len = len(preamble)
    k = 0
    while True:
        chunk = read_samples(HALF_N) #0.5シンボル分のサンプルを読み取る(同期ずれを防ぐため)
        if len(chunk) < HALF_N: #ファイル読み取り時にプリアンブル前に終了したときにエラー
            raise EOFError("preamble not found before end of input")
        buf = np.concatenate([buf[HALF_N:], chunk]) #バッファを更新
        recent_raw = np.concatenate([recent_raw[HALF_N:], chunk]) #直近4.5シンボル分の生データを保持するバッファ
        sym = detect_symbol(buf) #シンボル検出
        recent.append(sym) #recentに追加(recentがプリアンブルと一致したら同期)
        recent = recent[-(pre_len * 2):]
        k += 1 #n番目のシンボルを検出したかのループカウンタ
        print(f"[preamble] K={k:3d} sym={sym:2d} recent={recent[-8:]}") #デバッグ用
        if len(recent) >= pre_len * 2:
            window = recent[-pre_len * 2:] #recentの末尾から直近4シンボル(半シンボル8)を取り出す
            if window[::2] == preamble or window[1::2] == preamble: #多少位相がずれていても検出できるように奇数と偶数の並びがプリアンブルと一致するかを確認
                phase_offset = 0 if window[::2] == preamble else HALF_N
                temp_max = 0
                start_preamble = phase_offset #偶数での読み取り時はrecent_rawの先頭から、奇数での読み取り時は半シンボル分オフセットした位置から
                for i in range(phase_offset, phase_offset + HALF_N):
                    score = goertzel(recent_raw[i:i+N], signal_freqs[0], sampling_rate)
                    if score > temp_max:
                        temp_max = score
                        start_preamble = i
                post_preamble_idx = start_preamble + N * 4 #プリアンブルの開始位置+4シンボル→ヘッダの開始位置
                buf_size = len(recent_raw)  # = HALF_N * 9
                buffered = recent_raw[min(post_preamble_idx, buf_size):] #recent_rawに積んでいるヘッダの長さ
                overshoot = max(0, post_preamble_idx - buf_size) #ストリームに残っているプリアンブルの長さ
                stream_chunk = read_samples(overshoot + 6 * N - len(buffered)) #ヘッダの終端までの読み取り前サンプルをストリームから読み取る
                header_info = np.concatenate([buffered, stream_chunk])[overshoot:] #recent_raw内のヘッダ部分とストリームから読み取ったヘッダ部分を連結
                #ヘッダ情報受信
                pl_hi = detect_symbol(header_info[:N])
                pl_lo = detect_symbol(header_info[N:2 * N])
                payload_length = (pl_hi << 4) | pl_lo
                mi_hi = detect_symbol(header_info[2 * N:3 * N])
                mi_lo = detect_symbol(header_info[3 * N:4 * N])
                message_id = (mi_hi << 4) | mi_lo
                c8_hi = detect_symbol(header_info[4 * N:5 * N])
                c8_lo = detect_symbol(header_info[5 * N:6 * N])
                crc_raw = (c8_hi << 4) | c8_lo
                crc8_data = [pl_hi, pl_lo, mi_hi, mi_lo]
                print(crc8(crc8_data))
                if(crc_raw == crc8(crc8_data)):
                    print("CRC check passed")
                    break
                else:
                    print("header is broken")
                print(crc8(crc8_data + [c8_hi, c8_lo]))
    print(f"プリアンブル検出  K={k} sym={sym:2d} recent={recent[-8:]}")
    print(f"payload length={payload_length} message_id={message_id} crc={crc_raw}")
    #ペイロード受信
    payload_symbols = [read_symbol(read_samples) for _ in range(payload_length)]
    print(payload_symbols)
    correct_symbols = bits2index(str2bits(correct_data))
    print(correct_symbols)
    actually_correct = sum(p == c for p, c in zip(payload_symbols, correct_symbols))
    print(f"合致したシンボル数: {actually_correct} 精度: {actually_correct / payload_length}")
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
