# fixtures/mixed.Dockerfile
FROM --platform=linux/amd64 python:3.12 AS a
FROM scratch
FROM localhost:5000/app
FROM localhost:5000/app:1.0
FROM localhost:5000/app@sha256:abc123
FROM nginx