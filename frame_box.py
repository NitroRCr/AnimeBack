# -*- coding: utf-8 -*-
import os
import sqlite3
import time
import json
from bilibili_api import bangumi
from milvus import Milvus, IndexType, MetricType, Status
#from models.vgg16 import VGGNet
from models.xception import XceptionNet
#from models.densenet169 import DenseNet
import numpy as np
import plyvel
from os import path

model_classes = {
    # 'VGG16': VGGNet,
    'Xception': XceptionNet,
    # 'DenseNet': DenseNet
}
presets_info = [
    {
        'name': 'Xception_PQ',
        'enable': True,
        'model': 'Xception',
        'coll_param': {
            'collection_name': 'AnimeBack_Xception_PQ',
            'dimension': 1024,
            'index_file_size': 2048,
            'metric_type': MetricType.L2
        },
        'index_type': IndexType.IVF_PQ,
        'index_param': {
            "m": 32,
            "nlist": 2048
        },
        'extract_dim': 2048,
        'db_path': 'db/frames_Xception_PQ',
    },
    {
        'name': 'Xception_PCA',
        'enable': True,
        'model': 'Xception',
        'coll_param': {
            'collection_name': 'AnimeBack_Xception_PCA',
            'dimension': 512,
            'index_file_size': 1024,
            'metric_type': MetricType.L2
        },
        'index_type': IndexType.IVF_SQ8,
        'index_param': {
            "nlist": 2048
        },
        'extract_dim': 2048,
        'db_path': 'db/frames_Xception_PCA'
    }
]


def calculate_covariance_matrix(X, Y=None):
    # 计算协方差矩阵

    m = X.shape[0]
    X = X - np.mean(X, axis=0)
    Y = X if Y == None else Y - np.mean(Y, axis=0)
    return 1 / m * np.matmul(X.T, Y)


def transform(X, n_components):
    # 设n=X.shape[1]，将n维数据降维成n_component维

    covariance_matrix = calculate_covariance_matrix(X)

    # 获取特征值，和特征向量
    eigenvalues, eigenvectors = np.linalg.eig(covariance_matrix)

    # 对特征向量排序，并取最大的前n_component组
    idx = np.argsort(eigenvalues[::-1])
    eigenvectors = eigenvectors[:, idx]
    eigenvectors = eigenvectors[:, :n_components]

    # 转换
    return np.matmul(X, eigenvectors)

class ModelPreset:
    def __init__(self, info):
        self.name = info['name']
        self.coll_param = info['coll_param']
        self.index_type = info['index_type']
        self.index_param = info['index_param']
        self.extract_dim = info['extract_dim']
        self.pca_dim = info['coll_param']['dimension']
        self.db_path = info['db_path']
        self.model = info['model']
        self.coll_name = info['coll_param']['collection_name']
        self.db = plyvel.DB(self.db_path, create_if_missing=True)

    def get_frame_num(self):
        num = self.db.get('_num'.encode())
        if not num:
            self.set_frame_num(0)
            return 0
        return int(num)

    def set_frame_num(self, num):
        self.db.put('_num'.encode(), str(num).encode())

class FrameBox(object):
    

    def __init__(self, path="."):
        self.BUFFER_MAX_LEN = 10000
        self.frame_buffer = []
        self.milvus = None
        self.curr_presets = []
        self.config = self.get_json(os.path.join(path, 'config.json'))
        self.presets = [ModelPreset(info)
                        for info in presets_info if info['enable']]
        self.models = self.get_models()

    def get_json(self, path):
        f = open(path)
        ret = json.loads(f.read())
        f.close()
        return ret

    def get_models(self):
        models = {}
        for preset in self.presets:
            models[preset.model] = model_classes[preset.model]()
        return models

    def get_feats(self, img_path):
        feats = {}
        for key in self.models:
            feats[key] = self.models[key].extract_feat(img_path)
        return feats

    def create_collection(self):
        collections = self.milvus.list_collections()[1]
        for preset in self.presets:
            if preset.coll_name in collections:
                continue
            self.milvus.create_collection(preset.coll_param)
            self.milvus.create_index(
                preset.coll_name, preset.index_type, params=preset.index_param)

    def connect(self):
        self.milvus = Milvus(
            host=self.config['milvus_host'], port=self.config['milvus_port'])

        collections = self.milvus.list_collections()[1]
        self.create_collection()

    def close(self):
        self.flush()
        self.milvus.close()

    def append_to_buffer(self, feat, brief):
        if len(self.frame_buffer) >= self.BUFFER_MAX_LEN:
            self.flush()
        self.frame_buffer.append({"feat": feat, "brief": brief})

    def flush(self):
        length = len(self.frame_buffer)
        if length == 0:
            return
        for preset in self.curr_presets:
            now_id = preset.get_frame_num()
            vectors = np.zeros((length, preset.extract_dim), dtype=float)
            ids = []
            wb = preset.db.write_batch()
            for i in range(length):
                frame = self.frame_buffer[i]
                now_id += 1
                vectors[i] = frame['feat'][preset.model]
                ids.append(now_id)
                brief = frame['brief']
                wb.put(str(now_id).encode(), json.dumps(brief).encode())
            wb.write()
            preset.set_frame_num(now_id)
            if preset.extract_dim != preset.pca_dim:
                vectors = np.real(transform(vectors, preset.pca_dim))
            print(vectors[0])
            res = self.milvus.insert(collection_name=preset.coll_name,
                                     ids=ids, records=vectors.tolist())
        self.frame_buffer = []

    def search_img(self, img_path, preset_name=None, resultNum=20):
        for i in self.presets:
            if i.name == preset_name:
                preset = i
                break
        if preset_name == None:
            preset = self.presets[0]
        if not preset:
            raise ValueError('Invalid preset name')

        vector = self.get_feats(img_path)[preset.model]
        if preset.extract_dim != preset.pca_dim:
            vector = transform(np.asarray([vector]), preset.pca_dim)
        vector = vector.tolist()
        results = self.milvus.search(preset.coll_name, resultNum, vector, params={
                                     "nprobe": 64}, timeout=15)
        results = [{
            'frame_id': result.id,
            'score': 1 - result.distance/2,
            'preset': preset_name
        } for result in results[1][0]]
        for i in results:
            brief = json.loads(preset.db.get(i['frame_id'].encode()))
            for key in brief:
                i[key] = brief[key]
        return results

    def insert(self, frames, epid, preset_names):
        print('extract feat and insert into milvus')
        self.curr_presets = [preset for preset in self.presets if preset.name in preset_names]
        for frame in frames:
            self.append_to_buffer(self.get_feats(frame['file']), {
                'epid': epid,
                'time': frame['time']
            })
        self.flush()

    def close(self):
        self.flush()
        self.milvus.close()
