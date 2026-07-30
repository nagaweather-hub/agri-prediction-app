# -*- coding: utf-8 -*-
"""
水稲生育予測モジュール (modules/rice_predictor.py)
"""

import datetime
import math

# 品種ごとのパラメーター定義
RICE_VARIETY_PARAMS = {
    "コシヒカリ": {
        "has_p": False,
        "x1": -0.0052,
        "x2": 0.0009,
        "x3": 0.0,
        "hogoe_days_before_heading": 18,
        "seijuku_sum_temp": 1027,
        "nakaboshi_dvi": None,
    },
    "つや姫": {
        "has_p": False,
        "x1": -0.0067,
        "x2": 0.0009,
        "x3": 0.0,
        "hogoe_days_before_heading": 25,
        "seijuku_sum_temp": 989,
        "nakaboshi_dvi": None,
    },
    "ヒノヒカリ": {
        "has_p": True,
        "x1": 0.1438,
        "x2": 0.0004,
        "x3": -0.0101,
        "hogoe_days_before_heading": 20,
        "seijuku_sum_temp": 1027,
        "nakaboshi_dvi": None,
    },
    "にこまる": {
        "has_p": True,
        "x1": 0.1048,
        "x2": 0.0006,
        "x3": -0.0078,
        "hogoe_days_before_heading": 20,
        "seijuku_sum_temp": 1027,
        "nakaboshi_dvi": 0.22,
    },
    "なつほのか": {
        "has_p": True,
        "x1": 0.0545,
        "x2": 0.0007,
        "x3": -0.0041,
        "hogoe_days_before_heading": 20,
        "seijuku_sum_temp": 1050,
        "nakaboshi_dvi": 0.37,
    },
}


def calculate_daylight_hours(latitude, date):
  day_of_year = date.timetuple().tm_yday
  lat_rad = math.radians(latitude)
  declination = math.radians(
      23.45 * math.sin(2 * math.pi * (284 + day_of_year) / 365.0)
  )
  cos_h0 = -math.tan(lat_rad) * math.tan(declination)
  if cos_h0 >= 1.0:
    return 0.0
  if cos_h0 <= -1.0:
    return 24.0
  h0 = math.acos(cos_h0)
  return 2 * math.degrees(h0) / 15.0


def predict_rice_growth(lat, lon, variety_name, transplant_date, weather_data):
  """取得済みの気象データを使って水稲の生育ステージを予測する関数"""
  if variety_name not in RICE_VARIETY_PARAMS:
    return {"error": f"未定義の品種です: {variety_name}"}

  p = RICE_VARIETY_PARAMS[variety_name]
  current_date = transplant_date
  end_date = transplant_date + datetime.timedelta(days=150)

  accumulated_dvi = 0.0
  accumulated_temp = 0.0

  heading_date = None
  nakaboshi_date = None
  seijuku_date = None
  found_heading = False

  while current_date <= end_date:
    t = weather_data.get(current_date)
    if t is None:
      current_date += datetime.timedelta(days=1)
      continue

    daylight = calculate_daylight_hours(lat, current_date)

    if not found_heading:
      if p["has_p"]:
        dvr = p["x1"] + (p["x2"] * t) + (p["x3"] * daylight)
      else:
        dvr = p["x1"] + (p["x2"] * t)

      dvr = max(0.0, dvr)
      accumulated_dvi += dvr

      if (
          p["nakaboshi_dvi"] is not None
          and nakaboshi_date is None
          and accumulated_dvi >= p["nakaboshi_dvi"]
      ):
        nakaboshi_date = current_date

      if accumulated_dvi >= 1.0:
        heading_date = current_date
        found_heading = True
        current_date += datetime.timedelta(days=1)
        continue

    if found_heading:
      accumulated_temp += t
      if seijuku_date is None and accumulated_temp >= p["seijuku_sum_temp"]:
        seijuku_date = current_date
        break

    current_date += datetime.timedelta(days=1)

  hogoe_date = (
      heading_date - datetime.timedelta(days=p["hogoe_days_before_heading"])
      if heading_date
      else None
  )

  return {
      "variety": variety_name,
      "transplant_date": transplant_date,
      "nakaboshi_date": nakaboshi_date,
      "hogoe_date": hogoe_date,
      "heading_date": heading_date,
      "seijuku_date": seijuku_date,
      "enable_drainage": p["nakaboshi_dvi"] is not None,
  }