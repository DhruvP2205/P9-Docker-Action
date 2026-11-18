# fixtures/multistage.Dockerfile
FROM python:3.12 AS builder
FROM builder AS test
FROM python:3.12-slim