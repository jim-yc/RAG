import requests
from bs4 import BeautifulSoup as bs
import asyncio
import time
import re
import random
import json

from openai import OpenAI


client = OpenAI(
    base_url="http://localhost:9931/v1",
    api_key="not-needed"  # 本地模型不需要 key，但 SDK 要求必填，隨便給個字串即可
    )

model_name = client.models.list().data[0].id
print(f"目前 llama-server 運行的模型名稱為: {model_name}")

# 大腸癌相關新聞的網址
url = "https://www.healthnews.com.tw"
main_link = f"{url}/channel/9b508eee-a171-75b6-0963-eec4e463fc46"

# 定義 HTTP 請求的標頭，模擬瀏覽器行為
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/153.0.0.0 Safari/537.36"
}

# 用於總結文章內容的函數
def summarize_text(text):
    # 組合要傳送的訊息
    content = f'''請幫我總結、摘要以下文章內容：
    
    ============================

    {text}

    ============================

    注意：
    1. 使用繁體中文。
    2. 不要使用 markdown 語法。
    3. 只要提供總結、摘要的結果，不要提供其他內容。
    4. 不需要條列說明，將總結、摘要的結果以完整的文字段落形式呈現，不用換行。
    5. 摘要的字數應該介於 190 到 200 字之間，並且要包含文章的主要重點。
    6. 摘要的內容應該要有邏輯性。
    
    總結、摘要的結果：'''

    # 以多輪對話的型式，將文章內容傳送給 Ollama API，並取得總結結果
    messages = [
        {'role': 'system', 'content': '你是一個專業的新聞總結、摘要專家，請幫我將文章內容進行總結、摘要，並以繁體中文回答。'},
        {'role': 'user', 'content': content},
    ]

    response = client.chat.completions.create(
        model=model_name,
        messages=messages,
        temperature=0.7,
    )

    return response.choices[0].message.content



li_data = []     # 爬取每一頁的文章列表
t1 = time.time() # 計算時間
all_pages = 10   # 爬取頁數

for page in range(1, all_pages + 1):
    # 組合每一頁的 URL
    page_url = f"{main_link}/{page}"

    # 發送 GET 請求，取得網頁內容
    res = requests.get(page_url, headers=headers, timeout=10)

    # 解析網頁內容，取得文章文字
    if res.status_code == 200:
        # 解析網頁內容
        soup = bs(res.text, "lxml")

        # 取得每一則新聞
        li_news = soup.select("ul.list-unstyled > li.list-item")

        # 取得新聞底下的元素
        for li in li_news:
            # 新聞發文來源資訊
            source_info = li.select_one("div.list-info").get_text().strip()

            # 移除與大腸症無關的新聞
            if "大腸" not in source_info:
                continue

            # 取得新聞連結
            link = url + li.select_one("div.list-title > a[href]")["href"]

            # 取得記者名稱和發文日期
            m = re.search(r"(?:記者)?(\w+)(?:報導|整理)\s*(\d{4}-\d{1,2}-\d{1,2})", source_info)
            if m:
                reporter = m.group(1)
                date = m.group(2)
            
            # 將新聞資訊存入字典中
            li_data.append({"link": link, "reporter": reporter, "date": date})

    else:
        print(f"Failed to retrieve page {page}: {res.status_code}")

    # 隨機等待數秒，避免對網站造成過大壓力
    random_time = 0.01 * random.randint(100, 500)
    print(f"wait {random_time} seconds")
    time.sleep(random_time)

# 將 list 資料寫到 JSON 檔案中
with open("news_list.json", "w", encoding="utf-8") as f:
    json.dump(li_data, f, ensure_ascii=False, indent=None)

'''
如果上面的程式碼執行成功，會在同一個資料夾下產生 news_list.json 檔案，裡面包含了所有新聞的連結、記者名稱和發文日期。
有了 news_list.json 檔案後，就可以進一步爬取每一則新聞的內頁資訊，並將其存入 news_data.json 檔案中。
'''

# 讀取 news_list.json 檔案
with open("news_list.json", "r", encoding="utf-8") as f:
    li_data = json.load(f)
    print(f"已讀取 {len(li_data)} 筆新聞資料")

# 取得新聞內頁的資訊
for index, news in enumerate(li_data):
    # 發送 GET 請求，取得網頁內容
    res = requests.get(news["link"], headers=headers, timeout=10)

    # 解析網頁內容，取得文章文字
    if res.status_code == 200:
        # 解析網頁內容
        soup = bs(res.text, "lxml")

        # 取得新聞標題
        a = soup.select_one("div#article-title > a[href]")
        title = a.get_text().strip()

        # 取得新聞內文
        content = soup.select_one("div#article-content").get_text().strip()
        
        # 將新聞標題、內文、圖片路徑存入字典中
        news["id"] = index
        news["title"] = title
        news["content"] = content

        print("=" * 80)
        print(f"Index: {index}")
        print(f"新聞標題: {title}")

    else:
        print(f"Failed to retrieve news: {res.status_code}")
        print(f"url: {news['link']}")

    # 隨機等待數秒，避免對網站造成過大壓力
    random_time = 0.01 * random.randint(100, 500)
    print(f"wait {random_time} seconds")
    time.sleep(random_time)


# 將 list 資料寫到 JSON 檔案中
with open("news_data.json", "w", encoding="utf-8") as f:
    json.dump(li_data, f, ensure_ascii=False, indent=4)

# 爬完所有資料再進行總結，以免意外卡住
with open("news_data.json", "r", encoding="utf-8") as f:
    li_data = json.load(f)
    print(f"已讀取 {len(li_data)} 筆新聞資料")

for index, news in enumerate(li_data):
    title = news["title"]
    content = news["content"]
    news["summary"] = summarize_text(title + " " + content)

    print("=" * 80)
    print(f"Index: {index}")
    print(f"新聞標題: {title}")
    print(f"新聞摘要: {news['summary']}")

    # 每總結十筆存檔一次
    if index % 10 == 0:
        with open("news_data_all.json", "w", encoding="utf-8") as f:
            json.dump(li_data, f, ensure_ascii=False, indent=4)


with open("news_data_all.json", "w", encoding="utf-8") as f:
    json.dump(li_data, f, ensure_ascii=False, indent=4)

t2 = time.time()
print(f"Total time: {t2 - t1:.2f} seconds ({(t2 - t1)/60:.2f} minutes)")

