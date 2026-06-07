# receiver_test.py
import numpy as np
import scipy.signal as signal
import const

# 1シンボルあたりのサンプル数やホップ幅を const から再計算
N = int(const.sampling_rate * const.signal_ms / 1000)
HALF_N = N // 2


def goertzel(samples: np.ndarray, target_freq: float, sample_rate: int) -> float:
    """Goertzelアルゴリズムを用いて特定の周波数成分の強度を計算します。"""
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


def detect_symbol(samples: np.ndarray) -> int:
    """16チャネルのうち最も強度の強い周波数のインデックスを検出します。"""
    signal_freqs = [
        const.signal_freq_start + i * const.signal_freq_width
        for i in range(const.channels)
    ]
    powers = [goertzel(samples, f, const.sampling_rate) for f in signal_freqs]
    return int(np.argmax(powers))


def decode_symbols_to_text(payload_symbols: list[int]) -> str:
    """シンボル列をビット列経由でUTF-8テキストに変換します。"""
    bits: list[int] = []
    for s in payload_symbols:
        for i in range(const.bits_per_signal - 1, -1, -1):
            bits.append((s >> i) & 1)

    byte_array = list()
    for i in range(0, len(bits) - 7, 8):
        b = 0
        for bit in bits[i : i + 8]:
            b = (b << 1) | bit
        byte_array.append(b)
    return bytes(byte_array).decode("utf-8", errors="replace")


def crc8(data: list[int]) -> int:
    """ヘッダー検証用のCRC8チェックサムを計算します。"""
    crc = 0
    for val in data:
        crc ^= val
        for _ in range(8):
            if crc & 0x80:
                crc = ((crc << 1) ^ 0x07) & 0xFF
            else:
                crc = (crc << 1) & 0xFF
    return crc


def decode_framed_with_time(read_samples, get_pos) -> tuple[str, float, float]:
    """
    元の decode_framed の同期ロジックを完全に維持したまま、
    t1（プリアンブル検知・送信開始時刻）と t2（すべての処理完了時刻）を計測して返します。
    """
    buf = np.zeros(N, dtype="float32")
    recent: list[int] = []
    recent_raw = np.zeros(HALF_N * 9, dtype="float32")

    print("プリアンブル待機中...")
    pre_len = len(const.preamble)
    k = 0

    while True:
        chunk = read_samples(HALF_N)
        if len(chunk) < HALF_N:
            raise EOFError("preamble not found before end of input")

        buf = np.concatenate([buf[HALF_N:], chunk])
        recent_raw = np.concatenate([recent_raw[HALF_N:], chunk])

        sym = detect_symbol(buf)
        recent.append(sym)
        recent = recent[-(pre_len * 2) :]
        k += 1

        if len(recent) >= pre_len * 2:
            window = recent[-pre_len * 2 :]
            if window[::2] == const.preamble or window[1::2] == const.preamble:
                phase_offset = 0 if window[::2] == const.preamble else HALF_N
                temp_max = 0
                start_preamble = phase_offset

                for i in range(phase_offset, phase_offset + HALF_N):
                    signal_freqs = [
                        const.signal_freq_start + idx * const.signal_freq_width
                        for idx in range(const.channels)
                    ]
                    score = goertzel(
                        recent_raw[i : i + N], signal_freqs[0], const.sampling_rate
                    )
                    if score > temp_max:
                        temp_max = score
                        start_preamble = i

                post_preamble_idx = start_preamble + N * 4
                buf_size = len(recent_raw)
                buffered = recent_raw[min(post_preamble_idx, buf_size) :]
                overshoot = max(0, post_preamble_idx - buf_size)

                # ヘッダーの終端までストリームから読み取る
                header_requested_len = overshoot + 6 * N - len(buffered)
                stream_chunk = read_samples(header_requested_len)

                header_info = np.concatenate([buffered, stream_chunk])[overshoot:]

                # ヘッダー情報デコード
                pl_hi = detect_symbol(header_info[:N])
                pl_lo = detect_symbol(header_info[N : 2 * N])
                payload_length = (pl_hi << 4) | pl_lo

                mi_hi = detect_symbol(header_info[2 * N : 3 * N])
                mi_lo = detect_symbol(header_info[3 * N : 4 * N])

                c8_hi = detect_symbol(header_info[4 * N : 5 * N])
                c8_lo = detect_symbol(header_info[5 * N : 6 * N])
                crc_raw = (c8_hi << 4) | c8_lo

                crc8_data = [pl_hi, pl_lo, mi_hi, mi_lo]

                if crc_raw == crc8(crc8_data):
                    print("CRC check passed")

                    current_pos = get_pos()
                    t1_sample_pos = (
                        current_pos - len(stream_chunk) - (buf_size - start_preamble)
                    )
                    t1 = t1_sample_pos / const.sampling_rate
                    break
                else:
                    print("header is broken")

    print(f"プリアンブル検出  K={k}")
    print(f"payload length={payload_length}")

    # ペイロード受信
    payload_symbols = []
    for _ in range(payload_length):
        data = read_samples(N)

        # 💡 修正ポイント: 同期ズレによる数サンプルのファイル末尾での欠落を許容する
        if len(data) < N:
            # 半シンボル未満しか取れなかった場合は本当のファイル切れなのでエラー
            if len(data) < HALF_N:
                raise EOFError("symbol read requires more samples")
            # 数サンプル足りないだけなら、残りをゼロで埋めて(ゼロパディング)解析を強行する
            data = np.pad(data, (0, N - len(data)))

        payload_symbols.append(detect_symbol(data))

    t2_sample_pos = get_pos()
    t2 = t2_sample_pos / const.sampling_rate

    text = decode_symbols_to_text(payload_symbols)
    return text, t1, t2


def file_reader_factory(wav_data: np.ndarray):
    """音声配列から指定サンプルずつ切り出すファクトリ関数です（位置追跡機能付き）。"""
    cursor = 0

    def read_samples(count: int) -> np.ndarray:
        nonlocal cursor
        chunk = wav_data[cursor : cursor + count]
        cursor += len(chunk)
        return chunk

    def get_pos() -> int:
        return cursor

    return read_samples, get_pos
