'''
MIT License
Copyright (c) 2019 Luca Hammer
Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:
The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.
THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
'''

'''
Example script to collect old Tweets with the Twitter Premium Search API
Article: https://lucahammer.com/?p=350
To use this script, change the constants (UPPERCASE variables) to your needs,
and run it. For example in your CLI by executing: "python premiumapi.py".
Find your app credentials here: https://developer.twitter.com/en/apps
Find your dev environment label here: https://developer.twitter.com/en/account/environments
'''

from auth import *
import json
from searchtweets import load_credentials, gen_rule_payload, ResultStream
import yaml
from textblob import TextBlob
import re
import pymongo


def read_stream(apiscope, label):
    API_KEY = api_key
    API_SECRET_KEY = api_secret_key
    DEV_ENVIRONMENT_LABEL = label
    API_SCOPE = apiscope  # 'fullarchive'  # 'fullarchive' for full archive, '30day' for last 31 days

    SEARCH_QUERY = 'delays, @WestMidRailway OR @NetworkRailBHM OR @networkrail'
    RESULTS_PER_CALL = 100  # 100 for sandbox, 500 for paid tiers
    TO_DATE = '2021-01-30'  # format YYYY-MM-DD HH:MM (hour and minutes optional)
    FROM_DATE = '2021-01-01'  # format YYYY-MM-DD HH:MM (hour and minutes optional)

    MAX_RESULTS = 10000  # Number of Tweets you want to collect

    # --------------------------- STOP -------------------------------#
    # Don't edit anything below, if you don't know what you are doing.
    # --------------------------- STOP -------------------------------#

    config = dict(
        search_tweets_api=dict(
            account_type='premium',
            endpoint=f"https://api.twitter.com/1.1/tweets/search/{API_SCOPE}/{DEV_ENVIRONMENT_LABEL}.json",
            consumer_key=API_KEY,
            consumer_secret=API_SECRET_KEY
        )
    )

    with open('twitter_keys.yaml', 'w') as config_file:
        yaml.dump(config, config_file, default_flow_style=False)

    premium_search_args = load_credentials("twitter_keys.yaml",
                                           yaml_key="search_tweets_api",
                                           env_overwrite=False)

    rule = gen_rule_payload(SEARCH_QUERY,
                            results_per_call=RESULTS_PER_CALL,
                            from_date=FROM_DATE,
                            to_date=TO_DATE
                            )

    rs = ResultStream(rule_payload=rule,
                      max_results=MAX_RESULTS,
                      **premium_search_args)

    return rs


class WritetoMongo:
    def __init__(self):
        self.mongostr = 'mongodb://localhost:27017'
        self.mclient = pymongo.MongoClient(self.mongostr)
        self.db = self.mclient.tweets.thirty3

    def insert_data(self, mess):
        self.db.insert_one(mess)


class SentimentAnalysis:

    def clean_tweet(self, tweet):
        return ' '.join(re.sub('([^0-9A-Za-z \t])|(\\w+:\\/\\/\\S+)', '', tweet).split())

    def get_tweet_sentiment(self, tweet):

        # Utility function to classify sentiment of passed tweet
        # using textblob's sentiment method

        # create TextBlob object of passed tweet text
        analysis = TextBlob(self.clean_tweet(tweet))
        # set sentiment
        if analysis.sentiment.polarity > 0:
            return 'positive'
        elif analysis.sentiment.polarity == 0:
            return 'neutral'
        else:
            return 'negative'


def positive_negative_printer(tweets):
    # picking positive tweets from tweets
    ptweets = [tweet for tweet in tweets if tweet['sentiment'] == 'positive']
    # percentage of positive tweets
    print("Positive tweets percentage: {} %".format(100 * len(ptweets) / len(tweets)))
    # picking negative tweets from tweets
    ntweets = [tweet for tweet in tweets if tweet['sentiment'] == 'negative']
    # percentage of negative tweets
    print("Negative tweets percentage: {} %".format(100 * len(ntweets) / len(tweets)))
    # percentage of neutral tweets
    print(
        "Neutral tweets percentage: {} %".format(100 * (len(tweets) - (len(ntweets) + len(ptweets))) / len(tweets)))

    # printing first 5 positive tweets
    print("\n\nPositive tweets:")
    for tweet in ptweets[:10]:
        print(tweet['text'])

    # printing first 5 negative tweets
    print("\n\nNegative tweets:")
    for tweet in ntweets[:10]:
        print(tweet['text'])


def main():
    sa: SentimentAnalysis = SentimentAnalysis()
    tweets = []
    wmon: WritetoMongo = WritetoMongo()
    rs = read_stream('30day', 'i6example')

    for tweet in rs.stream():

        parsed_tweet = {}
        parsed_tweet['text'] = tweet['text']
        parsed_tweet['sentiment'] = sa.get_tweet_sentiment(tweet['text'])
        tweet['sentiment'] = sa.get_tweet_sentiment(tweet['text'])
        parsed_tweet['created_at'] = tweet['created_at']
        wmon.insert_data(tweet)

        if tweet['retweet_count'] > 0:
            if parsed_tweet not in tweets:
                tweets.append(parsed_tweet)
        else:
            tweets.append(parsed_tweet)

    positive_negative_printer(tweets)

    # FILENAME = 'twitter_sentiment_analysis_new.jsonl'  # Where the Tweets should be saved
    # # Script prints an update to the CLI every time it collected another X Tweets
    # PRINT_AFTER_X = 1000
    #
    # with open(FILENAME, 'a', encoding='utf-8') as f:
    #     n = 0
    #     for tweet in tweets:
    #         n += 1
    #         if n % PRINT_AFTER_X == 0:
    #             print('{0}: {1}'.format(str(n), tweet['created_at']))
    #         json.dump(tweet, f)
    #         f.write('\n')
    # print('done')


if __name__ == '__main__':
    main()
