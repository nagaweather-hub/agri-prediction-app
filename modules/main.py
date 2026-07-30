# -*- coding: utf-8 -*-
"""
Created on Tue Jul 28 15:27:28 2026

@author: user
"""

# -*- coding: utf-8 -*-
"""
水稲生育予測 実行メインスクリプト (main.py)
"""

# -*- coding: utf-8 -*-
import sys
from pathlib import Path

# 現在のファイルがある場所（APP開発フォルダ）をPythonの検索パスに強制追加する
current_dir = Path(__file__).resolve().parent
if str(current_dir) not in sys.path:
  sys.path.append(str(current_dir))

import datetime
from modules.rice_predictor import predict_rice_growth
from modules.weather_api import fetch_real_weather_dict




import datetime
from modules.rice_predictor import predict_rice_growth
from modules.weather_api import fetch_real_weather_dict


def main():
  # --- 条件設定 ---
  LATITUDE = 32.8343
  LONGITUDE = 130.0241
  VARIETY_NAME = "ヒノヒカリ"
  TRANSPLANT_DATE = datetime.date(2026, 5, 28)

  # 1. 共通の気象データ取得モジュールを使用
  end_date = TRANSPLANT_DATE + datetime.timedelta(days=150)
  print("ビジョンテックAPIから気象データを取得中...")
  weather_data = fetch_real_weather_dict(
      "dummy", "auth_key", LATITUDE, LONGITUDE, TRANSPLANT_DATE, end_date
  )

  if not weather_data:
    print("気象データの取得に失敗しました。")
    return

  # 2. 独立させた水稲予測モジュールを使用
  result = predict_rice_growth(
      LATITUDE, LONGITUDE, VARIETY_NAME, TRANSPLANT_DATE, weather_data
  )

  if "error" in result:
    print(result["error"])
    return

  # 3. 結果表示
  print("\n====================================")
  print(f"🌾 水稲生育予測結果 ({result['variety']})")
  print(f"設定地点: 緯度 {LATITUDE} / 経度 {LONGITUDE}")
  print(f"移植日: {result['transplant_date'].strftime('%Y/%m/%d')}")
  print("------------------------------------")

  nakaboshi_str = (
      result["nakaboshi_date"].strftime("%Y/%m/%d")
      if result["nakaboshi_date"]
      else "なし"
  )
  hogoe_str = (
      result["hogoe_date"].strftime("%Y/%m/%d")
      if result["hogoe_date"]
      else "データ不足"
  )
  heading_str = (
      result["heading_date"].strftime("%Y/%m/%d")
      if result["heading_date"]
      else "データ不足"
  )
  seijuku_str = (
      result["seijuku_date"].strftime("%Y/%m/%d")
      if result["seijuku_date"]
      else "データ不足"
  )

  print(f"・中干し開始日 : {nakaboshi_str}")
  print(f"・穂肥日       : {hogoe_str}")
  print(f"・出穂日 (DVI=1): {heading_str}")
  print(f"・成熟日       : {seijuku_str}")
  print("====================================")


if __name__ == "__main__":
  main()