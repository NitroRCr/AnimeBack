import json
from os import path
import os
from ldb import LDB
from bilibili_api import bangumi
from download_bilibili import download_bilibili_video
import re
import subprocess
import imagehash
from PIL import Image
from frame_box import FrameBox, PCATrainer
import random
import time
from urllib import request

NUMS_KEY = b'c_nums'
REFER_KEY = b'refer'

SKIP_MARK = 'skiped'
FAIL_MARK = 'failed'
DONE_MARK = 'done'

frame_box = None
pca_trainer = None

db_seasons = LDB(
    path.join('db', 'seasons'), create_if_missing=True)
db_episodes = LDB(
    path.join('db', 'episodes'), create_if_missing=True)
db_status = LDB(path.join('db', 'status'),
                create_if_missing=True)
if not db_status.get(NUMS_KEY):
    db_status.put(NUMS_KEY, json.dumps({
        "searchNum": 0,
        "maxSsId": 0,
        "maxEpId": 0,
        "tmpNum": 0
    }).encode())
if not db_status.get(REFER_KEY):
    db_status.put(REFER_KEY, json.dumps({
        'episode/bilibili': {},
        'season/bilibili': {}
    }).encode())


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


config = get_json('config.json')

DOWNLOAD_DIR = config['downloadDir']
VIDEO_OUT_DIR = config['videoOutDir']
IMG_TMP_DIR = config['imgTmpDir']
PROC_CONF = config['process']
COVER_DIR = config['coverDir']
ENABLE_CUDA = config['keras_cuda']


def load_frame_box(disable_gpu=False):
    global frame_box
    if not frame_box:
        frame_box = FrameBox(ENABLE_CUDA, disable_gpu=disable_gpu)
        frame_box.connect()


def load_trainer():
    global pca_trainer
    if not pca_trainer:
        pca_trainer = PCATrainer()


def close_db():
    db_seasons.close()
    db_episodes.close()
    db_status.close()


def get_num(key):
    nums = json.loads(db_status.get(NUMS_KEY).decode())
    nums[key] += 1
    db_status.put(NUMS_KEY, json.dumps(nums).encode())
    return nums[key]


def get_id(_type, type_id):
    refer = json.loads(db_status.get(REFER_KEY).decode())
    if str(type_id) in refer[_type]:
        return refer[_type][str(type_id)]
    return None


def set_refer(_type, type_id, _id):
    refer = json.loads(db_status.get(REFER_KEY).decode())
    refer[_type][str(type_id)] = _id
    db_status.put(REFER_KEY, json.dumps(refer).encode())


def create_mark(filename):
    f = open(filename, 'w')
    f.close()


