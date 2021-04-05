# Search Anime By Image

以图搜番。这是一个动漫场景搜索引擎服务端。可以通过番剧某一刻的截图，反向搜索它出自哪部番，以及出现的确切时间。[网站前端](https://anime.krytro.com)

与[trace.moe](https://github.com/soruly/trace.moe)相比，由于使用的是`vgg16`模型提取图像特征，此项目或许能够提供鲁棒性更高，更准确的搜索服务。也因此性能开销更大，收录比较慢。目前仍处于测试阶段

## 部署

### 环境要求

需要安装`python3`；需要安装`ffmpeg`

安装依赖项：

```bash
pip install bilibili_api imagehash pillow tensorflow keras flask pymilvus opencv-python sklearn joblib
```

### 运行

- 初始化配置文件

```bash
python init_conf.py
```

- 安装并启动[milvus](https://milvus.io/cn/)

- 编辑`config.json`：

  - ```json
    {"milvus_host": "127.0.0.1", "milvus_port": 19530}
    ```

  - 设置为`milvus`正在运行的地址和端口

- [运行下载程序](https://github.com/NitroRCr/SearchAnimeByImage/tree/main/download_bilibili)
- [运行视频处理/入库程序](https://github.com/NitroRCr/SearchAnimeByImage/tree/main/process)

#### 运行网站后端

```bash
python app.py
```

此方法仅供测试。生产环境请参考[Flask部署方式](https://dormousehole.readthedocs.io/en/latest/deploying/index.html)

下面 的例子使用`gunicorn`， 4 worker 进程（ `-w 4` ）来运行 Flask 应用，绑定到 localhost 的 4000 端口（ `-b 127.0.0.1:4000` ）:

```bash
gunicorn -w 4 -b 127.0.0.1:4000 app:flask_app
```

## 技术实现

- 通过[bilibili](https://www.bilibili.com/)的API，自动下载番剧，并初步保存番剧信息

- 使用[ffmpeg](https://ffmpeg.org/about.html)压缩视频并转为mp4，放到网站静态目录下
- 使用[ffmpeg](https://ffmpeg.org/about.html)，将视频以一定采样率转为图片，放到临时目录
- 逐帧读取图片，通过`dhash`算法过滤掉相邻的相似图片，其余的图片用`vgg16`模型提取特征向量，添加到`milvus`。添加的每帧的`id`、`time`、所属`cid`等对应信息存到数据库
- 搜索时同样提取图像特征向量，用`milvus`搜索，返回`帧id`，再通过数据库查询其他信息

## To-do

- [ ] 支持`Xception`预训练模型与`PCA`降维
- [ ] 训练更符合需求的模型
- [ ] 实现对op/ed的优化
- [ ] 支持`mysql`数据库
- [ ] 自动从[樱花动漫](http://www.yhdm.io/)下载
- [ ] 开放搜索API

## Thanks · 鸣谢

- 下载、预处理视频的部分参考[以图搜番](https://gitee.com/tuxiaobei/find_video_by_pic#https://github.com/Henryhaohao/Bilibili_video_download)。部分思路来自[tuxiaobei](https://gitee.com/tuxiaobei)
- VGG16：[Very Deep Convolutional Networks for Large-Scale Image Recognition](https://arxiv.org/abs/1409.1556)
- 使用了[milvus](https://github.com/milvus-io/milvus/)索引、搜索向量
- 自动裁剪图像黑边的实现，来源于[trace.moe](https://github.com/soruly/trace.moe)的`crop.py`
