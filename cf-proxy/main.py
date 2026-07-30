# -*- coding: utf-8 -*-
"""
Created on Mon Jul 27 10:04:05 2026

@author: user
"""

import functions_framework
import requests
import json

USER_ID = "nagasaki-nougi-env"
PASSWORD = "TWnht4Xc"
AUTH_URL = "https://agrometeorology.jp/LBW_API/AuthenticationKey"
DATA_URL = "https://agrometeorology.jp/LBW_API/AMD"

def get_auth_key():
    payload = {"userid": USER_ID, "password": PASSWORD}
    response = requests.post(AUTH_URL, data=payload)
    if response.status_code == 200:
        return response.text.strip()
    return None

@functions_framework.http
def proxy_weather_data(request):
    # CORS（異なるドメインからのアクセスを許可する設定）の対応
    if request.method == 'OPTIONS':
        headers = {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET',
            'Access-Control-Allow-Headers': 'Content-Type',
            'Access-Control-Allow-Max-Age': '3600'
        }
        return ('', 240, headers)

    headers = {'Access-Control-Allow-Origin': '*'}

    # アプリ側から送られてきたパラメータ（緯度・経度・期間など）を取得
    params = request.args
    lat = params.get('latitude')
    lon = params.get('longitude')
    start_date = params.get('startdate')
    end_date = params.get('enddate')

    if not all([lat, lon, start_date, end_date]):
        return (json.dumps({"error": "必要なパラメータ(latitude, longitude, startdate, enddate)が不足しています"}), 400, headers)

    # ビジョンテックの認証キーを取得
    auth_key = get_auth_key()
    if not auth_key:
        return (json.dumps({"error": "ビジョンテックAPIの認証に失敗しました"}), 500, headers)

    # ビジョンテックAPIへリクエストを転送
    api_params = {
        "userid": USER_ID,
        "authKey": auth_key,
        "dataset": "TMP_mea",
        "type": "json",
        "startdate": start_date,
        "enddate": end_date,
        "latitude": str(lat),
        "longitude": str(lon)
    }

    try:
        api_response = requests.get(DATA_URL, params=api_params)
        if api_response.status_code == 200:
            return (api_response.text, 200, headers)
        else:
            return (json.dumps({"error": f"ビジョンテックAPIエラー: {api_response.status_code}"}), api_response.status_code, headers)
    except Exception as e:
        return (json.dumps({"error": f"通信エラー: {str(e)}"}), 500, headers)


import os

if __name__ == "__main__":
    from functions_framework._cli import _cli
    _cli(target="proxy_weather_data")

