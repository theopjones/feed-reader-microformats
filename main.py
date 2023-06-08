'''
Copyright 2023 by Theodore Jones tjones2@fastmail.com 

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
'''

from flask import request, jsonify, Flask, current_app, make_response, render_template, redirect, url_for
from mongita import MongitaClientDisk
from urllib.parse import urlparse
import argparse
import secrets
import os
from functools import wraps
import datetime
import threading
import time
import sys

import feedparser
import mf2py

import requests
from bs4 import BeautifulSoup

import smtplib

import atexit
import threading

import hashlib
import uuid

import random

from waitress import serve

from html_sanitizer import Sanitizer
import bleach

import feeds

users_currently_authenticating = {}

def destroy_all_articles_in_db(articles_collection):
    articles_collection.delete_many({})

def get_first_email(email_collection):
    email_output = list(email_collection.find( {}))
    email = email_output[0].pop('email')
    return email

import bleach
from bs4 import BeautifulSoup

def send_email(email, subject, body, name, smtp_collection, email_collection):
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

def get_common_name_of_feed(feed,feed_collection):
    feed_output = list(feed_collection.find( {"feed" : feed} ))
    common_name = feed_output[0].pop('name')
    return common_name

def update_feed_probability(feed, feed_collection, probability):
    feed_collection.update_one({"feed": feed}, {"$set": {"probability": probability}})

def get_current_time():
    now = datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
    return now


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

def get_domain_from_db(domaincollection):
    #check for the case where there is no domain in the db
    if len(list(domaincollection.find( {}))) == 0:
        return None
    domain_output = list(domaincollection.find( {}))
    domain = domain_output[0].pop('domain')
    return domain

def initial_setup_check(app):
    if not is_any_email_in_db(app.email_collection):
        return False
    return True

def is_any_smtp_in_db(smtp_collection):
    if len(list(smtp_collection.find( {}))) == 0:
        return False
    else:
        return True

def add_smtp_to_db(smtp_host,smtp_port,smtp_user,smtp_password,smtp_collection):
    smtp_collection.insert_one({"smtp_host": smtp_host, "smtp_port": smtp_port, "smtp_username": smtp_user, "smtp_password": smtp_password})

def is_any_domain_in_db(domaincollection):
    if len(list(domaincollection.find( {}))) == 0:
        return False
    else:
        return True

def change_domain(domain, domaincollection):
    domaincollection.delete_many({})
    domaincollection.insert_one({"domain": domain})

def add_domain_to_db(domain, domaincollection):
    domaincollection.insert_one({"domain": domain})

def do_initial_setup_domain_email_api_key_smtp_load_initial_data_in_db(email, smtp_host, smtp_port, smtp_user, smtp_password, domain, api_collection, email_collection, smtp_collection, feed_collection, articlescollection, domaincollection):
    if not is_any_email_in_db(email_collection):
        add_email_to_db(email, email_collection)
    if not is_any_smtp_in_db(smtp_collection):
        add_smtp_to_db(smtp_host,smtp_port,smtp_user,smtp_password,smtp_collection)
    if not is_any_domain_in_db(domaincollection):
        add_domain_to_db(domain, domaincollection)
    if not is_any_email_in_db(email_collection):
        add_email_to_db(email, email_collection)
    if not is_any_smtp_in_db(feed_collection):
        add_smtp_to_db(smtp_host,smtp_port,smtp_user,smtp_password,smtp_collection)

def command_line_initial_setup_prompting_user_for_data():
    email = input("Please enter your email address: ")
    smtp_host = input("Please enter your SMTP host: ")
    smtp_port = input("Please enter your SMTP port: ")
    smtp_user = input("Please enter your SMTP username: ")
    smtp_password = input("Please enter your SMTP password: ")
    domain = input("Please enter your domain name: ")
    return email, smtp_host, smtp_port, smtp_user, smtp_password, domain

def is_initial_setup_info_in_env():
    if os.getenv('EMAIL') is None or os.getenv('SMTP_HOST') is None or os.getenv('SMTP_PORT') is None or os.getenv('SMTP_USER') is None or os.getenv('SMTP_PASSWORD') is None or os.getenv('DOMAIN') is None:
        return False
    else:
        return True

def get_initial_setup_info_from_env():
    email = os.getenv('EMAIL')
    smtp_host = os.getenv('SMTP_HOST')
    smtp_port = os.getenv('SMTP_PORT')
    smtp_user = os.getenv('SMTP_USER')
    smtp_password = os.getenv('SMTP_PASSWORD')
    domain = os.getenv('DOMAIN')
    return email, smtp_host, smtp_port, smtp_user, smtp_password, domain    

def command_line_initial_setup(app):
    
    if not is_initial_setup_info_in_env():
        email, smtp_host, smtp_port, smtp_user, smtp_password, domain = command_line_initial_setup_prompting_user_for_data()
    else:
        email, smtp_host, smtp_port, smtp_user, smtp_password, domain = get_initial_setup_info_from_env()
    
    db = app.db
    api_collection = db.api_keys
    email_collection = db.email_addresses
    smtp_collection = db.smtp
    feed_collection = db.feeds
    articlescollection = db.articles
    domaincollection = db.domain
    do_initial_setup_domain_email_api_key_smtp_load_initial_data_in_db(email, smtp_host, smtp_port, smtp_user, smtp_password, domain, api_collection, email_collection, smtp_collection, feed_collection, articlescollection, domaincollection)

