# -*- coding: utf-8 -*-
import requests
from urllib.request import urlretrieve
import re
from bs4 import BeautifulSoup
from numpy.compat import unicode
import os

host = 'www.yhdm.so'
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.93 Safari/537.36'
}


def get_season_info(season_id):
    season_id = str(season_id)
    resp = requests.get('http://%s/show/%s.html' %
                        (host, season_id), headers=headers)
    resp.encoding = 'utf-8'
    page = BeautifulSoup(resp.text, features='html.parser')
    season = {}
    season['id'] = season_id
    season['name'] = page.h1.string
    season['evaluate'] = page.select('div.info')[0].text
    season['cover'] = page.select('div.fire.l > .thumb.l > img')[0]['src']
    episodes = []
    for a in page.select('#main0 .movurl li a'):
        episodes.append({
            'id': re.match(r'\/v\/(\d+\-\w+)\.html$', a['href']).group(1),
            'name': a.text
        })
    season['episodes'] = episodes
    return season


def get_episode_info(ep_id):
    resp = requests.get('http://%s/v/%s.html' %
                        (host, ep_id), headers=headers)
    resp.encoding = 'utf-8'
    page = BeautifulSoup(resp.text, features='html.parser')
    episode = {}
    episode['id'] = ep_id
    episode['name'] = page.select('.gohome.l h1 span')[0].text
    episode['fullName'] = page.select('.gohome.l h1 a')[
        0].text + episode['name']
    episode['video'] = re.match(
        r'^(.*)\$', page.select('#playbox')[0]['data-vid']).group(1)
    return episode


def download(url, path):
    if not os.path.exists(path):
        os.makedirs(path)
    filename = os.path.join(path, 'video.mp4')
    print('start download from %s to %s' % (url, filename))
    urlretrieve(url, filename)
