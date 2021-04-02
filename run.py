from common import Episode, Season, get_json
import os
import re
import sys
import time

config = get_json('config.json')

def download_bilibili():
    queue = config['downloadBilibili']['queue']
    default = config['downloadBilibili']['default']
    for s in queue['seasons']:
        bili_ssid = s['seasonId']
        settings = {
            'SESSDATA': s['SESSDATA'] if 'SESSDATA' in s else default['SESSDATA'],
            'quality': s['quality'] if 'quality' in s else default['quality'],
            'presets': s['presets'] if 'presets' in s else default['presets'],
            'tag': s['tag'] if 'tag' in s else default['tag'],
        }
        season = Season(bili_ssid, settings=settings)
        season.load_episodes()
        season.download()

def process():
    for dirname in os.listdir(config['downloadDir']):
        season_dir = os.path.join(config['downloadDir'], dirname)
        if not os.path.isdir(season_dir):
            continue
        if not re.match(r'^\d+$', dirname):
            continue
        season = Season(from_id=dirname)
        for ep_dirname in os.listdir(season_dir):
            ep_dir = os.path.join(season_dir, ep_dirname)
            if not os.path.isdir(ep_dir):
                continue
            if not re.match(r'^\d+$', ep_dirname):
                continue
            if not os.path.exists(os.path.join(ep_dir, 'done')):
                continue
            season.add_episode(ep_dirname)
        season.process()

def main():
    start_time = time.time()
    if len(sys.argv) <= 1:
        print('Must input arg')
        return
    if sys.argv[1] == 'download-bilibili':
        download_bilibili()
    elif sys.argv[1] == 'process':
        process()
    else:
        print('Invalid arg')
        return
    end_time = time.time()
    if (end_time - start_time) > 60:
        global config
        config = get_json('config.json')
        main()

if __name__ == '__main__':
    main()