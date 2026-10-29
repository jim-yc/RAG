import streamlit as st
from openai import OpenAI, OpenAIError

import rag

client = OpenAI(
    base_url="http://localhost:9931/v1",
    api_key="not-needed"
)

model_name = client.models.list().data[0].id
print(f"目前 llama-server 運行的模型名稱為: {model_name}")

# 1. 頁面設定
st.set_page_config(page_title="AI 對話系統", page_icon="💬")
st.title("AI 連續對話")

# 2. 初始化對話紀錄
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# 3. 側邊欄
with st.sidebar:
    use_rag = st.checkbox("啟用 RAG 檢索", value=False)

    if st.button("清除歷史對話", use_container_width=True):
        st.session_state.chat_history = []
        st.rerun()

# 4. 呼叫 llama-server 串流生成
def generate_chat_stream(messages, use_rag=False):
    api_messages = [message.copy() for message in messages]

    # 依 use_rag 決定是否執行 RAG 檢索，並將檢索結果加入 api_messages。
    if use_rag:
        user_message = api_messages[-1]["content"]
        payload_dict = rag.retrieve_article(user_message)
        injected_message = rag.input_injection(user_message, payload_dict)
        api_messages[-1]["content"] = injected_message

    stream = client.chat.completions.create(
        model=model_name,
        messages=api_messages,
        temperature=0.7,
        stream=True,
    )

    for chunk in stream:
        if chunk.choices:
            content = chunk.choices[0].delta.content
            if content:
                yield content

# 5. 顯示歷史對話，使用 Markdown 解析
for message in st.session_state.chat_history:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# 6. 接收使用者輸入
if user_input := st.chat_input("請輸入你想說的話..."):
    user_message = {"role": "user", "content": user_input}
    st.session_state.chat_history.append(user_message)

    with st.chat_message("user"):
        st.markdown(user_input)

    with st.chat_message("assistant"):
        placeholder = st.empty()
        full_response = ""

        try:
            for chunk in generate_chat_stream(st.session_state.chat_history, use_rag=use_rag):
                full_response += chunk
                placeholder.markdown(full_response + "▌")

            # 完成後移除游標
            placeholder.markdown(full_response)

            st.session_state.chat_history.append({
                "role": "assistant",
                "content": full_response,
            })

        except OpenAIError as error:
            st.error(
                f"無法連線至 llama-server，"
                f"請確認伺服器是否啟動。\n\n{error}"
            )
