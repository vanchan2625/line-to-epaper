# ベースイメージとしてPython 3.9-slimを使用
FROM python:3.9-slim

# 作業ディレクトリを設定
WORKDIR /app

# 必要なパッケージをインストール
RUN apt-get update && apt-get install -y \
    libgl1-mesa-dev \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# requirements.txtをコピーしてライブラリをインストール
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# フォントファイルとサービスアカウントキーをコピー
COPY HGRGY.TTC HGRGY.TTC
COPY serviceAccountKey.json serviceAccountKey.json

# アプリケーションのコードをコピー
COPY app.py .

# ポート8080を開放
EXPOSE 8080

# アプリケーションをGunicornで起動
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "--workers", "1", "--threads", "8", "app:app"]