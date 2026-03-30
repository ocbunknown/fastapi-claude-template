FROM python:3.12.4

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONBUFFERED 1

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates && \
    rm -rf /var/lib/apt/lists/*

ADD https://astral.sh/uv/install.sh /uv-installer.sh

RUN sh /uv-installer.sh && rm /uv-installer.sh

ENV PATH="/root/.local/bin/:$PATH"
ENV UV_LINK_MODE=copy

COPY . .

EXPOSE 8091

RUN uv sync --frozen --no-dev --compile-bytecode
CMD ["sh", "-c", "uv run alembic upgrade head && uv run python -m src"]
