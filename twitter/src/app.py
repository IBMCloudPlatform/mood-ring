import requests
import json
import os
import sys
import logging
import time
import datetime
from logging import StreamHandler

# Define the base logger
logging.getLogger("twitter").setLevel(logging.DEBUG)
log = logging.getLogger("twitter")
# Logging config for console output
stream_handler = StreamHandler()
stream_formatter = logging.Formatter('[%(asctime)s] [%(thread)d] [%(module)s : %(lineno)d] [%(levelname)s] %(message)s')
stream_handler.setFormatter(stream_formatter)
log.addHandler(stream_handler)


def get_twitter_data(id_pwd, key, posted_time):
    """
    Obtain the twitter data for a given search key from twitter insights service
    :param id_pwd: id and pwd combination for the twitter insights service
    :param key: search key used to search twitter insights service
    :param posted_time: UTC time to limit tweets to a given posted time
    :return: twitter data for that search key
    """
    try:
        if posted_time is None:
            r = requests.get("https://" + id_pwd + "@cdeservice.mybluemix.net:443/api/v1/messages/search?q=" + key)
        else:
            # convert posted_time to desired format e.g. 2016-03-02T20:56:07Z
            before, sep, after = utc_now.isoformat().rpartition(".")
            r = requests.get("https://" + id_pwd + "@cdeservice.mybluemix.net:443/api/v1/messages/search?q="
                             + key + " posted:" + before + "Z")

    except Exception as e:
        # sleep 5 sec and retry as the container may not have network yet
        if posted_time is None:
            time.sleep(5)
            log.info("retry in 5 seconds")
            r = requests.get("https://" + id_pwd + "@cdeservice.mybluemix.net:443/api/v1/messages/search?q=" + key)

    j = None
    if r.status_code == 200:
        log.debug("Able to get valid response from twitter: %s", str(r.status_code))
        if hasattr(r, 'json') and len(r.content) > 0:
            try:
                j = r.json()
                send_json(j, key)
            except Exception as e:
                log.error("unable to get twitter data: %s", e.message)
    elif r.status_code == 401:
        log.error("please check your credential is correct: %s", id_pwd)
    else:
        log.error("invalid response.  code: %s, text: %s", str(r.status_code), r.text)
    return j


def send_json(j, key):
    """
    send twitter data to the tone demo analyzer microservice to analyze
    :param j: raw twitter data from twitter insights
    :param key: search key used
    :return:
    """
    if j is None:
        log.error("j is None, nothing to send")
        return

    if "tweets" in j:
        tweets = j['tweets']
        for tweet in tweets:
            log.debug("tweets is %s", json.dumps(tweet))

            # determine location
            location = "UnitedStates"
            if "cde" in tweet:
                if "author" in tweet['cde']:
                    if 'location' in tweet['cde']['author']:
                        if 'country' in tweet['cde']['author']['location']:
                            location = tweet['cde']['author']['location']['country']

            location = location.replace(" ", "")

            if "message" in tweet:
                if "body" in tweet['message']:
                    body = tweet['message']['body']
                    # check to see if body contains non-ASCII chars. if found, ignore it
                    try:
                        body.decode('ascii')
                    except UnicodeDecodeError:
                        log.warn("ignoring sending body %s", body)
                    except Exception as e:
                        log.warn("other exceptions: %s, ignore sending body, %s", e.message, json.dumps(body))
                    else:
                        # construct the body to send to the analyzer's /segments API
                        post_body = {"subject": key,
                                     "input_text": body,
                                     "location": location}
                        log.debug(json.dumps(post_body))

                        # send the body to the /segments API
                        r = requests.post('http://' + analyzer_host + '/segments',
                                          headers={'Content-type': 'application/json'},
                                          data=json.dumps(post_body))
                        if r.status_code != 201:
                            log.error("return code from segments API is %s, text is %s", r.status_code, r.text)
                        else:
                            log.info("sending data successfully to /segments")

                else:
                    continue


def check_required_vars(vcap_services, analyzer_host, id, pwd):
    if vcap_services is not None:
        log.info("VCAP_SERVICES is %s", vcap_services)
    else:
        log.error("Unable to obtain twitter insights VCAP_SERVICES, please ensure your service name is correct.")

    if analyzer_host is None:
        log.error("Please configure environment variable ANALYZER_HOST")
        sys.exit(1)

    if id is None or pwd is None:
        log.error("Unable to obtain twitter insights service id or pwd, please ensure your service name is correct.")
        sys.exit(1)


def process_twitter_data(id_pwd, key, post_time=None):
    """
    process twitter data and send to mood-ring tone analyzer service
    """
    j = get_twitter_data(id_pwd, key, post_time)
    send_json(j, key)


if __name__ == '__main__':
    vcap_services = os.getenv('VCAP_SERVICES')
    search_key = os.getenv('SEARCH_KEY', 'hacksummit')
    analyzer_host = os.getenv('ANALYZER_HOST')

    id = os.getenv('VCAP_SERVICES_TWITTERINSIGHTS_0_CREDENTIALS_USERNAME')
    pwd = os.getenv('VCAP_SERVICES_TWITTERINSIGHTS_0_CREDENTIALS_PASSWORD')
    check_required_vars(vcap_services, analyzer_host, id, pwd)

    log.info("attempt to send initial data from twitter")
    process_twitter_data(id + ":" + pwd, search_key)
    utc_now = datetime.datetime.utcnow()
    log.info("recorded last sent time window: " + utc_now.isoformat())
    loop_count = 0

    # Main control loop, continue sending data to mood-ring tone analyzer service every 5 minutes
    while True:
        try:
            # sleep 5 mins
            time.sleep(300)
            loop_count += 1
            log.info("sending %s count data from twitter", loop_count)

            process_twitter_data(id + ":" + pwd, search_key, utc_now)
            utc_now = datetime.datetime.utcnow()
        except Exception as e:
            # Want to catch these and print, but allow loop to continue
            log.error("Uncaught exception: %s", e.message)
