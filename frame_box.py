# -*- coding: utf-8 -*-
import os
import sqlite3
import time
import json
from bilibili_api import bangumi
from milvus import Milvus, IndexType, MetricType, Status
#from models.vgg16 import VGGNet
#from models.xception import XceptionNet
#from models.densenet169 import DenseNet
#from models.resnet50 import ResNet50
#from models.efficientnet_b4 import EfficientNetB4
#from models.efficientnet_b6 import EfficientNetB6
#from models.resnet50v2 import ResNet50V2
from models import resnet_feat
from models import resnet_flat
from tensorflow.python.keras.backend import set_session
import tensorflow as tf
import numpy as np
from ldb import LDB
from os import path
from sklearn.decomposition import PCA
from sklearn.preprocessing import scale
import joblib
import math as m

model_classes = {
    #'VGG16': VGGNet,
    #'Xception': XceptionNet,
    #'DenseNet': DenseNet,
    #'ResNet50': ResNet50,
    #'ResNet50V2': ResNet50V2,
    #'EfficientNetB4': EfficientNetB4,
    #'EfficientNetB6': EfficientNetB6,
    'ResNetFeat': resnet_feat.Model,
    'ResNetFlat': resnet_flat.Model
}
presets_info = [
    {
        'name': 'VGG16',
        'enable': False,
        'model': 'VGG16',
        'coll_param': {
            'collection_name': 'AnimeBack_VGG16',
            'dimension': 512,
            'index_file_size': 2048,
            'metric_type': MetricType.L2
        },
        'index_type': IndexType.IVF_SQ8,
        'index_param': {
            "nlist": 2048
        },
        'extract_dim': 512,
        'db_path': 'db/frames_VGG16',
        'search_param': {
            'nprobe': 16
        },
        'ifscale': False
    },
    {
        'name': 'DenseNet_PCA',
        'enable': False,
        'model': 'DenseNet',
        'coll_param': {
            'collection_name': 'AnimeBack_DenseNet_PCA',
            'dimension': 416,
            'index_file_size': 2048,
            'metric_type': MetricType.L2
        },
        'index_type': IndexType.IVF_PQ,
        'index_param': {
            "nlist": 2048
        },
        'extract_dim': 1664,
        'db_path': 'db/frames_DenseNet_PCA',
        'search_param': {
            'nprobe': 16
        },
        'ifscale': False,
        'pca_model': 'pca/pca_densenet_416.m',
        'isDefault': True
    },
    {
        'name': 'ResNet50',
        'enable': False,
        'model': 'ResNet50',
        'coll_param': {
            'collection_name': 'AnimeBack_ResNet50',
            'dimension': 2048,
            'index_file_size': 2048,
            'metric_type': MetricType.L2
        },
        'index_type': IndexType.IVF_SQ8,
        'index_param': {
            "nlist": 2048
        },
        'extract_dim': 2048,
        'db_path': 'db/frames_ResNet50',
        'search_param': {
            'nprobe': 16
        },
        'ifscale': False
    },
    {
        'name': 'ResNetFlat',
        'enable': True,
        'model': 'ResNetFlat',
        'coll_param': {
            'collection_name': 'AnimeBack_ResNetFlat',
            'dimension': 256,
            'index_file_size': 2048,
            'metric_type': MetricType.L2
        },
        'index_type': IndexType.IVF_PQ,
        'index_param': {
            "m": 16,
            "nlist": 4096
        },
        'extract_dim': 256,
        'db_path': 'db/frames_ResNetFlat',
        'search_param': {
            'nprobe': 64
        },
        'ifscale': False
    },
    {
        'name': 'ResNetFeat',
        'enable': True,
        'model': 'ResNetFeat',
        'coll_param': {
            'collection_name': 'AnimeBack_ResNetFeat',
            'dimension': 256,
            'index_file_size': 2048,
            'metric_type': MetricType.L2
        },
        'index_type': IndexType.IVF_PQ,
        'index_param': {
            "m": 16,
            "nlist": 4096
        },
        'extract_dim': 256,
        'db_path': 'db/frames_ResNetFeat',
        'search_param': {
            'nprobe': 64
        },
        'ifscale': False
    }
]


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
        self.search_param = info['search_param']
        self.ldb = LDB(self.db_path, create_if_missing=True)
        self.pca_enabled = ('pca_model' in info)
        self.ifscale = info['ifscale'] if 'ifscale' in info else False
        self.is_default = info['isDefault'] if 'isDefault' in info else False
        if self.pca_enabled:
            self.pca = joblib.load(info['pca_model'])

    def get_frame_num(self):
        num = self.ldb.get('_num'.encode())
        if not num:
            self.set_frame_num(0)
            return 0
        return int(num)

    def set_frame_num(self, num):
        self.ldb.put('_num'.encode(), str(num).encode())


class PCAPreset:
    def __init__(self, info):
        self.name = info['name']
        self.extract_dim = info['extract_dim']
        self.pca_dim = info['coll_param']['dimension']
        self.model = model_classes[info['model']]()
        self.vectors = np.zeros((0, self.extract_dim), dtype=float)
        self.pca = PCA(n_components=self.pca_dim)
        self.pca_path = info['pca_model']
        self.ifscale = info['ifscale']

    def add_frames(self, frames):
        vectors = np.zeros((len(frames), self.extract_dim), dtype=float)
        for i in range(len(frames)):
            vectors[i] = self.model.extract_feat(frames[i]['file'])
        self.vectors = np.concatenate((self.vectors, vectors))

    def train(self):
        vectors = self.vectors
        if self.ifscale:
            vectors = scale(vectors, axis=1)
        self.pca.fit(vectors)
        joblib.dump(self.pca, self.pca_path)


