FROM python:3.8

# ENV DOCKERIZED=1
ENV PYTHONBUFFERED=1
ENV CRYPTOGRAPHY_DONT_BUILD_RUST=1

WORKDIR /iago
COPY requirements.txt requirements.txt
RUN pip install -r /iago/requirements.txt --no-cache-dir
COPY manage.py manage.py
COPY iago iago
COPY action_engine action_engine
COPY start.sh start.sh
CMD ["bash", "/iago/start.sh"]
