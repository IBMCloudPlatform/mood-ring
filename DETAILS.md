## Analyzer service:

Code resides in the *analyzer* folder.

The Analyzer is a Python Flask server providing a REST API that accepts input text, which is analyzed using the Watson Tone
analyzer service. The analysis result, along with the original text, is then stored in an ElasticSearch index.
The ES index where the analyzed data is added can optionally be specified in the request body. Index "tone-analysis" is used by default.

To analyze a segment of text, POST to /segments a JSON message with the following structure:

```
{
    "subject": "My Subject",
    "input_text": "hello everyone ...",
    "timestamp": "2016-02-10T13:40:20.405000", (optional - default is now)
    "index": "my-index", (optional - default is "tone-analysis")
    "location": "Canada" (optional - default is "UNKNOWN")
}
```

For example, to analyze some text and add it to the index named 'my-index', POST a message something like this where ANALYZER_PUBLIC_IP is the public ip binded to the analyzer container:

```bash
curl -XPOST http://{ANALYZER_PUBLIC_IP}/segments \
  -H 'Content-Type: application/json' \
  -d '{"subject": "My Subject", "input_text": "hello there, this is my message.", "index": "my-index"}'
```

If everything worked as expected you should see a reply like this:

```bash
{"_type": "emotion_tone", "_id": "AVL6sPDNvyeHo3MnjUNH", "created": true, "_version": 1, "_index": "my-index"}
```

To query and view the analyzed data, refer to [Kibana service](#kibana-service), below.

If the Analyzer service is up, but the POST isn't working, the configured ElasticSearch instance may be the problem.

## Kibana service:
A Kibana endpoint configured to the same ES used by the Analyzer microservice, described above.
The ElasticSearch index entries added by the Analyzer have the following structure:

```
{
    "subject": "hacksummit",
    "input": "Registered for #hacksummit, a virtual event of top developers. Check it out!  https://t.co/YlKCdFSNx3",
    "location": "UnitedStates",
    "timestamp": "2016-02-19T16:51:51.229633",
    "tone": "positive",
    "tone_score": 33
}
```

The first 4 fields ("subject", "input", "location", "timestamp") are those provided in the Analyzer request. The rest are produced from
Watson Tone analyzer results.

The "tone" and "tone_score" fields are also computed (from the 5 emotions such as "joy", "anger", "fear", "disgust", and "sadness") values, intended to capture the overall tone of the text:
"tone" is one of "positive", "negative", or "neutral" and "tone_score" is a value between -100 (very negative) and +100 (very positive).
Essentially, this is our poor mans attempt at using Tone analyzer as a replacement for Watson Sentiment analyzer, which generates similar
stuff.

The current algorithm we're using for "tone" and "tone_score" is as follows:

```python
def get_tone(anger_score, disgust_score, fear_score, joy_score, sadness_score):
    max_neg_score = sorted([anger_score, disgust_score, fear_score, sadness_score])[3]
    tone_score = joy_score - max_neg_score
    delta = abs(tone_score)
    if  delta <= 15:
        tone = "neutral"
    elif joy_score > max_neg_score:
        tone = "positive"
    else:
        tone = "negative"
    return tone, tone_score
```

