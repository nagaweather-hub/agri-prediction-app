import os
from bs4 import BeautifulSoup
import requests

# --- 設定項目 ---
TARGET_URL = "https://okuyamiran.net/okuyami/published/nagasaki/"
# 必要に応じて、探したい苗字をここに自由に追加・変更してください
TARGET_SURNAMES = ["前田", "横田", "高橋", "馬場"]
# ----------------


def check_okuyami():
  try:
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )
    }
    response = requests.get(TARGET_URL, headers=headers, timeout=10)
    response.raise_for_status()
    response.encoding = response.apparent_encoding

    soup = BeautifulSoup(response.text, "html.parser")
    page_text = soup.get_text()

    hit_surnames = []
    for surname in TARGET_SURNAMES:
      if surname in page_text:
        hit_surnames.append(surname)

    if hit_surnames:
      surnames_str = "、".join(hit_surnames)
      message = (
          f"【おくやみ欄 通知】\n"
          f"指定した苗字「{surnames_str}」が掲載されている可能性があります。\n\n"
          f"確認URL:\n{TARGET_URL}"
      )
      send_line_messaging_api(message)
      print(f"検出成功: {surnames_str} のLINE通知を送信しました。")
    else:
      print("指定された苗字は該当ありませんでした。")

  except Exception as e:
    print(f"エラーが発生しました: {e}")


def send_line_messaging_api(message_text):
  access_token = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN")
  user_id = os.environ.get("LINE_USER_ID")

  url = "https://api.line.me/v2/bot/message/push"
  headers = {
      "Content-Type": "application/json",
      "Authorization": f"Bearer {access_token}",
  }
  payload = {"to": user_id, "messages": [{"type": "text", "text": message_text}]}

  response = requests.post(url, headers=headers, json=payload)
  if response.status_code != 200:
    print(
        f"LINE通知の送信に失敗しました: {response.status_code}, {response.text}"
    )


if __name__ == "__main__":
  check_okuyami()