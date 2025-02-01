# Telegram-бот для поиска кафе через Яндекс.Карты (Geosearch API)
# Требуется API-ключ от Яндекс.Облака

# === Секция 1: Импорты ===
import os
import logging
import signal
import requests
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    Updater,
    CommandHandler,
    MessageHandler,
    Filters,
    ConversationHandler,
    CallbackContext,
)

# === Секция 2: Конфигурация ===
TELEGRAM_TOKEN = os.getenv("8169183380:AAEp2I0Bb_Ljnzd4n8gMaDbVPLuFCi6BFDk")
YANDEX_API_KEY = os.getenv("AQVNznkv2cu-WerDTScb2YWsVBcomNIjvkzb9Tmy")
PORT = int(os.environ.get("PORT", 10000))  # Используем переменную окружения
WEBHOOK_URL = os.getenv("https://nearbyninjabot.onrender.com")

# Параметры поиска
MAX_RADIUS = 5000
MIN_RADIUS = 100
MAX_RESULTS = 3

# Состояния диалога
RADIUS, LOCATION = range(2)

# === Секция 3: Настройка логов ===
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(name)

# === Секция 4: Основной класс бота ===
class YandexCafeBot:
    def init(self):
        # Инициализация компонентов бота
        self.updater = Updater(TELEGRAM_TOKEN, use_context=True)
        self.session = requests.Session()

    # === Секция 5: Обработчики команд ===
    def start(self, update: Update, context: CallbackContext) -> None:
        """Обработка команды /start"""
        user = update.effective_user
        update.message.reply_text(
            f"Привет, {user.first_name}! 👋\n"
            "Я помогу найти ближайшие кафе через Яндекс.Карты!\n"
            "Используй /findcafe чтобы начать поиск",
            reply_markup=ReplyKeyboardRemove()
        )

    def find_cafe(self, update: Update, context: CallbackContext) -> int:
        """Начало процесса поиска"""
        update.message.reply_text(
            f"📏 Введите радиус поиска в метрах ({MIN_RADIUS}-{MAX_RADIUS}):",
            reply_markup=ReplyKeyboardRemove()
        )
        return RADIUS

    # === Секция 6: Обработка состояний ===
    def receive_radius(self, update: Update, context: CallbackContext) -> int:
        """Получение радиуса поиска"""
        try:
            radius = int(update.message.text)
            if not (MIN_RADIUS <= radius <= MAX_RADIUS):
                raise ValueError
                
            context.user_data["radius"] = radius
            return self._request_location(update)
            
        except ValueError:
            update.message.reply_text(
                f"❌ Некорректный радиус! Введите число от {MIN_RADIUS} до {MAX_RADIUS}:"
            )
            return RADIUS

    def _request_location(self, update: Update) -> int:
        """Запрос геолокации"""
        location_keyboard = ReplyKeyboardMarkup(
            [[{"text": "📍 Отправить геолокацию", "request_location": True}]],
            resize_keyboard=True,
            one_time_keyboard=True
        )
        update.message.reply_text(
            "✅ Радиус сохранен! Теперь отправьте ваше местоположение:",
            reply_markup=location_keyboard
        )
        return LOCATION

    # === Секция 7: Работа с API Яндекс ===
    def receive_location(self, update: Update, context: CallbackContext) -> int:
        """Обработка геолокации"""
        try:
            location = update.message.location
            lat, lon = location.latitude, location.longitude
            radius = context.user_data.get("radius", 1000)

            # Поиск через Яндекс API
            cafes = self._get_yandex_cafes(lon, lat, radius)
            
            if not cafes:
                raise ValueError("Кафе не найдено")
                
            return self._send_results(update, cafes, radius)
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Ошибка соединения: {str(e)}")
            update.message.reply_text("⚠️ Проблемы с соединением. Попробуйте позже.")
        except Exception as e:
            logger.error(f"Ошибка: {str(e)}")
            update.message.reply_text("😞 В этом районе кафе не найдено.")
            
        return ConversationHandler.END
