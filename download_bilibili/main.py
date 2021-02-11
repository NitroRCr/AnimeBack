# -*- coding: utf-8 -*-
# !/usr/bin/python
CURR_PATH = "download_bilibili"
import sys
sys.path.append(CURR_PATH)

from down_bilibili import download_video
import requests
import json
import os
import time
import base64
from PIL import Image
import imagehash
from bilibili_api import bangumi
from frame_box import FrameBox

frameBox = FrameBox()

config = json.loads(open(os.path.join(CURR_PATH, "config.json")).read())
BAIDU_API = config['baiduAPI']
VIDEO_OUT_PATH = config['videoOutPath']
if_use_baidu_api = config['ifUseBaiduAPI']

rate = json.loads(open(os.path.join(CURR_PATH, "setting.json")).read())['rate']
crf = json.loads(open(os.path.join(CURR_PATH, "setting.json")).read())['crf']
resolution = json.loads(open(os.path.join(CURR_PATH, "setting.json")).read())['resolution']
finish = json.loads(open(os.path.join(CURR_PATH, "finish.json")).read())
fail_f = open(os.path.join(CURR_PATH, "failed.json"))
failed = json.loads(fail_f.read())
fail_f.close()


def getak():
    response = requests.get(BAIDU_API)
    return response.json()['access_token']

if if_use_baidu_api:
    access_token = getak()


def end_task(frame, brief, tags):
    f = open(os.path.join(CURR_PATH, "pre.json"), "w")
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
    lst = imagehash.phash(Image.open(os.path.join(CURR_PATH, "black.jpeg")))
    cid = brief['cid']
    st -= 1
    while (True):
        try:
            st += 1
            file = os.path.join(CURR_PATH, 'image/%d/%d.jpeg' % (cid, st))
            if (os.path.exists(file) == False):
                if not if_use_baidu_api:
                    frameBox.flush()
                break
            now = imagehash.dhash(Image.open(file))
            sim = (1 - (now - lst) / len(now.hash) ** 2)
            print("%f %d" % (sim, st))
            if sim >= 0.90:  # 如果与上一帧相似度大于90%，跳过
                os.remove(file)
                continue
            lst = now
            brief['time'] = st / rate
            if if_use_baidu_api:
                image = get_file_content(file)
                ret = upload(image, tags, brief)  # 调用API
                try:
                    cont_sign = ret['cont_sign']
                    open(os.path.join(CURR_PATH, "cont_sign/%d" % cid), "a").write(str(cont_sign)+'\n')
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
                        open(os.path.join(CURR_PATH, "cont_sign/%d" % cid), "a").write(str(cont_sign)+'\n')
                    except:
                        pass
            else:
                frameBox.add_frame(Image.open(file), brief)
        except KeyboardInterrupt:
            end_task(st, brief, tags)
        os.remove(file)  # 删除图片
    fin = json.loads(open(os.path.join(CURR_PATH, "finish.json")).read())
    fin.append(cid)
    f = open(os.path.join(CURR_PATH, "finish.json"), "w")
    f.write(json.dumps(fin, indent=4, separators=(',', ': ')))  # 放入处理完成列表
    f.close()


def get_epInfo(epid):
    epinfo = bangumi.get_episode_info(epid=epid)['epInfo']
    return {'bvid': epinfo['bvid'], 'cid': epinfo['cid'], 'epid': epinfo['id']}


def pre_video(epid, cid):  # 视频预处理
    video = os.path.join(CURR_PATH, 'bilibili_video/%d/%d.flv' % (cid, cid))
    out_path = os.path.join(VIDEO_OUT_PATH, '%d.mp4' % cid)
    if os.path.exists(video) == False:
        download_video(
            "https://www.bilibili.com/bangumi/play/ep" + str(epid), 112)  # 下载视频
        if os.path.exists(video) == False:
            print("download failed, cid:%d, epid:%d"%(cid, epid))
            return -1
    if os.path.exists(out_path) == False:
        os.system("ffmpeg -i %s -vcodec libx264  -strict -2 -an -crf %d -vf scale=-2:%d %s" % (
            video, crf, resolution, out_path))  # 压缩视频
    if os.path.exists(os.path.join(CURR_PATH, "image", str(cid))) == False:
        os.mkdir(os.path.join(CURR_PATH, "image", str(cid)))
        # os.system("mkdir image/" + str(cid))
    pic_path = os.path.join(CURR_PATH, "image", str(cid), "%d.jpeg")
    os.system(
        "ffmpeg -i %s -r %d -q:v 2 -f image2 %s" % (video, rate, pic_path))  # 转化成图片
    os.remove(video)
    return 0


def update_season(season_id, tags):
    infor = bangumi.get_collective_info(season_id=season_id)
    episodes = infor['episodes']
    for key in episodes:
        cid = key['cid']
        if cid in finish:
            continue
        brief = {'bvid': key['bvid'], 'cid': key['cid'], 'epid': key['id']}
        try:
            code = pre_video(key['id'], key['cid'])
            if code < 0:
                add_to_failed(key['id'], key['cid'])
            update(tags, brief, 1)
        except KeyboardInterrupt:
            sys.exit(0)
        except:
            print("failed at: cid=%d, epid=%d"%(key['cid'], key['id']))
            add_to_failed(key['id'], key['cid'])

def main():
    pre = json.loads(open(os.path.join(CURR_PATH, "pre.json")).read())

    if pre['frame'] != 0:
        st = pre['frame']
        pre['frame'] = 0
        open(os.path.join(CURR_PATH, "pre.json"), "w").write(json.dumps(pre))
        update(pre['tags'], pre['brief'], st)

    queue = json.loads(open(os.path.join(CURR_PATH, "setting.json")).read())['queue']
    for key in queue['season_id']:
        update_season(key[1], key[0])
    for key in queue['epid']:
        brief = get_epInfo(key[1])
        tag = key[0]
        if brief['cid'] in finish:
            continue
        pre_video(brief['epid'], brief['cid'])
        update(tags, brief, 1)

def add_to_failed(epid, cid):
    failed.append({
        "epid": epid,
        "cid": cid
    })
    f = open(os.path.join(CURR_PATH, "faild.json"))
    f.write(json.dumps(failed))
    f.close()

if __name__ == "__main__":
    main()


