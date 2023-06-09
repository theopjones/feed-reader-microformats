'''
Copyright 2023 by Theodore Jones tjones2@fastmail.com 

This code is licensed under the The Parity Public License 7.0.0

As far as the law allows, this software comes as is, without any 
warranty or condition, and the contributor won't be liable to anyone
for any damages related to this software or this license, 
under any kind of legal claim.
'''


import html_processing 
import datetime
import datetime
import html_processing
import mf2py
import requests


class Article:
    def __init__(self, entry, feed_url):
        self.entry = entry
        self.feed_url = feed_url

    def to_dict(self):
        response = requests.get(self.entry.link)
        if response.ok:
            parsed = self.get_microformats(response)
            if parsed:
                title, content = self.extract_title_and_content(parsed, self.entry.link)
                if title or content:
                    return {"title": title or "", "content": content or "", 'published_time': self.get_published_time(), 'url': self.entry.link}
        return None

    def get_published_time(self):
        return int(datetime.datetime(*self.entry.published_parsed[:6]).timestamp())

    def get_microformats(self, response):
        parsed = mf2py.parse(doc=response.text, url=response.url)
        if parsed['items']:
            return parsed
        return None

    def extract_title_and_content(self, parsed, link):
        title = parsed['items'][0]['properties'].get('name', [None])[0]
        if title not in [None, '']:
            title = html_processing.clean_html(title, link)
        content = html_processing.clean_html(parsed['items'][0]['properties'].get('content', [None])[0]["html"], link)
        return title, content