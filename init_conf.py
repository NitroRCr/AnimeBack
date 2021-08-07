import os
import json

CONF_TEMPLATES = {
    "config.json": {
        "milvus_host": "127.0.0.1",
        "milvus_port": 19530,
        "keras_cuda": False,
        "ffmpeg_cuda": False,
        "downloadDir": "download",
        "videoOutDir": os.path.join("static", "video"),
        "imgTmpDir": "tmp_images",
        "coverDir": os.path.join("static", "img", "cover"),
        "logFile": "AnimeBack.log",
        "downloadBilibili": {
            "queue": {
                "seasons": []
            },
            "default": {
                "SESSDATA": "",
                "quality": 64,
                "audioQuality": 30216,
                "presets": [
                    "ResNetFlat",
                    "ResNetFeat"
                ],
                "tag": "$seasonId",
                "episodes": "^:$",
                "override": False
            },
        },
        "downloadSakura": {
            "queue": {
                "seasons": []
            },
            "default": {
                "presets": [
                    "ResNetFlat",
                    "ResNetFeat"
                ],
                "tag": "$seasonId",
                "episodes": "^:$",
                "override": False
            },
        },
        "process": {
            "rate": 5,
            "crf": 36,
            "resolution": 480,
            "removeVideo": True,
            "removeFrame": False,
            "filteSimlity": 0.85
        },
        "trainPCA": {
            "episodes": [],
            "selectNum": 512
        }
    }
}
DIRS = [
    'static',
    os.path.join('static', 'json'),
    os.path.join('static', 'img'),
    os.path.join('static', 'img', 'cover'),
    os.path.join('static', 'img', 'upload'),
    os.path.join('static', 'video'),
    'download',
    'tmp_images',
    'db',
    'pca',
    'saved_models'
]

def init():
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

init()