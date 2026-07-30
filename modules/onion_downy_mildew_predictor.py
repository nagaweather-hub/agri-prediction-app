# -*- coding: utf-8 -*-
"""
Created on Tue Jul 28 16:10:08 2026

@author: user
"""

# -*- coding: utf-8 -*-
"""
タマネギべと病 一次伝染株初発期予測モジュール (modules/onion_downy_mildew_predictor.py)
"""

import datetime


def predict_onion_downy_mildew(lat, lon, transplant_date, weather_data):
  """取得済みの気象データを使ってタマネギべと病の初発期（積算気温400℃到達日）を予測する関数

  Parameters:
      lat (float): 緯度
      lon (float): 経度
      transplant_date (datetime.date): 定植日
      weather_data (dict): 取得した気象データ (date -> temp)
  """
  # 条件：定植日翌日からスタート
  current_date = transplant_date + datetime.timedelta(days=1)
  end_date = transplant_date + datetime.timedelta(
      days=250
  )  # 最大250日先まで探索

  accumulated_temp = 0.0
  first_appearance_date = None

  while current_date <= end_date:
    t = weather_data.get(current_date)
    if t is None:
      current_date += datetime.timedelta(days=1)
      continue

    # 日平均気温を積算
    accumulated_temp += t

    # 積算気温が400℃に達した日
    if accumulated_temp >= 400.0:
      first_appearance_date = current_date
      break

    current_date += datetime.timedelta(days=1)

  return {
      "transplant_date": transplant_date,
      "target_threshold": 400.0,
      "accumulated_temp_at_end": accumulated_temp,
      "first_appearance_date": first_appearance_date,
  }