import logging
import os
import time
from http import HTTPStatus
from sys import stdout

import requests
import telegram
from dotenv import load_dotenv

from exceptions import GetAPIException, ParseStatusException
from settings import (DAYS, ENDPOINT, HOMEWORK_STATUSES, ONE_DAY_IN_SEC,
                      RETRY_TIME)

load_dotenv()


PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


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
    except telegram.error.TelegramError as error:
        logger.error(f'Ошибка при отправке сообщени: {error}')


def get_api_answer(current_timestamp):
    """Запрос на получение данных по домашним работам."""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=params)
    except Exception as error:
        logger.error(
            f'Ошибка при запросе к основному API: {error}'
        )
        raise GetAPIException
    if response.status_code == HTTPStatus.OK:
        try:
            response.json()
        except Exception as error:
            logger.error(
                f'Ощибка преобразования формата: {error}'
            )
        else:
            return response.json()
    else:
        logger.error(
            f'Сбой в работе программы: Эндпоинт {ENDPOINT} недоступен. '
            f'Код ответа API: {response.status_code}'
        )
        raise GetAPIException


def check_response(response):
    """Проверка корректности полученных данных."""
    if isinstance(response, dict):
        if 'homeworks' in response:
            if isinstance(response['homeworks'], list):
                if response['homeworks']:
                    return response.get('homeworks')
                else:
                    raise IndexError
            else:
                raise TypeError
        else:
            raise KeyError
    else:
        logger.error('Некорректные данные в response')
        raise TypeError


def parse_status(homework):
    """Извлечение статуса домашней работы."""
    if 'homework_name' in homework:
        homework_name = homework['homework_name']
    else:
        logger.error('Ошибка при извлечении имени домашней работы.')
        raise KeyError('Ошибка при извлечении имени домашней работы.')
    homework_status = homework.get('status')
    if homework_status not in HOMEWORK_STATUSES.keys():
        logger.error(f'Неизвестный статус домашней работы {homework_status}')
        raise ParseStatusException
    verdict = HOMEWORK_STATUSES[homework_status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Проверка наличия необходимых данных для корректной работы бота."""
    return all([PRACTICUM_TOKEN, TELEGRAM_CHAT_ID, TELEGRAM_TOKEN])


def main():
    """Основная логика работы бота."""
    if check_tokens():
        bot = telegram.Bot(token=TELEGRAM_TOKEN)
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
    else:
        logger.critical('Одна или более переменных окружения не определены')


if __name__ == '__main__':
    main()
