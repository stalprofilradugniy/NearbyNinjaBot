# Telegram-бот для поиска кафе через Яндекс.Карты (Geosearch API)
# Требуется API-ключ от Яндекс.Облака

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

# Конфигурация
YANDEX_API_KEY = os.getenv("AQVNznkv2cu-WerDTScb2YWsVBcomNIjvkzb9Tmy")  # Ключ из Яндекс.Облака
TELEGRAM_TOKEN = os.getenv("8169183380:AAEp2I0Bb_Ljnzd4n8gMaDbVPLuFCi6BFDk")
PORT = int(os.environ.get("PORT", 10000))
WEBHOOK_URL = os.getenv("https://nearbyninjabot.onrender.com")

# Параметры поиска
MAX_RADIUS = 5000    # Максимальный радиус (метры)
MIN_RADIUS = 100     # Минимальный радиус
MAX_RESULTS = 3      # Количество результатов

# Состояния диалога
RADIUS, LOCATION = range(2)

# Настройка логов
logging.basicConfig(
    format="%(asctime)s - %(__name__)s - %(levelname)s - %(message)s",
    level=logging.INFO,
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

class YandexCafeBot:
    def init(self):
        # Инициализация компонентов бота
        self.updater = Updater(TELEGRAM_TOKEN, use_context=True)
        self.session = requests.Session()

    def run(self):
        # Получение диспетчера
        dispatcher = self.updater.dispatcher

    # ================== Обработчики команд ==================
    
    def start(self, update: Update, context: CallbackContext) -> None:
        user = update.effective_user
        update.message.reply_text(
            f"Привет, {user.first_name}! 👋\n"
            "Я помогу найти ближайшие кафе через Яндекс.Карты!\n"
            "Используй /findcafe чтобы начать поиск",
            reply_markup=ReplyKeyboardRemove()
        )

    def find_cafe(self, update: Update, context: CallbackContext) -> int:
        update.message.reply_text(
            f"📏 Введите радиус поиска в метрах ({MIN_RADIUS}-{MAX_RADIUS}):",
            reply_markup=ReplyKeyboardRemove()
        )
        return RADIUS

    def receive_radius(self, update: Update, context: CallbackContext) -> int:
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
        location_keyboard = ReplyKeyboardMarkup(
            [[{"text": "📍 Отправить геолокацию", "request_location": True}]],
            resize_keyboard=True,
            one_time_keyboard=True
        )
        update.message.reply_text(
            "✅ Радиус сохранен! Отправьте ваше местоположение:",
            reply_markup=location_keyboard
        )
        return LOCATION

    def receive_location(self, update: Update, context: CallbackContext) -> int:
        try:
            location = update.message.location
            lat, lon = location.latitude, location.longitude
            radius = context.user_data.get("radius", 1000)

            # Поиск через Яндекс.Geosearch API
            cafes = self._get_yandex_cafes(lon, lat, radius)
            
            if not cafes:
                raise ValueError("Кафе не найдено")
                
            return self._send_results(update, cafes, radius)
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Ошибка соединения: {str(e)}")
            update.message.reply_text("⚠️ Проблемы с соединением. Попробуйте позже.")
        except Exception as e:
            logger.error(f"Ошибка: {str(e)}")
            update.message.reply_text("😞 Не удалось найти кафе в этом районе.")
            
        return ConversationHandler.END
# ================== Работа с Яндекс.API ==================
    
    def _get_yandex_cafes(self, lon: float, lat: float, radius: int) -> list:
        """Поиск кафе через Яндекс.Geosearch API"""
        url = "https://search-maps.yandex.ru/v1/"
        params = {
            "apikey": YANDEX_API_KEY,
            "text": "кафе",
            "lang": "ru_RU",
            "ll": f"{lon},{lat}",
            "spn": f"{self._degrees_for_radius(radius)}",
            "rspn": 1,
            "results": MAX_RESULTS,
            "type": "biz"
        }
        
        response = self.session.get(url, params=params, timeout=10).json()
        
        if "error" in response:
            raise Exception(f"Yandex API Error: {response.get('message', 'Unknown')}")
            
        return response.get("features", [])[:MAX_RESULTS]

    def _degrees_for_radius(self, radius_meters: int) -> float:
        """Конвертация метров в градусы (примерно)"""
        return (radius_meters / 1000) * 0.009  # ~1 км = 0.009 градуса

    # ================== Форматирование результатов ==================
    
    def _send_results(self, update: Update, cafes: list, radius: int) -> int:
        results = []
        
        for cafe in cafes:
            props = cafe.get("properties", {})
            company_meta = props.get("CompanyMetaData", {})
            
            __name__ = company_meta.get("__name__", "Кафе без названия")
            address = company_meta.get("address", "Адрес не указан")
            rating = props.get("rating", "нет оценок")
            lon, lat = cafe["geometry"]["coordinates"]
            yandex_url = f"https://yandex.ru/maps/?ll={lon}%2C{lat}&z=17&pt={lon},{lat}"
            
            cafe_info = (
                f"☕️ <b>{__name__}</b>\n"
                f"⭐ Рейтинг: {rating}\n"
                f"📌 Адрес: {address}\n"
                f"🌐 Ссылка: {yandex_url}"
            )
            results.append(cafe_info)

        response_text = (
            f"🏆 Топ {len(results)} ближайших кафе в радиусе {radius} м:\n\n"
            + "\n\n".join(results)
        )
        
        update.message.reply_html(response_text, reply_markup=ReplyKeyboardRemove())
        return ConversationHandler.END

    # ================== Управление жизненным циклом ==================
    
    def cancel(self, update: Update, context: CallbackContext) -> int:
        update.message.reply_text(
            "❌ Поиск отменен",
            reply_markup=ReplyKeyboardRemove()
        )
        return ConversationHandler.END

    def graceful_shutdown(self, signum, frame):
        logger.info("🛑 Получен сигнал завершения...")
        self.updater.stop()
        self.session.close()
        logger.info("✅ Ресурсы освобождены. Бот остановлен.")
        exit(0)

    def run(self):
        dispatcher = self.updater.dispatcher

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

        signal.signal(signal.SIGINT, self.graceful_shutdown)
        signal.signal(signal.SIGTERM, self.graceful_shutdown)

        # Для работы через вебхуки
        self.updater.start_webhook(
            listen="0.0.0.0",
            port=PORT,
            url_path=TELEGRAM_TOKEN,
            webhook_url=f"{WEBHOOK_URL}/{TELEGRAM_TOKEN}"
        )

        logger.info("🤖 Яндекс-бот запущен!")
        self.updater.idle()

if __name__ == '__main__':
    bot = YandexCafeBot()
    bot.run()
