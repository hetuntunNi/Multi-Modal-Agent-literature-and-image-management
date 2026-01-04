import os
import uuid
from src.embedding import EmbeddingModels
from src.vector_db import VectorDB

class ImageManager:
    def __init__(self, image_root: str = "./data/images"):
        self.image_root = image_root
        self.embedding_model = EmbeddingModels()
        self.vector_db = VectorDB()
        self.collection_name = "image_collection"  # 图像向量集合名
        self.supported_ext = [".jpg", ".jpeg", ".png", ".gif", ".bmp"]

        # 初始化图像目录
        os.makedirs(self.image_root, exist_ok=True)
        # 首次运行时扫描图像并建立索引
        self._init_image_index()

    # 初始化图像索引（扫描所有支持的图像文件）
    def _init_image_index(self):
        for root, _, files in os.walk(self.image_root):
            for file_name in files:
                if any(file_name.lower().endswith(ext) for ext in self.supported_ext):
                    image_path = os.path.join(root, file_name)
                    # 避免重复索引（简化：直接添加，可优化为判断元数据）
                    self.add_image(image_path)

    # 添加单张图像到向量库
    def add_image(self, image_path: str) -> str:
        if not os.path.exists(image_path):
            return f"错误：{image_path} 不存在"
        # 过滤非支持格式的文件
        if not any(image_path.lower().endswith(ext) for ext in self.supported_ext):
            return f"跳过：{image_path} 不是支持的图片格式"
        # 生成图像嵌入
        image_embedding = self.embedding_model.get_image_embedding(image_path)
        if not image_embedding:
            return f"错误：无法生成{image_path}的嵌入"
        # 存入向量数据库
        image_id = f"image_{uuid.uuid4().hex}"
        self.vector_db.add_data(
            collection_name=self.collection_name,
            ids=[image_id],
            embeddings=[image_embedding],
            metadatas=[{"path": image_path, "file_name": os.path.basename(image_path)}],
            documents=[os.path.basename(image_path)]
        )
        return f"成功：{image_path} 已添加到图像库"

    # 批量索引图片文件夹（新增：对应add_image命令的批量处理）
    def batch_index_images(self, folder_path: str) -> str:
        if not os.path.isdir(folder_path):
            return f"错误：{folder_path} 不是有效的文件夹"

        results = []
        # 递归遍历文件夹下所有图片
        for root, _, files in os.walk(folder_path):
            for file_name in files:
                file_path = os.path.join(root, file_name)
                if any(file_name.lower().endswith(ext) for ext in self.supported_ext):
                    result = self.add_image(file_path)
                    results.append(f"{file_name}: {result}")
        return "\n".join(results)

    # 以文搜图（返回最匹配的图像）
    def search_image(self, query: str, n_results: int = 5) -> list:
        # 生成查询的CLIP嵌入
        query_embedding = self.embedding_model.get_clip_text_embedding(query)
        if not query_embedding:
            return []
        # 查询向量数据库
        results = self.vector_db.query(
            collection_name=self.collection_name,
            query_embeddings=[query_embedding],
            n_results=n_results
        )
        # 格式化结果
        search_results = []
        for i in range(len(results["ids"][0])):
            meta = results["metadatas"][0][i]
            distance = results["distances"][0][i]
            search_results.append({
                "file_name": meta["file_name"],
                "path": meta["path"],
                "similarity": round(1 - distance, 4)
            })
        return search_results