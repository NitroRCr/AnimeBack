# -*- coding: utf-8 -*-
import time
from flask import Flask
from flask import request, url_for, abort
from frame_box import FrameBox
from flask import after_this_request
import init_conf
import subprocess
import json
import os
import re
import urllib.request
import cv2
import numpy as np
from flask.helpers import send_file
flask_app = None
class App:
            
    def __init__(self):
        self.hash_buffer = []
        self.IMAGE_TMP_PATH = os.path.join("static", "img", "tmp")
        self.IMAGE_SAVE_PATH = os.path.join("static", "img", "upload")
        self.IMAGE_EXTENSIONS = {'.png', '.jpg', '.jpeg'}
        self.STATE_PATH = "state.json"
        self.CONFIG_PATH = "config.json"
        self.RES_SAVE_PATH = os.path.join("static", "json", "response")
        self.VIDEO_PATH = os.path.join("static", "video")
        self.PRE_URL = ""
        
        self.frame_box = FrameBox()
        self.create_flask()

    def get_json(self, path):
        f = open(path)
        ret = json.loads(f.read())
        f.close()
        return ret

    def get_req_num(self):
        state = self.get_json(self.STATE_PATH)
        state['requestNum'] += 1
        f = open(self.STATE_PATH, "w")
        f.write(json.dumps(state))
        f.close()
        return state['requestNum']

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
                    if "tags" in request.form:
                        try:
                            tags = json.loads(request.form['tags'])
                            if len(tags) == 0:
                                tags = None
                        except:
                            tags = None
                    else:
                        tags = None
                    response['qid'] = qid
                    if request.form['crop'] == 'true':
                        crop = True
                    else:
                        crop = False
                    if method == "pic":
                        image_file = request.files["pic"]
                        self.save_image(image_file, qid)
                        response['pic_url'] = '/img/upload/%d' % qid
                        response['result'] = self.search_pic(qid, tags, crop=crop)
                    elif method == "url":
                        matched = re.match(r'((https?|ftp|file)://[-A-Za-z0-9+&@#/%?=~_|!:,.;]+[-A-Za-z0-9+&@#/%=~_|])',
                            request.form['url'])
                        if matched:
                            try:
                                save_path = os.path.join(self.IMAGE_SAVE_PATH, str(qid))
                                urllib.request.urlretrieve(matched.group(1), filename=save_path)
                            except urllib.error.HTTPError:
                                return {
                                    "error_code": 400,
                                    "error_msg": "无效的图像链接"
                                }
                            response['pic_url'] = "/img/upload/%d"%qid
                            response['result'] = self.search_pic(save_path)
                        else:
                            return {
                                "error_code": 400,
                                "error_msg": "无效的URL"
                            }
                    else:
                        abort(400)
                    self.save_res(response)
            return response

        @flask.route('/getframe', methods = ['POST'])
        def get_frame():
            cid = int(request.form['cid'])
            time = float(request.form['time'])
            video = os.path.join(self.VIDEO_PATH, '%d.mp4' % cid)
            req_id = self.get_req_num()
            if not os.path.exists(self.IMAGE_TMP_PATH):
                os.mkdir(self.IMAGE_TMP_PATH)
            tmp_img = os.path.join(self.IMAGE_TMP_PATH, '%d.jpg' % req_id)
            if os.path.exists(video) == False:
                abort(400)
            try:
                subprocess.run('ffmpeg -ss %.1f -i %s -f image2 -frames:v 1 %s' % (time, video, tmp_img), shell=True, check=True)
            except subprocess.CalledProcessError as e:
                print(e)
                abort(400)
            f = open(tmp_img)
            """ @after_this_request
            def remove_file(response):
                try:
                    os.remove(tmp_img)
                    f.close()
                except Exception as error:
                    flask.logger.error("Error removing or closing downloaded file handle", error)
                return response """
            return send_file(f, mimetype='image/jpg')

        @flask.route('/', methods = ['GET'])
        def getIndex():
            return flask.send_static_file('index.html')

        global flask_app
        flask_app = flask

    def search_pic(self, qid, tags, crop=False):
        origin_path = os.path.join(self.IMAGE_SAVE_PATH, str(qid))
        if crop:
            if not os.path.exists(self.IMAGE_TMP_PATH):
                os.mkdir(self.IMAGE_TMP_PATH)
            img_path = os.path.join(self.IMAGE_TMP_PATH, '%d.jpg' % qid)
            self.crop_image(origin_path, img_path)
        else:
            img_path = origin_path
        self.frame_box.connect()
        ret = self.frame_box.search_with_info(img_path, tags)
        self.frame_box.close()
        return ret

    def get_saved_res(self, qid):
        try:
            f = open(os.path.join(self.RES_SAVE_PATH, "%d.json"%qid))
        except IOError:
            return -1
        response = json.loads(f.read())
        f.close()
        return response
    def save_res(self, response):
        if not os.path.exists(self.RES_SAVE_PATH):
            os.makedirs(self.RES_SAVE_PATH)
        f = open(os.path.join(self.RES_SAVE_PATH, "%d.json"%response['qid']), 'w')
        f.write(json.dumps(response))
        f.close()
    

    def save_image(self, image, qid):
        extension = os.path.splitext(image.filename)[-1]
        if (extension not in self.IMAGE_EXTENSIONS):
            return -1
        now_num = qid
        if not os.path.exists(self.IMAGE_SAVE_PATH):
            os.makedirs(self.IMAGE_SAVE_PATH)
        save_path = os.path.join(self.IMAGE_SAVE_PATH, '%d'%(now_num))
        image.save(save_path)

    def crop_image(self, in_path, out_path):
        image = cv2.imread(in_path)
        height, width, channels = image.shape
        # Convert image to grayscale
        imgray = cv2.cvtColor(image,cv2.COLOR_BGR2GRAY)

        # Set threshold
        #th1 = cv2.adaptiveThreshold(imgray,255,cv2.ADAPTIVE_THRESH_GAUSSIAN_C,cv2.THRESH_BINARY,1023,0)
        _,th2 = cv2.threshold(imgray,8,255,cv2.THRESH_BINARY)
        contours, hierarchy = cv2.findContours(th2,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)

        # Find with the largest rectangle
        areas = [cv2.contourArea(contour) for contour in contours]
        max_index = np.argmax(areas)
        cnt = contours[max_index]
        x,y,w,h = cv2.boundingRect(cnt)

        # Ensure bounding rect should be at least 16:9 or taller
        # For images that is not ~16:9
        # And its detected bounding rect wider than 16:9
        if abs(width / height - 16 / 9) < 0.03 and (w / h - 16 / 9) > 0.03:
            # increase top and bottom margin
            newHeight = w / 16 * 9
            y = y - (newHeight - h ) / 2
            h = newHeight

        # ensure the image has dimension
        x = round(x)
        y = round(y)
        w = round(w)
        h = round(h)
        y = 0 if y < 0 else y
        x = 0 if x < 0 else x
        w = 1 if w < 1 else w
        h = 1 if h < 1 else h

        # Crop with the largest rectangle
        crop = image[y:y+h,x:x+w]
        cv2.imwrite(out_path, crop)

app = App()
if __name__ == '__main__':
    flask_app.run()
