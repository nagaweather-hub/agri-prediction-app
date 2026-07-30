# -*- coding: utf-8 -*-
"""
Created on Thu Jul 30 08:26:27 2026

@author: user
"""

# -*- coding: utf-8 -*-
"""
レタス収穫予測モジュール (modules/lettuce_predictor.py)
"""

import datetime


def calculate_lettuce_harvest(
    weather_dict, planting_date, covering_date, target_diameter, model_type
):
  """レタスの収穫日を積算温度（目標玉径から逆算）と被覆後温度補正を考慮して予測する。

  Parameters:
      weather_dict (dict): {datetime.date: 日平均気温, ...} の気象データ辞書
      planting_date (datetime.date): 定植日
      covering_date (datetime.date): 被覆日 (Noneの場合もあり得るが、日付またはNone)
      target_diameter (float): 目標玉径 (cm)
      model_type (str): "11・12月モデル", "1月モデル", "2月モデル" のいずれか

  Returns:
      dict: 予測結果（収穫予測日、必要積算温度、実積算温度、日別積算の推移など）
  """
  if not weather_dict:
    return {"error": "気象データが取得できませんでした。"}

  # 1. モデルごとの回帰係数 (y = ax - b の a と b)
  #    y: 玉径(cm), x: 積算温度(℃)
  #    逆算式: x = (目標玉径 + b) / a
  model_params = {
      "11・12月モデル": {"a": 0.0247, "b": 3.6921},
      "1月モデル": {"a": 0.0215, "b": 4.2965},
      "2月モデル": {"a": 0.0286, "b": 10.139},
  }

  if model_type not in model_params:
    return {"error": f"不明なモデルタイプです: {model_type}"}

  params = model_params[model_type]
  a = params["a"]
  b = params["b"]

  # 目標玉径から必要な積算温度（ターゲット）を逆算
  target_accumulated_temp = (target_diameter + b) / a

  # 2. 定植日以降の日付で積算温度を計算していく
  accumulated_temp = 0.0
  harvest_date = None
  daily_records = []

  # 気象データの日付を古い順にソートしてループ
  sorted_dates = sorted(weather_dict.keys())

  for current_date in sorted_dates:
    # 定植日より前のデータはスキップ
    if current_date < planting_date:
      continue

    raw_temp = weather_dict[current_date]
    if raw_temp is None:
      continue

    # 3. 被覆日以降は温度補正を適用
    #    被覆内温度 = 0.88 × 気温 + 2.052
    effective_temp = raw_temp
    is_covered = False
    if covering_date and current_date >= covering_date:
      effective_temp = 0.88 * raw_temp + 2.052
      is_covered = True

    accumulated_temp += effective_temp
    daily_records.append({
        "date": current_date,
        "raw_temp": raw_temp,
        "effective_temp": effective_temp,
        "accumulated_temp": accumulated_temp,
        "is_covered": is_covered,
    })

    # ターゲットの積算温度に到達したら、その日を収穫予測日とする
    if accumulated_temp >= target_accumulated_temp:
      harvest_date = current_date
      break

  # もし期間内のデータが終わっても目標に達しなかった場合
  if harvest_date is None and daily_records:
    # 最後の日のデータを仮の収穫日とする
    harvest_date = daily_records[-1]["date"]

  return {
      "planting_date": planting_date,
      "covering_date": covering_date,
      "target_diameter": target_diameter,
      "model_type": model_type,
      "target_accumulated_temp": target_accumulated_temp,
      "actual_accumulated_temp": (
          daily_records[-1]["accumulated_temp"] if daily_records else 0.0
      ),
      "harvest_date": harvest_date,
      "daily_records": daily_records,
  }