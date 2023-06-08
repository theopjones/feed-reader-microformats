
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
                if title:
                    return {"title": title, "content": content, 'published_time': self.get_published_time(), 'url': self.entry.link}
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