class Season:
    def __init__(self, bili_ssid=None, from_id=None,
                 settings=None):
        if from_id:
            self.id = from_id
            data = db_seasons.get(from_id.encode())
            if data:
                self.data = json.loads(data)
            else:
                raise ValueError('Invalid `from_id`')
        elif bili_ssid and get_id('season/bilibili', bili_ssid):
            self.id = get_id('season/bilibili', bili_ssid)
            self.data = json.loads(db_seasons.get(self.id.encode()).decode())
        else:
            self.id = str(get_num('maxSsId'))
            self.data = {}
            if bili_ssid:
                self.set_data_from_bili(bili_ssid)
            self.data['finishedPresets'] = []
            self.data['targetPresets'] = settings['presets']
            self.data['isDownloading'] = None
            self.data['isProcessing'] = False
            self.write_data()
        self.settings = settings
        self.episodes = []

    def _print(self, obj):
        print('[%s]:' % self.id, obj)

    def log(func):
        def wrapper(self, *args, **kw):
            start_time = time.time()
            onstart = lambda: self._print('%s start' % func.__name__)
            ret = func(self, *args, onstart=onstart, **kw)
            end_time = time.time()
            if ret == DONE_MARK:
                self._print('%s takes %.2fs' % (func.__name__,
                                                end_time - start_time))
            elif ret == FAIL_MARK:
                self._print('%s failed' % func.__name__)
            elif ret == SKIP_MARK:
                self._print('%s skiped' % func.__name__)
            return ret
        return wrapper

    def set_data_from_bili(self, season_id):
        info = bangumi.get_collective_info(season_id=season_id)
        self.data = {
            'name': info['title'],
            'type': 'season/bilibili',
            'info': {
                'ssId': season_id,
                'cover': info['cover']
            },
            # 链接不一定正确，需实测
            "wikiLink": "https://mzh.moegirl.org.cn/" + info['title'],
            "shortIntro": info['evaluate']
        }
        request.urlretrieve(info['cover'], path.join(COVER_DIR, self.id))
        set_refer('season/bilibili', season_id, self.id)

    def set_finished_presets(self):
        self.read_data()
        for preset in self.data['targetPresets']:
            if preset not in self.data['finishedPresets']:
                self.data['finishedPresets'].append(preset)
        self.write_data()

    @log
    def load_episodes(self, start=None, end=None, onstart=None):
        if self.data['type'] == 'season/bilibili':
            season_id = self.data['info']['ssId']
            info = bangumi.get_collective_info(season_id=season_id)
            episodes = info['episodes'][start:end]
            onstart and onstart()
            for i in episodes:
                self.episodes.append(
                    Episode(bili_epid=i['id'], settings=self.settings, season_id=self.id))
            return DONE_MARK

    def add_episode(self, epid):
        episode = Episode(from_id=epid, season_id=self.id,
                          settings=self.settings)
        self.episodes.append(episode)

    def write_data(self):
        db_seasons.put(self.id.encode(),
                       json.dumps(self.data, ensure_ascii=False).encode())

    def read_data(self):
        self.data = json.loads(db_seasons.get(self.id.encode()))

    def set_data(self, key, value):
        self.read_data()
        self.data[key] = value
        self.write_data()

    def need_download(self):
        for ep in self.episodes:
            if ep.need_download():
                return True
        return False

    def need_process(self):
        for ep in self.episodes:
            if ep.need_process():
                return True
        return False

    @log
    def download(self, onstart=None):
        if not self.need_download():
            return SKIP_MARK
        onstart and onstart()
        self.set_data('isDownloading', True)
        for ep in self.episodes:
            ep.download()
        self.set_data('isDownloading', False)
        return DONE_MARK

    @log
    def process(self, onstart=None):
        if not self.need_process():
            return SKIP_MARK
        onstart and onstart()
        self.set_data('isProcessing', True)
        for ep in self.episodes:
            ep.process()
        self.set_data('isProcessing', False)
        self.set_finished_presets()
        return DONE_MARK

    def train_add(self):
        for ep in self.episodes:
            ep.train_add()

    def update_data(self, info):
        self.read_data()
        for key in info:
            if key in self.data:
                self.data[key] = info[key]
        self.write_data()

    def update_settings(self, settings):
        self.settings = settings
        self.read_data()
        if 'presets' in settings:
            self.data['targetPresets'] = settings['presets']
        self.write_data()
        for ep in self.episodes:
            ep.update_settings(settings)


