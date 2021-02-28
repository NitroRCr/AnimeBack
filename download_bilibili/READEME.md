## 通过API自动从B站下载视频

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
    "SESSDATA": "",
    "downloadPath": "../download",
    "quality": 64
}
```

- `queue`：下载队列
  - `season_id`：通过`season_id`下载的列表，每个元素的第一项为字符串，指定该season的tag，用于搜索时指定tag。第二项为B站的番剧id
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
$ python down_bilibili.py
```

该目录下，`finish.json`将储存已下载的`cid`，`failed.json`储存下载失败的`cid`