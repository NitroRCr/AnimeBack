from flask import Flask
from flask import request
from search_client import HashSearchClient
from frame_box import FrameBox
import json
import time
import sqlite3
import os
import imagehash
class App:
    test_req = json.dumps({
        "jsonrpc": "2.0",
        "id": 1,
        "method": "search",
        "params": {
            "hash": "7ac5da7ec5a",
            "searchMethod": "hash"
        }
    })
    class Id:
        def __init__(self):
            self.value = 0
        def use(self):
            self.value += 1
            return self.value
    def __init__(self):
        self.sql_conn = sqlite3.connect('sql%sframes.db'%(os.sep))
        self.sql_cursor = self.sql_conn.cursor()
        sql_cmd_f = open("init.sql")
        self.SQL_INIT_CMD = sql_cmd_f.read()
        sql_cmd_f.close()
        self.req_num = 0
        self.hash_buffer = []
        self.unique_id = Id()
        self.IMAGE_SAVE_PATH = os.path.join("image", "upload")
        self.IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg'}

    def create_flask(self):
        flask = Flask(__name__, instance_relative_config=True)

        @flask.route('/search', methods=['POST'])
        def search():
            response = {}
            if ("search-method" in request.form):
                method = request.form['search-method']
                if method == "pic":
                    image = request.files["pic"]
                    response['result'] = self.search_pic(image)
                    response['qid'] = self.save_request(image)

            return response

        def search_pic(self, image):
            hash = imagehash.dhash(image)
            return self.search_hash(hash)
            

    def setup(self):
        self.sql_cursor.execute(self.SQL_INIT_CMD)

    def add_frame(self, hash_str, brief):
        name = brief['name']
        cid = brief['cid']
        time = brief['time']
        self.sql_cursor.execute(
            'INSERT INTO hash (hash, cid, time) VALUES (%d, %s, %d)'
            %(int(hash_str, 16), cid, time)
            )
        self.sql_cursor.execute(
            'INSERT INTO cid (cid, name) VALUES (%s, %s)'%(cid, name)
            )

        self.hash_buffer.append(hash_str)

    def save_request(self, image):
        extension = os.path.splitext(image.filename[-1])
        if (extension not in self.IMAGE_EXTENSIONS):
            return -1
        now_num = self.sql_cursor.execute('SELECT max(qid) from request').fetchall()[0][0] + 1
        save_path = os.path.join(self.IMAGE_SAVE_PATH, '%d.%s'%(now_num, extension))
        self.sql_cursor.execute('INSERT INTO request (img_path) VALUES(%s)'%save_path)
        image.save(save_path)
        return now_num

    def select_request(self, qid):
        path = self.sql_cursor.execute('SELECT ')
    
    def search_hash(self, hash_str):
        req_id = self.unique_id.use()
        f = open(os.path.join(self.SEARCH_REQ_PATH, "%d.req"%req_id))
        f.write(hash_str)
        f.close()
        res = self.get_res(req_id)
        result = []
        for row in res.split('\n'):
            if row != '':
                data = row.split(' ')
                from_hash = self.db_search_hash(data[1])
                for i in from_hash:
                    cid = i[1]
                    from_cid = self.db_search_cid(cid)
                    result.append({
                        'cid': cid,
                        'time': i[2],
                        'name': from_cid[1]
                    })
        return result

    

