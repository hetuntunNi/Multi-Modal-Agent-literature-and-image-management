import torch
import clip
from PIL import Image
from sentence_transformers import SentenceTransformer

# 单例模式加载模型，避免重复加载
class EmbeddingModels:
    _instance = None
    _text_model = None
    _clip_model = None
    _clip_preprocess = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            # 加载文本嵌入模型
            cls._text_model = SentenceTransformer('all-MiniLM-L6-v2')
            # 加载 CLIP 模型（图文匹配）
            device = "cuda" if torch.cuda.is_available() else "cpu"
            cls._clip_model, cls._clip_preprocess = clip.load("ViT-B/32", device=device)
            cls._clip_device = device
        return cls._instance

    # 生成文本嵌入（返回列表）
    def get_text_embedding(self, text):
        embedding = self._text_model.encode(text, convert_to_numpy=True)
        return embedding.tolist()  # 数组转列表

    # 生成图像嵌入（返回列表）
    def get_image_embedding(self, image_path):
        image = Image.open(image_path).convert("RGB")
        image_input = self._clip_preprocess(image).unsqueeze(0).to(self._clip_device)
        with torch.no_grad():
            image_embedding = self._clip_model.encode_image(image_input)
        # 张量→数组→列表
        return image_embedding.cpu().numpy().flatten().tolist()

    # 生成文本的 CLIP 嵌入（返回列表）
    def get_clip_text_embedding(self, text):
        text_input = clip.tokenize([text]).to(self._clip_device)
        with torch.no_grad():
            text_embedding = self._clip_model.encode_text(text_input)
        # 张量→数组→列表
        return text_embedding.cpu().numpy().flatten().tolist()