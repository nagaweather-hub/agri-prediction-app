# -*- coding: utf-8 -*-
"""
Created on Mon Jul 27 08:57:53 2026

@author: user
"""

import datetime
import math
import requests

# --- 1. 品種ごとのパラメーター定義 (画像データを元に設定) ---
VARIETY_PARAMS = {
    "コシヒカリ": {"has_p": False, "x1": -0.0052, "x2": 0.0009, "x3": 0.0, "hogoe_days_before_heading": 18, "seijuku_sum_temp": 1027, "nakaboshi_dvi": None},
    "つや姫": {"has_p": False, "x1": -0.0067, "x2": 0.0009, "x3": 0.0, "hogoe_days_before_heading": 25, "seijuku_sum_temp": 989, "nakaboshi_dvi": None},
    "ヒノヒカリ": {"has_p": True, "x1": 0.1438, "x2": 0.0004, "x3": -0.0101, "hogoe_days_before_heading": 20, "seijuku_sum_temp": 1027, "nakaboshi_dvi": None},
    "にこまる": {"has_p": True, "x1": 0.1048, "x2": 0.0006, "x3": -0.0078, "hogoe_days_before_heading": 20, "seijuku_sum_temp": 1027, "nakaboshi_dvi": 0.22},
    "なつほのか": {"has_p": True, "x1": 0.0545, "x2": 0.0007, "x3": -0.0041, "hogoe_days_before_heading": 20, "seijuku_sum_temp": 1050, "nakaboshi_dvi": 0.37}
}


# --- 2. API接続設定 ---
PROXY_URL = "https://proxy-weather-data-120087242080.asia-northeast1.run.app"



# --- 3. 気象データ取得関連の関数 ---
def get_auth_key(url, userid, password):
    payload = {"userid": userid, "password": password}
    response = requests.post(url, data=payload)
    if response.status_code == 200:
        return response.text.strip()
    return None

def convert_time_to_date_obj(days_since_1900):
    """1900からの日数を datetime.date オブジェクトに変換"""
    base_date = datetime.date(1900, 1, 1)
    return base_date + datetime.timedelta(days=int(days_since_1900))


def fetch_real_weather_dict(userid, auth_key, lat, lon, start_date, end_date):
    import datetime
    
    params = {
        "latitude": str(lat),
        "longitude": str(lon),
        "startdate": start_date.strftime("%Y-%m-%d"),
        "enddate": end_date.strftime("%Y-%m-%d")
    }
    
    try:
        response = requests.get(PROXY_URL, params=params)
        if response.status_code != 200:
            print(f"エラーが発生しました（ステータスコード: {response.status_code}）")
            return None
            
        raw_data = response.json()
        
        # --- 複雑な構造からデータを抽出して変換する処理 ---
        nodes = raw_data.get("nodes", [])
        if not nodes:
            return None
            
        leaves = nodes[0].get("leaves", [])
        
        # 気温データと時間データの取り出し
        tmp_data = []
        time_data = []
        for leaf in leaves:
            if leaf.get("name") == "TMP_mea":
                tmp_data = leaf.get("data", [])
            elif leaf.get("name") == "time":
                time_data = leaf.get("data", [])
                
        # { datetime.date: 気温 } の辞書を作成
        formatted_weather = {}
        base_date = datetime.date(1900, 1, 1)
        
        for t_val, tmp_val in zip(time_data, tmp_data):
            # 1900年からの経過日数を日付オブジェクトに変換
            date_key = base_date + datetime.timedelta(days=int(t_val))
            # 三次元配列の奥底から気温の値を取り出す
            actual_temp = tmp_val[0][0]
            formatted_weather[date_key] = actual_temp
            
        return formatted_weather
        
    except Exception as e:
        print(f"通信またはデータ処理エラー: {e}")
        return None


