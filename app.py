# ================== СЕКЦИЯ 1: ИМПОРТЫ ==================
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

# ================== Конфигурация ==================
TELEGRAM_TOKEN = os.getenv("TG_TOKEN")          # Изменил имя переменной для dockhost
YANDEX_API_KEY = os.getenv("YANDEX_API_KEY")
PORT = int(os.environ.get("PORT", 5000))        # Стандартный порт для dockhost
WEBHOOK_URL = os.getenv("WEBHOOK_URL")          # Будет предоставлен dockhost

# Параметры поиска
MAX_RADIUS = 5000
MIN_RADIUS = 100
MAX_RESULTS = 3

# Состояния диалога
RADIUS, LOCATION = range(2)

# Настройка логов
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

class YandexCafeBot:
    def __init__(self):
        self.updater = Updater(TELEGRAM_TOKEN, use_context=True)
        self.session = requests.Session()

    # ============== СЕКЦИЯ 5: ОБРАБОТЧИКИ КОМАНД ==============
    def start(self, update: Update, context: CallbackContext) -> None:
        """Обработчик команды /start"""
        user = update.effective_user
        update.message.reply_text(
            f"Привет, {user.first_name}! 👋\n"
            "Я помогу найти ближайшие кафе через Яндекс.Карты!\n"
            "Используй /findcafe чтобы начать поиск",
            reply_markup=ReplyKeyboardRemove()
        )

    def find_cafe(self, update: Update, context: CallbackContext) -> int:
        """Начало процесса поиска кафе"""
        update.message.reply_text(
            f"📏 Введите радиус поиска в метрах ({MIN_RADIUS}-{MAX_RADIUS}):",
            reply_markup=ReplyKeyboardRemove()
        )
        return RADIUS

    # ============ СЕКЦИЯ 6: ОБРАБОТКА СОСТОЯНИЙ =============
    def receive_radius(self, update: Update, context: CallbackContext) -> int:
        """Обработка введенного радиуса поиска"""
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
        """Запрос геолокации у пользователя"""
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

    # ============== СЕКЦИЯ 7: РАБОТА С API ЯНДЕКС ==============
    def receive_location(self, update: Update, context: CallbackContext) -> int:
        """Обработка полученной геолокации"""
        try:
            location = update.message.location
            lat, lon = location.latitude, location.longitude
            radius = context.user_data.get("radius", 1000)

            # Поиск кафе через Яндекс API
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

    # =========== СЕКЦИЯ 8: ФОРМАТИРОВАНИЕ РЕЗУЛЬТАТОВ ===========
    def _send_results(self, update: Update, cafes: list, radius: int) -> int:
        """Форматирование и отправка результатов пользователю"""
        results = []
        
        for cafe in cafes:
            props = cafe.get("properties", {})
            meta = props.get("CompanyMetaData", {})
            
            __name__ = meta.get("__name__", "Кафе без названия")
            address = meta.get("address", "Адрес не указан")
            rating = props.get("rating", "нет оценок")
            lon, lat = cafe["geometry"]["coordinates"]
            url = f"https://yandex.ru/maps/?ll={lon}%2C{lat}&z=17&pt={lon},{lat}"
            
            results.append(
                f"☕️ <b>{__name__}</b>\n"
                f"⭐ Рейтинг: {rating}\n"
                f"📌 Адрес: {address}\n"
                f"🌐 Ссылка: {url}"
            )

        update.message.reply_html(
            f"🏆 Топ {len(results)} ближайших кафе в радиусе {radius} м:\n\n" + "\n\n".join(results),
            reply_markup=ReplyKeyboardRemove()
        )
        return ConversationHandler.END

    # ========== СЕКЦИЯ 9: УПРАВЛЕНИЕ ЖИЗНЕННЫМ ЦИКЛОМ ==========
    def cancel(self, update: Update, context: CallbackContext) -> int:
        """Обработчик отмены поиска"""
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

    # ============== СЕКЦИЯ 10: ЗАПУСК ПРИЛОЖЕНИЯ ==============
    def run(self):
        """Запуск для dockhost"""
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

        # Настройка вебхуков
        self.updater.start_webhook(
            listen="0.0.0.0",
            port=PORT,
            url_path=TELEGRAM_TOKEN,
            webhook_url=f"{WEBHOOK_URL}/{TELEGRAM_TOKEN}"
        )

        logger.info(f"🚀 Бот запущен на {WEBHOOK_URL}")
        self.updater.idle()

if __name__ == '__main__':
    # Проверка переменных окружения
    required_vars = {
        "TG_TOKEN": TELEGRAM_TOKEN,
        "YANDEX_API_KEY": YANDEX_API_KEY,
        "WEBHOOK_URL": WEBHOOK_URL
    }
    
    for name, value in required_vars.items():
        if not value:
            logger.error(f"❌ Переменная окружения {name} не задана!")
            exit(1)

    bot = YandexCafeBot()
    bot.run()
