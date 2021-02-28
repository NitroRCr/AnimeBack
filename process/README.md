## 运行视频处理/入库程序

编辑`process/config.json`

```
{
    "rate": 5,
    "crf": 36,
    "resolution": 480,
    "videoOutPath": "../static/video",
    "downloadPath": "../download",
    "autoRemove": true
}
```

- `rate`：视频转为图片时，每秒的采样帧数
- `crf`：视频压缩的[Constant Rate Factor](https://trac.ffmpeg.org/wiki/Encode/H.264)
- `resolution`：视频压缩后的分辨率（宽）
- `videoOutPath`：视频压缩输出的目录
- `downloadPath`：下载目录，将从此目录读取视频
- `autoRemove`：处理/入库之后是否删除下载目录下的文件

在`process`目录下，运行：

```bash
$ python main.py
```

该目录下，`finish.json`将储存已处理并入库的`cid`，`failed.json`储存处理失败的`cid`

