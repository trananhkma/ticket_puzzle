FROM python:3.8

RUN apt-get update && apt-get -y upgrade
RUN apt-get -y install libpq-dev gcc

RUN mkdir /code

RUN curl -sSL https://install.python-poetry.org | python3 -
ENV PATH="/root/.local/bin:$PATH"

WORKDIR /code
COPY poetry.lock pyproject.toml /code
RUN poetry config virtualenvs.create false && poetry install --no-interaction

ENV PYTHONUNBUFFERED=1

# For debugging
RUN pip install debugpy
EXPOSE 5678
