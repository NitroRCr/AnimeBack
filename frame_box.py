# -*- coding: utf-8 -*-
import os
import sqlite3
import time
from bilibili_api import bangumi
from milvus import Milvus, IndexType, MetricType, Status
from extract_cnn_vgg16_keras import VGGNet

class FrameBox(object):
    def __init__(self):
        self.DB_PATH = os.path.join("sql", "frames.db")
        self.INIT_SQL_PATH = os.path.join("sql", "init.sql")
        self.BUFFER_MAX_LEN = 100
        self.frame_buffer = []
        self.COLL_NAME = "frames"
        self.model = VGGNet()
        self.milvus = None
        self.sql_conn = None
        self.sql_cursor = None
        self.curr_tag = ""
        self.curr_cid = ""
        self.curr_tags = []
        self.curr_cids = []

    def create_collection(self):
        self.milvus.create_collection({
            'collection_name': self.COLL_NAME,
            'dimension': 512,
            'index_file_size': 512,
            'metric_type': MetricType.L2
        })
        self.milvus.create_index(self.COLL_NAME, IndexType.IVF_SQ8, params = {
            "nlist": 2048
        })

    def get_all_cid(self):
        self.sql_cursor.execute("SELECT cid FROM cid")
        fetched =self.sql_cursor.fetchall()
        return [i[0] for i in fetched]

    def set_tag(self, tag):
        self.curr_tag = tag
        if (tag != "") and (tag not in self.curr_tags):
            self.milvus.create_partition(self.COLL_NAME, tag)
            self.curr_tags.append(tag)

    def set_brief(self, brief):
        cid = brief['cid']
        self.curr_cid = cid
        if cid not in self.curr_cids:
            epid = brief['epid']
            bvid = brief['bvid']

            try:
                info = bangumi.get_episode_info(epid=epid)
            except BaseException as e:
                print('except:', e)
                return

            name = info['h1Title']
            season_id = info['mediaInfo']['ssId']
            command = ('INSERT INTO cid (cid, name, epid, bvid, season_id)'
                'VALUES (%d, "%s", %d, "%s", %d)'%(cid, name, epid, bvid, season_id))
            try:
                self.sql_cursor.execute(command)
                print("add info", command)
            except sqlite3.IntegrityError as e:
                print("Warn: cid repeated")
            self.sql_conn.commit()
            self.curr_cids.append(cid)

    def connect(self):
        self.sql_conn = sqlite3.connect(self.DB_PATH)
        self.sql_cursor = self.sql_conn.cursor()
        self.milvus = Milvus(host='localhost', port='19530')
        
        collections = self.milvus.list_collections()[1]
        if not self.COLL_NAME in collections:
            self.create_collection()

        self.curr_tags = list(self.milvus.list_partitions(self.COLL_NAME))
        try:
            self.curr_cids = self.get_all_cid()
        except sqlite3.OperationalError as e:
            # first run
            self.init_db()
            print("table not found, created.")
            self.curr_cids = self.get_all_cid()

    def close(self):
        self.flush()
        self.sql_cursor.close()
        self.sql_conn.close()
        self.milvus.close()

    def append_to_buffer(self, feat, brief):
        if len(self.frame_buffer) >= self.BUFFER_MAX_LEN:
            self.flush()
        self.frame_buffer.append({"feat": feat, "brief": brief})

    def flush(self):
        if len(self.frame_buffer) == 0:
            return
        self.sql_cursor.execute("SELECT max(frame_id) FROM frames")
        now_id = self.sql_cursor.fetchall()[0][0]
        if now_id == None:
            now_id = 0
        vectors = []
        ids = []
        for i in self.frame_buffer:
            now_id += 1
            vectors.append(i['feat'])
            ids.append(now_id)
            brief = i['brief']
            self.sql_cursor.execute(
                'INSERT INTO frames (frame_id, cid, time) VALUES ("%d", %d, %f)'
                %(now_id, brief['cid'], brief['time'])
            )
        if self.curr_tag != "":
            res = self.milvus.insert(self.COLL_NAME, vectors,
                partition_tag=self.curr_tag, ids = ids)
        else:
            res = self.milvus.insert(collection_name = self.COLL_NAME,
                ids = ids, records = vectors)
        print("milvus response:", res)
        self.sql_conn.commit()
        self.frame_buffer = []
  
    def search_img(self, img_path, tags = None, resultNum = 20):
        vector = self.model.extract_feat(img_path)
        vector = vector.tolist()
        results = self.milvus.search(self.COLL_NAME, resultNum, [vector],
            partition_tags=tags, params={"nprobe": 64}, timeout=15)
        return [{'frame_id': result.id, 'score': 1 - result.distance/2}
            for result in results[1][0]]

    def search_frame_id(self, results):
        table_info = self.sql_cursor.execute('PRAGMA table_info(frames)').fetchall()
        keys = [i[1] for i in table_info]
        for i in results:
            self.sql_cursor.execute('SELECT * FROM frames WHERE frame_id=?', (i['frame_id'],))
            frame = self.sql_cursor.fetchall()[0]
            for j in range(len(keys)):
                i[keys[j]] = frame[j]
        return results

    def search_cid(self, results):
        table_info = self.sql_cursor.execute('PRAGMA table_info(cid)').fetchall()
        keys = [i[1] for i in table_info]
        for i in results:
            self.sql_cursor.execute('select * from cid where cid=?', (i['cid'],))
            cid_info = self.sql_cursor.fetchall()[0]
            for j in range(len(keys)):
                i[keys[j]] = cid_info[j]
        return results

    def search_with_info(self, img_path, tags = None, resultNum = 20):
        t_0 = time.time()
        results = self.search_img(img_path, tags, resultNum)
        t_1 = time.time()
        results = self.search_frame_id(results)
        t_2 = time.time()
        results = self.search_cid(results)
        t_3 = time.time()
        results = self.set_bili_url(results)
        t_4 = time.time()
        print({
            1: t_1 - t_0,
            2: t_2 - t_1,
            3: t_3 - t_2,
            4: t_4 - t_3,
            "all": t_4 - t_0
        })
        return results

    def init_db(self):
        sql_cmd_f = open(self.INIT_SQL_PATH)
        self.sql_cursor.executescript(sql_cmd_f.read())
        self.sql_conn.commit()
        sql_cmd_f.close()

    def add_frame(self, img_path, brief):
        feat = self.model.extract_feat(img_path).tolist()
        self.append_to_buffer(feat, brief)

    def set_bili_url(self, results):
        for i in results:
            if i['epid']:
                i['bili_url'] = 'https://www.bilibili.com/bangumi/play/ep%d?t=%.1f'%(i['epid'], i['time'])
            elif i['bvid']:
                i['bili_url'] = 'https://www.bilibili.com/video/%s?t=%.1f'%(i['bvid'], i['time'])
        return results

    def close(self):
        self.flush()
        self.milvus.close()
