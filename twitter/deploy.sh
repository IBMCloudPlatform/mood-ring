#!/bin/bash

CURR_DIR=$(cd $(dirname $0) && pwd)
source $CURR_DIR/../envrc

ANALYZER_HOST_URL=$ANALYZER_HOST".mybluemix.net"

# build twitter feeder image and push the image to your Bluemix registry
docker build -t twitter-data:v1 $CURR_DIR
docker tag -f twitter-data:v1 registry.ng.bluemix.net/$NAMESPACE/twitter-data:v1
docker push registry.ng.bluemix.net/$NAMESPACE/twitter-data:v1

# run it in IBM Bluemix
cf ic run --name tone_demo_twitter -m 256 --link tonedemo_analyzer:analyzer \
  -e ANALYZER_HOST="tonedemo_analyzer:5000" -e CCS_BIND_SRV="$TWITTER_CCS_BIND_SRV" \
  registry.ng.bluemix.net/$NAMESPACE/twitter-data:v1