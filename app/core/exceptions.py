import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger(__name__)

HTTP_ERROR_CODES = {
    400: "BAD_REQUEST",
    401: "UNAUTHORIZED",
    403: "FORBIDDEN",
    404: "NOT_FOUND",
    409: "CONFLICT",
}


class AppException(Exception):
    def __init__(
        self,
        status_code: int,
        code: str,
        message: str,
    ):
        self.status_code = status_code
        self.code = code
        self.message = message


def error_response(
    status_code: int,
    code: str,
    message: str,
    details=None,
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "error": {
                "code": code,
                "message": message,
                "details": details if details is not None else [],
            }
        },
    )


def register_exception_handlers(app: FastAPI) -> None:

    @app.exception_handler(AppException)
    async def app_exception_handler(
        request: Request,
        exc: AppException,
    ):
        return error_response(
            exc.status_code,
            exc.code,
            exc.message,
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(
        request: Request,
        exc: StarletteHTTPException,
    ):
        
        messages = {
            400: "Invalid request format",
            401: "Authentication required",
            403: "Access denied",
            404: "Resource not found",
            405: "HTTP method not allowed",
            409: "State conflict occurred",
        }


        return JSONResponse(
            status_code=exc.status_code,
            headers=exc.headers,
            content={
                "error": {
                    "code": HTTP_ERROR_CODES.get(
                        exc.status_code, "HTTP_ERROR"
                    ),
                    "message": messages.get(
                        exc.status_code, "Request error"
                    ),
                    "details": [],
                }
            },
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request,
        exc: RequestValidationError,
    ):
        details = [
            {
                "field": ".".join(str(item) for item in error["loc"]),
                "message": error["msg"],
                "type": error["type"],
            }
            for error in exc.errors()
        ]

        return error_response(
            422,
            "VALIDATION_ERROR",
            "Validation error",
            details,
        )

    @app.exception_handler(Exception)
    async def global_exception_handler(
        request: Request,
        exc: Exception,
    ):
        logger.error(
            "Internal error: %s %s",
            request.method,
            request.url.path,
            exc_info=exc,
        )

        return error_response(
            500,
            "INTERNAL_SERVER_ERROR",
            "Internal server error.",
        )