FROM nginx:1.19.0-alpine

RUN rm /etc/nginx/conf.d/default.conf
COPY nginx.deploy.conf /etc/nginx/conf.d/default.conf
# these are dummy keys so that nginx can run and gen the real keys
COPY fullchain.pem /etc/nginx/certs/metafill/fullchain.pem
COPY privkey.pem /etc/nginx/certs/metafill/privkey.pem

RUN apk add python3 python3-dev py3-pip build-base libressl-dev musl-dev libffi-dev
RUN pip3 install pip --upgrade
ENV CRYPTOGRAPHY_DONT_BUILD_RUST=1
RUN pip3 install certbot-nginx