class Episode(object):
    def __init__(self, bili_epid=None, from_id=None,
                 settings=None, season_id=None):
        if from_id:
            self.id = from_id
            data = db_episodes.get(from_id.encode())
            if data:
                self.data = json.loads(data)
            else:
                raise ValueError('Invalid `from_id`')
        elif bili_epid and get_id('episode/bilibili', bili_epid):
            self.id = get_id('episode/bilibili', bili_epid)
            self.data = json.loads(db_episodes.get(self.id.encode()))
        else:
            if bili_epid:
                self.id = str(get_num('maxEpId'))
                self.data = self.get_data_from_bili(bili_epid)
                self.data['quality'] = settings['quality']
                self.data['SESSDATA'] = settings['SESSDATA']
                set_refer('episode/bilibili', bili_epid, self.id)
            self.data['tag'] = settings['tag']
            self.data['status'] = 'waiting'
            self.data['finishedPresets'] = []
            self.data['targetPresets'] = settings['presets']
            self.data['seasonId'] = season_id

        self.write_data()
        self.download_path = path.join(
            DOWNLOAD_DIR, self.data['seasonId'], self.id)
        self.video_out_path = path.join(VIDEO_OUT_DIR, self.id)
        self.img_tmp_path = path.join(
            IMG_TMP_DIR, self.data['seasonId'], self.id)

    def log(func):
        def wrapper(self, *args, **kw):
            start_time = time.time()
            onstart = lambda: self._print('%s start' % func.__name__)
            ret = func(self, *args, onstart=onstart, **kw)
            end_time = time.time()
            if ret == DONE_MARK:
                self._print('%s takes %.2fs' % (func.__name__,
                                                end_time - start_time))
            elif ret == FAIL_MARK:
                self._print('%s failed' % func.__name__)
            return ret
        return wrapper

    def _print(self, obj):
        print('[%s>%s]:' % (self.data['seasonId'], self.id), obj)

    def get_data_from_bili(self, epid):
        info = bangumi.get_episode_info(epid=epid)
        return {
            'name': info['h1Title'],
            'type': 'episode/bilibili',
            'info': {
                'bvid': info['epInfo']['bvid'],
                'epid': epid,
                'cid': info['epInfo']['cid']
            },
            'hasNext': info['epInfo']['hasNext'],
            'title': info['epInfo']['title']
        }

    def set_info(self, info):
        for key in self.data:
            if key in info:
                self.data['key'] = info['key']

    def set_data(self, key, value):
        self.read_data()
        self.data[key] = value
        self.write_data()

    def write_data(self):
        db_episodes.put(self.id.encode(),
                        json.dumps(self.data, ensure_ascii=False).encode())

    def read_data(self):
        self.data = json.loads(db_episodes.get(self.id.encode()))

    def need_download(self):
        if path.exists(path.join(self.download_path, 'done')):
            return False
        if path.exists(path.join(self.img_tmp_path, 'ready')) and path.exists(path.join(self.video_out_path, 'done')):
            return False
        for preset in self.data['targetPresets']:
            if preset not in self.data['finishedPresets']:
                return True
        return False

    def need_process(self):
        for preset in self.data['targetPresets']:
            if preset not in self.data['finishedPresets']:
                return True

    def need_to_image(self):
        if path.exists(path.join(self.img_tmp_path, 'ready')):
            return False
        return True

    def need_compress(self):
        if path.exists(path.join(self.video_out_path, 'done')):
            return False
        return True

    @log
    def download(self, onstart=None):
        self.read_data()
        if not self.need_download():
            return SKIP_MARK
        onstart and onstart()
        if self.data['type'] == 'episode/bilibili':
            ret = download_bilibili_video(
                self.data['info']['epid'], self.download_path, {
                    'quality': self.data['quality'],
                    'SESSDATA': self.data['SESSDATA']
                })
        if ret < 0:
            self.set_data('status', 'download_failed')
            return FAIL_MARK
        else:
            self.set_data('status', 'downloaded')
            create_mark(path.join(self.download_path, 'done'))
            return DONE_MARK

    def get_downloaded_video(self):
        flv = path.join(self.download_path, 'video.flv')
        mp4 = path.join(self.download_path, 'video.mp4')
        if path.exists(flv):
            return flv
        elif path.exists(mp4):
            return mp4
        raise FileNotFoundError('video not found')

    @log
    def compress(self, onstart=None):
        self.read_data()
        if not self.need_compress():
            return SKIP_MARK
        onstart and onstart()
        self._print('compressing')
        video = self.get_downloaded_video()
        out_video = path.join(self.video_out_path, 'video.mp4')
        if not path.exists(self.video_out_path):
            os.makedirs(self.video_out_path)
        if path.exists(out_video):
            os.remove(out_video)
        subprocess.run("ffmpeg -i %s -vcodec libx264 -acodec aac -b:a 64k -ar 44100 -crf %d -tune animation -vf scale=-2:%d %s -y"
                       % (video, PROC_CONF['crf'], PROC_CONF['resolution'], out_video), check=True, shell=True)  # 压缩视频
        create_mark(path.join(self.video_out_path, 'done'))
        self._print('compressed')
        return DONE_MARK

    @log
    def to_image(self, onstart=None):
        self.read_data()
        if not self.need_to_image():
            return SKIP_MARK
        onstart and onstart()
        video = self.get_downloaded_video()
        if not path.exists(self.img_tmp_path):
            os.makedirs(self.img_tmp_path)
        pic_path = os.path.join(self.img_tmp_path, "%d.jpg")
        subprocess.run(
            "ffmpeg -i %s -r %d -q:v 2 -f image2 %s"
            % (video, PROC_CONF['rate'], pic_path), check=True, shell=True)
        create_mark(path.join(self.img_tmp_path, 'ready'))
        return DONE_MARK

    @log
    def insert_into_storage(self, onstart=None):
        onstart and onstart()
        frame_group = FrameGroup(self.img_tmp_path, PROC_CONF['rate'])
        frame_group.filte_sim(PROC_CONF['filteSimlity'])
        load_frame_box(disable_gpu=False)
        insert_presets = []
        for preset in self.data['targetPresets']:
            if preset not in self.data['finishedPresets']:
                insert_presets.append(preset)
        frame_box.insert(frame_group.frames, self.id, insert_presets)
        if PROC_CONF['removeFrame']:
            frame_group.clear_all()
            os.remove(path.join(self.img_tmp_path, 'ready'))
            os.remove(self.img_tmp_path)
        self.set_finished_presets()
        return DONE_MARK

    def set_finished_presets(self):
        self.read_data()
        for preset in self.data['targetPresets']:
            if preset not in self.data['finishedPresets']:
                self.data['finishedPresets'].append(preset)
        self.write_data()

    @log
    def process(self, onstart=None):
        self.read_data()
        if not self.need_process():
            return SKIP_MARK
        if self.need_download():
            return SKIP_MARK
        onstart and onstart()
        try:
            self.compress()
            self.to_image()
            self.insert_into_storage()
        except Exception as e:
            print(e)
            self.set_data('status', 'process_failed')
            return FAIL_MARK
        self.set_data('status', 'finished')
        if PROC_CONF['removeVideo']:
            self.remove_video()
        return DONE_MARK

    def add_to_trainer(self):
        frame_group = FrameGroup(self.img_tmp_path, PROC_CONF['rate'])
        frame_group.filte_sim(PROC_CONF['filteSimlity'])
        load_trainer()
        pca_trainer.add_frames(frame_group.random_select(
            config['trainPCA']['selectNum']))

    def train_add(self):
        self.download()
        self.to_image()
        self.add_to_trainer()

    def remove_video(self, onstart=None):
        if not path.exists(self.download_path):
            return SKIP_MARK
        onstart and onstart()
        try:
            os.remove(self.get_downloaded_video())
            os.remove(path.join(self.download_path, 'done'))
            os.rmdir(self.download_path)
            return DONE_MARK
        except Exception as e:
            print(e)
            return FAIL_MARK

    def update_data(self, info):
        self.read_data()
        for key in info:
            if key in self.data:
                self.data[key] = info[key]
        self.write_data()

    def update_settings(self, settings):
        self.read_data()
        if 'tag' in settings:
            self.data['tag'] = settings['tag']
        if 'presets' in settings:
            self.data['targetPresets'] = settings['presets']
        self.write_data()


