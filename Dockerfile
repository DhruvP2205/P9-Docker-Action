FROM python:3.11-alpine

WORKDIR /flag-app

COPY entrypoint.py .

ENTRYPOINT ["python", "/flag-app/entrypoint.py"]