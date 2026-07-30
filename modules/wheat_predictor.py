# -*- coding: utf-8 -*-
"""
Created on Tue Jul 28 16:04:28 2026

@author: user
"""

# -*- coding: utf-8 -*-
"""
麦生育予測モジュール (modules/wheat_predictor.py)
"""

import datetime
import math

# 品種ごとのパラメータ定義（画像に基づく）
WHEAT_VARIETY_PARAMS = {
    "長崎W2号": {
        # 積算気温 = a * X + b  (X は幼穂長のLog)
        "a": -227.01,
        "b": 493.65,
        "maturity_sum_temp": 930.0,
    },
    "長崎御島": {
        "a": -209.0,
        "b": 433.84,
        "maturity_sum_temp": 760.0,
    },
    "はるか二条": {
        "a": -223.8,
        "b": 476.16,
        "maturity_sum_temp": 750.0,
    },
}


def predict_wheat_growth(
    lat, lon, variety_name, survey_date, young_spike_length, weather_data
):
  """取得済みの気象データを使って麦の出穂日・成熟日を予測する関数

  Parameters:
      lat (float): 緯度
      lon (float): 経度
      variety_name (str): 品種名
      survey_date (datetime.date): 調査日
      young_spike_length (float): 主稈幼穂長 (cm または mm ※通常はcm等の実測値)
      weather_data (dict): 取得した気象データ (date -> temp)
  """
  if variety_name not in WHEAT_VARIETY_PARAMS:
    return {"error": f"未定義の品種です: {variety_name}"}

  if young_spike_length <= 0:
    return {"error": "主稈幼穂長は0より大きい値を入力してください。"}

  p = WHEAT_VARIETY_PARAMS[variety_name]

  # X は幼穂長のLog（※環境に合わせて math.log または math.log10 を選択。一般的には自然対数 math.log）
  # 常用対数の場合は math.log10(young_spike_length) に変更してください
  x_val = math.log(young_spike_length)

  # 調査日から出穂日までに必要な積算気温を算出
  required_temp_to_heading = (p["a"] * x_val) + p["b"]

  current_date = survey_date
  end_date = survey_date + datetime.timedelta(days=150)  # 調査日から最大150日先まで探索

  accumulated_temp = 0.0
  heading_date = None
  maturity_date = None

  found_heading = False

  while current_date <= end_date:
    t = weather_data.get(current_date)
    if t is None:
      current_date += datetime.timedelta(days=1)
      continue

    if not found_heading:
      accumulated_temp += t
      # 必要な積算気温に達したら出穂日
      if accumulated_temp >= required_temp_to_heading:
        heading_date = current_date
        found_heading = True
        # 出穂日以降の成熟期用積算温度の計算に切り替えるため、いったんリセットまたは継続
        accumulated_temp = 0.0
    else:
      accumulated_temp += t
      # 成熟期の積算温度に達したら成熟日
      if accumulated_temp >= p["maturity_sum_temp"]:
        maturity_date = current_date
        break

    current_date += datetime.timedelta(days=1)

  return {
      "variety": variety_name,
      "survey_date": survey_date,
      "young_spike_length": young_spike_length,
      "heading_date": heading_date,
      "seijuku_date": maturity_date,
  }