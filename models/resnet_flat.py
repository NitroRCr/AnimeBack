from keras.applications.resnet import preprocess_input
from embedding_model import EmbeddingModel


target_shape = (200, 200)
path = 'saved_models/resnet_flat'

class Model:
    def __init__(self):
        self.embedding = EmbeddingModel(path, target_shape, preprocess_input)
        self.model = self.embedding.model

    # (256,)
    def extract_feat(self, img_path):
        return self.embedding.extract_feat(img_path)

    def extract_feats(self, img_paths):
        return self.embedding.extract_feats(img_paths)

    