def _get_yandex_cafes(self, lon: float, lat: float, radius: int) -> list:
        """Запрос к API Яндекс.Карт"""
        url = "https://search-maps.yandex.ru/v1/"
        params = {
            "apikey": YANDEX_API_KEY,
            "text": "кафе",
            "lang": "ru_RU",
            "ll": f"{lon},{lat}",
            "spn": f"{(radius / 1000) * 0.009}",  # Конвертация метров в градусы
            "rspn": 1,
            "results": MAX_RESULTS,
            "type": "biz"
        }
        
        response = self.session.get(url, params=params, timeout=10).json()
        
        if "error" in response:
            raise Exception(f"Ошибка API: {response.get('message', 'Неизвестная ошибка')}")
            
        return response.get("features", [])[:MAX_RESULTS]

# === Секция 8: Форматирование результатов ===
def _send_results(self, update: Update, cafes: list, radius: int) -> int:
        """Форматирование результатов"""
        results = []
    
for cafe in cafes:
        props = cafe.get("properties", {})
        meta = props.get("CompanyMetaData", {})
        name = meta.get("name", "Кафе без названия")
        address = meta.get("address", "Адрес не указан")
        rating = props.get("rating", "нет оценок")
        lon, lat = cafe["geometry"]["coordinates"]
        url = f"https://yandex.ru/maps/?ll={lon}%2C{lat}&z=17&pt={lon},{lat}"
        
        results.append(
            f"☕️ <b>{name}</b>\n"
            f"⭐ Рейтинг: {rating}\n"
            f"📌 Адрес: {address}\n"
            f"🌐 Ссылка: {url}"
        )

update.message.reply_html(
        f"🏆 Топ {len(results)} ближайших кафе в радиусе {radius} м:\n\n" + "\n\n".join(results),
        reply_markup=ReplyKeyboardRemove()
    )
    return ConversationHandler.END

    # === Секция 9: Управление жизненным циклом ===
def cancel(self, update: Update, context: CallbackContext) -> int:
        """Отмена поиска"""
        update.message.reply_text(
            "❌ Поиск отменен",
            reply_markup=ReplyKeyboardRemove()
        )
        return ConversationHandler.END

def graceful_shutdown(self, signum, frame):
        """Корректное завершение работы"""
        logger.info("🛑 Получен сигнал завершения...")
        self.updater.stop()
        self.session.close()
        logger.info("✅ Ресурсы освобождены. Бот остановлен.")
        exit(0)

def run(self):
        """Основной метод запуска"""
        dispatcher = self.updater.dispatcher

        # Регистрация обработчиков
        conv_handler = ConversationHandler(
            entry_points=[CommandHandler('findcafe', self.find_cafe)],
            states={
                RADIUS: [MessageHandler(Filters.text & ~Filters.command, self.receive_radius)],
                LOCATION: [MessageHandler(Filters.location, self.receive_location)],
            },
            fallbacks=[CommandHandler('cancel', self.cancel)],
        )

        dispatcher.add_handler(CommandHandler("start", self.start))
        dispatcher.add_handler(conv_handler)

        # Обработка сигналов
        signal.signal(signal.SIGINT, self.graceful_shutdown)
        signal.signal(signal.SIGTERM, self.graceful_shutdown)

        # Настройка вебхуков
        self.updater.start_webhook(
            listen="0.0.0.0",
            port=PORT,
            url_path=TELEGRAM_TOKEN,
            webhook_url=f"{https://nearbyninjabot.onrender.com}/{8169183380:AAEp2I0Bb_Ljnzd4n8gMaDbVPLuFCi6BFDk}"
        )

        logger.info("🤖 Бот успешно запущен!")
        self.updater.idle()

# === Секция 10: Запуск приложения ===
if name == 'main':
    bot = YandexCafeBot()
    bot.run()
