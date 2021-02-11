from flask import Flask
from flask import request
from flask import redirect
from flask import url_for
from flask import escape
from PIL import Image
from search_client import HashSearchClient
from frame_box import FrameBox
import json
import time
import sqlite3
import os
import imagehash
class App:
            
    def __init__(self):
        self.req_num = 0
        self.hash_buffer = []
        self.IMAGE_SAVE_PATH = os.path.join("static", "img", "upload")
        self.IMAGE_EXTENSIONS = {'.png', '.jpg', '.jpeg'}
        self.STATE_PATH = "state.json"
        self.CONFIG_PATH = "config.json"
        self.RES_SAVE_PATH = os.path.join("static", "json", "response")
        self.PRE_URL = ""
        
        self.state = json.loads(open(self.STATE_PATH).read())
        self.search_client = HashSearchClient()
        self.frame_box = FrameBox()
        self.create_flask()

    def get_req_num(self):
        self.state['requestNum'] += 1;
        f = open(self.STATE_PATH, "w")
        f.write(json.dumps(self.state))
        f.close()
        return self.state['requestNum']

    def create_flask(self):
        flask = Flask(__name__, instance_relative_config=True, static_url_path='')

        @flask.route('/search', methods=['GET', 'POST'])
        def search():
            print(request.method)
            if (request.method == 'GET'):
                return "POST Only"
            if ("search-method" in request.form):
                method = request.form['search-method']
                if method == 'qid':
                    qid = int(request.form['qid'])
                    response = self.get_saved_res(qid)
                    if response == -1:
                        return {
                            "error_code": 404,
                            "error_msg": "Invalid qid"
                        }
                    else:
                        return response
                else:
                    response = {}
                    qid = self.get_req_num()
                    response['qid'] = qid
                    if method == "pic":
                        image = request.files["pic"]
                        response['pic_url'] = self.save_image(image, qid)
                        response['result'] = self.search_pic(image)
                    elif method == "url":
                        pass
                    else:
                        pass
                    self.save_res(response)
            return response

        @flask.route('/', methods = ['GET'])
        def getIndex():
            return flask.send_static_file('index.html')
        
        flask.run()

    def search_pic(self, image):
        hash_str = str(imagehash.dhash(Image.open(image)))
        return self.search_hash(hash_str)

    def get_saved_res(self, qid):
        try:
            f = open(os.path.join(self.RES_SAVE_PATH, "%d.json"%qid))
        except IOError:
            return -1
        response = json.loads(f.read())
        f.close()
        return response
    def save_res(self, response):
        try:
            f = open(os.path.join(self.RES_SAVE_PATH, "%d.json"%response['qid']), 'w')
            f.write(json.dumps(response))
            f.close()
        except FileNotFoundError as e:
            os.makedirs(self.RES_SAVE_PATH)
            self.save_res(response)
            

    

    def save_image(self, image, qid):
        extension = os.path.splitext(image.filename)[-1]
        if (extension not in self.IMAGE_EXTENSIONS):
            return -1
        now_num = qid
        save_path = os.path.join(self.IMAGE_SAVE_PATH, '%d%s'%(now_num, extension))
        try:
            image.save(save_path)
            return "/img/upload/%d%s"%(now_num, extension)
        except FileNotFoundError:
            os.makedirs(self.IMAGE_SAVE_PATH)
            return self.save_image(image)
    
    def search_hash(self, hash_str):
        results = self.search_client.search_hash(hash_str)
        results = self.frame_box.search_hash(results)
        results = self.frame_box.search_cid(results)
        results = self.frame_box.set_bili_url(results)
        return results

if __name__ == '__main__':
    app = App()

