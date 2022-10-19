import os
import sys
import time
import logging
import requests
import telegram
from dotenv import load_dotenv
from logging import StreamHandler
from http import HTTPStatus
from exceptions import SendMessageError, WarningMessage, UnavailableApi


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
    logger.info('Начало отправки сообщений.')
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
    except Exception as error:
        raise WarningMessage(
            f'Ошибка при отправке сообщения в ТГ: {error}'
        )
    else:
        logger.info(f'Сообщение отправлено: {message}')


def get_api_answer(current_timestamp):
    """Запрос к эндпоинту API-сервиса."""
    request_params = {
        'url': ENDPOINT,
        'headers': {'Authorization': f'OAuth {PRACTICUM_TOKEN}'},
        'params': {'from_date': current_timestamp or int(time.time())}
    }
    try:
        response = requests.get(**request_params)
        logger.info('Получаем информацию API.')
        if response.status_code != HTTPStatus.OK:
            error_message = f'Запрос к ресурсу ' \
                f'{ENDPOINT}' \
                f'Неверный код ответа от API: {response.status_code}' \
                f'Статус страницы не равен 200'
            raise Exception(error_message)
    except requests.exceptions.RequestException as ex:
        raise UnavailableApi(f'API-сервис Практикума недоступен. Ошибка: {ex}')
    else:
        return response.json()


def check_response(response):
    """Проверка ответа от API  и возврат списка ДЗ."""
    logger.info('Проверка корректности полученных данных.')
    if not isinstance(response, dict):
        raise TypeError('Ответ "response" должен быть словарем.'
                        f'response = {response}'
        )
    if 'homeworks' not in response:
        raise KeyError('Ответ должен содержать ключ "homeworks".')
    if not isinstance(response['homeworks'], list):
        raise KeyError(
            'В ответе от API под ключом "homeworks" пришел не список.'
            f'response = {response}.'
        )
    return response['homeworks']


def parse_status(homework):
    """Извлекает статус конкретного ДЗ."""
    homework_name = homework.get('homework_name')
    homework_status = homework.get('status')
    if homework_status not in HOMEWORK_STATUSES:
        message_homework_status = "Такого статуса ДЗ не существует."
        raise KeyError(message_homework_status)
    if "homework_name" not in homework:
        message_homework_name = "Такого имени не существует."
        raise KeyError(message_homework_name)
    verdict = HOMEWORK_STATUSES[homework_status]
    if not verdict:
        message_verdict = "Такого статуса нет в словаре."
        raise KeyError(message_verdict)
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Проверка доступности токенов из окружения."""
    logger.info('Проверка доступности токенов.')
    return all((PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID))


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        logger.critical('Ошибка в получении токенов. '
                        'Программа принудительно остановлена.')
        message = 'Проверьте корректность токенов.'
        logger.critical(message)
        sys.exit(message)
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
        except SendMessageError as warning:
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