class FrameBox(object):

    def __init__(self, enable_cuda, disable_gpu=False):
        if enable_cuda and disable_gpu:
            os.environ["CUDA_DEVICE_ORDER"] = "PCI_BUS_ID"
            os.environ["CUDA_VISIBLE_DEVICES"] = ""

        if enable_cuda and not disable_gpu:
            config = tf.compat.v1.ConfigProto()
            config.gpu_options.allow_growth = True
            sess = tf.compat.v1.Session(config=config)
            set_session(sess)
        
        self.BUFFER_MAX_LEN = 10000
        self.BATCH_SIZE = 32
        self.frame_buffer = []
        self.milvus = None
        self.curr_presets = []
        self.config = self.get_json('config.json')
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

    def get_feat(self, img_path):
        feats = {}
        for key in self.models:
            feats[key] = self.models[key].extract_feat(img_path)
        return feats

    def get_feats(self, img_paths):
        length = len(img_paths)
        all_feats = [{} for i in range(length)]
        for key in self.models:
            feats = self.models[key].extract_feats(img_paths)
            for i in range(length):
                all_feats[i][key] = feats[i]
        return all_feats

    def create_collection(self):
        collections = self.milvus.list_collections()[1]
        for preset in self.presets:
            if preset.coll_name in collections:
                continue
            self.milvus.create_collection(preset.coll_param)
            self.milvus.create_index(
                preset.coll_name, preset.index_type, params=preset.index_param)

    # test only !!
    def delete_preset(self, name):
        for preset in self.presets:
            if preset.name == name:
                print(self.milvus.drop_collection(preset.coll_name))
                preset.ldb.destroy()
                return
        raise ValueError('Invalid preset name: %s' % name)

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
        t0 = time.time()
        length = len(self.frame_buffer)
        if length == 0:
            return
        for preset in self.curr_presets:
            now_id = preset.get_frame_num()
            vectors = np.zeros((length, preset.extract_dim), dtype=float)
            ids = []
            preset.ldb.open()
            wb = preset.ldb.db.write_batch()
            for i in range(length):
                frame = self.frame_buffer[i]
                now_id += 1
                vectors[i] = frame['feat'][preset.model]
                ids.append(now_id)
                brief = frame['brief']
                wb.put(str(now_id).encode(), json.dumps(brief).encode())
            wb.write()
            preset.ldb.close()
            preset.set_frame_num(now_id)
            if preset.ifscale:
                vectors = scale(vectors, axis=1)
            if preset.pca_enabled:
                vectors = preset.pca.transform(vectors)
            res = self.milvus.insert(collection_name=preset.coll_name,
                                     ids=ids, records=vectors.tolist())
        self.frame_buffer = []
        t = time.time() - t0
        print('inserted %d frames in %.2fs, fps=%.2f' % (length, t, length/t))

    def get_default_preset(self):
        for preset in self.presets:
            if preset.is_default:
                return preset
        return self.presets[0]

    def search_img(self, img_path, resultNum, preset_name=None):
        preset = None
        for i in self.presets:
            if i.name == preset_name:
                preset = i
                break
        if preset_name == None or preset_name == 'default':
            preset = self.get_default_preset()
        if not preset:
            raise ValueError('Invalid preset name')
        vectors = np.zeros((1, preset.extract_dim), dtype=float)
        vectors[0] = self.get_feat(img_path)[preset.model]
        if preset.ifscale:
            vectors = scale(vectors, axis=1)
        if preset.pca_enabled:
            vectors = preset.pca.transform(vectors)
        results = self.milvus.search(
            preset.coll_name, resultNum, vectors.tolist(), params=preset.search_param, timeout=15)
        results = [{
            'frame_id': result.id,
            'score': 1 - result.distance/2,
            'preset': preset_name
        } for result in results[1][0]]
        for i in results:
            preset.ldb.open()
            brief = json.loads(preset.ldb.get(str(i['frame_id']).encode(), False))
            for key in brief:
                i[key] = brief[key]
            preset.ldb.close()
        return results

    def insert(self, frames, epid, preset_names):
        t0 = time.time()
        print('extract feat start')
        length = len(frames)
        self.curr_presets = [
            preset for preset in self.presets if preset.name in preset_names]
        paths = [f['file'] for f in frames]
        feats = []
        for i in range(0, length, self.BATCH_SIZE):
            end = min(i + self.BATCH_SIZE, length)
            feats += self.get_feats(paths[i:end])
        t = time.time() - t0
        fps = length/t
        print('extract feat takes %.2fs, fps=%.2f' % (t, fps))

        for i in range(length):
            self.append_to_buffer(feats[i], {
                'epid': epid,
                'time': frames[i]['time']
            })
        self.flush()

    def get_presets_status(self):
        info = {}
        for preset in self.presets:
            info[preset.name] = {
                'frameNum': preset.get_frame_num(),
                'isDefault': preset.is_default
            }
        return info

    def close(self):
        self.flush()
        self.milvus.close()


class PCATrainer:
    def __init__(self):
        self.presets = [PCAPreset(info)
                        for info in presets_info if 'pca_model' in info]

    def add_frames(self, frames):
        for preset in self.presets:
            preset.add_frames(frames)

    def train(self):
        for preset in self.presets:
            preset.train()
