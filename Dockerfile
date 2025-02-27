#syntax=docker/dockerfile:1

FROM python:3.8-slim

WORKDIR /alignment-flask

COPY templates static charter_annotation.py fsdb.py /alignment-flask
COPY templates/ /alignment-flask/templates
COPY static/ /alignment-flask/static
COPY requirements.txt /alignment-flask

RUN pip3 install --upgrade pip && pip install --no-cache-dir -r /alignment-flask/requirements.txt
RUN ls -l /alignment-flask

EXPOSE 5000

CMD ["python3","-m","flask","--app","charter_annotation","run"]
