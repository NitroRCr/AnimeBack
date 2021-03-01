# -*- coding: utf-8 -*-

'''
项目: B站动漫番剧(bangumi)下载
版本2: 无加密API版,但是需要加入登录后cookie中的SESSDATA字段,才可下载720p及以上视频
API:
1.获取cid的api为 https://api.bilibili.com/x/web-interface/view?aid=47476691 aid后面为av号
2.下载链接api为 https://api.bilibili.com/x/player/playurl?avid=44743619&cid=78328965&qn=32 cid为上面获取到的 avid为输入的av号 qn为视频质量
注意:
但是此接口headers需要加上登录后'Cookie': 'SESSDATA=3c5d20cf%2C1556704080%2C7dcd8c41' (30天的有效期)(因为现在只有登录后才能看到720P以上视频了)
不然下载之后都是最低清晰度,哪怕选择了80也是只有480p的分辨率!!
'''

import requests
import time
import urllib
import re
from moviepy.editor import *
import os
import sys
import threading
import json
from bilibili_api import bangumi

import imageio_ffmpeg
import subprocess

def get_json(filename):
    try:
        f = open(filename)
    except FileNotFoundError as e:
        print('json file not found:', filename)
        print('Maybe you should run `python init_conf.py` first.')
        raise e
    try:
        ret = json.loads(f.read())
    except json.JSONDecodeError as e:
        print('json loads failed at', filename)
        raise e
    f.close()
    return ret

DOWNLOAD_PATH = "../download"
INFO_PATH = os.path.join('..', 'static', 'json', 'info.json')
SETTING = get_json("setting.json")
COVER_PATH = os.path.join('..', 'static', 'img', 'cover')
finish = get_json("finish.json")
# 访问API地址

failed = get_json("failed.json")



def set_season(s_info):
    season_id = s_info['season_id']
    info = get_json(INFO_PATH)
    for i in info['seasons']:
        if season_id == i['seasonId']:
            return
    season = {
        "seasonId": season_id,
        "name": s_info['title'],
        "wikiLink": "https://zh.moegirl.org.cn/" + s_info['title'], # 链接不一定正确，需实测
        "shortIntro": s_info['evaluate'],
        "status": "waiting"
    }
    info["seasons"].append(season)
    f = open(INFO_PATH, 'w')
    f.write(json.dumps(info, indent=4, ensure_ascii=False))
    f.close()
    download_cover(s_info)

def add_to_failed(epid, cid):
    curr_failed = {
        "epid": epid,
        "cid": cid
    }
    if curr_failed not in failed:
        failed.append(curr_failed)
        f = open("failed.json", 'w')
        f.write(json.dumps(failed, indent=4))
        f.close()

def get_play_list(aid, cid, quality):
    url_api = 'https://api.bilibili.com/x/player/playurl?cid={}&avid={}&qn={}'.format(
        cid, aid, quality)
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/55.0.2883.87 Safari/537.36',
        # 登录B站后复制一下cookie中的SESSDATA字段,有效期1个月
        'Cookie': 'SESSDATA=%s'%SETTING['SESSDATA'],
        'Host': 'api.bilibili.com'
    }
    html = requests.get(url_api, headers=headers).json()
    # print(html)
    # 当下载会员视频时,如果cookie中传入的不是大会员的SESSDATA时就会返回: {'code': -404, 'message': '啥都木有', 'ttl': 1, 'data': None}
    if html['code'] != 0:
        print(html)
        print('注意!当前集数为B站大会员专享,若想下载,Cookie中请传入大会员的SESSDATA')
        return -1
    video_list = []
    for i in html['data']['durl']:
        video_list.append(i['url'])
    print('video list:', video_list)
    return video_list


# 下载视频
'''
 urllib.urlretrieve 的回调函数：
def callbackfunc(blocknum, blocksize, totalsize):
    @blocknum:  已经下载的数据块
    @blocksize: 数据块的大小
    @totalsize: 远程文件的大小
'''

