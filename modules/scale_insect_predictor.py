# -*- coding: utf-8 -*-
"""
Created on Tue Jul 28 16:51:09 2026

@author: user
"""

# -*- coding: utf-8 -*-
"""
露地ビワ ナシマルカイガラムシ 第一世代歩行幼虫発生ピーク予測モジュール
"""

import datetime


def predict_scale_insect_peak(lat, lon, target_year, weather_data):
  """指定された年の3月1日から起算し、発育零点・発育停止温度を考慮した有効積算温度から

  ナシマルカイガラムシ第一世代歩行幼虫の発生ピーク日（429日度到達日）を予測する関数

  Parameters:
      lat (float): 緯度
      lon (float): 経度
      target_year (int): 予測対象の年 (例: 2026)
      weather_data (dict): 取得した気象データ (date -> temp)
                           ※ここでは日平均気温を想定。もし日最高・最低がある場合は平均値等を利用
  """
  # 3月1日を起算日とする
  start_date = datetime.date(target_year, 3, 1)
  current_date = start_date
  end_date = datetime.date(target_year, 8, 31)  # 8月末まで探索

  effective_gdd_sum = 0.0
  peak_date = None

  # パラメータ設定
  base_temp = 10.5  # 発育零点
  upper_temp = 32.2  # 発育停止温度（上限）
  target_threshold = 429.0  # 目標積算温度（429日度）

  while current_date <= end_date:
    t = weather_data.get(current_date)
    if t is None:
      current_date += datetime.timedelta(days=1)
      continue

    # 発育停止温度を超える場合は上限に丸める、あるいは発育零点未満は0にする処理
    # 一般的なアボ法等の日別計算：
    # 日平均気温が発育零点以下の場合は有効温度0
    # 発育停止温度を超える場合は、有効温度の計算上限を考慮するか、あるいは上限温度で頭打ちにする
    if t <= base_temp:
      effective_temp = 0.0
    else:
      # 発育停止温度（32.2℃）を超える場合の処理（上限でキャップする一般的なモデル）
      capped_t = min(t, upper_temp)
      effective_temp = capped_t - base_temp

    effective_gdd_sum += effective_temp

    # 429日度に達した日
    if effective_gdd_sum >= target_threshold:
      peak_date = current_date
      break

    current_date += datetime.timedelta(days=1)

  return {
      "target_year": target_year,
      "start_date": start_date,
      "target_threshold": target_threshold,
      "accumulated_gdd": effective_gdd_sum,
      "peak_date": peak_date,
  }