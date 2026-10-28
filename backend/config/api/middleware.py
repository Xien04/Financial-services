"""Server-owned correlation labels, isolated between requests and execution contexts."""

import uuid
from contextvars import ContextVar

request_id_context: ContextVar[str | None] = ContextVar("request_id", default=None)


def is_api(request) -> bool:
    return request.path == "/api/v1" or request.path.startswith("/api/v1/")


def get_request_id(request) -> str:
    underlying = getattr(request, "_request", request)
    if not getattr(underlying, "request_id", None):
        underlying.request_id = str(uuid.uuid4())
    return underlying.request_id


class RequestIdMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not is_api(request):
            return self.get_response(request)
        # Caller-supplied headers are never consulted, copied, or logged.
        request.request_id = str(uuid.uuid4())
        token = request_id_context.set(request.request_id)
        try:
            response = self.get_response(request)
            response["X-Request-ID"] = request.request_id
            return response
        finally:
            request_id_context.reset(token)
