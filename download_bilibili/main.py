# -*- coding: utf-8 -*-
# !/usr/bin/python
CURR_PATH = "download_bilibili"
import sys

import init_conf
from download_bilibili.down_bilibili import download_video
import json
import os
from PIL import Image
import imagehash
from bilibili_api import bangumi
from frame_box import FrameBox

frame_box = FrameBox()

def get_json(filename):
    f = open(os.path.join(CURR_PATH, filename))
    ret = json.loads(f.read())
    f.close()
    return ret

config = get_json("config.json")
VIDEO_OUT_PATH = config['videoOutPath']

SETTING = get_json("setting.json")
rate = SETTING['rate']
crf = SETTING['crf']
resolution = SETTING['resolution']
finish = get_json("finish.json")
failed = get_json("failed.json")

def end_task(frame, brief, tags):
    f = open(os.path.join(CURR_PATH, "pre.json"), "w")
    f.write(json.dumps({"frame": frame, "brief": brief, "tags": tags},
                       indent=4, separators=(',', ': ')))
    f.close()
    sys.exit(0)

tags = ""

def update(tags, brief, st):  # 从 cid 视频的 st 帧开始
    lst = imagehash.dhash(Image.open(os.path.join(CURR_PATH, "black.jpeg")))
    st -= 1
    frame_box.connect()
    frame_box.set_tag(tags)
    frame_box.set_brief(brief)
    while (True):
        try:
            st += 1
            cid = brief['cid']
            file = os.path.join(CURR_PATH, 'image/%d/%d.jpeg' % (cid, st))
            if (os.path.exists(file) == False):
                frame_box.close()
                break
            now = imagehash.dhash(Image.open(file))
            sim = (1 - (now - lst) / len(now.hash) ** 2)
            if sim >= 0.90:  # 如果与上一帧相似度大于90%，跳过
                os.remove(file)
                continue
            lst = now
            time = st / rate
            brief['time'] = time
            frame_box.add_frame(file, {"cid": cid, "time": time})
            print("Add frame %d. sim: %f, time: %.1f." % (st, sim, time))
        except KeyboardInterrupt:
            frame_box.close()
            end_task(st, brief, tags)
        os.remove(file)  # 删除图片
    fin = get_json("finish.json")
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
                continue
            update(tags, brief, 1)
        except KeyboardInterrupt:
            sys.exit(0)
        except Exception as e:
            print(e)
            print("failed at: cid=%d, epid=%d"%(key['cid'], key['id']))
            add_to_failed(key['id'], key['cid'])

def main():
    pre = get_json("pre.json")

    if pre['frame'] > 0:
        st = pre['frame']
        pre['frame'] = 0
        open(os.path.join(CURR_PATH, "pre.json"), "w").write(json.dumps(pre))
        update(pre['tags'], pre['brief'], st)

    queue = get_json('setting.json')['queue']
    for key in queue['season_id']:
        update_season(key[1], key[0])
    for key in queue['epid']:
        brief = get_epInfo(key[1])
        tag = key[0]
        if brief['cid'] in finish:
            continue
        pre_video(brief['epid'], brief['cid'])
        update(tags, brief, 1)
    print('All Done')

def add_to_failed(epid, cid):
    curr_failed = {
        "epid": epid,
        "cid": cid
    }
    if curr_failed not in failed:
        failed.append(curr_failed)
        f = open(os.path.join(CURR_PATH, "failed.json"), 'w')
        f.write(json.dumps(failed, indent=4, separators=(',', ': ')))
        f.close()

if __name__ == "__main__":
    main()

