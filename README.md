# Mood-Ring

The [hack.summit](https://hacksummit.org) "mood ring" demo, built on [IBM Bluemix](http://bluemix.net/), used Docker containers and services to
display a real-time dashboard of the "tone" of the summit based on the Twitter hashtag #hacksummit.

Follow the steps below to deploy the demo yourself.  If you are not a bluemix user, you may register at [bluemix.net](http://bluemix.net/)

1. Deploy the following 2 services from [Bluemix Service catalog](https://console.ng.bluemix.net/catalog/):
  1. Insights for Twitter
  2. Watson Tone Analyzer

2. Configure the [envrc file](envrc) to your environment variable values.
  1. NAMESPACE should be your Bluemix registry namespace, e.g. *cf ic namespace get*
  2. ANALYZER_CCS_BIND_SRV should be the Watson Tone Analyzer service instance name
  3. TWITTER_CCS_BIND_SRV should be the Insights for Twitter service instance name

3. Download [Docker 1.10 or later](https://docs.docker.com/engine/installation/), [CF CLI 6.12.0 or later](https://github.com/cloudfoundry/cli/releases) and [IBM Container CLI extension](https://console.ng.bluemix.net/docs/containers/container_cli_ov.html#container_cli_ov).  [Login to IBM Bluemix container service](https://console.ng.bluemix.net/docs/containers/container_cli_ov.html#container_cli_login) using *cf login* and *cf ic login*.

3. Deploy the ElasticSearch, Kibana and Mood-Ring Analyzer container by running [analyzer/deploy.sh](analyzer/deploy.sh).

4. Deploy the Mood-Ring Twitter feeder container by running [twitter/deploy.sh](twitter/deploy.sh)

5. Bind a public ip to the Kibana container so you can access kibana web UI at http://{public_ip}:5601/.
From Kibana UI, you may create an index called "tone-analysis" and create your own visual diagrams or dashboard.

Interested in adding your own feeder from a different data source than twitter or knowing more details? Check [internal details](DETAILS.md).

