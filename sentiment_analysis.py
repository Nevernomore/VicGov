import tweepy
from textblob import TextBlob
import pymongo
import unicodedata

class Tweets_in_Mongo():
    def __init__(self):
        '''
             Connect to Mongodb
        '''
        self.myclient = pymongo.MongoClient("mongodb://localhost:27017/")

        self.mydb = self.myclient["tweets"]
        self.mycol = self.mydb["YarraCouncil"]

    def get_tweet_count(self):
        return self.mycol.estimated_document_count()

    def get_tweets_sentiment(self, tweet):
        '''
        Utility function to classify sentiment of passed tweet
        using textblob's sentiment method
        '''
        # create TextBlob object of passed tweet text
        analysis = TextBlob(tweet)
        # set sentiment
        return analysis.sentiment.polarity

    def get_tweets(self):
        '''
        Main function to fetch tweets from Mongodb
        :return: tweets list
        '''
        tweets = []
        try :
            for tweet in self.mycol.find({},{ "_id": 0,"text": 1}):
                tweets.append(tweet)
            return tweets

        except :
            print("Error: Get tweets failed!")



def main():
    me = Tweets_in_Mongo()
    tweets = me.get_tweets()   #{u'text': u'I have asked all these questions.'}

        # if isinstance(tweet, basestring):
        #     a = tweet["text"].encode('ascii', 'ignore')
        #     print (a)
        #
        # else:
        #     a = tweet["text"]

    # for tweet in tweets:
    #     print((unicodedata.normalize('NFKD', tweet["text"]).encode('ascii', 'ignore'))

    positive = 0
    negative = 0
    neutral = 0
    count_num = me.get_tweet_count()
    for tweet in tweets:
        # print ("positive: %d" % positive)
        # print ("negative: %d" % negative)
        # print ("neutral: %d" % neutral)

        if me.get_tweets_sentiment(str(tweet["text"]))>0:
            positive = positive + 1
        elif me.get_tweets_sentiment(str(tweet["text"]))==0:
            neutral = neutral + 1
        else:
            negative = negative +1

        # if me.get_tweets_sentiment((tweet["text"]).encode()) > 0:
        #     positive = positive + 1
        # elif me.get_tweets_sentiment((tweet["text"]).encode()) == 0:
        #     neutral = neutral + 1
        # else:
        #     negative = negative + 1
    # percentage of positive tweets
    print("Positive tweets percentage: %.2f%%" % (100 * positive / count_num))
    # percentage of negative tweets
    print("Negative tweets percentage: %.2f%%" % (100 * negative / count_num))
    # percentage of neutral tweets
    print("Neutral tweets percentage: %.2f%%" % (100 * neutral / count_num))


if __name__ == "__main__":
    main()