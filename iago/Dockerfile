FROM python:3.7.3-stretch

WORKDIR /iago
COPY requirements.txt requirements.txt
RUN pip install -r /iago/requirements.txt
COPY manage.py manage.py
COPY iago iago
COPY action_engine action_engine
ENV DOCKERIZED=1
ENV PYTHONBUFFERED=1
COPY start.sh start.sh
CMD ["bash", "/iago/start.sh"]