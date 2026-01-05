import chromadb
from chromadb.config import Settings

class VectorDB:
    def __init__(self, db_path: str = "./data/chroma_db"):
        # 初始化ChromaDB（持久化存储，Python 3.9 兼容）
        self.client = chromadb.PersistentClient(
            path=db_path,
            settings=Settings(allow_reset=True, anonymized_telemetry=False)  # 关闭匿名统计
        )

    # 获取或创建集合
    def get_collection(self, collection_name: str):
        return self.client.get_or_create_collection(name=collection_name)

    # 向集合添加数据（ids/embeddings为列表）
    def add_data(self, collection_name: str, ids: list, embeddings: list, metadatas: list = None, documents: list = None):
        try:
            collection = self.get_collection(collection_name)
            collection.add(
                ids=ids,
                embeddings=embeddings,
                metadatas=metadatas,
                documents=documents
            )
        except Exception as e:
            print(f"向量数据库添加数据失败：{e}")

    # 相似向量查询（返回top N结果）
    def query(self, collection_name: str, query_embeddings: list, n_results: int = 5):
        collection = self.get_collection(collection_name)
        return collection.query(
            query_embeddings=query_embeddings,
            n_results=n_results
        )