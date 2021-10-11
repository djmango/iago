#!/usr/bin/env sh
# python manage.py collectstatic --noinput --clear
if [ "$DEBUG" = "0" ]; then
    echo "RUNNING DJANGO START SCRIPT IN DEBUG"
    pip install debugpy -t /tmp
    python /tmp/debugpy --wait-for-client --listen 0.0.0.0:5678 manage.py runserver 0.0.0.0:8000 --noreload
else
    echo "RUNNING DJANGO START SCRIPT IN PRODUCTION"
    curl  -fsS --retry 3 "$DUCKDNS_UPDATE" > /dev/null
    daphne -b 0.0.0.0 -p 8000 iago.asgi:application
fi