# -*- coding: utf-8 -*-
# !/usr/bin/python
from frame_box import FrameBox
from bilibili_api import bangumi
import imagehash
from PIL import Image
import os
import json
from download_bilibili.down_bilibili import download_video
import init_conf
import sys
import subprocess
from milvus import NotConnectError
import threading
CURR_PATH = "download_bilibili"


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
    lst = imagehash.dhash(Image.open(os.path.join(CURR_PATH, "black.jpg")))
    st -= 1
    frame_box.connect()
    frame_box.set_tag(tags)
    frame_box.set_brief(brief)
    while (True):
        try:
            st += 1
            cid = brief['cid']
            file = os.path.join(CURR_PATH, 'image/%d/%d.jpg' % (cid, st))
            if not os.path.exists(file):
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
    down_done_mark = os.path.join(CURR_PATH, 'bilibili_video/%d/done' % cid)
    out_path = os.path.join(VIDEO_OUT_PATH, '%d.mp4' % cid)
    pre_done_mark = os.path.join(VIDEO_OUT_PATH, '%d.done' % cid)
    if not os.path.exists(VIDEO_OUT_PATH):
        os.makedirs(VIDEO_OUT_PATH)
    if not os.path.exists(pre_done_mark):
        subprocess.run("ffmpeg -i %s -vcodec libx264  -strict -2 -an -crf %d -vf scale=-2:%d %s" % (
            video, crf, resolution, out_path), check=True, shell=True)  # 压缩视频
        mark_f = open(pre_done_mark, 'w')
        mark_f.close()
    if not os.path.exists(os.path.join(CURR_PATH, "image", str(cid))):
        os.mkdir(os.path.join(CURR_PATH, "image", str(cid)))
    ready_mark = os.path.join(CURR_PATH, 'image', str(cid), 'ready')
    if not os.path.exists(ready_mark):
        pic_path = os.path.join(CURR_PATH, "image", str(cid), "%d.jpg")
        subprocess.run(
            "ffmpeg -i %s -r %d -q:v 2 -f image2 %s" % (video, rate, pic_path), check=True, shell=True)  # 转化成图片
        ready_mark = open(os.path.join(CURR_PATH, 'image', str(cid), 'ready'), 'w')
        ready_mark.close()
    os.remove(video)
    os.remove(down_done_mark)

def get_list():
    queue = get_json('setting.json')['queue']
    ep_list = []
    for i in queue['season_id']:
        info = bangumi.get_collective_info(season_id=i[1])
        episodes = info['episodes']
        for ep in episodes:
            if ep['cid'] in finish:
                continue
            ep_list.append( # status: waiting -> downloading -> download_failed/downloaded 
                            # -> processing -> process_failed/finished
                {'bvid': ep['bvid'], 'cid': ep['cid'], 'epid': ep['id'], 'tag': i[0], 'status': 'waiting'})
    for i in queue['epid']:
        ep = get_epInfo(i[1])
        if ep['cid'] in finish:
            continue
        ep_list.append(
                {'bvid': ep['bvid'], 'cid': ep['cid'], 'epid': ep['id'], 'tag': i[0], 'status': 'waiting'})
    return ep_list

def download_thread():
    is_downloading = True
    for ep in ep_list:
        if ep['status'] != 'waiting':
            continue
        print('download:', ep['cid'])
        try:
            ret = download_video("https://www.bilibili.com/bangumi/play/ep" + str(ep['epid']), 64)
        except Exception as e:
            print(e)
            ep['status'] = 'download_failed'
            add_to_failed(ep['epid'], ep['cid'])
            continue
        if ret < 0:
            ep['status'] = 'download_failed'
            add_to_failed(ep['epid'], ep['cid'])
        else:
            ep['status'] = 'downloaded'
            try_process()
            downloaded_num = 0
            for i in ep_list:
                if i['status'] == 'downloaded':
                    downloaded_num += 1
            if downloaded_num >= 3:
                print('download stoped')
                break
    is_downloading = False

def try_download():
    if not is_downloading:
        t = threading.Thread(target=download_thread, name='download')
        t.start()

def process():
    is_processing = True
    for ep in ep_list:
        if ep['status'] == 'downloaded':
            print('process:', ep['cid'])
            try:
                ep['status'] = 'processing'
                pre_video(ep['epid'], ep['cid'])
            except subprocess.CalledProcessError as e:
                print(e)
                ep['status'] = 'process_failed'
                add_to_failed(ep['epid'], ep['cid'])
                continue
            try:
                update(ep['tag'], brief={
                    'epid': ep['epid'],
                    'bvid': ep['bvid'],
                    'cid': ep['cid']
                }, st=1)
            except NotConnectError as e:
                print(e)
                ep['status'] = 'process_failed'
                add_to_failed(ep['epid'], ep['cid'])
                continue
            ep['status'] = 'finished'
            try_download()
    is_processing = False

def try_process():
    if not is_processing:
        t = threading.Thread(target=process, name='process')
        t.start()

ep_list = get_list()
is_downloading = False
is_processing = False

def main():
    pre = get_json("pre.json")

    if pre['frame'] > 0:
        st = pre['frame']
        pre['frame'] = 0
        open(os.path.join(CURR_PATH, "pre.json"),
             "w").write(json.dumps({'frame': 0}))
        update(pre['tags'], pre['brief'], st)

    try_download()
    try_process()
    print('Start !')


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
