# -*- coding: utf-8 -*-
# !/usr/bin/python
import time
from frame_box import FrameBox
from bilibili_api import bangumi
import imagehash
from PIL import Image
import os
import json
import sys
import subprocess
from milvus import NotConnectError
import threading
sys.path.append("..")
INFO_PATH = "../static/json/info.json"

frame_box = FrameBox('..')


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


CONFIG = get_json("config.json")
VIDEO_OUT_PATH = CONFIG['videoOutPath']
DOWNLOAD_PATH = CONFIG['downloadPath']
CRF = CONFIG['crf']
RATE = CONFIG['rate']
RESOLUTION = CONFIG['resolution']

failed = get_json("failed.json")
finish = get_json("finish.json")


def end_task(cid, frame, info):
    f = open("pre.json", "w")
    f.write(json.dumps({"cid": cid, "frame": frame, "info": info},
                       indent=4))
    f.close()
    sys.exit(0)


def update(cid, info, st):  # 从 cid 视频的 st 帧开始
    lst = imagehash.dhash(Image.open("black.jpg"))
    st -= 1
    frame_box.connect()
    frame_box.set_info(cid, info)
    while (True):
        try:
            st += 1
            file = 'image/%d/%d.jpg' % (cid, st)
            if not os.path.exists(file):
                frame_box.close()
                break
            now = imagehash.dhash(Image.open(file))
            sim = (1 - (now - lst) / len(now.hash) ** 2)
            if sim >= 0.90:  # 如果与上一帧相似度大于90%，跳过
                os.remove(file)
                continue
            lst = now
            time = st / RATE
            frame_box.add_frame(file, {"cid": cid, "time": time})
            print("Add frame %d. sim: %f, time: %.1f." % (st, sim, time))
            os.remove(file)  # 删除图片
        except KeyboardInterrupt:
            frame_box.close()
            end_task(cid, st, info)
    os.remove(os.path.join('image', str(cid), 'ready'))
    os.rmdir(os.path.join('image', str(cid)))


def pre_video(cid):  # 视频预处理
    flv = os.path.join(DOWNLOAD_PATH, str(cid), 'video.flv')
    video = None
    if os.path.exists(flv):
        video = flv
    mp4 = os.path.join(DOWNLOAD_PATH, str(cid), 'video.mp4')
    if os.path.exists(mp4):
        video = mp4
    if video == None:
        return -1
    out_path = os.path.join(VIDEO_OUT_PATH, '%d.mp4' % cid)
    pre_done_mark = os.path.join(VIDEO_OUT_PATH, '%d.done' % cid)
    if not os.path.exists(VIDEO_OUT_PATH):
        os.makedirs(VIDEO_OUT_PATH)
    if not os.path.exists(pre_done_mark):

        if os.path.exists(out_path):
            os.remove(out_path)
        subprocess.run("ffmpeg -i %s -vcodec libx264 -acodec aac -b:a 64k -ar 44100 -crf %d -tune animation -vf scale=-2:%d %s" % (
            video, CRF, RESOLUTION, out_path), check=True, shell=True)  # 压缩视频
        mark_f = open(pre_done_mark, 'w')
        mark_f.close()
    image_tmp_dir = os.path.join("image", str(cid))
    if not os.path.exists(image_tmp_dir):
        os.makedirs(image_tmp_dir)
    ready_mark = os.path.join(image_tmp_dir, 'ready')
    if not os.path.exists(ready_mark):
        pic_path = os.path.join(image_tmp_dir, "%d.jpg")
        subprocess.run(
            "ffmpeg -i %s -r %d -q:v 2 -f image2 %s" % (video, RATE, pic_path), check=True, shell=True)  # 转化成图片
        ready_mark = open(os.path.join(image_tmp_dir, 'ready'), 'w')
        ready_mark.close()

    return 0


def set_ss_status(ss_id, status):
    info = get_json(INFO_PATH)
    info_f = open(INFO_PATH, 'w')
    for season in info['seasons']:
        if season['seasonId'] == ss_id:
            season['status'] = status
            break
    info_f.write(json.dumps(info, ensure_ascii=False))


def process_video(cid):
    video_dir = os.path.join(DOWNLOAD_PATH, str(cid))
    if not os.path.exists(video_dir):
        return -1
    info_path = os.path.join(video_dir, 'info.json')
    if not os.path.exists(info_path):
        return -1
    info = get_json(info_path)
    if info['title'] == '1':
        set_ss_status(info['seasonId'], 'processing')
    if pre_video(cid) < 0:
        return -1
    update(cid, info, 1)
    if not info['hasNext']:
        set_ss_status(info['seasonId'], 'finished')
    return 0


def main():
    pre = get_json("pre.json")

    if pre['frame'] > 0:
        st = pre['frame']
        open("pre.json",
             "w").write(json.dumps({'frame': 0}))
        update(pre['cid'], pre['info'], st)
    video_dirs = [cid for cid in os.listdir(
        DOWNLOAD_PATH) if os.path.isdir(os.path.join(DOWNLOAD_PATH, cid))]
    video_dirs = sorted(video_dirs, key=lambda cid: os.path.getmtime(
        os.path.join(DOWNLOAD_PATH, cid)))
    t_start = time.time()
    for cid in video_dirs:
        down_done_mark = os.path.join(DOWNLOAD_PATH, cid, 'done')
        if not os.path.exists(down_done_mark):
            continue
        cid = int(cid)
        if cid in finish:
            continue
        code = process_video(cid)
        if code < 0:
            add_to_failed(cid)
            continue
        finish.append(cid)
        finish_f = open("finish.json", "w")
        finish_f.write(json.dumps(finish, indent=4))  # 放入处理完成列表
        finish_f.close()
        if CONFIG['autoRemove']:
            os.remove(down_done_mark)
            os.remove(ep_info_path)
            flv = os.path.join(DOWNLOAD_PATH, str(cid), 'video.flv')
            if os.path.exists(flv):
                os.remove(flv)
            mp4 = os.path.join(DOWNLOAD_PATH, str(cid), 'video.mp4')
            if os.path.exists(mp4):
                os.remove(mp4)
            os.rmdir(os.path.join(DOWNLOAD_PATH, str(cid)))
    t_end = time.time()
    if t_end - t_start > 60:
        main()


def add_to_failed(cid):
    if cid not in failed:
        failed.append(cid)
        f = open("failed.json", 'w')
        f.write(json.dumps(failed, indent=4))
        f.close()


if __name__ == "__main__":
    main()
