import os
import sqlite3
from bilibili_api import bangumi
import imagehash
from search_client import HashSearchClient

class FrameBox(object):
    def __init__(self):
        self.DB_PATH = os.path.join("sql", "frames.db")
        self.INIT_SQL_PATH = os.path.join("sql", "init.sql")
        self.BUFFER_MAX_LEN = 100
        self.search_client = HashSearchClient()
        self.hash_buffer = []
        self.last_cid = ""

    def connect(self):
        self.sql_conn = sqlite3.connect(self.DB_PATH)
        self.sql_cursor = self.sql_conn.cursor()

    def close(self, with_commit = False):
        self.sql_cursor.close()
        if (with_commit):
            self.sql_conn.commit()
        self.sql_conn.close()

    def add_hash(self, hash_str, brief):
        cid = brief['cid']
        time = brief['time']
        self.connect()
        try:
            self.sql_cursor.execute(
                'INSERT INTO hash (hash, cid, time) VALUES ("%s", %d, %f)'
                %(hash_str, cid, time)
            )
            print("add frame:", cid, time)
        except sqlite3.IntegrityError as e:
            self.close()
            print("Warn: frame repeated")
            return
        except sqlite3.OperationalError as e:
            self.close()
            self.init_db()
            print("table 'hash' not found, created")
            self.add_hash(hash_str, brief)
            return
        self.close(True)
        self.append_to_buffer(hash_str)

    def append_to_buffer(self, hash_str):
        if len(self.hash_buffer) >= self.BUFFER_MAX_LEN:
            self.flush()
        self.hash_buffer.append(hash_str)

    def flush(self):
        self.search_client.add_hash(self.hash_buffer)
        self.hash_buffer = []
        

    def search_hash(self, half_results):
        self.connect()
        table_info = self.sql_cursor.execute('PRAGMA table_info(hash)').fetchall()
        keys = []
        for i in table_info:
            keys.append(i[1])
        results = []
        last_hash = ""
        for i in half_results:
            if i['hash'] == last_hash:
                continue
            last_hash = i['hash']
            self.sql_cursor.execute('select * from hash where hash=?', (i['hash'],))
            fetched = self.sql_cursor.fetchall()
            print('fetched:', fetched)
            for j in fetched:
                result = {}
                for k in range(len(keys)):
                    result[keys[k]] = j[k]
                for k2 in i:
                    result[k2] = i[k2]
                results.append(result)
        self.close()
        return results
    
    def search_cid(self, half_results):
        self.connect()
        table_info = self.sql_cursor.execute('PRAGMA table_info(cid)').fetchall()
        keys = []
        for i in table_info:
            keys.append(i[1])
        for i in half_results:
            self.sql_cursor.execute('select * from cid where cid=?', (i['cid'],))
            fetched = self.sql_cursor.fetchall()
            print('fetched:', fetched)
            for j in range(len(keys)):
                i[keys[j]] = fetched[0][j]
        self.close()
        return half_results

    def init_db(self):
        sql_cmd_f = open(self.INIT_SQL_PATH)
        self.connect()
        self.sql_cursor.executescript(sql_cmd_f.read())
        self.close(True)
        sql_cmd_f.close()

    def add_frame(self, image, brief):
        cid = brief['cid']
        bvid = brief['bvid']
        epid = brief['epid']
        time = brief['time']

        self.add_hash(str(imagehash.dhash(image)), brief)
        if cid == self.last_cid:
            return

        try:
            info = bangumi.get_episode_info(epid=epid)
        except BaseException as e:
            print('except:', e)
            return
        
        name = info['h1Title']
        self.connect()
        command = ('INSERT INTO cid (cid, name, epid, bvid)'
            'VALUES (%d, "%s", %d, "%s")'%(cid, name, epid, bvid))
        try:
            self.sql_cursor.execute(command)
            print("add info", command)
        except sqlite3.IntegrityError as e:
            print("Warn: cid repeated")
        self.close(True)
        self.last_cid = cid

    def set_bili_url(self, results):
        for i in results:
            if i['epid']:
                i['bili_url'] = 'https://www.bilibili.com/bangumi/play/ep%d?t=%f'%(i['epid'], i['time'])
            elif i['bvid']:
                i['bili_url'] = 'https://www.bilibili.com/video/%s?t=%f'%(i['bvid'], i['time'])
        return results

    def push_all_hash(self):
        print("start push all hash")
        self.connect()
        self.sql_cursor.execute("SELECT max(rowid) from hash")
        all_num = self.sql_cursor.fetchall()[0][0]
        print("hash all num:", all_num)
        num = 0
        while num < all_num:
            print("pushed:", num)
            self.sql_cursor.execute("SELECT hash FROM hash WHERE rowid > ? AND rowid <= ?", (num, num + 10000))
            fetched = self.sql_cursor.fetchall()
            hashList = []
            for i in fetched:
                hashList.append(i[0])
            self.search_client.add_hash(hashList)
            num += 10000
        self.close()
        print("done")


        
