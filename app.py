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
    class SavedInfo:
        def save_req(self):
            pass
    def __init__(self):
        self.req_num = 0
        self.hash_buffer = []
        self.unique_id = Id()
        self.IMAGE_SAVE_PATH = os.path.join("image", "upload")
        self.IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg'}
        self.search_client = HashSearchClient()
        self.frame_box = FrameBox()

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
                    self.save_image(image)

            return response

        def search_pic(self, image):
            hash = imagehash.dhash(image)
            return self.search_hash(hash)
            

    def setup(self):
        self.sql_cursor.execute(self.SQL_INIT_CMD)

    

    def save_image(self, image):
        extension = os.path.splitext(image.filename[-1])
        if (extension not in self.IMAGE_EXTENSIONS):
            return -1
        now_num = 0
        save_path = os.path.join(self.IMAGE_SAVE_PATH, '%d.%s'%(now_num, extension))
        image.save(save_path)
        return now_num

    def select_request(self, qid):
        path = self.sql_cursor.execute('SELECT ')
    
    def search_hash(self, hash_str):
        results = self.search_client.search_hash(hash_str)
        results = self.frame_box.search_hash(results)
        results = self.frame_box.search_cid(results)
        return results

    

