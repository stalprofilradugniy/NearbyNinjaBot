import os
import logging
import signal
import time
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
from logging.handlers import RotatingFileHandler

# ================== Конфигурация ==================
TELEGRAM_TOKEN = os.getenv("TG_TOKEN")
YANDEX_API_KEY = os.getenv("YANDEX_API_KEY")
PORT = int(os.environ.get("PORT", 5000))
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

# Параметры поиска
MAX_RADIUS = 5000
MIN_RADIUS = 100
MAX_RESULTS = 3

# Состояния диалога
RADIUS, LOCATION = range(2)

# Настройка логов
log_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
log_handler = RotatingFileHandler('bot.log', maxBytes=1024*1024, backupCount=5) # Ротация логов
log_handler.setFormatter(log_formatter)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.addHandler(log_handler)
logger.addHandler(logging.StreamHandler()) # Вывод логов в консоль

class YandexCafeBot:
    def __init__(self):
        self.updater = Updater(TELEGRAM_TOKEN, use_context=True)
        self.session = requests.Session()

    # ... (остальные методы: start, find_cafe, receive_radius, _request_location)

    def receive_location(self, update: Update, context: CallbackContext) -> int:
        try:
            location = update.message.location
            lat, lon = location.latitude, location.longitude
            radius = context.user_data.get("radius", 1000)

            cafes = self._get_yandex_cafes(lon, lat, radius)

            if not cafes:
                update.message.reply_text(" Поблизости ничего не найдено. Попробуйте увеличить радиус.")
                return RADIUS # Предлагаем повторить поиск с другим радиусом

            return self._send_results(update, cafes, radius)

        except requests.exceptions.RequestException as e:
            logger.error(f"Ошибка соединения: {str(e)}")
            update.message.reply_text("⚠️ Проблемы с соединением. Попробуйте позже.")
        except Exception as e:
            logger.error(f"Ошибка: {str(e)}")
            update.message.reply_text(" Произошла ошибка. Попробуйте позже.")

        return ConversationHandler.END

    def _get_yandex_cafes(self, lon: float, lat: float, radius: int) -> list:
        url = "https://search-maps.yandex.ru/v1/"
        params = {
            "apikey": YANDEX_API_KEY,
            "text": "кафе",
            "lang": "ru_RU",
            "ll": f"{lon},{lat}",
            "spn": f"{(radius / 1000) * 0.009}",  #  Уточнить формулу spn, возможно нужна поправка на широту
            "rspn": 1,
            "results": MAX_RESULTS,
            "type": "biz"
        }
        try:
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status() # Проверяем HTTP статус код
            data = response.json()
            logger.info(f"Ответ от API Яндекс.Карт: {data}")

            if "error" in data:
                error_message = data.get("message", "Неизвестная ошибка")
                logger.error(f"Ошибка API: {error_message}")

                # Обработка конкретных ошибок API (пример)
                if error_message == "Api key is invalid":
                    update.message.reply_text("⚠️ Неверный API ключ Яндекс.Карт!")

                raise Exception(f"Ошибка API: {error_message}")

            time.sleep(0.5)  # Задержка перед следующим запросом
            return data.get("features", [])[:MAX_RESULTS]
        except requests.exceptions.RequestException as e:
            logger.error(f"Ошибка соединения: {str(e)}")
            raise
        except requests.exceptions.HTTPError as e: # Обработка HTTP ошибок
            logger.error(f"Ошибка HTTP: {e}")
            raise
        except Exception as e:
            logger.error(f"Ошибка: {str(e)}")
            raise


    # ... (остальные методы: _send_results, cancel)

    def graceful_shutdown(self, signum, frame):
        logger.info(" Получен сигнал завершения...")
        self.updater.stop()
        self.session.close()
        logger.info("✅ Ресурсы освобождены. Бот остановлен.")
        exit(0)

    def sigterm_handler(self, signum, frame): # Обработчик SIGTERM
        logger.info(" Получен сигнал SIGTERM...")
        self.updater.stop()
        self.session.close()
        logger.info("✅ Ресурсы освобождены. Бот остановлен.")
        exit(0)

    def run(self):
       # ... (остальной код run)
        signal.signal(signal.SIGINT, self.graceful_shutdown) # Ctrl+C
        signal.signal(signal.SIGTERM, self.sigterm_handler) # Docker stop

        self.updater.idle()

if __name__ == '__main__':
    # Проверка переменных окружения
    required_vars = {
        "TG_TOKEN": TELEGRAM_TOKEN,
        "YANDEX_API_KEY": YANDEX_API_KEY,
        "WEBHOOK_URL": WEBHOOK_URL
    }

    for var_name, value in required_vars.items():
        if not value:
            logger.error(f"❌ Переменная окружения {var_name} не задана!")
            exit(1)

    bot = YandexCafeBot()
    bot.run()
