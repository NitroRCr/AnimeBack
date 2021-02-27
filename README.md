# Search Anime By Image

这是一个动漫场景搜索引擎服务端。可以通过番剧某一刻的截图，反向搜索它出自哪部番，以及出现的确切时间。[网站前端](https://anime.krytro.com)

## 部署

### 环境要求

需要安装`python3`；需要安装`ffmpeg`

安装依赖项：

```bash
pip install bilibili_api imagehash pillow tensorflow keras flask pymilvus opencv-python
```

### 运行

初始化配置文件

```bash
python init_conf.py
```

安装并启动[milvus](https://milvus.io/cn/)

#### 运行下载程序

- 从B站API下载

编辑`download_bilibili/setting.json`：

```javascript
{
    "queue": {
        "season_id": [
            [
                "425",
                425
            ]
        ],
        "epid": []
    },
    "rate": 5,
    "resolution": 480,
    "SESSDATA": "",
    "downloadPath": "../download",
    "quality": 64
}
```

- `queue`：下载队列
  - `season_id`：通过`season_id`下载的列表，每个元素的第一项为字符串，指定该season的tag，用于搜索时指定tag。第二项为B站的番剧id
- `rate`：转为图片时，每秒的采样帧数
- `resolution`：压缩的分辨率（宽）
- `SESSDATA`：决定你能下载哪些视频/画质。登录B站后在cookie中查看
- `quality`：下载画质，可选值：
  - `116`：`1080P60`（需要大会员）
  - `112`：`1080P+`（需要大会员）
  - `80`：`1080P`
  - `74`：`720P60`（需要大会员）
  - `64`：`720P`
  - `32`：`480P`
  - `16`：`320P`
- `downloadPath`：下载目录

在`download_bilibili`目录下，运行：

```bash
python down_bilibili.py
```

该目录下，`finish.json`将储存已下载的`cid`，`failed.json`储存下载失败的`cid`

#### 运行视频处理/入库程序

编辑`process/config.json`

```

```

## 技术实现

- 使用`vgg16`