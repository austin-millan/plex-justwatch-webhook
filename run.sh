#!/bin/bash

docker run -ti \
        --rm \
        -p 5000:5000/tcp \
        --env-file=.env \
        aamillan/plex-justwatch-webhook:latest
    #    /usr/bin/plex-justwatch/plex-justwatch.py
