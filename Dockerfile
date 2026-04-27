FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /carebridge/app

# system deps (important for psycopg, bcrypt, etc.)
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# copy requirements first (better caching)
COPY requirements.txt .

# install dependencies INSIDE IMAGE
RUN pip install --upgrade pip && pip install -r requirements.txt

# copy project
COPY . .

# run app
CMD ["uvicorn", "carebridge.app.main:app", "--host", "0.0.0.0", "--port", "8000"]