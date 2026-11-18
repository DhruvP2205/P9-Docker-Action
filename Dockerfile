FROM python:3.11-alpine

WORKDIR /flag-app

RUN apk update && apk add --no-cache curl jq

COPY entrypoint.py .

ENTRYPOINT ["python", "entrypoint.py"]