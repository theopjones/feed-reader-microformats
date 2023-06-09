'''
Copyright 2023 by Theodore Jones tjones2@fastmail.com 

This code is licensed under the The Parity Public License 7.0.0

As far as the law allows, this software comes as is, without any 
warranty or condition, and the contributor won't be liable to anyone
for any damages related to this software or this license, 
under any kind of legal claim.
'''

import concurrent.futures
import uuid
import datetime

import concurrent.futures
import datetime
import uuid

import feed

class FeedProcessor:
    def __init__(self, feed_collection, smtp_collection, email_collection, articles_collection):
        self.feed_collection = feed_collection
        self.smtp_collection = smtp_collection
        self.email_collection = email_collection
        self.articles_collection = articles_collection

    def process_all_feeds_and_send_email(self):
        feeds = self.get_all_feeds()
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(self.process_feed_and_send_email, feed) for feed in feeds]
            for future in concurrent.futures.as_completed(futures):
                try:
                    future.result()
                except Exception as e:
                    print(f'Error: {e}')

    def get_all_feeds(self):
        feed_output = list(self.feed_collection.find({}))
        feeds = []
        for feed in feed_output:
            feeds.append(feed['feed'])
        return feeds

    def process_feed_and_send_email(self, feed_url):
        feed_object = feed.Feed(feed_url, self.feed_collection)
        articles = feed_object.download_articles()
        if articles:
            articles.reverse()
            for article in articles:
                try:
                    article_id = self.add_article_to_database(article, feed_url)
                    self.send_email_for_article(article, article_id, feed_url)
                except Exception as e:
                    print(f"Error processing article {article['url']}: {e}")

    def add_article_to_database(self, article, feed_url):
        article_id = str(uuid.uuid4())
        title = article.get('title', '')
        content = article.get('content', '')
        posted_time = article.get('published_time', datetime.datetime.utcnow())
        self.articles_collection.insert_one({
            'id': article_id,
            'title': title,
            'content': content,
            'url': article['url'],
            'feed_name': feed_url,
            'date_added': datetime.datetime.utcnow(),
            'posted_date': posted_time,
        })
        return article_id

    def send_email_for_article(self, article, article_id, feed_url):
        article_url = article['url']
        raw_html_link = f'/article_raw_html?id={article_id}'
        # email_body = clean_html(article['content'] + f'<br><a href="{article_url}">View original post</a>' + f'<br>View raw HTML by going to {raw_html_link} on the server of your reader application.')
        # email = get_all_emails(email_collection)[0]
        # subject = f"New Article from {get_feed_name(feed, feed_collection)}"
        # if article['title']:
            # subject += f": {article['title']}"
        # send_email(email, subject, email_body, get_feed_name(feed,feed_collection) , smtp_collection, email_collection)

    def list_feeds_with_last_updated(self):
        feeds_output = list(self.feed_collection.find({}))
        feeds = []
        for feedfromdb in feeds_output:
            feed = [feedfromdb.pop('feed'), feedfromdb.pop('last_updated'), feedfromdb.pop('name')]
            probability = feedfromdb.get('probability')
            if probability is not None:
                feed.append(probability)
            feeds.append(feed)
        return feeds

    def list_feeds(self):
        feeds_output = list(self.feed_collection.find( {}))
        feeds = []
        for feedfromdb in feeds_output:
            feeds.append(feedfromdb.pop('feed'))
        return feeds
