FROM python:3.8-slim

RUN pip install flask
RUN pip install plexapi
RUN pip install justwatch
RUN pip install pyOpenSSL
RUN pip install pylogrus
# RUN python -m easy_install –upgrade OpenSSL

WORKDIR /usr/bin/plex_justwatch
COPY plex_justwatch/ /usr/bin/plex_justwatch
ENTRYPOINT [ "python" ]
CMD ["plex-justwatch.py"]