class FrameGroup:
    def __init__(self, img_path, rate):
        self.path = img_path
        self.rate = rate
        self.frames = self.get_frames()
        self.BUFFER_MAX_LEN = 25

    def log(func):
        def wrapper(self, *args, **kw):
            print('%s start' % (func.__name__))
            start_time = time.time()
            ret = func(self, *args, **kw)
            t = time.time() - start_time
            fps = len(self.frames)/t
            print('%s takes %.2fs, fps=%.2f' % (func.__name__, t, fps))
            return ret
        return wrapper

    @log
    def get_frames(self):
        files = os.listdir(self.path)
        frames = []
        for i in files:
            file_path = path.join(self.path, i)
            if not path.isfile(file_path):
                continue
            matched = re.match(r'^(\d+)\.jpg$', i)
            if not matched:
                continue
            frames.append({
                'file': file_path,
                'time': int(matched.group(1))/self.rate,
                'phash': imagehash.phash(Image.open(file_path))
            })
            frames.sort(key=lambda x: x['time'])
        return frames

    @log
    def filte_sim(self, rate):
        hash_buffer = []
        frames = []
        for i in range(len(self.frames)):
            frame = self.frames[i]
            has_sim = False
            for phash in hash_buffer:
                if (1 - (frame['phash'] - phash) / len(phash.hash) ** 2) >= rate:
                    has_sim = True
                    break
            if has_sim:
                os.remove(frame['file'])
            else:
                hash_buffer.append(frame['phash'])
                frames.append(frame)
                if len(hash_buffer) > self.BUFFER_MAX_LEN:
                    hash_buffer.pop(0)
        self.frames = frames

    def clear_all(self):
        for frame in self.frames:
            os.remove(frame['file'])
        self.frames = []

    def random_select(self, num):
        return random.sample(self.frames, num)


