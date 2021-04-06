import json
import os
CONF_TEMPLATES = {
    "config.json": {
        "milvus_host": "127.0.0.1",
        "milvus_port": 19530,
        "downloadDir": "download",
        "videoOutDir": "static/video",
        "imgTmpDir": "tmp_images",
        "downloadBilibili": {
            "queue": {
                "seasons": []
            },
            "default": {
                "SESSDATA": "",
                "quality": 64,
                "presets": [
                    "Xception_PCA"
                ],
                "tag": "$seasonId",
                "episodes": "^:$"
            },
        },
        "process": {
            "rate": 5,
            "crf": 36,
            "resolution": 480,
            "removeVideo": True,
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
    'static/json',
    'static/img',
    'static/video',
    'download',
    'tmp_images',
    'db',
    'pca'
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
