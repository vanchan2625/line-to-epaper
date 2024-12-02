import os
import json
import logging
import firebase_admin
from firebase_admin import credentials, storage, db
from flask import Flask, request, abort, jsonify
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
from PIL import Image, ImageDraw, ImageFont
from datetime import timedelta
import time

# ロギングの設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# LINE Botの設定
LINE_CHANNEL_ACCESS_TOKEN = 'zXQfQu1F2R+jUdANkbDFNEQnoNzqkWK8aTCyi5AZnWR3Ka7o+yaWZkB0sA5/DTl3QxrUjQPMHdV2qMu5tMw2whG7cKPgjgs4GIv0On7wSD3wcLZxabr6pEfudTI9J/+Q0BivyZAaX2dZJ8VlI5hlKgdB04t89/1O/w1cDnyilFU='
LINE_CHANNEL_SECRET = 'e0e18f978a3f5f7ccee72bbfb06a4d85'
line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)

# Secret Managerからサービスアカウントキーを取得
SERVICE_ACCOUNT_KEY = os.getenv('SERVICE_ACCOUNT_KEY')
service_account_info = json.loads(SERVICE_ACCOUNT_KEY)

# Firebaseの設定（Secret Managerを使用）
cred = credentials.Certificate(service_account_info)
firebase_admin.initialize_app(cred, {
    'storageBucket': 'line-to-epaper-26be0.firebasestorage.app',
    'databaseURL': 'https://line-to-epaper-26be0-default-rtdb.firebaseio.com/'
})
bucket = storage.bucket()

# フォントのパス
FONT_PATH = 'HGRGY.TTC'

@app.route("/callback", methods=['POST'])
def callback():
    # リクエストヘッダーから署名検証のための値を取得
    signature = request.headers.get('X-Line-Signature')

    # リクエストボディを取得
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)

    # 署名を検証し、問題なければハンドラーに渡す
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)

    return 'OK'

# メッセージ受信時の処理
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    try:
        text = event.message.text.strip()
        if len(text) == 2:
            # 画像を生成してFirebaseにアップロード
            image_path = generate_image(text)
            image_url = upload_image_to_firebase(image_path)
            # Firebase Realtime Databaseを更新
            update_database(image_url)
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text='画像を更新しました')
            )
        else:
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text='漢字二文字を送信してください')
            )
    except Exception as e:
        logger.error(f"Error handling message: {e}", exc_info=True)
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text='エラーが発生しました。もう一度お試しください。')
        )

def generate_image(text):
    # 画像サイズを設定
    img = Image.new('1', (800, 480), color=1)  # モノクロ、背景白
    draw = ImageDraw.Draw(img)
    # フォントを読み込む
    font = ImageFont.truetype(FONT_PATH, 400)
    # テキストのサイズを取得
    w, h = draw.textsize(text, font=font)
    # テキストを中央に配置
    draw.text(((800 - w) / 2, (480 - h) / 2), text, font=font, fill=0)
    # 画像を保存
    image_path = 'output.bmp'
    img.save(image_path)
    return image_path

def upload_image_to_firebase(image_path):
    blob = bucket.blob('images/output.bmp')
    blob.upload_from_filename(image_path, content_type='image/bmp')
    # キャッシュを無効にするために、メタデータを設定
    blob.cache_control = 'no-cache'
    blob.patch()
    # 画像のダウンロードURLを取得
    image_url = blob.generate_signed_url(expiration=timedelta(hours=1))
    return image_url

def update_database(image_url):
    # Firebase Realtime Databaseに画像のURLとタイムスタンプを保存
    ref = db.reference('latest_image')
    ref.set({
        'image_url': image_url,
        'timestamp': int(time.time())
    })

@app.errorhandler(Exception)
def handle_exception(e):
    logger.error(f"Unhandled exception: {e}", exc_info=True)
    return jsonify({"message": "内部サーバーエラーが発生しました。"}), 500

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))