#  下载视频
def down_video(video_list, title, start_url):
    down_dir = os.path.join(DOWNLOAD_PATH, title)
    num = 1
    print('[正在下载]:' + title)
    for i in video_list:
        opener = urllib.request.build_opener()
        # 请求头
        opener.addheaders = [
            # ('Host', 'upos-hz-mirrorks3.acgvideo.com'),  #注意修改host,不用也行
            ('User-Agent', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.13; rv:56.0) Gecko/20100101 Firefox/56.0'),
            ('Accept', '*/*'),
            ('Accept-Language', 'en-US,en;q=0.5'),
            ('Accept-Encoding', 'gzip, deflate, br'),
            ('Range', 'bytes=0-'),  # Range 的值要为 bytes=0- 才能下载完整视频
            ('Referer', start_url),  # 注意修改referer,必须要加的!
            ('Origin', 'https://www.bilibili.com'),
            ('Connection', 'keep-alive'),

        ]
        urllib.request.install_opener(opener)
        # 创建文件夹存放下载的视频
        if not os.path.exists(down_dir):
            os.makedirs(down_dir)
        # 开始下载
        if len(video_list) > 1:
            urllib.request.urlretrieve(url=i, filename=os.path.join(down_dir, 'part-%d.flv'%num))  # 写成mp4也行  title + '-' + num + '.flv'
        else:
            urllib.request.urlretrieve(url=i, filename=os.path.join(down_dir, 'video.flv'))  # 写成mp4也行  title + '-' + num + '.flv'
        num += 1


def download_video(epid, quality):
    ep_url = 'https://www.bilibili.com/bangumi/play/ep' + str(epid)
    start_time = time.time()
    # 用户输入番剧完整链接地址
    # 1. https://www.bilibili.com/bangumi/play/ep267692 (用带ep链接)
    # 2. https://www.bilibili.com/bangumi/play/ss26878  (不要用这个ss链接,epinfo的aid会变成'-1')
    # print('*' * 30 + 'B站番剧视频下载小助手' + '*' * 30)
    # print('[提示]: 1.如果您想下载720P60,1080p+,1080p60质量的视频,请将35行代码中的SESSDATA改成你登录大会员后得到的SESSDATA,普通用户的SESSDATA最多只能下载1080p的视频')
    # print('       2.若发现下载的视频质量在720p以下,请将35行代码中的SESSDATA改成你登录后得到的SESSDATA(有效期一个月),而失效的SESSDATA就只能下载480p的视频')

    # start = input(
    #    '请输入您要下载的B站番剧的完整链接地址(例如:https://www.bilibili.com/bangumi/play/ep267692):')
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/55.0.2883.87 Safari/537.36'
    }
    html = requests.get(ep_url, headers=headers).text
    ep_info = re.search(r'INITIAL_STATE__=(.*?"]});', html).group(1)
    # print(ep_info)
    ep_info = json.loads(ep_info)
    # print('您将要下载的番剧名为:' + ep_info['mediaInfo']['title']) # 字段格式太不统一了
    # y = input('请输入1或2 - 1.只下载当前一集 2.下载此番剧的全集:')
    # 1.如果只下载当前ep
    try:
        item = [ep_info['epInfo']['aid'], ep_info['epInfo']['cid'],
                            str(ep_info['epInfo']['cid'])]
    except:
        item = [ep_info['epInfo']['aid'], ep_info['epInfo']['cid'],
                            str(ep_info['epInfo']['index'])]

    # qn参数就是视频清晰度
    # 可选值：
    # 116: 高清1080P60 (需要带入大会员的cookie中的SESSDATA才行,普通用户的SESSDATA最多只能下载1080p的视频,不带入SESSDATA就只能下载480p的)
    # 112: 高清1080P+ (hdflv2) (需要大会员)
    # 80: 高清1080P (flv)
    # 74: 高清720P60 (需要大会员)
    # 64: 高清720P (flv720)
    # 32: 清晰480P (flv480)
    # 16: 流畅360P (flv360)
    # print('请输入您要下载视频的清晰度(1080p60:116;1080p+:112;1080p:80;720p60:74;720p:64;480p:32;360p:16; **注意:1080p+,1080p60,720p60都需要带入大会员的cookie中的SESSDATA才行,普通用户的SESSDATA最多只能下载1080p的视频):')
    # quality = input('请输入116或112或80或74或64或32或16:')
    threadpool = []
    page = 1
    aid = str(item[0])
    cid = str(item[1])
    title = item[2]
    if os.path.exists(os.path.join(DOWNLOAD_PATH, cid, 'done')):
        return 0
    # title = re.sub(r'[\/\\:*?"<>|]', '', title)  # 替换为空的
    print('[下载番剧标题]:' + title)
    start_url = ep_url
    video_list = get_play_list(aid, cid, quality)
    # down_video(video_list, title, start_url, page)
    # 定义线程
    if video_list == -1:
        return -1
    else:
        down_video(video_list, title, start_url)

    if os.path.exists(os.path.join(DOWNLOAD_PATH, cid, 'part-1.flv')):
        combine_video(cid)

    end_time = time.time()  # 结束时间
    print('下载耗时%.2f秒,约%.2f分钟' %
          (end_time - start_time, int(end_time - start_time) / 60))

    f = open(os.path.join(DOWNLOAD_PATH, cid, 'done'), 'w')
    f.close()
    return 0

