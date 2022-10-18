class WarningMessage(Exception):
    """Исключение для случаев, когда не нужно отправлять сообщение в ТГ."""
    pass

class UnavailableApi(Exception):
    """Исключение при недоступном API Практикума."""
    pass
