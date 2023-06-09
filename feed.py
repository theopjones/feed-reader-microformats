'''
Copyright 2023 by Theodore Jones tjones2@fastmail.com 

This code is licensed under the The Parity Public License 7.0.0

As far as the law allows, this software comes as is, without any 
warranty or condition, and the contributor won't be liable to anyone
for any damages related to this software or this license, 
under any kind of legal claim.
'''

import feed_article
import html_processing 
import datetime
import datetime
import feedparser
import html_processing
import random

class Feed:
    def __init__(self, feed_url, feed_collection):
        self.feed_url = feed_url
        self.feed_collection = feed_collection
        self.feed_data = self.feed_collection.find_one({'feed': self.feed_url})
        self.last_updated = self.get_feed_last_updated()

    def get_feed_last_updated(self):
        if self.feed_data:
            return datetime.datetime.strptime(self.feed_data['last_updated'], '%Y-%m-%d %H:%M:%S')
        else:
            return None

    def download_articles(self):
        try:
            cleaned_feed = html_processing.remove_all_georss(self.feed_url)
            feed = feedparser.parse(cleaned_feed)
            print(feed)
        except Exception as e:
            print(f"Error parsing RSS feed: {e}")
            return []

        try:
            articles = self.download_articles_in_feed_and_update_last_updated(feed)
        except Exception as e:
            print(f"Error downloading articles for feed {self.feed_url}: {e}")
            return []

        return articles

    def download_articles_in_feed_and_update_last_updated(self, feed):
        last_updated = self.last_updated
        output_feed_articles = []

        for entry in feed.entries:
            try:
                probability = float(self.feed_data.get('probability'))
                if probability is None or random.random() <= probability:
                    published_time = datetime.datetime(*entry.published_parsed[:6])
                    if last_updated is None or published_time > last_updated:
                        article = feed_article.Article(entry, self.feed_url)
                        if article:
                            output_feed_articles.append(article.to_dict())
            except Exception as e:
                print(f"Error processing RSS feed entry: {e}")

        self.update_feed_last_updated()
        return output_feed_articles

    def update_feed_last_updated(self):
        self.feed_collection.update_one({"feed": self.feed_url}, {"$set": {"last_updated": datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}})
