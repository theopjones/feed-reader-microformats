'''
Written in 2023 by Theodore Jones tjones2@fastmail.com 
To the extent possible under law, the author(s) have dedicated all copyright 
and related and neighboring rights to this software to the public domain worldwide. 
This software is distributed without any warranty. 
http://creativecommons.org/publicdomain/zero/1.0/.
'''

from flask import request, jsonify, Flask, current_app, make_response, render_template, redirect, url_for
from mongita import MongitaClientDisk
import argparse
import secrets
import os
from functools import wraps
import datetime
import threading
import time

import feedparser
import mf2py

import requests
from bs4 import BeautifulSoup

import smtplib

import concurrent.futures
import atexit
import threading

import hashlib
import uuid

import random

users_currently_authenticating = {}

def destroy_all_articles_in_db(articles_collection):
    articles_collection.delete_many({})


def send_email_about_new_articles_in_all_feeds(feed_collection, smtp_collection, email_collection,articles_collection):
    feeds = get_all_feeds(feed_collection)
    with concurrent.futures.ThreadPoolExecutor(max_workers=100) as executor:
        futures = [executor.submit(send_email_about_new_articles_in_feed, feed, feed_collection, smtp_collection, email_collection,articles_collection) for feed in feeds]
        for future in concurrent.futures.as_completed(futures):
            try:
                future.result()
            except Exception as e:
                print(f'Error: {e}')

def get_all_feeds(feed_collection):
    feed_output = list(feed_collection.find( {}))
    feeds = []
    for feed in feed_output:
        feeds.append(feed.pop('feed'))
    return feeds

def get_first_email(email_collection):
    email_output = list(email_collection.find( {}))
    email = email_output[0].pop('email')
    return email

def get_feed_name(feed_url,feed_collection):
    feed_output = list(feed_collection.find( {"feed" : feed_url} ))
    feed_name = feed_output[0].pop('name')
    return feed_name

def clean_html(html):
    soup = BeautifulSoup(html, 'html.parser')
     # Handle YouTube videos
    for iframe in soup.find_all('iframe'):
        if 'youtube.com' in iframe['src']:
            video_id = iframe['src'].split('/')[-1]
            iframe.replace_with(soup.new_tag('div', string=f'[YouTube video removed from content of website. Video ID: {video_id}]'))
    # Replace video tags with note
    for video in soup.find_all('video'):
        video.replace_with(soup.new_tag('div', string='[Video removed from content of website]'))
    # Replace audio tags with note
    for audio in soup.find_all('audio'):
        audio.replace_with(soup.new_tag('div', string='[Audio removed from content of website]'))
    # Replace SVG graphics with note
    for svg in soup.find_all('svg'):
        svg.replace_with(soup.new_tag('div', string='[SVG graphic removed from content of website]'))
    # Replace form elements with note
    for form in soup.find_all('form'):
        form.replace_with(soup.new_tag('div', string='[Form removed from content of website]'))
    # Remove unwanted tags
    for tag in soup(['script', 'style', 'iframe', 'embed', 'object', 'link']):
        tag.decompose()
    # Remove unwanted attributes
    for tag in soup():
        tag.attrs = {key: val for key, val in tag.attrs.items() if key not in ['class', 'id', 'style']}
    # Limit image size
    for img in soup.find_all('img'):
        img['style'] = 'max-width: 100%;'
    return str(soup)


def send_email_about_new_articles_in_feed(feed, feed_collection, smtp_collection, email_collection, articles_collection):
    feed_data = feed_collection.find_one({'feed': feed})
    if feed_data:
        articles = download_articles_in_feed_and_update_last_updated(feed, feed_collection)
        articles.reverse()
        if len(articles) > 0:
                for article in articles:
                    # Generate unique identifier for article
                    article_id = str(uuid.uuid4())
                    # Add article to database
                    articles_collection.insert_one({
                        'id': article_id,
                        'title': article['title'],
                        'content': article['content'],
                        'url': article['url'],
                        'feed_name': get_feed_name(feed, feed_collection),
                        'date_added': datetime.datetime.utcnow()
                    })
                    article_url = article['url']

                    # Add link to raw HTML page to email body
                    raw_html_link = f'/article_raw_html?id={article_id}'
                    email_body = clean_html(article['content'] + f'<br><a href="{article_url}">View original post</a>' + f'<br>View raw HTML by going to {raw_html_link} on the server of your reader application.')
                    # Send email
                    email = get_all_emails(email_collection)[0]
                    subject = f"New Article from {get_feed_name(feed, feed_collection)}"
                    if article['title']:
                        subject += f": {article['title']}"
                    send_email(email, subject, email_body, get_feed_name(feed,feed_collection) , smtp_collection, email_collection)

