#!/bin/bash
docker version
echo $DOCKER_PASSWORD | docker login -u $DOCKER_USERNAME --password-stdin
docker push tcprescott/tileroombot
