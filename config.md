## 配置指南
配置文件`config.json`:
```javaScript
{
    // 运行milvus的主机和端口
    "milvus_host": "127.0.0.1",
    "milvus_port": 19530,
    // 下载目录
    "downloadDir": "download",
    // 压缩视频的输出目录
    "videoOutDir": "static/video",
    // 帧截图临时目录
    "imgTmpDir": "tmp_images",
    // 动漫封面图片下载目录
    "coverDir": "static/img/cover",
    // 从B站下载的相关配置
    "downloadBilibili": {
        // 下载队列
        "queue": {
            // 需下载的季(season)的列表
            "seasons": [
                {
                    // 
                    "SESSDATA"： "27786f15%2C1626621493%2C3b652*11",
                    "quality": 64,
                    "presets": [
                        "Xception_PCA",
                        "Xception_PQ"
                    ],
                    "tag": "$seasonId",
                    "episodes": "^:$",
                    "override": false
                }
            ]
        },
        "default": {
            "SESSDATA": "27786f15%2C1626621493%2C3b652*11",
            "quality": 64,
            "presets": [
                "Xception_PCA",
                "Xception_PQ"
            ],
            "tag": "$seasonId",
            "episodes": "^:$",
            "override": false
        }
    },
    "process": {
        "rate": 5,
        "crf": 36,
        "resolution": 480,
        "removeVideo": true,
        "filteSimlity": 0.85,
        "seasonIds": []
    },
    "trainPCA": {
        "episodes": ["1","58","38","59","60","61",
            "62", "63", "64", "65"],
        "selectNum": 512
    }
}
```
### 一些解释
- 季(season)：对应动漫的每个季度
- 剧集(episode)：对应动漫的每一话
- 模型(model)：用于提取图像特征。在`models`目录下定义，在`frame_box.py`中导入。我们预设了几个使用深度学习网络的模型。
- 预设(preset)：在`frame_box.py`中定义。每个预设可配置不同的索引参数、搜索参数和模型。编辑下载队列时可指定录入的预设
