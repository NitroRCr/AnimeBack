
import os
import re
import sys
import time
import json
import init_conf
from common import (
    Episode,
    Season,
    get_json,
    train_apply,
    sort_key,
    db_status,
    SKIP_MARK,
    DONE_MARK,
    HAS_ERR_MARK,
    FAIL_MARK
)

config = get_json('config.json')

PROC_LIST_KEY = b'proc_list'
HISTORY_KEY = b'history'
if not db_status.get(PROC_LIST_KEY):
    db_status.put(PROC_LIST_KEY, json.dumps([]).encode())
if not db_status.get(HISTORY_KEY):
    db_status.put(HISTORY_KEY, json.dumps({
        'downloadBilibili': None,
        'downloadSakura': None
    }).encode())


def get_history(key):
    return json.loads(db_status.get(HISTORY_KEY).decode())[key]

def put_history(key, value):
    history = json.loads(db_status.get(HISTORY_KEY).decode())
    history[key] = value
    db_status.put(HISTORY_KEY, json.dumps(history).encode())

def proc_list_push(season_id):
    proc_list = json.loads(db_status.get(PROC_LIST_KEY).decode())
    proc_list.append(season_id)
    db_status.put(PROC_LIST_KEY, json.dumps(proc_list).encode())

def proc_list_pop(index):
    proc_list = json.loads(db_status.get(PROC_LIST_KEY).decode())
    if index >= len(proc_list):
        return None
    ret = proc_list.pop(index)
    db_status.put(PROC_LIST_KEY, json.dumps(proc_list).encode())
    return ret

def proc_list_get(index):
    proc_list = json.loads(db_status.get(PROC_LIST_KEY).decode())
    if index >= len(proc_list):
        return None
    return proc_list[index]

def download_bilibili():
    queue = config['downloadBilibili']['queue']['seasons']
    default = config['downloadBilibili']['default']
    ids = [item['seasonId'] for item in queue]
    history_id = get_history('downloadBilibili')
    if history_id in ids:
        index = ids.index(history_id)
        queue = queue[index:] + queue[:index]
    for s in queue:
        bili_ssid = s['seasonId']
        settings = {
            'SESSDATA': s['SESSDATA'] if 'SESSDATA' in s else default['SESSDATA'],
            'quality': s['quality'] if 'quality' in s else default['quality'],
            'presets': s['presets'] if 'presets' in s else default['presets'],
            'tag': s['tag'] if 'tag' in s else default['tag'],
        }
        episodes_str = s['episodes'] if 'episodes' in s else default['episodes']
        override = s['override'] if 'override' in s else default['override']
        start, end = episodes_str.split(":")
        if start == '^':
            start = None
        else:
            start = int(start)
        if end == '$':
            end = None
        else:
            end = int(end)
        season = Season(bili_ssid=bili_ssid, settings=settings)
        if season.load_episodes(start, end) == FAIL_MARK:
            continue
        if override:
            season.update_settings(settings)
        need_process = season.need_process()
        if need_process and season.need_download():
            put_history('downloadBilibili', season.data['info']['ssId'])
            season.download()
        if need_process:
            proc_list_push(season.id)


def download_sakura():
    queue = config['downloadSakura']['queue']['seasons']
    default = config['downloadSakura']['default']
    ids = [item['seasonId'] for item in queue]
    history_id = get_history('downloadSakura')
    if history_id in ids:
        index = ids.index(history_id)
        queue = queue[index:] + queue[:index]
    for s in queue:
        sakura_id = s['seasonId']
        settings = {
            'presets': s['presets'] if 'presets' in s else default['presets'],
            'tag': s['tag'] if 'tag' in s else default['tag'],
        }
        episodes_str = s['episodes'] if 'episodes' in s else default['episodes']
        override = s['override'] if 'override' in s else default['override']
        start, end = episodes_str.split(":")
        if start == '^':
            start = None
        else:
            start = int(start)
        if end == '$':
            end = None
        else:
            end = int(end)
        season = Season(sakura_id=sakura_id, settings=settings)
        season.load_episodes(start, end)
        if override:
            season.update_settings(settings)
        need_process = season.need_process()
        if need_process and season.need_download():
            put_history('downloadSakura', season.id)
            season.download()
        if need_process:
            proc_list_push(season.id)


def process():
    failed = []
    while proc_list_get(0):
        season_id = proc_list_get(0)
        season_dir = os.path.join(config['imgTmpDir'], season_id)
        season = Season(from_id=season_id)
        epids = []
        if os.path.exists(season_dir):
            for ep_dirname in os.listdir(season_dir):
                ep_dir = os.path.join(season_dir, ep_dirname)
                if not os.path.isdir(ep_dir):
                    continue
                if not re.match(r'^\d+$', ep_dirname):
                    continue
                if not os.path.exists(os.path.join(ep_dir, 'ready')):
                    continue
                season.add_episode(ep_dirname)
                epids.append(ep_dirname)

        season_dir = os.path.join(config['downloadDir'], season_id)
        if os.path.exists(season_dir):
            for ep_dirname in os.listdir(season_dir):
                ep_dir = os.path.join(season_dir, ep_dirname)
                if not os.path.isdir(ep_dir):
                    continue
                if not re.match(r'^\d+$', ep_dirname):
                    continue
                if not os.path.exists(os.path.join(ep_dir, 'done')):
                    continue
                if ep_dirname in epids:
                    continue
                season.add_episode(ep_dirname)

        season.episodes.sort(key=lambda ep: sort_key(ep.id))
        if season.process() == HAS_ERR_MARK:
            failed.append(season.id)
        proc_list_pop(0)
    for i in failed:
        proc_list_push(i)


def train_pca():
    for epid in config['trainPCA']['episodes']:
        episode = Episode(from_id=str(epid))
        episode.train_add()
    train_apply()


def import_info(info):
    for i in info:
        if 'episode/' in i['type']:
            item = Episode(from_id=i['id'])
        elif 'season/' in i['type']:
            item = Season(from_id=i['id'])
        item.update_data(i)


def main():
    if len(sys.argv) <= 1:
        return
    if sys.argv[1] == 'download-bilibili':
        download_bilibili()
        restart()
    elif sys.argv[1] == 'download-sakura':
        download_sakura()
        restart()
    elif sys.argv[1] == 'process':
        process()
    elif sys.argv[1] == 'train-pca':
        train_pca()
    elif sys.argv[1] == 'import-info':
        import_info(get_json(sys.argv[2]))
    else:
        print('Invalid arg')
        return


def restart():
    global config
    new_config = get_json('config.json')
    if not new_config == config:
        config = new_config
        main()


if __name__ == '__main__':
    main()
