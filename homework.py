import os
import time
import requests
import logging
from telegram import Bot
from dotenv import load_dotenv
from http import HTTPStatus
load_dotenv()

ONE_DAY_IN_SEC = 86400
DAYS = 30

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO)


def send_message(bot, message):
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logging.info(f'Сообщение: "{message}" удачно отправлено!')
    except Exception as error:
        logging.error(f'Ошибка при отправке сообщени: {error}')


def get_api_answer(current_timestamp):
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    response = requests.get(ENDPOINT, headers=HEADERS, params=params)
    if response.status_code == HTTPStatus.OK:
        return response.json()
    else:
        logging.error(
            f'Сбой в работе программы: Эндпоинт {ENDPOINT} недоступен. '
            f'Код ответа API: {response.status_code}'
        )
        raise AssertionError


def check_response(response):
    if isinstance(response, dict) and isinstance(response['homeworks'], list):
        return response.get('homeworks')
    else:
        logging.error('Отсутствуют ожидаемые ключи в ответе API')
        raise TypeError


def parse_status(homework):
    try:
        homework_name = homework['homework_name']
    except KeyError:
        raise KeyError
    homework_status = homework.get('status')
    if homework_status not in HOMEWORK_STATUSES.keys():
        logging.error(f'Неизвестный статус домашней работы {homework_status}')
        raise AssertionError
    verdict = HOMEWORK_STATUSES[homework_status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    is_exist = True
    if (PRACTICUM_TOKEN is None
        or TELEGRAM_CHAT_ID is None
            or TELEGRAM_TOKEN is None):
        logging.critical('Одна или более переменных окружения не определены')
        is_exist = False
    return is_exist


def main():
    """Основная логика работы бота."""
    if check_tokens():
        bot = Bot(token=TELEGRAM_TOKEN)
        current_timestamp = int(time.time()) - (ONE_DAY_IN_SEC * DAYS)
        status = ''
        while True:
            try:
                response = get_api_answer(current_timestamp)
                homework = check_response(response)
                message = parse_status(homework)
                if status != message:
                    send_message(bot, message)
                    status = message
            except Exception as error:
                message = f'Сбой в работе программы: {error}'
                logging.error(message)
                send_message(bot, message)
            finally:
                time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
