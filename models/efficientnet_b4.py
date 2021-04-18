import numpy as np
from numpy import linalg as LA

from tensorflow.keras.applications import EfficientNetB4 as ENB4
from keras.preprocessing import image
from tensorflow.keras.applications.efficientnet import preprocess_input
class EfficientNetB4:
    def __init__(self):
        self.input_shape = (380, 380, 3)
        self.weight = 'imagenet'
        self.pooling = 'max'
        self.model = ENB4(weights = self.weight, input_shape = (self.input_shape[0], self.input_shape[1], self.input_shape[2]), pooling = self.pooling, include_top = False)
        self.model.predict(np.zeros((1, 380, 380 , 3)))

    # (1792,)
    def extract_feat(self, img_path):
        img = image.load_img(img_path, target_size=(self.input_shape[0], self.input_shape[1]))
        img = image.img_to_array(img)
        img = np.expand_dims(img, axis=0)
        img = preprocess_input(img)
        feat = self.model.predict(img)
        norm_feat = feat[0]/LA.norm(feat[0])
        return norm_feat