import requests
import telegram
import socks
import os
from telegram.utils.request import Request
from dotenv import load_dotenv


def main():
    load_dotenv()

    bot = telegram.Bot(
        token=os.getenv('TELEGRAM_TOKEN'),
        request=Request(proxy_url='socks5://127.0.0.1:10808')
    )
    url = 'https://dvmn.org/api/long_polling/'
    headers = {
        "Authorization": os.getenv('DEVMAN_TOKEN')
    }

    timestamp = None

    while True:
        params = {}
        if timestamp is not None:
            params['timestamp'] = timestamp
        try:
            response = requests.get(url, headers=headers,
                                    params=params, timeout=5)
            response.raise_for_status()
            data = response.json()

            if data['status'] == 'found':
                timestamp = data['last_attempt_timestamp']

                if data['new_attempts']:
                    new_attempt = data['new_attempts']
                    for attempt in new_attempt:
                        lesson_title = attempt['lesson_title']
                        lesson_url = attempt['lesson_url']
                        status = attempt['is_negative']
                        bot.send_message(
                            text=f'Преподаватель проверил работу по уроку: «{lesson_title}!»\nURL: {lesson_url}\n{"К сожалению, в работе есть ошибки" if status else "Преподавателю все понравлось, можно приступать к следующему уроку!"}',
                            chat_id=os.getenv('TG_CHAT_ID')
                        )

            elif data['status'] == 'timeout':
                timestamp = data['timestamp_to_request']
        except requests.exceptions.ReadTimeout:
            print('Таймаут, пробуем снова')
            continue
        except requests.exceptions.ConnectionError:
            print('Проверьте соединение')
            continue


if __name__ == '__main__':
    main()
