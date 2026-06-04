# MFSK

このリポジトリは MFSK（Multiple Frequency-Shift Keying）の送信（player）と受信（receiver）の実験コードを含みます。

構成:

- player/: 送信側コード（`D2A_MFSK.py` など）
- receiver/: 受信側コード（`A2D_MFSK.py`, `main.py` など）
- const.py: 共通定数

使い方（簡易）:

1. 依存関係をインストールします（例: 仮想環境を作成してから）:

```bash
python -m venv .venv
.venv\Scripts\activate  # Windows
pip install -r requirements.txt  # または pyproject.toml の依存を手動でインストール
```

2. 送信（例）:

```bash
python player/D2A_MFSK.py
```

3. 受信（例）:

```bash
python receiver/main.py
```

注意:
- `receiver/main.py` は実験用スクリプトで、実行前に入力ファイル名やパラメータの確認が必要です。
- 追加の整理（パッケージ化、テストの追加など）を希望する場合は教えてください。
