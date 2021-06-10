## 配置指南
配置文件`config.json`:
- `milvus_host`: 运行milvus的主机
- `milvus_port`: milvus绑定的端口
- `keras_cuda`: 是否使用`CUDA`加速特征提取（为减少显存消耗，仅在处理部分启用）
- `downloadDir`: 视频下载目录
- `imgTmpDir`: 帧截图临时目录
- `coverDir`: 动漫封面图片下载目录

**下载部分**

从B站下载

`downloadBilibili`: 

- `seasons`: 需下载的季(season)的列表，每一项有以下参数：
  - `seasonId`: 必填。该季在B站的id，在页面链接中查看。如`https://www.bilibili.com/bangumi/play/ss425/`，id为`425`
  - `quality`：下载画质，可选值：
    - `116`：`1080P60`（需要大会员）
    - `112`：`1080P+`（需要大会员）
    - `80`：`1080P`
    - `74`：`720P60`（需要大会员）
    - `64`：`720P`
    - `32`：`480P`
    - `16`：`360P`
  - `presets`: 将会录入的预设(preset)
  - `tag`: 标签。用于搜索结果的过滤。
  - `episodes`: 将会下载的剧集范围。用切片索引表示。默认`^:$`，从开始(`^`)到结束(`$`)。
  - `override`: 是否覆写参数。如果为`false`，已下载的`season`的参数不会更新
- `default`: 每个season的默认参数

从`Halihali`下载

`downloadSakura`:

- `seasons`: 需下载的季(season)的列表，每一项有以下参数：
  - `seasonId`: 必填。该季在[halihali](http://halihali2.com/)或者[AnimePure](https://animepure.netlify.app/)的id，在页面链接中查看。如`https://animepure.netlify.app/bangumi/18217/1`，id为`18217`
  - `presets`: 将会录入的预设(preset)
  - `tag`: 标签。用于搜索结果的过滤。
  - `episodes`: 将会下载的剧集范围。用切片索引表示。默认`^:$`，从开始(`^`)到结束(`$`)。
  - `override`: 是否覆写参数。如果为`false`，已下载的`season`的参数不会更新
- `default`: 每个season的默认参数

**处理部分**

`process`: 

- `rate`: 视频转截图的采样率。单位：帧/秒
- `crf`: 视频压缩的码率控制参数。越大压缩率越高
- `resolution`: 视频压缩的分辨率
- `removeVideo`: 是否在处理后删除原视频
- `removeFrame`: 是否在处理后删除帧截图
- `filteSimlity`: 相似帧过滤阈值。录入时将会过滤掉相似度高于此的相邻帧

**PCA训练部分**

如果预设启用了PCA降维，就需要相应的PCA模型。我们训练了几个PCA模型，可[前往下载](https://file.krytro.com:1443/AnimeBack/pca/)。也可以直接训练。在这里可以配置训练PCA模型的参数。

`trainPCA`:

- `episodes`: 用于训练的剧集的id。这些剧集将作为训练集，格式为`[< epid >, < epid >, ...]`
- `selectNum`: 从每个剧集随机抽取的帧数

### 一些解释

- 季(season)：对应动漫的每个季度。包含若干剧集。有一个字符串id(`seasonId`)。
- 剧集(episode)：对应动漫的每一话。有一个字符串id(`epid`)。下载目录为`< downloadDir >/< seasonId >/< epid >`。帧截图目录为`< imgTmpDir >/< seasonId >/< epid >`
- 模型(model)：用于提取图像特征。在`models`目录下定义，在`frame_box.py`中导入。我们预设了几个使用深度学习网络的模型。
- 预设(preset)：在`frame_box.py`中定义。每个预设可配置不同的索引参数、搜索参数和模型。编辑下载队列时可指定录入的预设