# Search Anime By Image

以图搜番。这是一个动漫场景搜索引擎服务端。可以通过番剧某一刻的截图，反向搜索它出自哪部番，以及出现的确切时间。[网站前端](https://anime.krytro.com)

与[trace.moe](https://github.com/soruly/trace.moe)相比，由于使用的是`vgg16`模型提取图像特征，此项目或许能够提供鲁棒性更高的搜索服务。缺点是性能开销更大，收录比较慢。目前仍处于测试阶段

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

- 目前仅支持从B站API下载

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

README完善中。。。。。。

## 技术实现

- 通过[bilibili](https://www.bilibili.com/)的API，自动下载番剧，并初步保存番剧信息

- 使用[ffmpeg](https://ffmpeg.org/about.html)压缩视频并转为mp4，放到网站静态目录下
- 使用[ffmpeg](https://ffmpeg.org/about.html)，将视频以一定采样率转为图片，放到临时目录
- 逐帧读取图片，通过`dhash`算法过滤掉相邻的相似图片，其余的图片用`vgg16`模型提取特征向量，添加到`milvus`。添加的每帧的`id`、`time`、所属`cid`等对应信息存到数据库
- 搜索时同样提取图像特征向量，用`milvus`搜索，返回`帧id`，再通过数据库查询其他信息

## Thanks · 鸣谢

- 下载、预处理视频的部分参考[以图搜番](https://gitee.com/tuxiaobei/find_video_by_pic#https://github.com/Henryhaohao/Bilibili_video_download)

- 使用了[`keras vgg16`预训练模型](https://keras.io/api/applications/vgg/)提取图像特征
- 使用了[milvus](https://github.com/milvus-io/milvus/)索引、搜索向量
- 自动裁剪图像黑边的实现，来源于[trace.moe](https://github.com/soruly/trace.moe)的`crop.py`

