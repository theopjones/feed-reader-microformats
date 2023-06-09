'''
Copyright 2023 by Theodore Jones tjones2@fastmail.com 

This code is licensed under the The Parity Public License 7.0.0

As far as the law allows, this software comes as is, without any 
warranty or condition, and the contributor won't be liable to anyone
for any damages related to this software or this license, 
under any kind of legal claim.
'''

from urllib.parse import urlparse
import requests
from bs4 import BeautifulSoup
import bleach


def remove_all_georss(url):
    # Request the raw RSS feed
    response = requests.get(url)

    # Parse the feed with BeautifulSoup
    soup = BeautifulSoup(response.content, 'xml')

    # List of GeoRSS elements to remove
    georss_elements_list = ['georss:point', 'georss:line', 'georss:polygon', 
                            'georss:box', 'georss:where', 'georss:elev', 
                            'georss:floor', 'georss:radius']

    for georss_element in georss_elements_list:
        # Find all elements of this type
        elements = soup.findAll(georss_element)

        # Remove each element
        for element in elements:
            element.decompose()

    # Return the cleaned feed as a string
    return str(soup)

def clean_html(html, url):
    # Extract domain and protocol from URL
    parsed_url = urlparse(url)
    domain = parsed_url.scheme + "://" + parsed_url.netloc

    # Remove unwanted tags and attributes
    soup = BeautifulSoup(html, 'html.parser')
    for tag in soup(['script', 'style', 'iframe', 'embed', 'object', 'link']):
        tag.decompose()
    for tag in soup():
        tag.attrs = {key: val for key, val in tag.attrs.items() if key not in ['class', 'id', 'style']}
    for img in soup.find_all('img'):
        # Check if image path is relative
        if not img['src'].startswith('http'):
            img['src'] = domain + img['src']
        img['style'] = 'max-width: 100%;'
    for a in soup.find_all('a'):
        # Check if link path is relative
        if not a['href'].startswith('http'):
            a['href'] = domain + a['href']
    for video in soup.find_all('video'):
        video.replace_with(soup.new_tag('div', string='[Video removed from content of website]'))
    for audio in soup.find_all('audio'):
        audio.replace_with(soup.new_tag('div', string='[Audio removed from content of website]'))
    for svg in soup.find_all('svg'):
        svg.replace_with(soup.new_tag('div', string='[SVG graphic removed from content of website]'))
    for form in soup.find_all('form'):
        form.replace_with(soup.new_tag('div', string='[Form removed from content of website]'))
    cleaned_html = str(soup)

    # Sanitize HTML using Bleach
    tags = ['img', 'p', 'br', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'div']
    attributes = {
        '*': ['class', 'id', 'style'],
        'img': ['src', 'alt', 'title', 'width', 'height'],
        'a': ['href', 'title'],
        'div': ['align']
    }
    cleaned_html = bleach.clean(cleaned_html, tags=tags, attributes=attributes, strip=True)

    return cleaned_html