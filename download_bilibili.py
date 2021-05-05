# -*- coding: utf-8 -*-
import requests
import time
import urllib
import os
import threading
import json
import re

import subprocess


def get_play_list(aid, cid, settings):
    url_api = 'https://api.bilibili.com/x/player/playurl?cid={}&avid={}&qn={}'.format(
        cid, aid, settings['quality'])
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/55.0.2883.87 Safari/537.36',
        # 登录B站后复制一下cookie中的SESSDATA字段,有效期1个月
        'Cookie': 'SESSDATA=%s' % settings['SESSDATA'],
        'Host': 'api.bilibili.com'
    }
    html = requests.get(url_api, headers=headers).json()
    # print(html)
    # 当下载会员视频时,如果cookie中传入的不是大会员的SESSDATA时就会返回: {'code': -404, 'message': '啥都木有', 'ttl': 1, 'data': None}
    if html['code'] != 0:
        print(html)
        print('注意!当前集数为B站大会员专享,若想下载,Cookie中请传入大会员的SESSDATA')
        raise ValueError('No VIP')
    video_list = []
    for i in html['data']['durl']:
        video_list.append(i['url'])
    print('video list:', video_list)
    return video_list


def download_bilibili_video(epid, down_path, settings):
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

    str_id = str(epid)
    # title = re.sub(r'[\/\\:*?"<>|]', '', title)  # 替换为空的
    print('[下载番剧标题]:' + title)
    start_url = ep_url
    video_list = get_play_list(aid, cid, settings)
    # down_video(video_list, title, start_url, page)
    # 定义线程

    down_video(video_list, title, start_url, down_path)

    if os.path.exists(os.path.join(down_path, 'part-1.flv')):
        combine_video(str_id, down_path)

    end_time = time.time()  # 结束时间
    print('下载耗时%.2f秒,约%.2f分钟' %
          (end_time - start_time, int(end_time - start_time) / 60))
    return 0


def down_video(video_list, title, start_url, down_path):
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
        if not os.path.exists(down_path):
            os.makedirs(down_path)
        # 开始下载
        if len(video_list) > 1:
            urllib.request.urlretrieve(url=i, filename=os.path.join(
                down_path, 'part-%d.flv' % num))  # 写成mp4也行  title + '-' + num + '.flv'
        else:
            urllib.request.urlretrieve(url=i, filename=os.path.join(
                down_path, 'video.flv'))  # 写成mp4也行  title + '-' + num + '.flv'
        num += 1


def combine_video(epid, down_path):
    filelist = open(os.path.join(down_path, 'filelist.txt'), 'w')
    num = 1
    while os.path.exists(os.path.join(down_path, 'part-%d.flv' % num)):
        filename = os.path.join(down_path, 'part-%d.flv' % num)
        filelist.write("file %s\n" % 'part-%d.flv' % num)
        num += 1
    filelist.close()
    subprocess.run(['ffmpeg', '-f', 'concat', '-i', os.path.join(
        down_path, 'filelist.txt'), '-c', 'copy', os.path.join(down_path, 'video.flv')])
    num = 1
    while os.path.exists(os.path.join(down_path, 'part-%d.flv' % num)):
        os.remove(os.path.join(down_path, 'part-%d.flv' % num))
        num += 1
    os.remove(os.path.join(down_path, 'filelist.txt'))
