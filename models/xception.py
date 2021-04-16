import numpy as np
from numpy import linalg as LA

from keras.applications.xception import Xception
from keras.preprocessing import image
from keras.applications.xception import preprocess_input

class XceptionNet:
    def __init__(self):
        self.input_shape = (299, 299, 3)
        self.weight = 'imagenet'
        self.pooling = 'max'
        self.model = Xception(weights = self.weight, input_shape = (self.input_shape[0], self.input_shape[1], self.input_shape[2]), pooling = self.pooling, include_top = False)
        self.model.predict(np.zeros((1, 299, 299 , 3)))

    
    def extract_feat(self, img_path):
        img = image.load_img(img_path, target_size=(self.input_shape[0], self.input_shape[1]))
        img = image.img_to_array(img)
        img = np.expand_dims(img, axis=0)
        img = preprocess_input(img)
        feat = self.model.predict(img)
        norm_feat = feat[0]/LA.norm(feat[0])
        return norm_feat