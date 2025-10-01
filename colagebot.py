import os
import logging
from PIL import Image
import telebot
from telebot import types

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Токен бота (замени на свой)
BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"

# Создание экземпляра бота
bot = telebot.TeleBot(BOT_TOKEN)

# Папка для временных файлов
TEMP_FOLDER = "temp_images"
if not os.path.exists(TEMP_FOLDER):
    os.makedirs(TEMP_FOLDER)

# Словарь для хранения данных пользователей
user_data = {}

class UserData:
    def __init__(self):
        self.photos = []
        self.waiting_for_photos = False
        self.expected_count = 0

def create_collage(photos_paths, layout):
    """Создание коллажа из фотографий"""
    try:
        # Открываем все изображения
        images = [Image.open(path) for path in photos_paths]
        
        # Приводим все изображения к одному размеру (квадрат)
        size = 400
        images = [img.resize((size, size)) for img in images]
        
        # Создаем холст в зависимости от layout
        if layout == 3:
            # 3 фото: одна сверху, две снизу
            collage = Image.new('RGB', (size * 2, size * 2))
            collage.paste(images[0], (0, 0, size * 2, size))
            collage.paste(images[1], (0, size, size, size * 2))
            collage.paste(images[2], (size, size, size * 2, size * 2))
        elif layout == 4:
            # 4 фото: 2x2
            collage = Image.new('RGB', (size * 2, size * 2))
            collage.paste(images[0], (0, 0, size, size))
            collage.paste(images[1], (size, 0, size * 2, size))
            collage.paste(images[2], (0, size, size, size * 2))
            collage.paste(images[3], (size, size, size * 2, size * 2))
        elif layout == 5:
            # 5 фото: 3 сверху, 2 снизу
            collage = Image.new('RGB', (size * 3, size * 2))
            for i in range(3):
                collage.paste(images[i], (i * size, 0, (i + 1) * size, size))
            for i in range(3, 5):
                collage.paste(images[i], ((i - 3) * size, size, (i - 2) * size, size * 2))
        elif layout == 6:
            # 6 фото: 3x2
            collage = Image.new('RGB', (size * 3, size * 2))
            for i in range(6):
                x = (i % 3) * size
                y = (i // 3) * size
                collage.paste(images[i], (x, y, x + size, y + size))
        
        # Сохраняем коллаж
        output_path = os.path.join(TEMP_FOLDER, f"collage_{layout}.jpg")
        collage.save(output_path, "JPEG", quality=95)
        
        # Закрываем все изображения
        for img in images:
            img.close()
            
        return output_path
        
    except Exception as e:
        logger.error(f"Error creating collage: {e}")
        return None

@bot.message_handler(commands=['start'])
def send_welcome(message):
    """Обработчик команды /start"""
    user_id = message.from_user.id
    user_data[user_id] = UserData()
    
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn3 = types.KeyboardButton("3 фото")
    btn4 = types.KeyboardButton("4 фото")
    btn5 = types.KeyboardButton("5 фото")
    btn6 = types.KeyboardButton("6 фото")
    markup.add(btn3, btn4, btn5, btn6)
    
    bot.send_message(
        message.chat.id,
        "👋 Привет! Я бот для создания коллажей!\n\n"
        "Выбери количество фотографий для коллажа:",
        reply_markup=markup
    )

@bot.message_handler(func=lambda message: message.text in ["3 фото", "4 фото", "5 фото", "6 фото"])
def handle_photo_count(message):
    """Обработчик выбора количества фото"""
    user_id = message.from_user.id
    
    if user_id not in user_data:
        user_data[user_id] = UserData()
    
    # Определяем количество фото
    count_map = {"3 фото": 3, "4 фото": 4, "5 фото": 5, "6 фото": 6}
    expected_count = count_map[message.text]
    
    user_data[user_id].expected_count = expected_count
    user_data[user_id].waiting_for_photos = True
    user_data[user_id].photos = []
    
    bot.send_message(
        message.chat.id,
        f"📸 Отправь мне {expected_count} фотографий.\n\n"
        f"Можно отправить все сразу или по одной.",
        reply_markup=types.ReplyKeyboardRemove()
    )

@bot.message_handler(content_types=['photo'])
def handle_photos(message):
    """Обработчик получения фотографий"""
    user_id = message.from_user.id
    
    if user_id not in user_data or not user_data[user_id].waiting_for_photos:
        bot.send_message(message.chat.id, "Сначала выбери количество фото для коллажа!")
        return
    
    user_data_obj = user_data[user_id]
    
    try:
        # Получаем файл фотографии
        file_info = bot.get_file(message.photo[-1].file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        
        # Сохраняем фотографию
        file_path = os.path.join(TEMP_FOLDER, f"{user_id}_{len(user_data_obj.photos)}.jpg")
        with open(file_path, 'wb') as new_file:
            new_file.write(downloaded_file)
        
        user_data_obj.photos.append(file_path)
        
        # Показываем прогресс
        remaining = user_data_obj.expected_count - len(user_data_obj.photos)
        
        if remaining > 0:
            bot.send_message(
                message.chat.id,
                f"✅ Получено {len(user_data_obj.photos)} из {user_data_obj.expected_count} фото\n"
                f"Осталось: {remaining}"
            )
        else:
            # Все фото получены, создаем коллаж
            bot.send_message(message.chat.id, "🔄 Создаю коллаж...")
            
            collage_path = create_collage(
                user_data_obj.photos, 
                user_data_obj.expected_count
            )
            
            if collage_path:
                # Отправляем коллаж
                with open(collage_path, 'rb') as photo:
                    bot.send_photo(
                        message.chat.id, 
                        photo,
                        caption="🎉 Ваш коллаж готов!"
                    )
                
                # Очищаем временные файлы
                for photo_path in user_data_obj.photos:
                    if os.path.exists(photo_path):
                        os.remove(photo_path)
                if os.path.exists(collage_path):
                    os.remove(collage_path)
                
                # Сбрасываем состояние пользователя
                user_data_obj.photos = []
                user_data_obj.waiting_for_photos = False
                
                # Предлагаем создать новый коллаж
                markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
                btn3 = types.KeyboardButton("3 фото")
                btn4 = types.KeyboardButton("4 фото")
                btn5 = types.KeyboardButton("5 фото")
                btn6 = types.KeyboardButton("6 фото")
                markup.add(btn3, btn4, btn5, btn6)
                
                bot.send_message(
                    message.chat.id,
                    "Хочешь создать ещё один коллаж? Выбери количество фото:",
                    reply_markup=markup
                )
            else:
                bot.send_message(message.chat.id, "❌ Ошибка при создании коллажа")
                # Очищаем временные файлы
                for photo_path in user_data_obj.photos:
                    if os.path.exists(photo_path):
                        os.remove(photo_path)
                user_data_obj.photos = []
                user_data_obj.waiting_for_photos = False
                
    except Exception as e:
        logger.error(f"Error handling photo: {e}")
        bot.send_message(message.chat.id, "❌ Произошла ошибка при обработке фото")

@bot.message_handler(commands=['help'])
def send_help(message):
    """Обработчик команды /help"""
    help_text = """
🤖 Бот для создания коллажей

Как пользоваться:
1. Нажми на кнопку с количеством фото (3, 4, 5 или 6)
2. Отправь боту указанное количество фотографий
3. Получи готовый коллаж!

Команды:
/start - начать работу
/help - показать эту справку

Бот автоматически удаляет все фото после создания коллажа.
    """
    bot.send_message(message.chat.id, help_text)

@bot.message_handler(func=lambda message: True)
def handle_other_messages(message):
    """Обработчик всех остальных сообщений"""
    bot.send_message(
        message.chat.id,
        "Я понимаю только команды и фотографии 😊\n"
        "Используй /start для начала работы или /help для справки."
    )

if __name__ == "__main__":
    logger.info("Бот запущен...")
    try:
        bot.polling(none_stop=True)
    except Exception as e:
        logger.error(f"Ошибка при работе бота: {e}")
