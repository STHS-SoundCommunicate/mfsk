channels = 16
bits_per_signal = 4
bps = 200  # 200bpsを目標
sampling_rate = 44100  # 44100hzで通信
signal_ms = 1 / bps * bits_per_signal * 1000  # シグナル1つの長さ (ms)
baud_rate = 1000 / signal_ms  # ボーレート。分解能は12.5hz
signal_freq_start = 10000
signal_freq_width = 125
preamble = [0,4,8,12] #プリアンブルをインデックス形式で表記

signal_freqs = [signal_freq_start + i * signal_freq_width for i in range(channels)]