def combine_video(cid):
    video_dir = os.path.join(DOWNLOAD_PATH, cid)
    filelist = open(os.path.join(video_dir, 'filelist.txt'), 'w')
    num = 1
    while os.path.exists(os.path.join(video_dir, 'part-%d.flv' % num)):
        filelist.write(os.path.join(video_dir, 'part-%d.flv' % num) + '\n')
        num += 1
    subprocess.run(['ffmpeg', '-f', 'concat', '-i', os.path.join(video_dir, 'filelist.txt'), '-c', 'copy', os.path.join(video_dir, 'video.flv')])
    num = 1
    while os.path.exists(os.path.join(video_dir, 'part-%d.flv' % num)):
        os.remove(os.path.join(video_dir, 'part-%d.flv' % num))
        num += 1


def download_cover(info):
    season_id = info['season_id']
    print('download cover:', season_id)
    if not os.path.exists(COVER_PATH):
        os.mkdir(COVER_PATH)
    cover_path = os.path.join(COVER_PATH, str(season_id))
    if not os.path.exists(cover_path):
        urllib.request.urlretrieve(info['cover'], cover_path)


def get_list():
    queue = SETTING['queue']
    ep_list = []
    print('[正在获取信息]')
    for i in queue['season_id']:
        info = bangumi.get_collective_info(season_id=i[1])
        set_season(info)
        episodes = info['episodes']
        for episode in episodes:
            if episode['cid'] in finish:
                continue
            ep_list.append(Ep(episode['id'], i[0]))
                
    for i in queue['epid']:
        ep = Ep(i[1], i[0])
        if ep.cid in finish:
            continue
        ep_list.append(ep)
    return ep_list

def set_ss_status(ss_id, status):
    info = get_json(INFO_PATH)
    info_f = open(INFO_PATH, 'w')
    for season in info['seasons']:
        if season['seasonId'] == ss_id:
            if season['status'] != status:
                season['status'] = status
                info_f.write(json.dumps(info, ensure_ascii=False))
                break
            else:
                return

class Ep(object):
    def __init__(self, epid, tag):
        info = bangumi.get_episode_info(epid=epid)
        self.id = epid
        self.cid = info['epInfo']['cid']
        self.name = info['h1Title']
        self.tag = tag
        self.season_id = info['mediaInfo']['ssId']
        self.info = {'bvid': info['epInfo']['bvid'], 'epid': epid}
        self.has_next = info['epInfo']['hasNext']
        self.title = info['epInfo']['title']

    def write_info(self):
        f = open(os.path.join(DOWNLOAD_PATH, str(self.cid), 'info.json'), 'w')
        f.write(json.dumps({
            "name": self.name,
            "seasonId": self.season_id,
            "info": self.info,
            "tag": self.tag,
            "hasNext": self.has_next,
            "title": self.title
        }, ensure_ascii=False))
        f.close()

def download():
    ep_list = get_list()
    for ep in ep_list:
        print('download:', ep.cid)
        if ep.title == '1':
            set_ss_status(ep.season_id, 'downloading')
        try:
            ret = download_video(ep.id, SETTING['quality'])
        except Exception as e:
            print(e)
            add_to_failed(ep.id, ep.cid)
            continue
        if ret < 0:
            add_to_failed(ep.id, ep.cid)
        else:
            add_to_finish(ep.cid)
            ep.write_info()
            if not ep.has_next:
                set_ss_status(ep.season_id, 'downloaded')

def add_to_finish(cid):
    finish = get_json("finish.json")
    finish.append(cid)
    f = open("finish.json", 'w')
    f.write(json.dumps(finish, indent=4))
    f.close()

if __name__ == '__main__':
    download()
