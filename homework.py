import os
import sys
import time
import logging
import requests
import telegram
from dotenv import load_dotenv
from logging import StreamHandler
from http import HTTPStatus
from exceptions import WarningMessage


load_dotenv()


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
logger.setLevel(logging.DEBUG)
handler = StreamHandler(stream=sys.stdout)
logger.addHandler(handler)
formatter = logging.Formatter(
    '%(asctime)s [%(levelname)s] %(message)s'
)
handler.setFormatter(formatter)


def send_message(bot, message):
    """Отправка сообщений в ТГ."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logger.info(f'Бот отправил сообщение: {message}')
    except Exception as error:
        raise WarningMessage(
            f'Ошибка при отправке сообщения в ТГ: {error}'
        )


def get_api_answer(current_timestamp):
    """Запрос к эндпоинту API-сервиса."""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    try:
        api_answer = requests.get(ENDPOINT, headers=HEADERS, params=params)
        if api_answer.status_code != HTTPStatus.OK:
            message = (f'Эндпонит {ENDPOINT} недоступен.'
                       f'Код ответа API-сервиса: {api_answer.status_code}')
            raise Exception(message)
    except requests.exceptions.RequestException as ex:
        raise Exception(f'Ошибка при запросе к API: {ex}')
    else:
        return api_answer.json()


def check_response(response):
    """Проверка ответа от API  и возврат списка ДЗ."""
    if not isinstance(response, dict):
        raise TypeError('Ответ должен быть словарем.')
    if 'homeworks' not in response:
        raise KeyError('Ответ должен содержать ключ homeworks.')
    if not isinstance(response['homeworks'], list):
        raise WarningMessage('ДЗ не возвращается в виде списка.')
    return response['homeworks']


def parse_status(homework):
    """Извлекает статус конкретного ДЗ."""
    homework_name = homework.get('homework_name')
    homework_status = homework.get('status')
    logger.debug(f'На входе в parse_status: {homework}')
    homework_name = homework.get('homework_name')
    logger.debug(f'Название домашки: {homework_name}')
    homework_status = homework.get('status')
    logger.debug(f'Статус домашки: {homework_status}')
    if homework_status not in HOMEWORK_STATUSES:
        raise KeyError('Недокументированный статус домашней '
                       'работы в ответе API.')
    verdict = HOMEWORK_STATUSES.get(homework_status)
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Проверка доступности токенов из окружения."""
    return all((PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID))


def main():
    """Основная логика работы бота."""
    if check_tokens() is False:
        logger.critical('Отсутствует обязательная переменная окружения. '
                        'Программа принудительно остановлена.')
        raise SystemExit
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    MESSAGE = ''
    ERROR = ''

    while True:
        try:
            response = get_api_answer(current_timestamp)
            logger.debug(f'Ответ get_api_answer: {response}')
            check = check_response(response)
            if len(check) == 0:
                logger.debug('Список домашек пуст. Подождем ещё.')
                current_timestamp = response['current_date']
                continue
            logger.debug(f'Ответ check_response: {check}')
            message = parse_status(check[0])
            logger.debug(f'Ответ parse_status: {message}')
            if message != MESSAGE:
                send_message(bot, message)
                MESSAGE = message
            else:
                logger.debug('Ответ не изменился. Подождем ещё.')
        except WarningMessage as warning:
            message = f'Внимание: {warning}'
            logger.error(message)
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logger.error(message)
            if message != ERROR:
                send_message(bot, message)
                ERROR = message
        else:
            current_timestamp = response['current_date']
        finally:
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
