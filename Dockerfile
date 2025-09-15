FROM python:3.12.1-slim

ENV POETRY_VERSION=1.6.1
ENV POETRY_HOME=/opt/poetry
ENV POETRY_VENV=/opt/poetry-venv
ENV POETRY_CACHE_DIR=/opt/.cache
ENV POETRY_VIRTUALENVS_CREATE=false
ENV TZ=Europe/Moscow

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl git \
    && rm -rf /var/lib/apt/lists/* \
    && ln -snf /usr/share/zoneinfo/$TZ /etc/localtime  \
    && echo $TZ > /etc/timezone

RUN pip install "poetry==$POETRY_VERSION"

WORKDIR /backend

COPY poetry.lock pyproject.toml /backend/

RUN poetry install --no-root --no-interaction

ENV PYTHONPATH=/backend:${PYTHONPATH}
