FROM python:3.12.6

RUN apt-get update && \
    apt-get install -y \
    curl \
    screen \
    build-essential \
    redis-server \
    jq

# Enable print statements in Cloud Run
ENV PYTHONUNBUFFERED True

# Clean apt cache
RUN rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN curl -sSL https://install.python-poetry.org | python3 - && \
    ln -s /root/.local/bin/poetry /usr/local/bin/poetry

# Set working directory
WORKDIR /app

COPY . .

# Install dependencies using Poetry
RUN poetry config virtualenvs.create false && \
    poetry install --no-root --only main

EXPOSE 8000
EXPOSE 6379

CMD ["bash", "-c", "python manage.py runserver 0.0.0.0:8000"]