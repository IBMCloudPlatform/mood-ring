#!/bin/bash

CURR_DIR=$(cd $(dirname $0) && pwd)
source $CURR_DIR/../envrc

# copy elasticsearch image to your Bluemix registry
cf ic cpi elasticsearch registry.ng.bluemix.net/$NAMESPACE/elasticsearch

# run it in IBM Bluemix
cf ic run --name tonedemo_es -p 9200 -m 256 \
  registry.ng.bluemix.net/$NAMESPACE/elasticsearch

# copy kibana image to your Bluemix registry
cf ic cpi kibana registry.ng.bluemix.net/$NAMESPACE/kibana

# run it in IBM Bluemix
cf ic run --name tonedemo_kibana --link tonedemo_es:elasticsearch \
  -e ELASTICSEARCH_URL=http://tonedemo_es:9200 -p 5601 -m 256 \
  registry.ng.bluemix.net/$NAMESPACE/kibana

# build analyzer image and push the image to your Bluemix registry
docker build -t analyzer:v3 $CURR_DIR
docker tag -f analyzer:v3 registry.ng.bluemix.net/$NAMESPACE/analyzer:v3
docker push registry.ng.bluemix.net/$NAMESPACE/analyzer:v3

# run it in IBM Bluemix
cf ic run --name tonedemo_analyzer -p 5000 -m 256 --link tonedemo_es:elasticsearch \
  -e ELASTICSEARCH_EP="http://tonedemo_es:9200" -e CCS_BIND_SRV="$ANALYZER_CCS_BIND_SRV" \
  registry.ng.bluemix.net/$NAMESPACE/analyzer:v3