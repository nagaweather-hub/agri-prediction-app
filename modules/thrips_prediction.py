# -*- coding: utf-8 -*-
"""
Created on Tue Aug  4 16:16:49 2026

@author: user
"""

# -*- coding: utf-8 -*-
"""
チャノキイロアザミウマ（スリップス） 複数世代発生予測モジュール
（1月1日起算・有効積算温度モデル）
"""

import datetime
import pandas as pd

def predict_thrips_generations(target_year, weather_data):
    """
    指定された年の1月1日から起算し、チャノキイロアザミウマの各世代の到達日を予測する関数
    
    Parameters:
        target_year (int): 予測対象の年 (例: 2026)
        weather_data (dict): 取得した気象データ (datetime.date -> float: 日平均気温)
        
    Returns:
        list: 各世代の予測到達日と積算温度のリスト
    """
    # 起算日を1月1日に設定
    start_date = datetime.date(target_year, 1, 1)
    end_date = datetime.date(target_year, 12, 31)  # 年末まで探索
    
    # パラメータ設定（画像に基づく条件）
    base_temp = 9.7     # 発育零点 (℃)
    upper_temp = 33.0   # 発育上限温度 (℃)
    stop_temp = 35.0    # 発育停止温度 (℃)
    
    # 各世代の目標積算温度（日度）
    generations = [
        {"name": "第1世代", "target": 360.0},
        {"name": "第2世代", "target": 670.0},
        {"name": "第3世代", "target": 980.0},
        {"name": "第4世代", "target": 1290.0},
        {"name": "第5世代", "target": 1600.0},
        {"name": "第6世代", "target": 1910.0},
        {"name": "第7世代", "target": 2220.0},
        {"name": "第8世代", "target": 2530.0},
        {"name": "第9世代", "target": 2840.0},
        {"name": "第10世代", "target": 3150.0},
    ]
    
    current_date = start_date
    effective_gdd_sum = 0.0
    results = []
    gen_idx = 0
    
    while current_date <= end_date and gen_idx < len(generations):
        t = weather_data.get(current_date)
        if t is None:
            # 気象データが存在しない日はスキップ
            current_date += datetime.timedelta(days=1)
            continue
            
        # 有効温度の計算
        # 発育停止温度以上、または発育零点以下の場合は有効温度0
        if t >= stop_temp or t <= base_temp:
            effective_temp = 0.0
        else:
            # 発育上限温度を超える場合は上限温度でキャップする
            capped_t = min(t, upper_temp)
            effective_temp = capped_t - base_temp
            
        effective_gdd_sum += effective_temp
        
        # 現在の世代の目標値に達したか判定
        target_threshold = generations[gen_idx]["target"]
        if effective_gdd_sum >= target_threshold:
            results.append({
                "世代": generations[gen_idx]["name"],
                "到達日": current_date,
                "積算温度(日度)": round(effective_gdd_sum, 2)
            })
            gen_idx += 1
            
        current_date += datetime.timedelta(days=1)
        
    return results

# --- 実行・テスト用コード ---
if __name__ == "__main__":
    target_year = 2026
    
    # ダミーの気象データ作成（1月1日〜12月31日までの日平均気温）
    date_range = pd.date_range(start=f"{target_year}-01-01", end=f"{target_year}-12-31", freq="D")
    
    # 簡易的な季節変動を持つ気温データを生成（テスト用）
    import numpy as np
    dummy_temps = 15 + 15 * np.sin(2 * np.pi * (date_range.dayofyear - 80) / 365)
    
    # 辞書型に変換 ({date: temp})
    weather_dict = {d.date(): t for d, t in zip(date_range, dummy_temps)}
    
    # 予測実行
    forecast_results = predict_thrips_generations(target_year, weather_dict)
    
    # 結果の表示
    print(f"【チャノキイロアザミウマ 世代別発生予測 ({target_year}年)】")
    for res in forecast_results:
        print(f"{res['世代']}: 到達日 = {res['到達日']} （積算温度: {res['積算温度(日度)']} 日度）")