from tensorflow.keras import models
import numpy as np
import tensorflow as tf
from pathlib import Path
from matplotlib import pyplot as plt
from keras.applications import resnet
from keras import metrics
import os

target_shape = (200, 200)


class EmbeddingModel:
    def __init__(self, filepath, target_shape=target_shape, preprocess_input=None):
        self.model = models.load_model(filepath)
        self.target_shape = target_shape
        self.preprocess_input = preprocess_input
        
    def preprocess_image(self, filename):
        """
        Load the specified file as a JPEG image, preprocess it and
        resize it to the target shape.
        """

        image_string = tf.io.read_file(filename)
        image = tf.image.decode_jpeg(image_string, channels=3)
        image = tf.image.convert_image_dtype(image, tf.float32)
        image = tf.image.resize(image, target_shape)
        return image

    def l2_distance(self, vec1, vec2):
        return np.linalg.norm(vec1 - vec2)

    def extract_feat(self, img_path):
        img = self.preprocess_image(img_path)
        print(img.shape)
        img = np.expand_dims(img, axis=0).copy()
        return self.model(self.preprocess_input(img))

    def extract_feats(self, img_paths):
        num = len(img_paths)
        imgs = np.zeros((num,) + self.target_shape + (3,))
        for i in range(num):
            imgs[i] = self.preprocess_image(img_paths[i])
        return self.model(self.preprocess_input(imgs))