def get_some_posts_based_on_starting_post_and_numb_of_posts(articles_collection, starting_post, numb_of_posts):
    posts = []
    # Search database for posts based on starting post and numb of posts
    # Query DB for posts based on post date. Sort by post date descending
    # Use articles collection, not feed collection, 'posted_date' contains the time
    # the post was made. startin_post is the number of posts to skip, numb_of_posts is the number of posts to return

    # Get the numb_of_posts posts starting from the starting_post
    for post in articles_collection.find().sort('posted_date', -1).skip(starting_post).limit(numb_of_posts):
        # Convert ObjectId to string
        post['_id'] = str(post['_id'])
        posts.append(post)

    return posts

def some_long_task(app):
    # Get the current Unix time
    current_time = int(time.time())

    # Check if a file with a similar name already exists
    for filename in os.listdir('/tmp'):
        if filename.startswith('check_if_feed_downloadtask_is_loaded_'):
            file_time = int(filename.split('_')[-1])
            if abs(current_time - file_time) < 300:
                print('Task already loaded, skipping...')
                return

    # Create a file with the current Unix time in the name
    filename = f'check_if_feed_downloadtask_is_loaded_{current_time}'
    with open(f'/tmp/{filename}', 'w') as f:
        f.write('')

    # Run the task
    while True:
        process_feeds = feeds.FeedProcessor(app.feed_collection, app.smtp_collection, app.email_collection, app.articles_collection)
        process_feeds.process_all_feeds_and_send_email()
        print('Ran the task!')
        # This could be any long running task, just a delay as an example
        time.sleep(900)

def create_app() :

    app = Flask(__name__)
    app.secret_key = os.urandom(24)
    database_path = os.getenv('DATABASE_PATH')
    app.dbconnection = MongitaClientDisk(database_path)
    app.db = app.dbconnection['microformats-reader']
    app.api_collection = app.db.api_keys
    app.email_collection = app.db.email_addresses
    app.feed_collection = app.db.feeds
    app.smtp_collection = app.db.smtp
    app.articlescollection = app.db.articles
    app.domaincollection = app.db.domain

    if not initial_setup_check(app):
        command_line_initial_setup(app)     
    
    if not is_any_domain_in_db(app.domaincollection):
        add_domain_to_db("localhost", app.domaincollection)

    app.domain = get_domain_from_db(app.domaincollection)
    
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

def get_db_path_from_env():
    if os.getenv('DATABASE_PATH') is None:
        return 'microformats-reader.db'
    else:
        return os.getenv('DATABASE_PATH')

app = create_app()

@app.route('/api/login', methods=['POST'])
def login():
    username = request.form.get('username')
    password = request.form.get('password')
    if not username or not password:
        return jsonify({'error': 'Username and password are required.'}), 400

    if username == os.environ.get('APP_USERNAME') and password == os.environ.get('APP_PASSWORD'):
        # Create a unique user ID for the new user
        user_id = uuid.uuid4().hex

        api_key = generate_and_add_api_key_to_db(user_id, app.api_collection)
        
        response = make_response(jsonify({'message': 'Authenticated successfully.', 'api_key': api_key}), 200)
        
        # Set the user_id and api_key as cookies
        response.set_cookie('user_id', user_id, httponly=True)
        response.set_cookie('api_key', api_key, httponly=True)
        
        return response
    else:
        return jsonify({'error': 'Invalid username or password.'}), 401


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
    feeds_object = feeds.FeedProcessor(app.feed_collection, app.smtp_collection, app.email_collection, app.articles_collection)
    return jsonify(feeds_object.list_feeds()), 200

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
    feeds_object = feeds.FeedProcessor(app.feed_collection, app.smtp_collection, app.email_collection, app.articles_collection)
    return jsonify(feeds_object.list_feeds_with_last_updated()), 200

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
        feeds.send_email_about_new_articles_in_feed(url, app.feed_collection, app.smtp_collection, app.email_collection, app.articlescollection)
        return jsonify("success"), 200
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
        feeds.send_email_about_new_articles_in_feed(feedurl,app.feed_collection,app.smtp_collection,app.email_collection,app.articlescollection)
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
    feeds.send_email_about_new_articles_in_all_feeds(app.feed_collection,app.smtp_collection,app.email_collection,app.articlescollection)
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

@app.route('/api/get_posts_bt_start_and_limit', methods=['GET'])
@require_api_key
def get_posts_bt_start_and_limit_route():
    # Wrapper arround get_some_posts_based_on_starting_post_and_numb_of_posts(articles_collection, starting_post, numb_of_posts)
    start = int(request.args.get('start'))
    limit = int(request.args.get('limit'))
    posts = get_some_posts_based_on_starting_post_and_numb_of_posts(app.articlescollection, start, limit)
    return jsonify(posts), 200
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

@app.route('/scroll', methods=['GET'])
def scroll_route():
    return render_template('scroll.html')


background_thread = threading.Thread(target=some_long_task, args=(app,))
background_thread.start()
serve(app, port=5000,threads=2)