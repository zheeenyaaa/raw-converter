import os
import tempfile
import zipfile
import json
import time
import telebot
import yadisk
import rawpy
from PIL import Image
from urllib.parse import unquote

with open("data.json", "r", encoding="utf-8-sig") as f:
    data = json.load(f)

TELEGRAM_BOT_TOKEN = data["TELEGRAM_BOT_TOKEN"]

yadisk_client = yadisk.Client()
work_dir = os.path.dirname(os.path.abspath(__file__))
bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)


@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "Привет! Отправь мне публичную ссылку на папку Яндекс.Диска с CR2 файлами.")
   
@bot.message_handler(func=lambda message: True)
def process_yandex_disk_link(message):
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