# --- 4. 可照日長時間を計算する関数 ---
def calculate_daylight_hours(latitude, date):
    day_of_year = date.timetuple().tm_yday
    lat_rad = math.radians(latitude)
    declination = math.radians(23.45 * math.sin(2 * math.pi * (284 + day_of_year) / 365.0))
    cos_h0 = -math.tan(lat_rad) * math.tan(declination)
    if cos_h0 >= 1.0: return 0.0
    if cos_h0 <= -1.0: return 24.0
    h0 = math.acos(cos_h0)
    return 2 * math.degrees(h0) / 15.0

# --- 5. シミュレーション実行メインロジック ---

# --- 5. シミュレーション実行メインロジック (出穂翌日積算版) ---
def run_real_simulation(auth_key):
    # --- 条件設定 ---
    LATITUDE = 32.8343        # 緯度
    LONGITUDE = 130.0241      # 経度
    VARIETY_NAME = "ヒノヒカリ"  # 品種名
    TRANSPLANT_DATE = datetime.date(2026, 5, 20)  # 移植日

    p = VARIETY_PARAMS[VARIETY_NAME]
    
    # 移植日から220日間の気象データを取得
    end_date = TRANSPLANT_DATE + datetime.timedelta(days=220)
    print("ビジョンテックAPIから気象データを取得中...")
    weather_data = fetch_real_weather_dict("dummy", auth_key, LATITUDE, LONGITUDE, TRANSPLANT_DATE, end_date)
    
    print("★取得したデータの中身:", weather_data)
    
    if not weather_data:
        print("気象データの取得に失敗しました。")
        return

    current_date = TRANSPLANT_DATE
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
            
        daylight = calculate_daylight_hours(LATITUDE, current_date)
        
        # 1. 出穂前であればDVRの計算と積算を行う
        if not found_heading:
            if p["has_p"]:
                dvr = p["x1"] + (p["x2"] * t) + (p["x3"] * daylight)
            else:
                dvr = p["x1"] + (p["x2"] * t)
                
            # DVRがマイナスにならないよう調整
            if dvr < 0:
                dvr = 0.0
                
            accumulated_dvi += dvr
        
            # 2. 中干し日判定
            if p["nakaboshi_dvi"] and nakaboshi_date is None and accumulated_dvi >= p["nakaboshi_dvi"]:
                nakaboshi_date = current_date
                
            # 3. 出穂日判定
            if accumulated_dvi >= 1.0:
                heading_date = current_date
                found_heading = True
                # ★出穂翌日から気温を積算するため、出穂日はここで処理をスキップして翌日へ進む
                current_date += datetime.timedelta(days=1)
                continue
            
        # 4. 成熟日判定 (出穂翌日以降の処理)
        if found_heading:
            accumulated_temp += t
            if seijuku_date is None and accumulated_temp >= p["seijuku_sum_temp"]:
                seijuku_date = current_date
                break # 成熟日決定でループ終了
            
        current_date += datetime.timedelta(days=1)
        
    if heading_date:
        # 穂肥日 (出穂日の〇日前)
        hogoe_date = heading_date - datetime.timedelta(days=p["hogoe_days_before_heading"])
        
        # 結果表示
        print("\n====================================")
        print(f"🌾 【修正版】水稲生育予測結果 ({VARIETY_NAME})")
        print(f"設定地点: 緯度 {LATITUDE} / 経度 {LONGITUDE}")
        print(f"移植日: {TRANSPLANT_DATE.strftime('%Y/%m/%d')}")
        print("------------------------------------")
        print(f"・中干し開始日 : {nakaboshi_date.strftime('%Y/%m/%d') if nakaboshi_date else 'なし'}")
        print(f"・穂肥日       : {hogoe_date.strftime('%Y/%m/%d')}")
        print(f"・出穂日 (DVI=1): {heading_date.strftime('%Y/%m/%d')}")
        print(f"・成熟日       : {seijuku_date.strftime('%Y/%m/%d') if seijuku_date else 'データ不足'}")
        print("====================================")


    else:
        print("\n期間内に出穂日に達しませんでした。データ取得期間またはパラメーターを確認してください。")


if __name__ == "__main__":
    # 認証キーの取得はスキップして、直接シミュレーションを実行します
    run_real_simulation("dummy")