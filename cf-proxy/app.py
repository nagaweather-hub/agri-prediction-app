import streamlit as st
import datetime
import pandas as pd
import requests
from geopy.geocoders import Nominatim
from streamlit_folium import st_folium
import folium
from streamlit_js_eval import get_geolocation

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

# 品種のパラメータ
VARIETY_PARAMS = {
    "コシヒカリ": {"GDD_limit": 900.0, "base_temp": 10.0, "enable_drainage": False},
    "つや姫":     {"GDD_limit": 980.0, "base_temp": 10.0, "enable_drainage": False},
    "ヒノヒカリ": {"GDD_limit": 1000.0, "base_temp": 10.0, "enable_drainage": False},
    "にこまる":   {"GDD_limit": 1100.0, "base_temp": 10.0, "enable_drainage": True},
    "なつほのか": {"GDD_limit": 1050.0, "base_temp": 10.0, "enable_drainage": True}
}

# ---------------------------------------------------------
# 気象データ取得関数（デバッグ表示追加版）
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
            st.error(f"APIエラー: ステータスコード {response.status_code}")
            return None
            
        raw_data = response.json()
        
        # 🔍 【デバッグ用】プロキシから返ってきた生の構造を画面に表示
        st.write("▼ プロキシから返ってきた生データの中身:", raw_data)
        
        nodes = raw_data.get("nodes", [])
        if not nodes:
            st.warning("nodesが空です")
            return None
            
        leaves = nodes[0].get("leaves", [])
        
        # 🔍 【デバッグ用】leavesに含まれている 'name' の一覧を表示
        leaf_names = [leaf.get("name") for leaf in leaves]
        st.write("▼ 取得できたleafのname一覧:", leaf_names)
        
        tmp_data = []
        time_data = []
        for leaf in leaves:
            # 暫定的に TMP_mea または他のキーに対応できるよう広く受け取る
            if leaf.get("name") in ["TMP_mea", "TMP_fcst", "TMP_avn", "TMP"]:
                tmp_data = leaf.get("data", [])
            elif leaf.get("name") == "time":
                time_data = leaf.get("data", [])
                
        if not tmp_data or not time_data:
            st.warning("気温データまたは時間データが見つかりませんでした。")
            return None
            
        formatted_weather = {}
        base_date = datetime.date(1900, 1, 1)
        
        for t_val, tmp_val in zip(time_data, tmp_data):
            date_key = base_date + datetime.timedelta(days=int(t_val))
            # 多重リスト構造の安全な取得
            try:
                actual_temp = tmp_val[0][0]
            except (IndexError, TypeError):
                try:
                    actual_temp = tmp_val[0]
                except Exception:
                    actual_temp = tmp_val
            formatted_weather[date_key] = actual_temp
            
        return formatted_weather
    except Exception as e:
        st.error(f"例外発生: {e}")
        return None

# ---------------------------------------------------------
# 住所から緯度経度を検索する関数
# ---------------------------------------------------------
def get_lat_lon_from_address(address):
    try:
        geolocator = Nominatim(user_agent="rice_growth_app")
        location = geolocator.geocode(address)
        if location:
            return location.latitude, location.longitude
    except Exception as e:
        pass
    return None, None

# ---------------------------------------------------------
# セッション状態の初期化 ＆ 現在地（GPS）の自動取得
# ---------------------------------------------------------
if "lat" not in st.session_state or "lon" not in st.session_state:
    loc = get_geolocation()
    if loc and 'coords' in loc:
        st.session_state["lat"] = loc['coords']['latitude']
        st.session_state["lon"] = loc['coords']['longitude']
        st.session_state["location_label"] = f"現在地 (緯度:{st.session_state['lat']:.4f}, 経度:{st.session_state['lon']:.4f})"
    else:
        st.session_state["lat"] = 32.8343
        st.session_state["lon"] = 130.0241
        st.session_state["location_label"] = "長崎県諫早市"

# ---------------------------------------------------------
# タイトル・ヘッダー
# ---------------------------------------------------------
st.title("🌾 水稲生育予測システム")
st.markdown("地図での位置選択や住所検索、リアルタイム気象データから生育ステージを予測します。")
st.divider()

# ---------------------------------------------------------
# サイドバー：基本設定（品種・移植日など）
# ---------------------------------------------------------
st.sidebar.header("⚙️ 予測条件設定")

variety = st.sidebar.selectbox("品種", list(VARIETY_PARAMS.keys()))

current_year = datetime.date.today().year
default_transplant = datetime.date(current_year, 4, 15)

transplant_date = st.sidebar.date_input(
    "移植日（田植え日）",
    value=default_transplant,
    min_value=datetime.date(2020, 1, 1),
    max_value=datetime.date(current_year + 1, 12, 31)
)

st.sidebar.divider()
run_prediction = st.sidebar.button("🚀 生育予測を実行", type="primary", use_container_width=True)

# ---------------------------------------------------------
# メイン画面：地点選択エリア（住所検索 ＆ 大きな地図）
# ---------------------------------------------------------
st.subheader("📍 予測地点の選択")

col_search, col_info = st.columns([2, 1])
with col_search:
    input_address = st.text_input("町単位の住所・地名で検索", value=st.session_state["location_label"])
    if st.button("🔍 住所から位置を反映"):
        with st.spinner("住所を検索中..."):
            lat_res, lon_res = get_lat_lon_from_address(input_address)
            if lat_res and lon_res:
                st.success("位置を更新しました！")
                st.session_state["lat"] = lat_res
                st.session_state["lon"] = lon_res
                st.session_state["location_label"] = input_address
                st.rerun()
            else:
                st.error("❌ 見つかりませんでした。少し広めの地名でお試しください。")

with col_info:
    st.markdown(f"**現在の設定地**")
    st.text(f"緯度: {st.session_state['lat']:.4f}\n経度: {st.session_state['lon']:.4f}")

st.markdown("👇 **地図上をクリック（またはタップ）すると、その場所が選択されます**")
m = folium.Map(location=[st.session_state["lat"], st.session_state["lon"]], zoom_start=14)
folium.Marker(
    [st.session_state["lat"], st.session_state["lon"]],
    popup=st.session_state["location_label"],
    icon=folium.Icon(color="green", icon="info-sign")
).add_to(m)

map_data = st_folium(m, width="100%", height=400, key="main_map")

if map_data and map_data.get("last_clicked"):
    clicked_lat = map_data["last_clicked"]["lat"]
    clicked_lon = map_data["last_clicked"]["lng"]
    if clicked_lat != st.session_state["lat"] or clicked_lon != st.session_state["lon"]:
        st.session_state["lat"] = clicked_lat
        st.session_state["lon"] = clicked_lon
        st.session_state["location_label"] = f"緯度:{clicked_lat:.4f}, 経度:{clicked_lon:.4f}"
        st.rerun()

st.divider()

# ---------------------------------------------------------
# メイン表示エリア：予測結果
# ---------------------------------------------------------
if run_prediction:
    lat = st.session_state["lat"]
    lon = st.session_state["lon"]
    
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
                st.subheader(f"📊 予測結果：{st.session_state['location_label']} （{variety}）")
                
                drainage_date = None
                do_drainage = p.get("enable_drainage", False)
                
                if do_drainage:
                    drainage_date = heading_date - datetime.timedelta(days=35)
                    if drainage_date < transplant_date:
                        drainage_date = transplant_date + datetime.timedelta(days=25)

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
    st.info("👆 上の地図で地点を選び、左サイドバーで品種と移植日を設定してから「生育予測を実行」ボタンを押してください。")