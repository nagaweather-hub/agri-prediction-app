# -*- coding: utf-8 -*-
"""
気象データ取得専用モジュール (modules/weather_api.py)
"""

import datetime
import requests

# --- API接続設定 ---
PROXY_URL = "https://proxy-weather-data-120087242080.asia-northeast1.run.app"


def fetch_raw_chunk(userid, auth_key, lat, lon, start_date, end_date):
  """1回分のAPIリクエストを安全に実行する基本関数"""
  params = {
      "latitude": str(lat),
      "longitude": str(lon),
      "startdate": start_date.strftime("%Y-%m-%d"),
      "enddate": end_date.strftime("%Y-%m-%d"),
  }

  try:
    print(f"🔍 APIリクエスト送信: {start_date} ~ {end_date}")
    response = requests.get(PROXY_URL, params=params, timeout=20)
    print(f"📡 ステータスコード: {response.status_code}")

    if response.status_code != 200:
      print(f"❌ APIエラー ({response.status_code}): {response.text}")
      return {}

    raw_data = response.json()
    nodes = raw_data.get("nodes", [])
    if not nodes:
      return {}

    leaves = nodes[0].get("leaves", [])

    time_data = []
    for leaf in leaves:
      if leaf.get("name") == "time":
        time_data = leaf.get("data", [])
        break

    target_vars = ["TMP_mea", "TMP_ave", "TMP"]
    tmp_data = []
    for var_name in target_vars:
      for leaf in leaves:
        if leaf.get("name") == var_name:
          tmp_data = leaf.get("data", [])
          break
      if tmp_data:
        break

    if not tmp_data or not time_data:
      return {}

    formatted_weather = {}
    base_date = datetime.date(1900, 1, 1)

    for t_val, tmp_val in zip(time_data, tmp_data):
      date_key = base_date + datetime.timedelta(days=int(t_val))

      # 🔽 リスト構造（[[数値]]など）から確実に取り出して数値（float）に変換する処理
      try:
        if isinstance(tmp_val, list):
          val = tmp_val[0]
          while isinstance(val, list):
            val = val[0]
          actual_temp = float(val)
        else:
          actual_temp = float(tmp_val)
      except (IndexError, TypeError, ValueError):
        actual_temp = 0.0

      # デバッグ確認用（必要に応じて残してあります）
      print(
          f"DEBUG: t_val={t_val} -> 計算された日付={date_key},"
          f" 変換後温度={actual_temp}"
      )

      formatted_weather[date_key] = actual_temp

    return formatted_weather

  except Exception as e:
    print(f"❌ 例外発生: {e}")
    return {}


def fetch_real_weather_dict(
    userid, auth_key, lat, lon, start_date, end_date, chunk_days=60
):
  """指定された期間の気象データを取得する。

  年をまたぐ場合は自動で年ごとに分割してリクエストを送信する。
  """
  combined_weather = {}

  current_start = start_date
  sub_ranges = []

  while current_start <= end_date:
    potential_end = min(
        current_start + datetime.timedelta(days=chunk_days - 1), end_date
    )

    if current_start.year != potential_end.year:
      chunk_end = datetime.date(current_start.year, 12, 31)
    else:
      chunk_end = potential_end

    sub_ranges.append((current_start, chunk_end))
    current_start = chunk_end + datetime.timedelta(days=1)

  for s_date, e_date in sub_ranges:
    chunk_data = fetch_raw_chunk(userid, auth_key, lat, lon, s_date, e_date)
    if chunk_data:
      combined_weather.update(chunk_data)

  return combined_weather if combined_weather else None