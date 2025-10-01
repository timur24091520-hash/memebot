import telebot
from PIL import Image, ImageDraw, ImageFont
import os
import textwrap

# Токен бота (получи у @BotFather)
BOT_TOKEN = 'YOUR_BOT_TOKEN_HERE'

# Создаем экземпляр бота
bot = telebot.TeleBot(BOT_TOKEN)

# Папка для временных файлов
TEMP_DIR = 'temp'
if not os.path.exists(TEMP_DIR):
    os.makedirs(TEMP_DIR)

def create_meme(image_path, top_text="", bottom_text=""):
    """Создает мем из изображения с текстом"""
    
    # Открываем изображение
    image = Image.open(image_path)
    draw = ImageDraw.Draw(image)
    
    # Получаем размеры изображения
    width, height = image.size
    
    # Выбираем шрифт (размер зависит от размера изображения)
    font_size = min(width, height) // 10
    try:
        # Пробуем использовать стандартный шрифт
        font = ImageFont.truetype("arial.ttf", font_size)
    except:
        # Если шрифт не найден, используем дефолтный
        font = ImageFont.load_default()
    
    # Функция для добавления текста
    def add_text(text, position):
        if not text:
            return
            
        # Разбиваем текст на строки
        avg_char_width = font_size * 0.6
        max_chars = int(width / avg_char_width)
        wrapped_text = textwrap.fill(text, width=max_chars)
        
        # Получаем размеры текста
        bbox = draw.textbbox((0, 0), wrapped_text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        
        # Позиционируем текст
        if position == "top":
            x = (width - text_width) / 2
            y = 10
        else:  # bottom
            x = (width - text_width) / 2
            y = height - text_height - 10
        
        # Добавляем обводку для лучшей читаемости
        outline_range = 2
        for dx in range(-outline_range, outline_range + 1):
            for dy in range(-outline_range, outline_range + 1):
                if dx != 0 or dy != 0:
                    draw.text((x + dx, y + dy), wrapped_text, font=font, fill="black")
        
        # Основной текст
        draw.text((x, y), wrapped_text, font=font, fill="white")
    
    # Добавляем верхний и нижний текст
    add_text(top_text, "top")
    add_text(bottom_text, "bottom")
    
    # Сохраняем результат
    output_path = os.path.join(TEMP_DIR, "meme_result.jpg")
    image.save(output_path, "JPEG")
    
    return output_path

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    """Обработчик команд start и help"""
    welcome_text = """
🤖 Бот для создания мемов!

📸 Как использовать:
1. Отправь картинку
2. В подписи к картинке напиши текст
3. Бот создаст мем!

💡 Примеры текста:
- Одна строка: "Текст мема"
- Две строки: "Верхний текст\\nНижний текст"
- Разделитель \\n для верхнего и нижнего текста

🎨 Текст автоматически размещается сверху и снизу изображения.
    """
    bot.reply_to(message, welcome_text)

@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    """Обработчик получения фото"""
    
    try:
        # Отправляем сообщение о обработке
        processing_msg = bot.reply_to(message, "🔄 Обрабатываю изображение...")
        
        # Получаем информацию о фото (берем самое большоее качество)
        file_info = bot.get_file(message.photo[-1].file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        
        # Сохраняем временный файл
        input_path = os.path.join(TEMP_DIR, f"input_{message.message_id}.jpg")
        with open(input_path, 'wb') as new_file:
            new_file.write(downloaded_file)
        
        # Получаем текст из подписи
        caption = message.caption or ""
        
        # Разделяем текст на верхний и нижний
        if "\\n" in caption:
            parts = caption.split("\\n", 1)
            top_text = parts[0].strip()
            bottom_text = parts[1].strip() if len(parts) > 1 else ""
        else:
            top_text = caption
            bottom_text = ""
        
        # Создаем мем
        output_path = create_meme(input_path, top_text, bottom_text)
        
        # Отправляем результат
        with open(output_path, 'rb') as photo:
            bot.send_photo(message.chat.id, photo, caption="🎉 Ваш мем готов!")
        
        # Удаляем сообщение о обработке
        bot.delete_message(message.chat.id, processing_msg.message_id)
        
        # Удаляем временные файлы
        os.remove(input_path)
        os.remove(output_path)
        
    except Exception as e:
        bot.reply_to(message, f"❌ Произошла ошибка: {str(e)}")
        
        # Удаляем временные файлы в случае ошибки
        try:
            if 'input_path' in locals() and os.path.exists(input_path):
                os.remove(input_path)
            if 'output_path' in locals() and os.path.exists(output_path):
                os.remove(output_path)
        except:
            pass

@bot.message_handler(func=lambda message: True)
def handle_text(message):
    """Обработчик текстовых сообщений"""
    if message.text and not message.text.startswith('/'):
        bot.reply_to(message, "📸 Отправь мне картинку с текстом в подписи, и я сделаю из нее мем!")

if __name__ == "__main__":
    print("Бот запущен...")
    bot.infinity_polling()
