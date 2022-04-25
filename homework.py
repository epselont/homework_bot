import logging
import os
import time
from http import HTTPStatus
from sys import stdout

import requests
from dotenv import load_dotenv
from telegram import Bot

from exceptions import GetAPIException, ParseStatusException

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

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler(stdout)
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
handler.setFormatter(formatter)
logger.addHandler(handler)


def send_message(bot, message):
    """Отправка сообщения."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logger.info(f'Сообщение: "{message}", удачно отправлено!')
    except Exception as error:
        logger.error(f'Ошибка при отправке сообщени: {error}')


def get_api_answer(current_timestamp):
    """Запрос на получение данных по домашним работам."""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    response = requests.get(ENDPOINT, headers=HEADERS, params=params)
    if response.status_code == HTTPStatus.OK:
        return response.json()
    else:
        logger.error(
            f'Сбой в работе программы: Эндпоинт {ENDPOINT} недоступен. '
            f'Код ответа API: {response.status_code}'
        )
        raise GetAPIException


def check_response(response):
    """Проверка корректности полученных данных."""
    if isinstance(response, dict) and isinstance(response['homeworks'], list):
        return response.get('homeworks')
    else:
        logger.error('Некорректные данные в response')
        raise TypeError


def parse_status(homework):
    """Извлечение статуса домашней работы."""
    try:
        homework_name = homework['homework_name']
    except Exception as error:
        err_message = f'Ошибка при извлечении статуса домашней работы: {error}'
        logger.error(err_message)
        raise KeyError(err_message)
    homework_status = homework.get('status')
    if homework_status not in HOMEWORK_STATUSES.keys():
        logger.error(f'Неизвестный статус домашней работы {homework_status}')
        raise ParseStatusException
    verdict = HOMEWORK_STATUSES[homework_status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Проверка наличия необходимых данных для корректной работы бота."""
    is_exist = True
    if (PRACTICUM_TOKEN is None
        or TELEGRAM_CHAT_ID is None
            or TELEGRAM_TOKEN is None):
        logger.critical('Одна или более переменных окружения не определены')
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
                message = parse_status(homework[0])
                if status != message:
                    send_message(bot, message)
                    status = message
            except Exception as error:
                message = f'Сбой в работе программы: {error}'
                logger.error(message)
                send_message(bot, message)
            finally:
                time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
