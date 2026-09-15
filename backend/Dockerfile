FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN addgroup --system timberops \
    && adduser --system --ingroup timberops timberops

COPY requirements.txt ./
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

COPY --chown=timberops:timberops app ./app
COPY --chown=timberops:timberops migrations ./migrations
COPY --chown=timberops:timberops alembic.ini ./alembic.ini

USER timberops

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
