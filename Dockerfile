FROM mcr.microsoft.com/playwright/python:v1.63.0-noble

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir --requirement requirements.txt

COPY --chown=pwuser:pwuser app ./app

USER pwuser

ENTRYPOINT ["python", "-m", "app"]
CMD ["https://example.com", "--max-pages", "10", "--max-depth", "1"]
