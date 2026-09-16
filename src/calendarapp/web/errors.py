from jakarta.inject import Singleton
from micronaut.http import HttpRequest, HttpResponse
from micronaut.http.annotation import Produces
from micronaut.http.server.exceptions import ExceptionHandler

from ..domain.errors import InvalidRequestException, NotFoundException


def _message(exception) -> str:
    # Java code hands us the Java side of the Python subclass; the Python object is behind `this`.
    for read in (lambda: exception.message, lambda: exception.this.message):
        try:
            return str(read())
        except AttributeError:
            continue
    return "Request failed"


def _error(message: str) -> dict:
    return {"message": message, "_embedded": {"errors": [{"message": message}]}}


@Produces
@Singleton
class NotFoundExceptionHandler(ExceptionHandler[NotFoundException, HttpResponse]):
    def handle(self, request: HttpRequest, exception: NotFoundException) -> HttpResponse:
        return HttpResponse.notFound(_error(_message(exception)))


@Produces
@Singleton
class InvalidRequestExceptionHandler(ExceptionHandler[InvalidRequestException, HttpResponse]):
    def handle(self, request: HttpRequest, exception: InvalidRequestException) -> HttpResponse:
        return HttpResponse.badRequest(_error(_message(exception)))
