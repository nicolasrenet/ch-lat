#syntax=docker/dockerfile:1

FROM python:3.10-slim

WORKDIR /alignment-flask

COPY templates static charter_annotation.py fsdb.y /alignment-flask

RUN pip3 install --no-cache-dir -r requirements

EXPOSE 5000

CMD ['python3', '-m', 'flask', '--app' 'charter_annotation', 'run' ]
