import json
from pathlib import Path

import torch
from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams


# 基本設定
DATA_FILE = Path("news_data_all.json")
DB_PATH = "db_20261027"
COLLECTION_NAME = "health_news"
MODEL_NAME = "BAAI/bge-m3"


def main():
    # 1. 讀取 JSON：支援單筆物件或物件列表
    with DATA_FILE.open("r", encoding="utf-8") as file:
        records = json.load(file)

    if not isinstance(records, list) or not records:
        raise ValueError("JSON 必須是非空的物件或物件列表")

    # 2. 載入向量模型
    encoder = SentenceTransformer(MODEL_NAME,
                                device="xpu",
                                model_kwargs={"torch_dtype": torch.bfloat16})

    summaries = [record["summary"] for record in records]

    vectors = encoder.encode(
        summaries,
        batch_size=8,
        normalize_embeddings=True,
        show_progress_bar=True,
    )

    # 3. 建立本地 Qdrant 資料庫
    client = QdrantClient(path=DB_PATH)

    try:
        vector_size = encoder.get_sentence_embedding_dimension()

        if client.collection_exists(COLLECTION_NAME):
            collection = client.get_collection(COLLECTION_NAME)
            existing_size = collection.config.params.vectors.size

            if existing_size != vector_size:
                raise ValueError(
                    f"Collection 向量維度不符："
                    f"{existing_size} != {vector_size}"
                )
        else:
            client.create_collection(
                collection_name=COLLECTION_NAME,
                vectors_config=VectorParams(
                    size=vector_size,
                    distance=Distance.COSINE,
                ),
            )

        # 4. 將向量與完整原始資料寫入 Qdrant
        points = [
            PointStruct(id=record["id"], vector=vector.tolist(), payload=record.copy())
            for record, vector in zip(records, vectors)
        ]

        client.upsert(
            collection_name=COLLECTION_NAME,
            points=points,
            wait=True,
        )

        print(f"成功寫入 {len(points)} 筆資料")
        print(f"資料庫位置：{Path(DB_PATH).resolve()}")
        print(f"Collection：{COLLECTION_NAME}")
        print(f"向量維度：{vector_size}")

    finally:
        client.close()


if __name__ == "__main__":
    main()