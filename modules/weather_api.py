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
        print(f"🔍 APIリクエスト送信: {start_date} ~ {end_date} (Lat: {lat}, Lon: {lon})")
        response = requests.get(PROXY_URL, params=params, timeout=20)
        print(f"📡 ステータスコード: {response.status_code}")

        if response.status_code != 200:
            print(f"❌ APIエラー ({response.status_code}): {response.text}")
            return {}

        raw_data = response.json()
        nodes = raw_data.get("nodes", [])
        if not nodes:
            print("⚠️ APIレスポンスに 'nodes' が含まれていません。")
            return {}

        leaves = nodes[0].get("leaves", [])
        
        # 利用可能な葉（変数名）のリストをデバッグ表示
        available_leaves = [leaf.get("name") for leaf in leaves if leaf.get("name")]
        print(f"🌿 取得可能な変数一覧: {available_leaves}")

        # --- 気温データなどを柔軟に探す（自動フォールバック対応） ---
        target_vars = ["TMP_mea", "TMP_ave", "TMP", "temp", "temperature"]
        tmp_data = []
        found_var = None
        
        # 1. 優先候補から探す
        for var_name in target_vars:
            for leaf in leaves:
                if leaf.get("name") == var_name:
                    tmp_data = leaf.get("data", [])
                    found_var = var_name
                    break
            if tmp_data:
                break

        # 2. もし候補に見つからない場合、time以外の最初の有効なデータを自動採用する
        if not tmp_data and leaves:
            for leaf in leaves:
                if leaf.get("name") != "time" and len(leaf.get("data", [])) > 0:
                    tmp_data = leaf.get("data", [])
                    found_var = leaf.get("name")
                    break

        print(f"🎯 実際に採用された変数名: {found_var}")

        # タイムデータの取得
        time_data = []
        for leaf in leaves:
            if leaf.get("name") == "time":
                time_data = leaf.get("data", [])
                break

        if not tmp_data or not time_data:
            print(f"⚠️ 気温データまたは時間データが見つかりませんでした (tmp_data: {len(tmp_data)}, time_data: {len(time_data)})")
            return {}

        formatted_weather = {}
        base_date = datetime.date(1900, 1, 1)

        for t_val, tmp_val in zip(time_data, tmp_data):
            # 経過日数を日付に変換
            date_key = base_date + datetime.timedelta(days=int(t_val))
            
            # 気温値のネストを安全に解除
            actual_temp = tmp_val
            while isinstance(actual_temp, list):
                if len(actual_temp) > 0:
                    actual_temp = actual_temp[0]
                else:
                    actual_temp = None
                    break

            if actual_temp is not None:
                try:
                    formatted_weather[date_key] = float(actual_temp)
                except (ValueError, TypeError):
                    pass

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