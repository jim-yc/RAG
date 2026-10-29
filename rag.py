from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient


# 初始化模型與本地資料庫
encoder = SentenceTransformer("BAAI/bge-m3")
client = QdrantClient(path="db_20261027")


def retrieve_article(question: str) -> dict | None:
    # 將問題轉換為向量
    query_vector = encoder.encode(
        question,
        normalize_embeddings=True,
    ).tolist()

    # 搜尋餘弦相似度最高的文章
    results = client.query_points(
        collection_name="health_news",
        query=query_vector,
        limit=1,
        with_payload=True,
    ).points

    # 回傳完整 metadata，沒有結果則回傳 None
    return results[0].payload if results else None


def input_injection(question: str, payload_dict: dict) -> str:
    prompt = f"""
    使用者原始問題： {question}；
    你參考以下資料直接回答，不能憑空捏造不存在的資訊： {payload_dict["content"]}；
    在回答的後面必須加上如下資訊，格式和內容必須完全一模一樣：
    參考來源標題：{payload_dict["title"]}, 連結：{payload_dict["link"]}, 時間：{payload_dict["date"]}
    """
    return prompt