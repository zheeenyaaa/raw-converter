import os
import tempfile
import zipfile
import json
import time
import telebot
import requests
import yadisk
import rawpy
from PIL import Image
from urllib.parse import unquote

with open("data.json", "r", encoding="utf-8-sig") as f:
    data = json.load(f)

# CLIENT_ID = data["CLIENT_ID"]
# CLIENT_SECRET = data["CLIENT_SECRET"]
# AUTHORIZATION_URL = data["AUTHORIZATION_URL"]
TELEGRAM_BOT_TOKEN = data["TELEGRAM_BOT_TOKEN"]
# DEV_YANDEX_TOKEN = data["DEV_YANDEX_TOKEN"]
# DEV_ID = data["DEV_ID"]
# REDIRECT_URL = data["REDIRECT_URL"]

# YANDEX_TOKENS = {
#     int(DEV_ID): DEV_YANDEX_TOKEN
# }

# user_auth_status = {}
yadisk_client = yadisk.Client()
work_dir = os.path.dirname(os.path.abspath(__file__))
bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)
# auth_url = f"{AUTHORIZATION_URL}?response_type=code&client_id={CLIENT_ID}&redirect_uri={REDIRECT_URL}"


@bot.message_handler(commands=['start'])
def send_welcome(message):
    # if message.chat.id in YANDEX_TOKENS:
    bot.reply_to(message, "Привет! Отправь мне публичную ссылку на папку Яндекс.Диска с CR2 файлами.")
    # else:
        # bot.send_message(message.chat.id, f"Привет! Тебе нужно авторизировать через яндекс. Я отправлю тебе ссылку, по которой тебе нужно будет перейти. После выполнения авторизация отправь мне, пожалуйста, код, который высветится на главной странице \nВот ссылка: {auth_url}")
        # user_auth_status[message.chat.id] = True


@bot.message_handler(func=lambda message: True)
def process_yandex_disk_link(message):
    # if message.chat.id not in YANDEX_TOKENS:
    #     if user_auth_status.get(message.chat.id) is None:
    #         bot.send_message(message.chat.id, f"Привет! Тебе нужно авторизировать через яндекс. Я отправлю тебе ссылку, по которой тебе нужно будет перейти. После выполнения авторизация отправь мне, пожалуйста, код, который высветится на главной странице \nВот ссылка: {auth_url}")
    #         user_auth_status[message.chat.id] = True
    #     else:
    #         try:
    #             auth_code = message.text.strip()
    #             get_token_data = {
    #                 "grant_type": "authorization_code",
    #                 "code": f"{auth_code}",
    #                 "client_id": f"{CLIENT_ID}", 
    #                 "client_secret": f"{CLIENT_SECRET}"
    #             }   
    #             r = requests.post("https://oauth.yandex.ru/token", data=get_token_data)

    #             json_data = r.json()
    #             token = json_data.get("access_token")
    #             YANDEX_TOKENS[message.chat.id] = token
    #             print("Получен токен - ", token)
    #             bot.reply_to(message, "Вы успешно авторизованы! Ваш токен сохранен.")
    #         except Exception as e:
    #             print(f"Error: {e}")
    #             bot.reply_to(message, "Не удалось получить токен доступа, проверьте код и попробуйте снова.")
    #     return
    # yadisk_client = yadisk.Client(token = YANDEX_TOKENS[message.chat.id])
    
    try:
        # Извлекаем публичный ресурс из ссылки
        public_url = message.text.strip()
        public_meta = yadisk_client.get_public_meta(public_url)
        bot.reply_to(message, "Начинаю обработку файлов. Это может занять некоторое время.")
        
        with tempfile.TemporaryDirectory(dir=work_dir) as temp_dir:
            input_dir = os.path.join(temp_dir, 'input')
            output_dir = os.path.join(temp_dir, 'output')
            os.makedirs(input_dir)
            os.makedirs(output_dir)

            input_archive = os.path.join(input_dir, f"{public_meta.name}.zip")

            # Скачиваем файлы с публичной папки Яндекс.Диска
            yadisk_client.download_public(public_url, input_archive)
            
            # for item in yadisk_client.listdir(public_resource.path + public_resource.name):
            #     if item['type'] == 'file' and item['name'].lower().endswith('.cr2'):
            #         yadisk_client.download(item["path"], os.path.join(input_dir, item["name"]))
    
            # Конвертируем CR2 в JPEG

            with zipfile.ZipFile(input_archive, "r") as zipf:
                zipf.extractall(input_dir)
    
            for filename in os.listdir(os.path.join(input_dir, f"{public_meta.name}")):
                if filename.lower().endswith('.cr2'):
                    cr2_path = os.path.join(input_dir, f"{public_meta.name}", filename)
                    jpeg_path = os.path.join(output_dir, f"{os.path.splitext(filename)[0]}.jpg")
                    with rawpy.imread(cr2_path) as raw:
                        rgb = raw.postprocess()
                        Image.fromarray(rgb).save(jpeg_path, 'JPEG', quality=85)  # Adjust quality as needed
                        print(f"Окончил конвертацию в {jpeg_path}")
            
            # Создаем архив с обработанными файлами
            archive_path = os.path.join(temp_dir, 'converted_images.zip')
            with zipfile.ZipFile(archive_path, 'w') as zipf:
                for root, _, files in os.walk(output_dir):
                    for file in files:
                        zipf.write(os.path.join(root, file), file)
            
            # Отправляем архив пользователю
            with open(archive_path, 'rb') as archive:
                bot.send_document(message.chat.id, archive, caption="Вот ваши конвертированные изображения.", timeout=120)
        
    except Exception as e:
        bot.reply_to(message, f"Произошла ошибка: {str(e)}")

bot.polling()
