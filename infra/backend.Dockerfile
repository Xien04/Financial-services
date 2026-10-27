FROM ghcr.io/astral-sh/uv:0.13.2 AS uv
FROM python:3.14.8-slim-bookworm
COPY --from=uv /uv /uvx /usr/local/bin/
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=never PYTHONUNBUFFERED=1
ENV PATH="/app/.venv/bin:$PATH"
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-dev
COPY backend ./backend
RUN useradd --create-home --uid 10001 app
USER app
WORKDIR /app/backend
EXPOSE 8000
CMD ["/app/.venv/bin/python", "manage.py", "runserver", "0.0.0.0:8000", "--noreload"]
