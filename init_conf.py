import json
import os
CONF_TEMPLATES = {
    "state.json": {
        "requestNum": 0
    },
    "download_bilibili/failed.json": [],
    "download_bilibili/finish.json": [],
    "download_bilibili/config.json": {
        "videoOutPath": "static/video",
        "SESSDATA": ""
    },
    "download_bilibili/pre.json": {"frame": 0},
    "download_bilibili/setting.json": {
        "queue": {
            "season_id": [
                []
            ],
            "epid": [
                []
            ]
        },
        "rate": 5,
        "crf": 36,
        "resolution": 480
    }
}

for i in CONF_TEMPLATES:
    if not os.path.exists(i):
        print("init", i)
        f = open(i, 'w')
        f.write(json.dumps(CONF_TEMPLATES[i]))
        f.close()
