import os
import shutil
import uuid
from PyPDF2 import PdfReader
from src.embedding import EmbeddingModels
from src.vector_db import VectorDB


class DocumentManager:
    def __init__(self, paper_root: str = "./data/papers"):
        self.paper_root = paper_root
        self.embedding_model = EmbeddingModels()
        self.vector_db = VectorDB()
        self.collection_name = "paper_collection"  # 论文向量集合名
        self.chunk_size = 500  # 文本片段大小（字符）
        self.overlap = 50  # 片段重叠字符（避免语义割裂）

        # 初始化论文根目录
        os.makedirs(self.paper_root, exist_ok=True)

    # 增强版PDF文本提取：按页码拆分片段（保留页码+文本映射）
    def extract_pdf_with_pages(self, pdf_path: str) -> list:
        """
        提取PDF文本并按页码拆分片段
        返回格式：[{"page": 页码, "text": 页面文本, "chunks": 文本片段列表}, ...]
        """
        if not os.path.exists(pdf_path) or not pdf_path.endswith(".pdf"):
            return []
        try:
            reader = PdfReader(pdf_path)
            page_data = []
            # 提取所有页（不再限制前10页，保证搜索完整性）
            for page_num, page in enumerate(reader.pages, start=1):
                page_text = page.extract_text() or ""
                if not page_text:
                    continue
                # 拆分页面文本为片段（避免单页文本过长）
                chunks = self._split_text_to_chunks(page_text)
                page_data.append({
                    "page": page_num,
                    "text": page_text,
                    "chunks": chunks
                })
            return page_data
        except Exception as e:
            print(f"PDF文本提取失败：{e}")
            return []

    # 辅助函数：拆分文本为固定大小的片段（带重叠）
    def _split_text_to_chunks(self, text: str) -> list:
        chunks = []
        start = 0
        text_len = len(text)
        while start < text_len:
            end = start + self.chunk_size
            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)
            # 移动起始位置（保留重叠）
            start = end - self.overlap
        return chunks

    # 计算余弦相似度（用于论文分类）
    def _cosine_similarity(self, vec1: list, vec2: list) -> float:
        import numpy as np
        vec1 = np.array(vec1)
        vec2 = np.array(vec2)
        if np.linalg.norm(vec1) == 0 or np.linalg.norm(vec2) == 0:
            return 0.0
        return np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2))

    # 自动分类论文（根据指定主题）
    def classify_paper(self, pdf_path: str, topics: list) -> str:
        # 提取全文本用于分类（兼容旧逻辑）
        page_data = self.extract_pdf_with_pages(pdf_path)
        full_text = "\n".join([p["text"] for p in page_data])
        if not full_text or not topics:
            return "Unclassified"
        # 生成论文文本嵌入
        text_embedding = self.embedding_model.get_text_embedding(full_text)
        # 生成每个主题的嵌入
        topic_embeddings = [self.embedding_model.get_text_embedding(topic) for topic in topics]
        # 计算相似度，返回最匹配的主题
        similarities = [self._cosine_similarity(text_embedding, te) for te in topic_embeddings]
        return topics[similarities.index(max(similarities))]

    # 添加单篇论文（按片段存入向量库，保留页码）
    def add_paper(self, pdf_path: str, topics: list) -> str:
        # 验证PDF文件
        if not os.path.isfile(pdf_path) or not pdf_path.endswith(".pdf"):
            return f"错误：{pdf_path} 不是有效的PDF文件"

        # 提取带页码的文本片段
        page_data = self.extract_pdf_with_pages(pdf_path)
        if not page_data:
            return f"错误：无法提取{pdf_path}的文本内容"

        # 分类论文
        topic = self.classify_paper(pdf_path, topics)
        topic_dir = os.path.join(self.paper_root, topic)
        os.makedirs(topic_dir, exist_ok=True)

        # 复制文件到分类目录（保留原文件）
        file_name = os.path.basename(pdf_path)
        file_base, file_ext = os.path.splitext(file_name)
        dest_file_name = f"{file_base}_{uuid.uuid4().hex[:8]}{file_ext}"
        dest_path = os.path.join(topic_dir, dest_file_name)
        shutil.copy2(pdf_path, dest_path)

        # 按片段存入向量数据库（核心改造）
        all_ids = []
        all_embeddings = []
        all_metadatas = []
        all_documents = []

        for page in page_data:
            page_num = page["page"]
            page_text = page["text"]
            for chunk in page["chunks"]:
                # 生成唯一ID（关联论文+页码+片段）
                chunk_id = f"paper_{uuid.uuid4().hex}_page{page_num}"
                # 生成片段嵌入
                chunk_embedding = self.embedding_model.get_text_embedding(chunk)
                # 组装数据
                all_ids.append(chunk_id)
                all_embeddings.append(chunk_embedding)
                all_metadatas.append({
                    "path": dest_path,
                    "topic": topic,
                    "file_name": dest_file_name,
                    "page": page_num  # 存储页码
                })
                all_documents.append(chunk)  # 存储完整片段（而非前500字符）

        # 批量添加到向量库
        if all_ids:
            self.vector_db.add_data(
                collection_name=self.collection_name,
                ids=all_ids,
                embeddings=all_embeddings,
                metadatas=all_metadatas,
                documents=all_documents
            )

        return f"成功：论文已分类到【{topic}】目录，路径：{dest_path}（拆分{len(all_ids)}个片段）"

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

    # 增强版语义搜索：返回匹配片段+页码
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

        # 格式化结果（新增片段+页码）
        search_results = []
        for i in range(len(results["ids"][0])):
            meta = results["metadatas"][0][i]
            distance = results["distances"][0][i]
            search_results.append({
                "file_name": meta["file_name"],
                "path": meta["path"],
                "topic": meta["topic"],
                "page": meta["page"],  # 返回匹配的页码
                "matched_chunk": results["documents"][0][i],  # 返回匹配的文本片段
                "similarity": round(1 - distance, 4)  # 相似度（0-1）
            })
        return search_results