FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY --chmod=644 requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY --chmod=644 telegramirc.py .

RUN useradd --system --no-create-home --uid 1000 telegramirc
USER telegramirc

ENTRYPOINT ["python", "telegramirc.py", "/config/telegramirc.toml"]
