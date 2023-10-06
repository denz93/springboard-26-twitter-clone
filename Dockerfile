FROM python:3.12.0-slim
RUN apt-get update && \
    apt-get install -y build-essential libpq-dev python3-dev libffi-dev

RUN mkdir /app
WORKDIR /app

COPY . .
RUN pip install -r requirements.txt

RUN mkdir -p /root/.postgresql && mkdir -p /home/.postgresql
RUN cp ./postgresql/root.crt /root/.postgresql/root.crt
RUN cp ./postgresql/root.crt /home/.postgresql/root.crt

CMD gunicorn -b "0.0.0.0:5000" -w 2 --timeout 0 "app:app"