def send_email(email, subject, body, name, smtp_collection, email_collection):
    print( "Sending email to " + email + " with subject " + subject + " and body " + body)
    smtp_host, smtp_port, smtp_username, smtp_password = get_smtp_data(smtp_collection)
    server = smtplib.SMTP(smtp_host, smtp_port)
    server.starttls()
    server.login(smtp_username, smtp_password)
    sender_email = get_first_email(email_collection)
    message = f"From: {name} <{sender_email}>\nContent-Type: text/html\nSubject: {subject}\n\n{body}"
    message_bytes = message.encode('utf-8')
    server.sendmail(get_all_emails(email_collection)[0], email, message_bytes)
    server.quit()
    print( "Email sent to " + email + " with subject " + subject + " and body " + body)


def get_smtp_data(smtp_collection):
    smtp_output = list(smtp_collection.find( {}))
    smtp_host = smtp_output[0].pop('smtp_host')
    smtp_port = smtp_output[0].pop('smtp_port')
    smtp_username = smtp_output[0].pop('smtp_username')
    smtp_password = smtp_output[0].pop('smtp_password')
    return smtp_host,smtp_port,smtp_username,smtp_password

def is_smtp_data_set(smtp_collection):
    if len(list(smtp_collection.find( {}))) == 0:
        return False
    else:
        return True

def set_needed_smtp_vars_into_db(smtp_host,smtp_port,smtp_username,smtp_password,smtp_collection):
    smtp_collection.delete_many({})
    smtp_collection.insert_one({"smtp_host": smtp_host, "smtp_port": smtp_port, "smtp_username": smtp_username, "smtp_password": smtp_password})

def change_feed_last_updated(feed,feed_collection,new_date):
    feed_collection.update_one({"feed": feed}, {"$set": {"last_updated": new_date}})
    return True

def download_articles_in_feed_and_update_last_updated(feed,feed_collection):
    feed_data = feed_collection.find_one({'feed': feed})
    last_updated = get_feed_last_updated(feed,feed_collection)
    articles = download_articles_in_rss_feed(feed,last_updated,feed_data)
    update_feed_last_updated(feed,feed_collection)
    return articles

def get_feed_last_updated(feed,feed_collection):
    feed_output = list(feed_collection.find( {"feed" : feed} ))
    last_updated = feed_output[0].pop('last_updated')
    return last_updated

def update_feed_last_updated(feed,feed_collection):
    feed_collection.update_one({"feed": feed}, {"$set": {"last_updated": get_current_time()}})

def update_feed_probability(feed, feed_collection, probability):
    feed_collection.update_one({"feed": feed}, {"$set": {"probability": probability}})

def get_current_time():
    now = datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
    return now

def download_articles_in_rss_feed(feed_url,last_updated_string,feed_data):
    format_string = '%Y-%m-%d %H:%M:%S'
    last_updated = datetime.datetime.strptime(last_updated_string, format_string)
    output_feed_articles = []
    feed = feedparser.parse(feed_url)
    for entry in feed.entries:
        probability = float(feed_data.get('probability'))
        if probability is None or random.random() <= probability:
            published_time = datetime.datetime(*entry.published_parsed[:6])
            if last_updated is None or published_time > last_updated:
              response = requests.get(entry.link)
              if response.ok:
                    # Check if the page contains microformats
                   parsed = mf2py.parse(doc=response.text, url=response.url)
                   if parsed['items']:
                       # Extract the title and content of the item
                      title = parsed['items'][0]['properties'].get('name', [None])[0]
                      content = parsed['items'][0]['properties'].get('content', [None])[0]["html"]
                      output_feed_articles.append({"title": title, "content": content, 'published_time': published_time, 'url': entry.link})
    return output_feed_articles            


def get_rss_feed_url(url):
    # Send a GET request to the URL
    response = requests.get(url)

    # If the GET request is successful, the status code will be 200
    if response.ok:
        # Parse the response text with Beautiful Soup
        soup = BeautifulSoup(response.text, 'html.parser')

        # Find the <link> element with rel="alternate" and type="application/rss+xml"
        link = soup.find('link', {'rel': 'alternate', 'type': 'application/rss+xml'})

        # If the <link> element is found, return its href attribute (the RSS feed URL)
        if link:
            return link.get('href')
        else:
            return None
    else:
        return f"Failed to access {url}. Please check the URL."

