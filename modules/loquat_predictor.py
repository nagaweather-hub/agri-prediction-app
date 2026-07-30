# -*- coding: utf-8 -*-
"""
Created on Tue Jul 28 16:46:49 2026

@author: user
"""

# -*- coding: utf-8 -*-
"""
びわ 収穫予測モジュール (modules/loquat_predictor.py)
"""

import datetime

# 品種ごとの「茂木」の収穫日からの日数差（オフセット）
LOQUAT_VARIETY_OFFSETS = {
    "涼峰": -10,
    "長崎早生": -10,
    "涼風": -8,
    "福原早生": -6,
    "なつたより": -5,
    "茂木": 0,
    "陽玉": 5,
    "白茂木": 7,
}


def predict_loquat_growth(
    lat, lon, variety_name, flowering_end_date, weather_data
):
  """取得済みの気象データを使って、茂木のDVRモデルをベースにびわの収穫日を予測する関数

  Parameters:
      lat (float): 緯度
      lon (float): 経度
      variety_name (str): 品種名
      flowering_end_date (datetime.date): 開花終期（起算日）
      weather_data (dict): 取得した気象データ (date -> temp)
  """
  if variety_name not in LOQUAT_VARIETY_OFFSETS:
    return {"error": f"未定義の品種です: {variety_name}"}

  day_offset = LOQUAT_VARIETY_OFFSETS[variety_name]

  # 1. まず基準となる「茂木」の収穫日（DVRが1.0に達する日）を計算
  current_date = flowering_end_date + datetime.timedelta(days=1)
  end_date = flowering_end_date + datetime.timedelta(days=250)  # 最大250日先まで探索

  dvr_sum = 0.0
  mogegi_harvest_date = None

  while current_date <= end_date:
    t = weather_data.get(current_date)
    if t is None:
      current_date += datetime.timedelta(days=1)
      continue

    # 茂木のDVR計算式: DVR = 0.00107299 * 日平均気温 - 0.00578827
    dvr = (0.00107299 * t) - 0.00578827
    # DVRがマイナスになる場合は0に補正
    dvr = max(0.0, dvr)

    dvr_sum += dvr

    # DVRの積算が 1.0 に達したら茂木の収穫日
    if dvr_sum >= 1.0:
      mogegi_harvest_date = current_date
      break

    current_date += datetime.timedelta(days=1)

  if mogegi_harvest_date is None:
    return {
        "error": "期間内にDVRが1.0に達しませんでした（データ不足の可能性）"
    }

  # 2. 茂木の収穫日に、品種ごとの日数差を足し引きして対象品種の収穫日を算出
  target_harvest_date = mogegi_harvest_date + datetime.timedelta(
      days=day_offset
  )

  return {
      "variety": variety_name,
      "flowering_end_date": flowering_end_date,
      "mogegi_harvest_date": mogegi_harvest_date,
      "day_offset": day_offset,
      "harvest_date": target_harvest_date,
  }