class WarningMessage(Exception):
    """Исключение для случаев, когда не нужно отправлять сообщение в ТГ."""
    pass

class UnavailableApi(Exception):
    """Исключение при недоступном API Практикума."""
    pass

class SendMessageError(Exception):
    """Исключение при ошибке отправке сообщения."""

class WrongApiStatus(Exception):
    """Исключение при неверном API-статусе."""