def search(img_path, preset=None, resultNum=None, tag=None):
    resultNum = resultNum if resultNum else 20 if not tag else 100
    load_frame_box(disable_gpu=True)
    results = frame_box.search_img(
        img_path, resultNum=resultNum, preset_name=preset)
    _set_epinfo(results)
    _set_bili_url(results)
    if tag:
        results = _filte_tag(results, tag)
    return results


def _set_epinfo(results):
    for result in results:
        episode = Episode(from_id=result['epid'])
        result['name'] = episode.data['name']
        result['type'] = episode.data['type']
        result['info'] = episode.data['info']
        result['title'] = episode.data['title']
        result['seasonId'] = episode.data['seasonId']
        result['previewUrl'] = '/video/%s/video.mp4' % result['epid']
    return results


def _set_bili_url(results):
    for i in results:
        if i['type'] == 'episode/bilibili':
            i['biliUrl'] = 'https://www.bilibili.com/bangumi/play/ep%d?t=%.1f' % (
                i['info']['epid'], i['time'])
    return results


def _filte_tag(results, tag):
    return [i for i in results if i['tag'] == tag]


def sort_key(id):
    if re.match(r'^\d+$', id):
        return int(id)
    return id


def get_status():
    seasons = {}
    db_seasons.open()
    for key, value in db_seasons.db:
        season_id = key.decode()
        season = json.loads(value.decode())
        seasons[season_id] = {
            'name': season['name'],
            'type': season['type'],
            'isDownloading': season['isDownloading'],
            'isProcessing': season['isProcessing'],
            'targetPresets': season['targetPresets'],
            'finishedPresets': season['finishedPresets']
        }
    db_seasons.close()
    presets = frame_box.get_presets_status()
    for preset_name in presets:
        preset = presets[preset_name]
        season = seasons[season_id]
        preset['seasonIds'] = []
        for season_id in seasons:
            if preset_name in season['finishedPresets']:
                preset['seasonIds'].append(season_id)
        preset['seasonIds'].sort(key=sort_key)
    return {
        'seasons': seasons,
        'presets': presets
    }


def train_apply():
    pca_trainer.train()
