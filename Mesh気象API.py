import requests
import csv
from datetime import datetime, timedelta


USER_ID = "nagasaki-nougi-env"
PASSWORD = "TWnht4Xc"
AUTH_URL = "https://agrometeorology.jp/LBW_API/AuthenticationKey"
DATA_URL = "https://agrometeorology.jp/LBW_API/AMD"

def get_auth_key(url, userid, password):
    payload = {"userid": userid, "password": password}
    response = requests.post(url, data=payload)
    if response.status_code == 200:
        return response.text.strip()
    return None

def convert_time_to_date(days_since_1900):
    base_date = datetime(1900, 1, 1)
    target_date = base_date + timedelta(days=int(days_since_1900))
    return target_date.strftime("%Y-%m-%d")

# 1年分の単年データを取得するサブ関数
def fetch_single_period_data(userid, auth_key, lat, lon, startdate, enddate):
    params = {
        "userid": userid,
        "authKey": auth_key,
        "dataset": "TMP_mea",
        "type": "json",
        "startdate": startdate,
        "enddate": enddate,
        "latitude": str(lat),
        "longitude": str(lon)
    }
    response = requests.get(DATA_URL, params=params)
    if response.status_code == 200:
        return response.json()
    else:
        print(f"取得エラー ({startdate}～{enddate}): {response.status_code}")
        print(response.text)
        return None

# 年またぎに対応したメイン関数
def download_weather_to_csv_multi_year(userid, auth_key, lat, lon, startdate_str, enddate_str, output_csv):
    start_dt = datetime.strptime(startdate_str, "%Y-%m-%d")
    end_dt = datetime.strptime(enddate_str, "%Y-%m-%d")
    
    # リクエストを年単位の期間に分割するリストを作成
    periods = []
    curr_start = start_dt
    
    while curr_start <= end_dt:
        # その年の12月31日、または指定の終了日のいずれか早い方を区切りとする
        curr_end = min(datetime(curr_start.year, 12, 31), end_dt)
        periods.append((curr_start.strftime("%Y-%m-%d"), curr_end.strftime("%Y-%m-%d")))
        curr_start = curr_end + timedelta(days=1)

    all_rows = []

    # 分割した期間ごとにAPIを呼び出し
    for s_date, e_date in periods:
        print(f"データ取得中... (期間: {s_date} ～ {e_date})")
        res_json = fetch_single_period_data(userid, auth_key, lat, lon, s_date, e_date)
        
        if res_json:
            try:
                leaves = res_json['nodes'][0]['leaves']
                tmp_data = next(item['data'] for item in leaves if item['name'] == 'TMP_mea')
                time_data = next(item['data'] for item in leaves if item['name'] == 'time')
                
                for t_val, temp_val in zip(time_data, tmp_data):
                    date_str = convert_time_to_date(t_val)
                    temperature = round(temp_val[0][0], 2)
                    all_rows.append([date_str, lat, lon, temperature])
            except Exception as e:
                print(f"データ解析失敗 ({s_date}～{e_date}): {e}")

    # CSV出力
    if all_rows:
        with open(output_csv, mode="w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow(["日付", "緯度", "経度", "日平均気温(℃)"])
            writer.writerows(all_rows)
        print(f"\nCSV出力完了！全 {len(all_rows)} 件のデータを保存しました: {output_csv}")

if __name__ == "__main__":
    auth_key = get_auth_key(AUTH_URL, USER_ID, PASSWORD)
    
    if auth_key:
        latitude = 32.83433481269516
        longitude =  130.02409751074833
        
        # 年を跨ぐ期間でもOKになりました！
        start_date = "2020-01-01"
        end_date = "2026-12-31"
        
        output_filename = f"日平均気温_{start_date}_{end_date}.csv"
        
        download_weather_to_csv_multi_year(
            USER_ID, auth_key, latitude, longitude, start_date, end_date, output_filename
        )