import os
import time
import logging
import requests
import telegram
from dotenv import load_dotenv


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


def process_attempt(attempt, bot, chat_id, logger):
    lesson_title = attempt['lesson_title']
    lesson_url = attempt['lesson_url']
    is_negative = attempt['is_negative']

    if is_negative:
        result = 'К сожалению, в работе есть ошибки'
    else:
        result = 'Преподавателю все понравилось!'

    message = f'Проверка работы: {lesson_title}\nURL: {lesson_url}\n{result}'
    bot.send_message(chat_id=chat_id, text=message)
    logger.info(f"Уведомление отправлено: {lesson_title}")


def main():
    load_dotenv()

    telegram_token = os.environ['TELEGRAM_TOKEN']
    devman_token = os.environ['DEVMAN_TOKEN']
    tg_chat_id = os.environ['TG_CHAT_ID']
    proxy_url = os.getenv('PROXY_URL')

    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)

    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    if proxy_url:
        request = telegram.utils.request.Request(proxy_url=proxy_url)
        bot = telegram.Bot(token=telegram_token, request=request)
    else:
        bot = telegram.Bot(token=telegram_token)

    if telegram_token and tg_chat_id:
        telegram_handler = TelegramLogHandler(telegram_token, tg_chat_id)
        telegram_handler.setLevel(logging.ERROR)
        telegram_handler.setFormatter(formatter)
        logger.addHandler(telegram_handler)

    logger.info("Бот запущен и начал мониторинг")

    url = 'https://dvmn.org/api/long_polling/'
    headers = {'Authorization': f'Token {devman_token}'}
    timestamp = None

    while True:
        try:
            response = requests.get(url, headers=headers, timeout=90, params={'timestamp': timestamp})
            response.raise_for_status()

            api_response = response.json()
            if api_response.get('status') != 'found':
                continue

            for attempt in api_response.get('new_attempts', []):
                process_attempt(attempt, bot, tg_chat_id, logger)

        except requests.exceptions.ReadTimeout:
            continue
        except requests.exceptions.ConnectionError:
            logger.error("Ошибка подключения к API Девмана")
            time.sleep(10)
        except Exception as e:
            logger.error(f"Ошибка: {e}", exc_info=True)
            time.sleep(5)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Бот остановлен вручную")
    except Exception as e:
        logger.error(f"Ошибка: {e}", exc_info=True)
