import json
import os
CONF_TEMPLATES = {
    "state.json": {
        "requestNum": 0
    },
    "config.json": {
        "milvus_host": "127.0.0.1",
        "milvus_port": 19530
    },
    "download_bilibili/failed.json": [],
    "download_bilibili/finish.json": [],
    "download_bilibili/setting.json": {
        "queue": {
            "season_id": [],
            "epid": []
        },
        "SESSDATA": "",
        "downloadPath": "../download",
        "quality": 64
    },
    "static/json/info.json": {
        "seasons": [],
        "frameNum": 0
    },
    "process/config.json": {
        "rate": 5,
        "crf": 36,
        "resolution": 480,
        "videoOutPath": "../static/video",
        "downloadPath": "../download",
        "autoRemove": True
    },
    "process/finish.json": [],
    "process/failed.json": [],
    "process/pre.json": {"frame": 0}
}
DIRS = [
    'static',
    'static/json',
    'static/img',
    'static/video',
    'process/image',
    'download'
]

for i in DIRS:
    if not os.path.exists(i):
        print('mkdir', i)
        os.mkdir(i)

for i in CONF_TEMPLATES:
    if not os.path.exists(i):
        print("init", i)
        f = open(i, 'w')
        f.write(json.dumps(CONF_TEMPLATES[i], indent=4))
        f.close()
