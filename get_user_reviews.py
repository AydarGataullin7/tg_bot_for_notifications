import os
import time
import logging
import requests
import telegram
from dotenv import load_dotenv

load_dotenv()


class TelegramLogHandler(logging.Handler):
    def __init__(self, bot_token, chat_id):
        super().__init__()
        self.bot = telegram.Bot(token=bot_token)
        self.chat_id = chat_id

    def emit(self, record):
        log_entry = self.format(record)
        try:
            if len(log_entry) > 4000:
                log_entry = log_entry[:4000] + "... (обрезано)"
            self.bot.send_message(chat_id=self.chat_id, text=f"🚨 Ошибка в боте:\n{log_entry}")
        except telegram.error.TelegramError:
            pass


TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
DEVMAN_TOKEN = os.getenv('DEVMAN_TOKEN')
TG_CHAT_ID = os.getenv('TG_CHAT_ID')
PROXY_URL = os.getenv('PROXY_URL')

if PROXY_URL:
    request = telegram.utils.request.Request(proxy_url=PROXY_URL)
    bot = telegram.Bot(token=TELEGRAM_TOKEN, request=request)
else:
    bot = telegram.Bot(token=TELEGRAM_TOKEN)


def process_attempt(attempt):
    lesson_title = attempt['lesson_title']
    lesson_url = attempt['lesson_url']
    is_negative = attempt['is_negative']

    if is_negative:
        result = 'К сожалению, в работе есть ошибки'
    else:
        result = 'Преподавателю все понравилось!'

    message = f'Проверка работы: {lesson_title}\nURL: {lesson_url}\n{result}'
    bot.send_message(chat_id=TG_CHAT_ID, text=message)
    logger.info(f"Уведомление отправлено: {lesson_title}")


def main():
    global logger

    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)

    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    if TELEGRAM_TOKEN and TG_CHAT_ID:
        telegram_handler = TelegramLogHandler(TELEGRAM_TOKEN, TG_CHAT_ID)
        telegram_handler.setLevel(logging.ERROR)
        telegram_handler.setFormatter(formatter)
        logger.addHandler(telegram_handler)

    logger.info("Бот запущен и начал мониторинг")

    url = 'https://dvmn.org/api/long_polling/'
    headers = {'Authorization': f'Token {DEVMAN_TOKEN}'}
    timestamp = None

    while True:
        try:
            response = requests.get(url, headers=headers, timeout=90, params={'timestamp': timestamp})

            if not response.ok:
                if response.status_code == 400:
                    logger.warning("Неверный запрос к API Девмана")
                continue

            api_response = response.json()
            if api_response.get('status') != 'found':
                continue

            for attempt in api_response.get('new_attempts', []):
                process_attempt(attempt)

        except requests.exceptions.ConnectionError:
            logger.error("Ошибка подключения к API Девмана")
            time.sleep(10)
        except Exception as e:
            logger.error(f"Критическая ошибка: {e}", exc_info=True)
            time.sleep(5)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Бот остановлен вручную")
    except Exception as e:
        logger.error(f"Необработанная ошибка: {e}", exc_info=True)
