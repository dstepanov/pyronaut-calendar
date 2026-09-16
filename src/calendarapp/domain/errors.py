from java.lang import RuntimeException


class CalendarException(RuntimeException):
    def __init__(self, message: str):
        super().__init__()
        self.message = message


class NotFoundException(CalendarException):
    """Raised when a requested calendar resource does not exist."""


class InvalidRequestException(CalendarException):
    """Raised when a request is well-formed but breaks a business rule."""
