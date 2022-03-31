#!/usr/bin/env sh
echo "RUNNING SCRAPY START"
pip install debugpy -t /tmp
cd scrapy_app
python /tmp/debugpy --wait-for-client --listen 0.0.0.0:5678 /usr/local/bin/scrapy crawl update_medium