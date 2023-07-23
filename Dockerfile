FROM python:3.10-slim-bullseye

WORKDIR /bot

RUN pip install poetry
COPY poetry.lock .
COPY pyproject.toml .

RUN poetry install

COPY . .

RUN chmod +x scripts/*

CMD ["bash", "scripts/run.sh"]
