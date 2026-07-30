# -*- coding: utf-8 -*-
"""
Created on Tue Jul 28 16:41:54 2026

@author: user
"""

# -*- coding: utf-8 -*-
"""
バレイショ春作マルチ栽培 目標収量到達時期予測モジュール (modules/potato_predictor.py)
"""

import datetime

# 画像の定義に基づく品種別パラメータ（目標積算温度）
POTATO_VARIETY_PARAMS = {
    "ニシユタカ": {"target_sum_temp": 894.0},
    "デジマ": {"target_sum_temp": 820.0},
    "アイユタカ": {"target_sum_temp": 863.0},
    "さんじゅう丸": {"target_sum_temp": 740.0},
    "アイマサリ": {"target_sum_temp": 732.0},
}


def predict_potato_growth(lat, lon, variety_name, emergence_date, weather_data):
  """取得済みの気象データを使ってバレイショの目標収量到達時期を予測する関数

  Parameters:
      lat (float): 緯度
      lon (float): 経度
      variety_name (str): 品種名
      emergence_date (datetime.date): 出芽日
      weather_data (dict): 取得した気象データ (date -> temp)
  """
  if variety_name not in POTATO_VARIETY_PARAMS:
    return {"error": f"未定義の品種です: {variety_name}"}

  p = POTATO_VARIETY_PARAMS[variety_name]

  # 条件：出芽日の翌日から日平均気温の積算を開始
  current_date = emergence_date + datetime.timedelta(days=1)
  end_date = emergence_date + datetime.timedelta(days=180)  # 最大180日先まで探索

  accumulated_temp = 0.0
  target_achieved_date = None

  while current_date <= end_date:
    t = weather_data.get(current_date)
    if t is None:
      current_date += datetime.timedelta(days=1)
      continue

    # 日平均気温を積算
    accumulated_temp += t

    # 品種ごとの目標積算温度に達した日
    if accumulated_temp >= p["target_sum_temp"]:
      target_achieved_date = current_date
      break

    current_date += datetime.timedelta(days=1)

  return {
      "variety": variety_name,
      "emergence_date": emergence_date,
      "target_sum_temp": p["target_sum_temp"],
      "accumulated_temp_at_end": accumulated_temp,
      "target_achieved_date": target_achieved_date,
  }