def get_api_key(api_collection):
    api_key_output = list(api_collection.find( {}))
    api_key = api_key_output[0].pop('hash')
    return api_key

def destroy_all_api_key(api_collection):
    # Delete all API keys
    api_collection.delete_many({})

    # Generate and store a new API key
    return "Destroyed all API keys "


def remove_feed(feed,feed_collection):
    feed_collection.delete_one({"feed": feed})

def add_feed(feed, name, feed_collection, probability=None):
    feeddata = {"feed": feed, "last_updated": "1970-01-25 20:46:58", "name": name, "probability": probability}
    feed_collection.insert_one(feeddata)


def list_feeds_with_last_updated(feed_collection):
    feeds_output = list(feed_collection.find({}))
    feeds = []
    for feedfromdb in feeds_output:
        feed = [feedfromdb.pop('feed'), feedfromdb.pop('last_updated'), feedfromdb.pop('name')]
        probability = feedfromdb.get('probability')
        if probability is not None:
            feed.append(probability)
        feeds.append(feed)
    return feeds

def list_feeds(feed_collection):
    feeds_output = list(feed_collection.find( {}))
    print(feeds_output)
    feeds = []
    for feedfromdb in feeds_output:
        feeds.append(feedfromdb.pop('feed'))
    return feeds

def remove_email(email,email_collection):
    email_collection.delete_one({"email": email})

def add_email(email,email_collection):
    email_collection.insert_one({"email": email})

def is_email_in_emails_list(email,email_collection):
    if len(list(email_collection.find( {"email" : email} ))) == 0:
        return False
    else:
        return True

def get_all_emails(email_collection):
    emails_output = list(email_collection.find( {}))
    emails = []
    for emailfromdb in emails_output:
        emails.append(emailfromdb.pop('email'))
    return emails

def check_db_for_api_key(api_key,database_collection):
    if len(list(database_collection.find( {"key" : api_key} ))) == 0:
        return False
    else:
        return True

def check_db_for_email(email,database_collection):
    if len(list(database_collection.find( {"email" : email} ))) == 0:
        return False
    else:
        return True

def is_any_api_key_in_db(api_collection):
    if len(list(api_collection.find( {}))) == 0:
        return False
    else:
        return True

def is_any_email_in_db(email_collection):
    if len(list(email_collection.find( {}))) == 0:
        return False
    else:
        return True

def add_email_to_db(email,email_collection):
    email_collection.insert_one({"email": email})

def generate_api_key():
    return secrets.token_hex(32)

def add_api_key_to_db(api_key, user_id, api_collection):
    # Generate a new random salt
    salt = os.urandom(32)

    # Combine the salt and API key and hash them
    hash = hashlib.pbkdf2_hmac('sha256', api_key.encode('utf-8'), salt, 100000)

    # Store the salt, hash, and user_id in the database
    api_collection.insert_one({"salt": salt, "hash": hash, "user_id": user_id})

def generate_and_add_api_key_to_db(user_id, api_collection):
    generated_api_key = generate_api_key()
    add_api_key_to_db(generated_api_key, user_id, api_collection)
    print("The newly generated API Key is: " + generated_api_key)
    return generated_api_key

def destroy_api_key(user_id, api_collection):
    # Locate the record by user_id
    record = api_collection.find_one({"user_id": user_id})
    if record:
        # Delete the specific record from the collection
        api_collection.delete_one({"user_id": user_id})



def create_app(database_path, email, api_key, email_env, domain) :
    app = Flask(__name__)
    app.dbconnection = MongitaClientDisk(database_path)
    app.db = app.dbconnection['microformats-reader']
    app.api_collection = app.db.api_keys
    app.email_collection = app.db.email_addresses
    app.feed_collection = app.db.feeds
    app.smtp_collection = app.db.smtp
    app.articlescollection = app.db.articles
    app.domain = domain

    if email:
        if not check_db_for_email(email, app.email_collection):
            add_email_to_db(email, app.email_collection)
    if email_env:
        if not check_db_for_email(email_env, app.email_collection):
            add_email_to_db(email_env, app.email_collection)
    if not is_any_email_in_db(app.email_collection):
        exit("No email address found in the database. Please add one with the --email flag. An email can also be added with the email_for_microformats_reader environment variable.")      
    
    def some_long_task(app):
        while True:
            send_email_about_new_articles_in_all_feeds(app.feed_collection,app.smtp_collection,app.email_collection,app.articlescollection)
            print('Ran the task!')
            # This could be any long running task, just a delay as an example
            time.sleep(900)

    def run_continuously(app, interval=1):
        cease_continuous_run = threading.Event()

        class ScheduleThread(threading.Thread):
            def __init__(self, app):
                super().__init__()
                self.app = app

            def run(self):
                while not cease_continuous_run.is_set():
                    some_long_task(self.app)
                    time.sleep(interval)

        continuous_thread = ScheduleThread(app)
        continuous_thread.start()
        return cease_continuous_run

    # This will keep running even after Flask app has started
    stop_run_continuously = run_continuously(app, interval=900)
    # This will ensure the task stops if Flask stops
    atexit.register(stop_run_continuously.set)
    
    return app

