FROM python:3.9-slim-bookworm

ENV PYTHONUNBUFFERED 1

EXPOSE 8000
WORKDIR /app


RUN apt-get update && \
    apt-get install -y --no-install-recommends netcat-openbsd build-essential && \
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

COPY poetry.lock pyproject.toml ./
RUN pip install --upgrade pip && \
    pip install "poetry==1.8.5" && \
    poetry config virtualenvs.in-project true && \
    poetry install --no-dev && \
    .venv/bin/pip install "setuptools<70"

COPY . ./

CMD while ! nc -z db 5432; do sleep 1; done && \
    poetry run alembic upgrade head && \
    poetry run uvicorn --host=0.0.0.0 app.main:app
