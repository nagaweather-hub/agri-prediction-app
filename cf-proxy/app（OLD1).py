import streamlit as st
import datetime
import pandas as pd
import requests

# ---------------------------------------------------------
# ページ基本設定
# ---------------------------------------------------------
st.set_page_config(
    page_title="水稲生育予測システム",
    page_icon="🌾",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 接続設定
PROXY_URL = "https://proxy-weather-data-120087242080.asia-northeast1.run.app"

# 品種のパラメータ（enable_drainage で中干し計算の有無を品種ごとに設定）
VARIETY_PARAMS = {
    "コシヒカリ": {"GDD_limit": 900.0, "base_temp": 10.0, "enable_drainage": False},
    "つや姫":     {"GDD_limit": 980.0, "base_temp": 10.0, "enable_drainage": False},
    "ヒノヒカリ": {"GDD_limit": 1000.0, "base_temp": 10.0, "enable_drainage": False},
    "にこまる":   {"GDD_limit": 1100.0, "base_temp": 10.0, "enable_drainage": True},
    "なつほのか": {"GDD_limit": 1050.0, "base_temp": 10.0, "enable_drainage": True}
}

# ---------------------------------------------------------
# 気象データ取得関数
# ---------------------------------------------------------
def fetch_real_weather_dict(lat, lon, start_date, end_date):
    params = {
        "latitude": str(lat),
        "longitude": str(lon),
        "startdate": start_date.strftime("%Y-%m-%d"),
        "enddate": end_date.strftime("%Y-%m-%d")
    }
    try:
        response = requests.get(PROXY_URL, params=params)
        if response.status_code != 200:
            return None
            
        raw_data = response.json()
        nodes = raw_data.get("nodes", [])
        if not nodes:
            return None
            
        leaves = nodes[0].get("leaves", [])
        tmp_data = []
        time_data = []
        for leaf in leaves:
            if leaf.get("name") == "TMP_mea":
                tmp_data = leaf.get("data", [])
            elif leaf.get("name") == "time":
                time_data = leaf.get("data", [])
                
        formatted_weather = {}
        base_date = datetime.date(1900, 1, 1)
        
        for t_val, tmp_val in zip(time_data, tmp_data):
            date_key = base_date + datetime.timedelta(days=int(t_val))
            actual_temp = tmp_val[0][0]
            formatted_weather[date_key] = actual_temp
            
        return formatted_weather
    except Exception as e:
        return None

# ---------------------------------------------------------
# タイトル・ヘッダー
# ---------------------------------------------------------
st.title("🌾 水稲生育予測システム")
st.markdown("リアルタイムに気象データを取得し、積算温度とDVIモデルから生育ステージを予測します。")
st.divider()

# ---------------------------------------------------------
# サイドバー：入力フォーム
# ---------------------------------------------------------
st.sidebar.header("⚙️ 予測条件設定")

location_name = st.sidebar.text_input("対象地域・地点名", value="長崎県諫早市")
lat = st.sidebar.number_input("緯度", value=32.8343, format="%.4f")
lon = st.sidebar.number_input("経度", value=130.0241, format="%.4f")

variety = st.sidebar.selectbox("品種", list(VARIETY_PARAMS.keys()))

transplant_date = st.sidebar.date_input(
    "移植日（田植え日）",
    value=datetime.date(2025, 5, 2),
    min_value=datetime.date(2020, 1, 1),
    max_value=datetime.date(2026, 12, 31)
)

run_prediction = st.sidebar.button("🚀 生育予測を実行", type="primary", use_container_width=True)

# ---------------------------------------------------------
# メイン表示エリア
# ---------------------------------------------------------
if run_prediction:
    with st.spinner("Google Cloudから気象データを取得してシミュレーション中..."):
        end_date = transplant_date + datetime.timedelta(days=220)
        weather_data = fetch_real_weather_dict(lat, lon, transplant_date, end_date)
        
        if not weather_data:
            st.error("❌ 気象データの取得に失敗しました。通信状況や座標を確認してください。")
        else:
            p = VARIETY_PARAMS[variety]
            dvi = 0.0
            gdd_sum = 0.0
            
            panicle_date = None
            heading_date = None
            maturity_date = None
            
            current_date = transplant_date
            
            while current_date <= end_date:
                if current_date in weather_data:
                    temp = weather_data[current_date]
                    eff_temp = max(0.0, temp - p["base_temp"])
                    gdd_sum += eff_temp
                    dvi = gdd_sum / p["GDD_limit"]
                    
                    if panicle_date is None and dvi >= 0.7:
                        panicle_date = current_date
                        
                    if heading_date is None and dvi >= 1.0:
                        heading_date = current_date
                        
                    if heading_date is not None and maturity_date is None and (current_date - heading_date).days >= 35:
                        maturity_date = current_date
                        break
                        
                current_date += datetime.timedelta(days=1)
            
            if heading_date is None:
                st.warning("⚠️ 期間内に出穂日に達しませんでした。データ取得期間またはパラメーターを確認してください。")
            else:
                st.success("✅ 生育予測が完了しました！")
                st.subheader(f"📍 予測条件：{location_name} （{variety} / 移植日: {transplant_date.strftime('%Y/%m/%d')}）")
                
                # 品種ごとの設定（enable_drainage）に連動して中干し日を計算
                drainage_date = None
                do_drainage = p.get("enable_drainage", False)
                
                if do_drainage:
                    drainage_date = heading_date - datetime.timedelta(days=35)
                    if drainage_date < transplant_date:
                        drainage_date = transplant_date + datetime.timedelta(days=25)

                # 表示カラムの動的切り替え
                if do_drainage:
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric(label="💧 中干し開始日", value=drainage_date.strftime("%Y/%m/%d"), delta=f"移植後 {(drainage_date - transplant_date).days} 日目")
                    with col2:
                        st.metric(label="🌾 穂肥日（目安）", value=panicle_date.strftime("%Y/%m/%d") if panicle_date else "計算不可", delta=f"移植後 {(panicle_date - transplant_date).days} 日目" if panicle_date else None)
                    with col3:
                        st.metric(label="🌸 出穂日（予測）", value=heading_date.strftime("%Y/%m/%d"), delta=f"移植後 {(heading_date - transplant_date).days} 日目")
                    with col4:
                        st.metric(label="🌾 成熟日・刈取適期", value=maturity_date.strftime("%Y/%m/%d") if maturity_date else "計算中", delta=f"移植後 {(maturity_date - transplant_date).days} 日目" if maturity_date else None)
                else:
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric(label="🌾 穂肥日（目安）", value=panicle_date.strftime("%Y/%m/%d") if panicle_date else "計算不可", delta=f"移植後 {(panicle_date - transplant_date).days} 日目" if panicle_date else None)
                    with col2:
                        st.metric(label="🌸 出穂日（予測）", value=heading_date.strftime("%Y/%m/%d"), delta=f"移植後 {(heading_date - transplant_date).days} 日目")
                    with col3:
                        st.metric(label="🌾 成熟日・刈取適期", value=maturity_date.strftime("%Y/%m/%d") if maturity_date else "計算中", delta=f"移植後 {(maturity_date - transplant_date).days} 日目" if maturity_date else None)
                
                st.divider()
                
                # スケジュール表の動的切り替え
                st.subheader("📅 生育ステージ一覧")
                schedule_data = [
                    {"ステージ": "移植（田植え）", "予測日": transplant_date.strftime("%Y/%m/%d"), "備考": "起算日"}
                ]
                if do_drainage and drainage_date:
                    schedule_data.append({"ステージ": "中干し開始期", "予測日": drainage_date.strftime("%Y/%m/%d"), "備考": "有効茎の調整・根腐れ防止の水抜き"})
                
                schedule_data.extend([
                    {"ステージ": "穂肥期", "予測日": panicle_date.strftime("%Y/%m/%d") if panicle_date else "---", "備考": "幼穂形成期・追肥のタイミング"},
                    {"ステージ": "出穂期", "予測日": heading_date.strftime("%Y/%m/%d"), "備考": "水管理・病害虫防除の重要時期"},
                    {"ステージ": "成熟期", "予測日": maturity_date.strftime("%Y/%m/%d") if maturity_date else "---", "備考": "収穫・刈り取り適期"}
                ])
                
                st.dataframe(pd.DataFrame(schedule_data), use_container_width=True, hide_index=True)
else:
    st.info("👈 左側のサイドバーで条件を設定し、「生育予測を実行」ボタンを押してください。")