def require_api_key(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        api_key = request.headers.get('X-API-Key')
        if api_key is None:
            api_key = request.cookies.get('api_key')

        # Get the user_id directly from the cookies
        user_id = request.cookies.get('user_id')

        if api_key is not None and user_id is not None:
            # Retrieve the salt and hash for this user
            record = current_app.api_collection.find_one({"user_id": user_id})
            if record is None:
                return jsonify({'error': 'Invalid API key.'}), 401

            # Hash the provided API key with the stored salt and compare it to the stored hash
            hash = hashlib.pbkdf2_hmac('sha256', api_key.encode('utf-8'), record['salt'], 100000)
            if hash != record['hash']:
                return jsonify({'error': 'Invalid API key.'}), 401
        else:
            return jsonify({'error': 'Invalid API key.'}), 401

        return f(*args, **kwargs)
    return decorated_function

    

parser = argparse.ArgumentParser(description='Start the app with a given database file.')
parser.add_argument('--database', required=True, help='The path to the database file.')
parser.add_argument('--domain', required=False, default='http://localhost', help='The path to the domain that the server is at.')
parser.add_argument('--email', required=False, help='The email address.')
parser.add_argument('--api_key', required=False, help='The API Key.')

'''
parser.add_argument('--host', required=False, help='The MongoDB host.')
parser.add_argument('--port', required=False, help='The MongoDB port.')
parser.add_argument('--username', required=False, help='The MongoDB username.')
parser.add_argument('--password', required=False, help='The MongoDB password.')
parser.add_argument('--database', required=False, help='The MongoDB database name.')
'''

args = parser.parse_args()

email_env = os.getenv('email_for_microformats_reader')

print(args.database)

app = create_app(args.database, args.email, args.api_key, email_env,args.domain)

@app.route('/api/send_magic_link', methods=['POST'])
def send_magic_link():
    email = request.form.get('email')
    if not email:
        return jsonify({'error': 'Email is required.'}), 400

    if is_email_in_emails_list(email,app.email_collection):
        token = secrets.token_hex(32)
        users_currently_authenticating[token] = email
        domainname = app.domain
        msg = 'Your Magic Link \n Click this link to login: ' + domainname + ':5000/api/authenticate?token=' + token
    
        send_email(email, "Magic Link", msg, "Login", app.smtp_collection, app.email_collection)
    else: 
        print("Email not found in database." + email)
    return jsonify({'message': 'Magic link sent.'}), 200

@app.route('/api/authenticate', methods=['GET'])
def authenticate():
    token = request.args.get('token')
    if not token or token not in users_currently_authenticating:
        return jsonify({'error': 'Invalid token.'}), 400

    # Create a unique user ID for the new user
    user_id = uuid.uuid4().hex

    api_key = generate_and_add_api_key_to_db(user_id, app.api_collection)
    del users_currently_authenticating[token]
    
    response = make_response(jsonify({'message': 'Authenticated successfully.', 'api_key': api_key}), 200)
    
    # Set the user_id and api_key as cookies
    response.set_cookie('user_id', user_id, httponly=True)
    response.set_cookie('api_key', api_key, httponly=True)
    
    return response


@app.route('/api/hello', methods=['GET'])
@require_api_key
def hello():
    return jsonify({'message': 'Hello World'}), 200

@app.route('/api/emails', methods=['GET'])
@require_api_key
def emails():
    return jsonify(get_all_emails(app.email_collection)), 200

@app.route('/api/add_email', methods=['POST'])
@require_api_key
def add_email_route():
    email = request.form.get('email')
    if email:
        add_email(email,app.email_collection)
        return jsonify({'message': 'Email added.'}), 200
    else:
        return jsonify({'error': 'No email address provided.'}), 400
@app.route('/api/remove_email', methods=['POST'])
@require_api_key
def remove_email_route():
    email = request.form.get('email')
    if email:
        remove_email(email,app.email_collection)
        return jsonify({'message': 'Email removed.'}), 200
    else:
        return jsonify({'error': 'No email address provided.'}), 400

@app.route('/api/feeds', methods=['GET'])
@require_api_key
def feeds():
    return jsonify(list_feeds(app.feed_collection)), 200

@app.route('/api/add_feed', methods=['POST'])
@require_api_key
def add_feed_route():
    feed = request.form.get('feed')
    feed_name = request.form.get('name')
    probability = request.form.get('probability')
    if feed:
        add_feed(feed, feed_name, app.feed_collection, probability)
        response_data = {'message': 'Feed added.'}
        if probability is not None:
            response_data['probability'] = probability
        return jsonify(response_data), 200
    else:
        return jsonify({'error': 'No feed provided.'}), 400

@app.route('/api/remove_feed', methods=['POST'])
@require_api_key
def remove_feed_route():
    feed = request.form.get('feed')
    if feed:
        remove_feed(feed,app.feed_collection)
        return jsonify({'message': 'Feed removed.'}), 200
    else:
        return jsonify({'error': 'No feed provided.'}), 400

@app.route('/api/get_api_key', methods=['GET'])
@require_api_key
def get_api_key_route():
    return jsonify({'api_key': get_api_key(app.api_collection)}), 200

@app.route('/api/destroy_all_api_key', methods=['GET'])
@require_api_key
def generate_api_key_route():
    api_key = destroy_all_api_key(app.api_collection)
    return jsonify({'message': 'API Key regenerated.', 'api_key' : api_key}), 200

@app.route('/api/is_any_email_in_db', methods=['GET'])
@require_api_key
def is_any_email_in_db_route():
    return jsonify({'is_any_email_in_db': is_any_email_in_db(app.email_collection)}), 200

@app.route('/api/get_rss_feed_url', methods=['POST'])
@require_api_key
def get_rss_feed_url_route():
    print(request.form.get)
    url = request.form.get('homepageurl')
    if url:
        return jsonify({'rss_feed_url': get_rss_feed_url(url)}), 200
    else:
        return jsonify({'error': 'No URL provided.'}), 400

@app.route('/api/download_articles_in_rss_feed', methods=['POST'])
@require_api_key
def download_articles_in_rss_feed_route():
    url = request.form.get('feedurl')
    lastupdated = request.form.get('lastupdated')
    if not lastupdated:
        lastupdated = None
    if url:
        download_articles_in_rss_feed(url, lastupdated)
        return jsonify(download_articles_in_rss_feed(url,lastupdated)), 200
    else:
        return jsonify({'error': 'No URL provided.'}), 400

@app.route('/api/get_current_time', methods=['GET'])
@require_api_key
def get_current_time_route():
    return jsonify({'current_time': get_current_time()}), 200

@app.route('/api/list_feeds_with_last_updated', methods=['GET'])
@require_api_key
def list_feeds_with_last_updated_route():
    return jsonify(list_feeds_with_last_updated(app.feed_collection)), 200

@app.route('/api/get_feed_last_updated', methods=['POST'])
@require_api_key
def get_feed_last_updated_route():
    url = request.form.get('feedurl')
    if url:
        return jsonify({'last_updated': get_feed_last_updated(url,app.feed_collection)}), 200
    else:
        return jsonify({'error': 'No URL provided.'}), 400

@app.route('/api/change_feed_last_updated', methods=['POST'])
@require_api_key
def change_feed_last_updated_route():
    url = request.form.get('feedurl')
    lastupdated = request.form.get('lastupdated')
    if url:
        change_feed_last_updated(url, app.feed_collection, lastupdated)
        return jsonify({'message': 'Feed last updated changed.'}), 200
    else:
        return jsonify({'error': 'No URL provided.'}), 400

@app.route('/api/download_articles_in_feed_and_update_last_updated', methods=['POST'])
@require_api_key
def download_articles_in_feed_and_update_last_updated_route():
    url = request.form.get('feedurl')
    if url:
        return jsonify(download_articles_in_feed_and_update_last_updated(url, app.feed_collection)), 200
    else:
        return jsonify({'error': 'No URL provided.'}), 400

@app.route('/api/set_needed_smtp_vars_into_db', methods=['POST'])
@require_api_key
def set_needed_smtp_vars_into_db_route():
    host = request.form.get('host')
    port = request.form.get('port')
    username = request.form.get('username')
    password = request.form.get('password')
    if host and port and username and password:
        set_needed_smtp_vars_into_db(host, port, username, password, app.smtp_collection)
        return jsonify({'message': 'SMTP variables set.'}), 200
    else:
        return jsonify({'error': 'Not all SMTP variables provided.'}), 400

@app.route('/api/is_smtp_data_set', methods=['GET'])
@require_api_key
def is_smtp_data_set_route():
    return jsonify({'is_smtp_data_set': is_smtp_data_set(app.smtp_collection)}), 200

@app.route('/api/send_test_email', methods=['POST'])
@require_api_key
def send_test_email_route():
    email = request.form.get('email')
    subject = request.form.get('subject')
    body = request.form.get('body')
    if email:
        send_email(email,subject,body,app.smtp_collection,app.email_collection)
        return jsonify({'message': 'Test email sent.'}), 200

@app.route('/api/send_email_about_new_articles_in_feed', methods=['POST'])
@require_api_key
def send_email_about_new_articles_in_feed_route():
    feedurl = request.form.get('feedurl')
    if feedurl:
        send_email_about_new_articles_in_feed(feedurl,app.feed_collection,app.smtp_collection,app.email_collection,app.articlescollection)
        return jsonify({'message': 'Email sent.'}), 200
    else:
        return jsonify({'error': 'No feed URL provided.'}), 400

@app.route('/api/get_smtp_data', methods=['GET'])
@require_api_key
def get_smtp_data_route():
    return jsonify(get_smtp_data(app.smtp_collection)), 200


@app.route('/api/send_email_about_new_articles_in_all_feeds', methods=['GET'])
@require_api_key
def send_email_about_new_articles_in_all_feeds_route():
    send_email_about_new_articles_in_all_feeds(app.feed_collection,app.smtp_collection,app.email_collection,app.articlescollection)
    return jsonify({'message': 'Email sent.'}), 200

@app.route('/api/has_valid_api_key', methods=['GET'])
@require_api_key
def has_valid_api_key_route():
    return jsonify({'has_valid_api_key': True}), 200

@app.route('/api/destroy_current_api_key', methods=['GET'])
@require_api_key
def destroy_current_api_key_route():
    user_id = request.cookies.get('user_id')  # assuming you've implemented this function
    if user_id is not None:
        destroy_api_key(user_id, app.api_collection)
        return jsonify({'message': 'Current API key destroyed.'}), 200
    else:
        return jsonify({'message': 'Failed to destroy API key. User not authenticated.'}), 401


@app.route('/api/create_new_api_key', methods=['GET'])
@require_api_key
def create_new_api_key_route():
    user_id = uuid.uuid4().hex  # Generate a new user ID
    new_api_key = generate_and_add_api_key_to_db(user_id, app.api_collection)  # Pass user ID as an argument to the function
    return jsonify({'message': 'New API key created.', 'api_key': new_api_key, 'user_id': user_id}), 200

@app.route('/article_raw_html')
@require_api_key
def article_raw_html():
    article_id = request.args.get('id')
    article = app.articlescollection.find_one({'id': article_id})
    if article:
        return f'<pre>{article["content"]}</pre>'
    else:
        return 'Article not found'

@app.route('/api/destroy_all_articles_in_db', methods=['GET'])
@require_api_key
def destroy_all_articles_in_db_route():
    destroy_all_articles_in_db(app.articlescollection)
    return jsonify({'message': 'All articles destroyed.'}), 200

@app.route('/api/update_feed_probability', methods=['POST'])
@require_api_key
def update_feed_probability_route():
    feedurl = request.form.get('feedurl')
    probability = request.form.get('probability')
    if feedurl and probability:
        update_feed_probability(feedurl, app.feed_collection, probability)
        return jsonify({'message': 'Feed probability updated.'}), 200
    else:
        return jsonify({'error': 'No feed URL or probability provided.'}), 400

#FRONTEND ROUTES

@app.route('/')
def homepage():
    return redirect(url_for('manage_feeds_route'))

@app.route('/login')
def login_route():
    return render_template('login.html')

@app.route('/manage_feeds')
def manage_feeds_route():
    return render_template('manage_feeds.html')

@app.route('/settings')
def settings_route():
    return render_template('settings.html')

@app.route('/logout', methods=['GET'])
def logout_route():
    return render_template('logout.html')

if __name__ == '__main__':
    app.run()
