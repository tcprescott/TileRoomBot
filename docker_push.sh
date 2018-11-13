#!/bin/bash
echo $DOCKER_PASSWORD | docker login -u $DOCKER_USERNAME --password-stdin
export REPO=tcprescott/tileroombot
export TAG=`if [ "$TRAVIS_BRANCH" == "master" ]; then echo "latest"; else echo $TRAVIS_BRANCH ; fi`
docker tag $REPO:$COMMIT $REPO:$TAG
docker tag $REPO:$COMMIT $REPO:travis-$TRAVIS_BUILD_NUMBER
docker push $REPO
