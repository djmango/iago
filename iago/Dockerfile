FROM python:3.10.5

ENV PYTHONBUFFERED=1
ENV CRYPTOGRAPHY_DONT_BUILD_RUST=1

WORKDIR /iago
RUN apt-get update && apt-get install tesseract-ocr poppler-utils -y \
  wget
RUN mkdir tesseract && wget https://github.com/tesseract-ocr/tessdata_fast/blob/923915d4ced2a7235221788285785a29c4a42d4a/eng.traineddata?raw=true -O tesseract/eng.traineddata
COPY requirements.txt requirements.txt
RUN pip install -r /iago/requirements.txt --no-cache-dir
COPY manage.py manage.py
COPY iago iago
COPY v0 v0
COPY start.sh start.sh
CMD ["bash", "/iago/start.sh"]
