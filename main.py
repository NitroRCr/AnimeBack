# !/usr/bin/python
# -*- coding:utf-8 -*-
from down_bilibili import download_video
import requests
import json
import os
import sys
import time
import base64
from PIL import Image
import imagehash
from bilibili_api import bangumi

BAIDU_API = 'https://aip.baidubce.com/oauth/2.0/token?grant_type=client_credentials&client_id=<需要修改>&client_secret=<需要修改>'


rate = json.loads(open("setting.json").read())['rate']
crf = json.loads(open("setting.json").read())['crf']
resolution = json.loads(open("setting.json").read())['resolution']
finish = json.loads(open("finish.json").read())


def getak():
    response = requests.get(BAIDU_API)
    return response.json()['access_token']


access_token = getak()


def end_task(frame, brief, tags):
    f = open("pre.json", "w")
    f.write(json.dumps({"frame": frame, "brief": brief, "tags": tags},
                       indent=4, separators=(',', ': ')))
    f.close()
    sys.exit(0)


tags = "33378,1"


def get_file_content(filePath):
    return base64.b64encode(open(filePath, 'rb').read())


def upload(image, tags, brief):
    params = {"image": image, "brief": json.dumps(brief), "tags": tags}
    request_url = "https://aip.baidubce.com/rest/2.0/image-classify/v1/realtime_search/similar/add"
    request_url = request_url + "?access_token=" + access_token
    headers = {'content-type': 'application/x-www-form-urlencoded'}
    time.sleep(0.5)
    try:
        return requests.post(request_url, data=params, headers=headers).json()
    except:
        return {'error_code': 233}


def update(tags, brief, st):  # 从 cid 视频的 st 帧开始
    lst = imagehash.phash(Image.open("black.jpeg"))
    cid = brief['cid']
    st -= 1
    while (True):
        st += 1
        file = 'image/%d/%d.jpeg' % (cid, st)
        if (os.path.exists(file) == False):
            break
        now = imagehash.phash(Image.open(file))
        sim = (1 - (now - lst) / len(now.hash) ** 2)
        print("%f %d" % (sim, st))
        if sim >= 0.90:  # 如果与上一帧相似度大于90%，跳过
            os.remove(file)
            continue
        lst = now
        brief['time'] = st / rate
        image = get_file_content(file)
        ret = upload(image, tags, brief)  # 调用API
        try:
            cont_sign = ret['cont_sign']
            open("cont_sign/%d" % cid, "a").write(str(cont_sign)+'\n')
        except:
            error_code = ret['error_code']
            if error_code == 17 or error_code == 19:  # 今日调用次数达到限制
                end_task(st, brief, tags)
            if error_code == 216681:  # 完全相同的图片不能入库
                continue
            time.sleep(5)
            ret = upload(image, tags, brief)  # 重新尝试
            try:
                cont_sign = ret['cont_sign']
                open("cont_sign/%d" % cid, "a").write(str(cont_sign)+'\n')
            except:
                pass
        os.remove(file)  # 删除图片
    fin = json.loads(open("finish.json").read())
    fin.append(cid)
    f = open("finish.json", "w")
    f.write(json.dumps(fin, indent=4, separators=(',', ': ')))  # 放入处理完成列表
    f.close()


def get_epInfo(epid):
    epinfo = bangumi.get_episode_info(epid=epid)['epInfo']
    return {'bvid': epinfo['bvid'], 'cid': epinfo['cid'], 'epid': epinfo['id']}


def pre_video(epid, cid):  # 视频预处理
    video = 'bilibili_video/%d/%d.flv' % (cid, cid)
    if os.path.exists(video) == False:
        download_video(
            "https://www.bilibili.com/bangumi/play/ep" + str(epid), 112)  # 下载视频
    if os.path.exists('video/%d.mp4' % cid) == False:
        os.system("ffmpeg -i %s -vcodec libx264  -strict -2 -an -crf %d -vf scale=-2:%d video/%d.mp4" % (
            video, crf, resolution, cid))  # 压缩视频
    if os.path.exists("./image/"+str(cid)) == False:
        os.mkdir("./image/"+str(cid))
        # os.system("mkdir image/" + str(cid))
    os.system(
        "ffmpeg -i %s -r %d -q:v 2 -f image2 image/%d/%%d.jpeg" % (video, rate, cid))  # 转化成图片
    os.remove(video)


def update_season(season_id, tags):
    infor = bangumi.get_collective_info(season_id=season_id)
    episodes = infor['episodes']
    for key in episodes:
        cid = key['cid']
        if cid in finish:
            continue
        brief = {'bvid': key['bvid'], 'cid': key['cid'], 'epid': key['id']}
        pre_video(key['id'], key['cid'])
        update(tags, brief, 1)


pre = json.loads(open("pre.json").read())

if pre['frame'] != 0:
    st = pre['frame']
    pre['frame'] = 0
    open("pre.json", "w").write(json.dumps(pre))
    update(pre['tags'], pre['brief'], st)

queue = json.loads(open("setting.json").read())['queue']
for key in queue['season_id']:
    update_season(key[1], key[0])
for key in queue['epid']:
    brief = get_epInfo(key[1])
    tag = key[0]
    if brief['cid'] in finish:
        continue
    pre_video(brief['epid'], brief['cid'])
    update(tags, brief, 1)
