from bs4 import BeautifulSoup
import requests
import re
import time
import os
from urllib.request import urlretrieve

host = 'halihali2.com'
list_host = '121.4.190.96:9991'
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.93 Safari/537.36'
}
js_url = 'http://d.gqyy8.com:8077/ne2/s%s.js?1622904201'

cached = {}

def get_resp(url, with_try=(1, 3, 5, 10, 30)):
    try:
        resp = requests.get(url, headers=headers)
    except Exception as e:
        print('connection error')
        if len(with_try) == 0:
            raise e
        time.sleep(with_try[0])
        return get_resp(url, with_try[1:])
    resp.encoding = 'utf-8'
    return resp

def get_season_info(season_id):
    season_id = str(season_id)
    if season_id in cached:
        return cached[season_id]
    resp = get_resp('http://%s/acg/%s/' % (host, season_id))
    if re.search(r'该链接已失效|无此片源', resp.text):
        return None
    page = BeautifulSoup(resp.text, features='html.parser')
    season = {}
    season['id'] = season_id
    info_div = page.select('div.wrap > div.content.mb.clearfix > div.info')[0]
    season['name'] = list(info_div.select('dl > dt.name')[0].strings)[0]
    strings = list(info_div.select('dl')[0].strings)
    for i in range(len(strings)):
        if re.search(r'地区', strings[i]):
            season['area'] = strings[i+1]
        elif re.search(r'年代', strings[i]):
            season['age'] = strings[i+1]
    tag_a = info_div.select('dl > dd > a')
    season['tags'] = []
    for a in tag_a:
        season['tags'].append(a.text)
    img = page.select('div.wrap > div.content.mb.clearfix > div.pic > img')[0]
    season['cover'] = img['data-original'].replace('http://', 'https://')
    season['evaluate'] = list(info_div.select('.desd .des2')[0].strings)[1]
    season['episodes'] = []
    tag_a = page.select('#stab_1_71 > ul > li > a')
    resp = get_resp(js_url % season_id)
    videos = find_videos(resp.text)
    for a in tag_a:
        if re.search(r'备', a.text):
            continue
        num = int(re.findall(r'\/(\d+)\.html$', a['href'])[0])
        if num not in videos:
            continue
        if not re.search(r'\.mp4', str(videos[num])):
            continue
        for url in videos[num]:
            if re.search(r'\.mp4', url):
                video = url
                break
        season['episodes'].append({
            'title': a.text,
            'video': url,
            'id': '%s-%d' % (season_id, num),
            'name': season['name'] + ': ' + a.text,
        })
    cached[season_id] = season
    return season if season['episodes'] else None

def get_episode_info(epid):
    season_id, ep_num = epid.split('-')
    season = get_season_info(season_id)
    for ep in season['episodes']:
        if ep['id'] == epid:
            return ep

def find_videos(js):
    videos = {}
    pattern = '%s\\[(\\d+)\\]=\"(.*?),.*?\"'
    for num, url in re.findall(pattern % 'playarr', js):
        url = url.replace('http://', 'https://')
        videos[int(num)] = [url]
    arr_num = 1
    while re.findall(pattern % 'playarr_%d' % arr_num, js):
        for num, url in re.findall(pattern % 'playarr_%d' % arr_num, js):
            url = url.replace('http://', 'https://')
            if int(num) in videos:
                videos[int(num)].append(url)
            else:
                videos[int(num)] = [url]
        arr_num += 1
    return videos

def download(url, path):
    if not os.path.exists(path):
        os.makedirs(path)
    filename = os.path.join(path, 'video.mp4')
    print('start download from %s to %s' % (url, filename))
    urlretrieve(url, filename)
