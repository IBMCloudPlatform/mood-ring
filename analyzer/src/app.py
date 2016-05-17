import os, json, requests
from flask import Flask, Response, abort, request
from elasticsearch import Elasticsearch, exceptions
from datetime import datetime
import logging
from logging import StreamHandler
import urllib3

urllib3.disable_warnings()
# Define the base logger
logging.getLogger("analyzer").setLevel(logging.DEBUG)
log = logging.getLogger("analyzer")
stream_handler = StreamHandler()
stream_formatter = logging.Formatter('[%(asctime)s] [%(thread)d] [%(module)s : %(lineno)d] [%(levelname)s] %(message)s')
stream_handler.setFormatter(stream_formatter)
log.addHandler(stream_handler)

# Flask config
app = Flask(__name__, static_url_path='')
app.config['PROPAGATE_EXCEPTIONS'] = True

# other global variables
ELASTICSEARCH_EP = os.environ['ELASTICSEARCH_EP']
ES = Elasticsearch([ELASTICSEARCH_EP], verify_certs=False)
tone_analyzer_ep = None

def score_to_percent(score):
    return int(score*100) if score is not None else 0


def get_scores(tone_doc):
    anger_score = disgust_score = fear_score = joy_score = sadness_score = None
    for tone_category in tone_doc['document_tone']['tone_categories']:
        if tone_category['category_id'] == 'emotion_tone':
            for tone in tone_category['tones']:
                if tone['tone_id'] == 'anger':
                    anger_score = tone['score']
                elif tone['tone_id'] == 'disgust':
                    disgust_score = tone['score']
                elif tone['tone_id'] == 'fear':
                    fear_score = tone['score']
                elif tone['tone_id'] == 'joy':
                    joy_score = tone['score']
                elif tone['tone_id'] == 'sadness':
                    sadness_score = tone['score']
            break
    return score_to_percent(anger_score), score_to_percent(disgust_score), score_to_percent(fear_score), \
        score_to_percent(joy_score), score_to_percent(sadness_score)


def get_tone(tone_doc):
    """
    This function tries to compute, from "tone analyzer" data, a reasonable equivalent of
    what "sentiment analyzer" produces, i.e., a value of positive, negative, or neutral,
    and a corresponding numeric score.
    """
    anger_score, disgust_score, fear_score, joy_score, sadness_score = get_scores(tone_doc)
    max_neg_score = sorted([anger_score, disgust_score, fear_score, sadness_score])[3]
    tone_score = joy_score - max_neg_score
    delta = abs(tone_score)
    if delta <= 15:
        tone = "neutral"
    elif joy_score > max_neg_score:
        tone = "positive"
    else:
        tone = "negative"
    return tone, tone_score


def add_to_index(subject, location, input_text, tone_doc, index, timestamp=None):
    """
    this method adds the analyzed tone information to Elastic search
    """
    tone, tone_score = get_tone(tone_doc)
    es_doc = {
        "subject": subject,
        "location": location,
        "input": input_text,
        "tone": tone,
        "tone_score": tone_score,
        "timestamp": timestamp if timestamp else datetime.utcnow()
    }
    res = ES.index(index=index, doc_type='emotion_tone', body=es_doc)
    #print(res['created'])    
    response = Response(json.dumps(res))
    response.headers['Content-Type'] = 'application/json'
    response.status_code = 201 if res['created'] else 400
    if response.status_code != 201:
        log.error("FAILED add to index: '%s'", json.dumps(res))
    return response


def analyze_tone(input_text):
    r = requests.post(tone_analyzer_ep, headers={'Content-type': 'text/plain'}, data=input_text)
    if r.status_code != 200: 
        log.error("FAILED analyze tone: '%s', msg: '%s'", input_text, r.text)
        return None
    return r.json()

'''
 This is the analyzer API that accepts POST data as describes below:
 POST http://localhost:5000/segments body=\
 {
     "subject": "Hacksummit",
     "input_text": "hello everyone ...",
     "timestamp": "2016-02-10T13:40:20.405000", (optional)
     "location": "Canada" (optional)
 }
'''
@app.route('/segments', methods=['POST'])
def add_segment():
    if not request.json or not 'subject' in request.json or not 'input_text' in request.json:
        log.error("add segment bad body: '%s'", request.data)
        abort(400)

    subject = request.json['subject'] 
    input_text = request.json['input_text']
    timestamp = request.json.get('timestamp') # optional (defaults to now)
    location = request.json.get('location', 'UNKNOWN') # optional
    
    tone_doc = analyze_tone(input_text)

    return add_to_index(subject, location, input_text, tone_doc, "tone-analysis", timestamp)

if __name__ == '__main__':
    PORT = os.getenv('VCAP_APP_PORT', '5000')
    vcap_services = os.getenv('VCAP_SERVICES')
    id = os.getenv('VCAP_SERVICES_TONE_ANALYZER_0_CREDENTIALS_USERNAME')
    pwd = os.getenv('VCAP_SERVICES_TONE_ANALYZER_0_CREDENTIALS_PASSWORD')
    url = os.getenv('VCAP_SERVICES_TONE_ANALYZER_0_CREDENTIALS_URL')
    short_url = url[8:]
    tone_analyzer_ep = "https://" + id + ":" + pwd + "@" + short_url + "/v3/tone?version=2016-02-11"

    log.info("Starting analyzer tone_analyzer_ep: %s ELASTICSEARCH_EP: %s", tone_analyzer_ep, ELASTICSEARCH_EP)
    app.run(host='0.0.0.0', port=int(PORT))
