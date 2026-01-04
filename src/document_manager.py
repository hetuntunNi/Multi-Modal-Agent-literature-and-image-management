import os
import shutil
import uuid
from PyPDF2 import PdfReader
from src.embedding import EmbeddingModels
from src.vector_db import VectorDB
import numpy as np

class DocumentManager:
    def __init__(self, paper_root: str = "./data/papers"):
        self.paper_root = paper_root
        self.embedding_model = EmbeddingModels()
        self.vector_db = VectorDB()
        self.collection_name = "paper_collection"  # 论文向量集合名

        # 初始化论文根目录
        os.makedirs(self.paper_root, exist_ok=True)

    # 提取PDF文本（前10页，平衡性能和内容）
    def extract_pdf_text(self, pdf_path: str) -> str:
        if not os.path.exists(pdf_path) or not pdf_path.endswith(".pdf"):
            return ""
        try:
            reader = PdfReader(pdf_path)
            text = ""
            # 只提取前10页（避免大PDF处理过慢）
            for page in reader.pages[:10]:
                page_text = page.extract_text() or ""
                text += page_text + "\n"
            return text.strip()
        except Exception as e:
            print(f"PDF文本提取失败：{e}")
            return ""

    # 计算余弦相似度（用于论文分类）
    def _cosine_similarity(self, vec1: list, vec2: list) -> float:
        vec1 = np.array(vec1)
        vec2 = np.array(vec2)
        if np.linalg.norm(vec1) == 0 or np.linalg.norm(vec2) == 0:
            return 0.0
        return np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2))

    # 自动分类论文（根据指定主题）
    def classify_paper(self, pdf_text: str, topics: list) -> str:
        if not pdf_text or not topics:
            return "Unclassified"
        # 生成论文文本嵌入
        text_embedding = self.embedding_model.get_text_embedding(pdf_text)
        # 生成每个主题的嵌入
        topic_embeddings = [self.embedding_model.get_text_embedding(topic) for topic in topics]
        # 计算相似度，返回最匹配的主题
        similarities = [self._cosine_similarity(text_embedding, te) for te in topic_embeddings]
        return topics[similarities.index(max(similarities))]

    # 添加单篇论文（分类+存入向量库）
    def add_paper(self, pdf_path: str, topics: list) -> str:
        # 验证PDF文件
        if not os.path.isfile(pdf_path) or not pdf_path.endswith(".pdf"):
            return f"错误：{pdf_path} 不是有效的PDF文件"

        # 提取文本
        pdf_text = self.extract_pdf_text(pdf_path)
        if not pdf_text:
            return f"错误：无法提取{pdf_path}的文本内容"

        # 分类论文
        topic = self.classify_paper(pdf_text, topics)
        topic_dir = os.path.join(self.paper_root, topic)
        os.makedirs(topic_dir, exist_ok=True)

        # 复制文件到分类目录（保留原文件）
        file_name = os.path.basename(pdf_path)
        # 避免文件名重复
        file_base, file_ext = os.path.splitext(file_name)
        dest_file_name = f"{file_base}_{uuid.uuid4().hex[:8]}{file_ext}"
        dest_path = os.path.join(topic_dir, dest_file_name)
        shutil.copy2(pdf_path, dest_path)

        # 存入向量数据库
        paper_id = f"paper_{uuid.uuid4().hex}"
        text_embedding = self.embedding_model.get_text_embedding(pdf_text)
        self.vector_db.add_data(
            collection_name=self.collection_name,
            ids=[paper_id],
            embeddings=[text_embedding],
            metadatas=[{"path": dest_path, "topic": topic, "file_name": dest_file_name}],
            documents=[pdf_text[:500]]  # 存储前500字符作为摘要
        )

        return f"成功：论文已分类到【{topic}】目录，路径：{dest_path}"

    # 批量整理论文文件夹
    def batch_organize(self, folder_path: str, topics: list) -> str:
        if not os.path.isdir(folder_path):
            return f"错误：{folder_path} 不是有效的文件夹"

        results = []
        for file_name in os.listdir(folder_path):
            file_path = os.path.join(folder_path, file_name)
            if file_name.endswith(".pdf") and os.path.isfile(file_path):
                result = self.add_paper(file_path, topics)
                results.append(f"{file_name}: {result}")
        return "\n".join(results)

    # 语义搜索论文
    def search_paper(self, query: str, n_results: int = 5) -> list:
        # 生成查询嵌入
        query_embedding = self.embedding_model.get_text_embedding(query)
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
            distance = results["distances"][0][i]  # 距离越小越相似
            search_results.append({
                "file_name": meta["file_name"],
                "path": meta["path"],
                "topic": meta["topic"],
                "similarity": round(1 - distance, 4)  # 转换为相似度（0-1）
            })
        return search_results