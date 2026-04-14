# MFSK(マルチFSK)

## 仕様と変数の解説

| 変数名 | 内容 | 初期設定 |
| --- | --- | --- |
| channels | チャンネル数 | 16チャンネル |
| bits_per_signal | 1シグナルあたりのビット数 | 4[bits] |
| bps | 1秒あたりの送信ビット数	| 200[bits] |
| sampling_rate | サンプリングレート | 44100[Hz] |
| signal_ms | 1シグナルあたりの時間[ms] | 20[ms] |
| boud_rate |ボーレート（1000ミリ秒あたりに送るシグナルの数） | 50[Hz] |
| signal_freq_start | 周波数計算の基準値 | 15000[Hz] |
| signal_freq_width | 1チャンネルあたりの周波数の幅 | 125[Hz] |
| signal_freqs |  | 空のリスト |

## 関数の解説

| 関数名 | 役割 | 引数 | 出力 |
| --- | --- | --- | --- |
| str2bits(s) | 文字列をUTF-8のバイト列に変換し、シフトしてAND演算を行うことによって各バイトを8ビットのリストに展開する | s: str | list[int] (0/1のビット列) |
| pad_bits(bits) | ビット列の長さを bits_per_signal の倍数にそろえるため、パディング(必要な数だけ0を追加)を行う | bits: list[int] | list[int] (パディング後のビット列) |
| bits2index(bits) | bits_per_signal(4ビット) ごとにビットをまとめ、0~15を表す周波数チャンネルのインデックスに変換する | bits: list[int] | list[int] (チャンネルのインデックス列) |
| gen_wave(index) | 指定インデックスに対応する周波数のサイン波を1シグナル分生成する | index: int | np.ndarray (波形データ) |
| play(data) | 生成した波形をsounddeviceライブラリの機能で再生し、再生完了まで待機する | data: np.ndarray | なし |
| save_wave(data, filename) | 波形を32ビットのPCMに変換し、wavファイルとして保存する | data: np.ndarray , filename: str | なし |



