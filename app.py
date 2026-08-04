# -*- coding: utf-8 -*-
"""
総合農業予測システム (app.py)
水稲, 麦, タマネギべと病, バレイショ, びわ, ナシマルカイガラムシ, レタス の予測を統合
（縦型スクロールで直感的に操作できるシンプルバージョン - 現在地取得ボタン・CSVダウンロード機能付き）
"""

import datetime
import pandas as pd
import streamlit as st
import folium
from streamlit_folium import st_folium
from streamlit_js_eval import get_geolocation
from geopy.geocoders import Nominatim

# 各種予測モジュールのインポート
from modules.weather_api import fetch_real_weather_dict
from modules.rice_predictor import predict_rice_growth, RICE_VARIETY_PARAMS
from modules.wheat_predictor import predict_wheat_growth, WHEAT_VARIETY_PARAMS
from modules.onion_downy_mildew_predictor import predict_onion_downy_mildew
from modules.potato_predictor import predict_potato_growth, POTATO_VARIETY_PARAMS
from modules.loquat_predictor import predict_loquat_growth, LOQUAT_VARIETY_OFFSETS
from modules.scale_insect_predictor import predict_scale_insect_peak
from modules.lettuce_predictor import calculate_lettuce_harvest

# ---------------------------------------------------------
# ページ基本設定
# ---------------------------------------------------------
st.set_page_config(
    page_title="総合農業予測システム",
    page_icon="🌱",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# ---------------------------------------------------------
# 住所から緯度経度を検索する関数
# ---------------------------------------------------------
def get_lat_lon_from_address(address):
    try:
        geolocator = Nominatim(user_agent="agri_growth_app")
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
    if loc and "coords" in loc:
        st.session_state["lat"] = loc["coords"]["latitude"]
        st.session_state["lon"] = loc["coords"]["longitude"]
        st.session_state["location_label"] = f"現在地 (緯度:{st.session_state['lat']:.4f}, 経度:{st.session_state['lon']:.4f})"
    else:
        st.session_state["lat"] = 32.8343
        st.session_state["lon"] = 130.0241
        st.session_state["location_label"] = "長崎県諫早市"

# ---------------------------------------------------------
# メインタイトル
# ---------------------------------------------------------
st.title("🌾 総合農業生育・病害虫予測システム")
st.markdown("上から順番に条件を確認・設定し、予測を実行してください。")
st.divider()

# ---------------------------------------------------------
# 1. 品目カテゴリの選択
# ---------------------------------------------------------
st.subheader("🌱 1. 品目カテゴリの選択")

current_year = datetime.date.today().year

crop_category = st.selectbox(
    "予測したい品目・病害虫を選んでください",
    [
        "水稲",
        "麦",
        "タマネギべと病",
        "バレイショ（春作マルチ）",
        "びわ（収穫予測）",
        "ナシマルカイガラムシ（露地ビワ）",
        "レタス（収穫予測）",
    ],
)

st.markdown("---")

# ---------------------------------------------------------
# 2. 品目ごとの詳細条件設定（完全縦型）
# ---------------------------------------------------------
st.subheader("⚙️ 2. 詳細条件の設定")

inputs = {}
if crop_category == "水稲":
    inputs["variety"] = st.selectbox("品種", list(RICE_VARIETY_PARAMS.keys()))
    inputs["start_date"] = st.date_input("移植日（田植え日）", value=datetime.date(current_year, 4, 15))

elif crop_category == "麦":
    inputs["variety"] = st.selectbox("品種", list(WHEAT_VARIETY_PARAMS.keys()))
    inputs["start_date"] = st.date_input("調査日", value=datetime.date(current_year, 2, 1))
    inputs["young_spike_length"] = st.number_input("主稈幼穂長 (cm)", min_value=0.1, value=1.0, step=0.1)

elif crop_category == "タマネギべと病":
    inputs["start_date"] = st.date_input("定植日", value=datetime.date(current_year, 12, 5))

elif crop_category == "バレイショ（春作マルチ）":
    inputs["variety"] = st.selectbox("品種", list(POTATO_VARIETY_PARAMS.keys()))
    inputs["start_date"] = st.date_input("出芽日", value=datetime.date(current_year, 2, 25))

elif crop_category == "びわ（収穫予測）":
    inputs["variety"] = st.selectbox("品種", list(LOQUAT_VARIETY_OFFSETS.keys()))
    inputs["start_date"] = st.date_input("開花終期（起算日）", value=datetime.date(current_year, 12, 10))

elif crop_category == "ナシマルカイガラムシ（露地ビワ）":
    inputs["target_year"] = st.selectbox("予測年", [current_year - 1, current_year, current_year + 1], index=1)

elif crop_category == "レタス（収穫予測）":
    inputs["planting_date"] = st.date_input("定植日", value=datetime.date(current_year, 10, 15))
    inputs["model_type"] = st.selectbox("収穫モデル", ["11・12月モデル", "1月モデル", "2月モデル"])
    inputs["use_covering"] = st.checkbox("被覆を行う", value=True)
    if inputs["use_covering"]:
        inputs["covering_date"] = st.date_input("被覆日", value=datetime.date(current_year, 12, 1))
    else:
        inputs["covering_date"] = None
    inputs["target_diameter"] = st.number_input("目標玉径 (cm)", min_value=5.0, max_value=25.0, value=15.0, step=0.5)

st.markdown("---")

# ---------------------------------------------------------
# 3. 予測地点の設定（現在地ボタン ＆ 住所検索 ＆ 地図）
# ---------------------------------------------------------
st.subheader("📍 3. 予測地点の設定")

# 2カラムで「現在地を取得」ボタンと「住所検索」を配置
col_gps, col_addr_btn = st.columns([1, 1])

with col_gps:
    if st.button("📍 現在地を取得して反映", use_container_width=True):
        loc = get_geolocation()
        if loc and "coords" in loc:
            st.session_state["lat"] = loc["coords"]["latitude"]
            st.session_state["lon"] = loc["coords"]["longitude"]
            st.session_state["location_label"] = f"現在地 (緯度:{st.session_state['lat']:.4f}, 経度:{st.session_state['lon']:.4f})"
            st.success("現在地を取得しました！")
            st.rerun()
        else:
            st.error("❌ 現在地を取得できませんでした。ブラウザの位置情報権限をご確認ください。")

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

st.text(f"現在選択中の地点 ➔ 緯度: {st.session_state['lat']:.4f} / 経度: {st.session_state['lon']:.4f}")

# 地図の表示
st.markdown("👇 **地図上をクリックすると、その場所が選択されます**")
m = folium.Map(location=[st.session_state["lat"], st.session_state["lon"]], zoom_start=14)
folium.Marker(
    [st.session_state["lat"], st.session_state["lon"]],
    popup=st.session_state["location_label"],
    icon=folium.Icon(color="green", icon="info-sign")
).add_to(m)

map_data = st_folium(m, width="100%", height=350, key="main_map")

if map_data and map_data.get("last_clicked"):
    clicked_lat = map_data["last_clicked"]["lat"]
    clicked_lon = map_data["last_clicked"]["lng"]
    if clicked_lat != st.session_state["lat"] or clicked_lon != st.session_state["lon"]:
        st.session_state["lat"] = clicked_lat
        st.session_state["lon"] = clicked_lon
        st.session_state["location_label"] = f"緯度:{clicked_lat:.4f}, 経度:{clicked_lon:.4f}"
        st.rerun()

st.markdown("---")

# ---------------------------------------------------------
# 4. 実行ボタン
# ---------------------------------------------------------
run_prediction = st.button("🚀 生育・発生予測を実行", type="primary", use_container_width=True)

st.markdown("---")

# ---------------------------------------------------------
# 5. 予測結果の表示エリア（実行後に縦に表示）
# ---------------------------------------------------------
if run_prediction:
    lat = st.session_state["lat"]
    lon = st.session_state["lon"]

    with st.spinner("気象データを取得してシミュレーションしています..."):
        if crop_category == "水稲":
            start_dt = inputs["start_date"]
            end_dt = start_dt + datetime.timedelta(days=220)
        elif crop_category == "麦":
            start_dt = inputs["start_date"]
            end_dt = start_dt + datetime.timedelta(days=150)
        elif crop_category == "タマネギべと病":
            start_dt = inputs["start_date"]
            end_dt = start_dt + datetime.timedelta(days=250)
        elif crop_category == "バレイショ（春作マルチ）":
            start_dt = inputs["start_date"]
            end_dt = start_dt + datetime.timedelta(days=180)
        elif crop_category == "びわ（収穫予測）":
            start_dt = inputs["start_date"]
            end_dt = start_dt + datetime.timedelta(days=180)
        elif crop_category == "ナシマルカイガラムシ（露地ビワ）":
            target_y = inputs["target_year"]
            start_dt = datetime.date(target_y, 3, 1)
            end_dt = datetime.date(target_y, 8, 31)
        elif crop_category == "レタス（収穫予測）":
            start_dt = inputs["planting_date"]
            end_dt = start_dt + datetime.timedelta(days=240)

        # 気象データを取得
        weather_data = fetch_real_weather_dict("", "", lat, lon, start_dt, end_dt)

        if not weather_data:
            result = {"error": "❌ 気象データの取得に失敗しました。期間を確認してください。"}
        else:
            if crop_category == "水稲":
                result = predict_rice_growth(lat, lon, inputs["variety"], start_dt, weather_data)
            elif crop_category == "麦":
                result = predict_wheat_growth(lat, lon, inputs["variety"], start_dt, inputs["young_spike_length"], weather_data)
            elif crop_category == "タマネギべと病":
                result = predict_onion_downy_mildew(lat, lon, start_dt, weather_data)
            elif crop_category == "バレイショ（春作マルチ）":
                result = predict_potato_growth(lat, lon, inputs["variety"], start_dt, weather_data)
            elif crop_category == "びわ（収穫予測）":
                result = predict_loquat_growth(lat, lon, inputs["variety"], start_dt, weather_data)
            elif crop_category == "ナシマルカイガラムシ（露地ビワ）":
                result = predict_scale_insect_peak(lat, lon, target_y, weather_data)
            elif crop_category == "レタス（収穫予測）":
                result = calculate_lettuce_harvest(weather_data, inputs["planting_date"], inputs["covering_date"], inputs["target_diameter"], inputs["model_type"])

    # 結果の描画
    if "error" in result:
        st.error(result["error"])
    else:
        st.success("✅ 予測が完了しました！")
        st.subheader(f"📊 予測結果：{st.session_state['location_label']} （{crop_category}）")

        if crop_category == "水稲":
            heading_date = result.get("heading_date")
            maturity_date = result.get("seijuku_date")
            panicle_date = result.get("hogoe_date")
            drainage_date = result.get("nakaboshi_date")
            do_drainage = result.get("enable_drainage", False)

            if do_drainage:
                st.metric(label="💧 中干し開始日", value=drainage_date.strftime('%Y/%m/%d') if drainage_date else "なし")
            st.metric(label="🌾 穂肥日（目安）", value=panicle_date.strftime('%Y/%m/%d') if panicle_date else "計算不可")
            st.metric(label="🌸 出穂日（予測）", value=heading_date.strftime('%Y/%m/%d') if heading_date else "期間内未到達")
            st.metric(label="🌾 成熟日・刈取適期", value=maturity_date.strftime('%Y/%m/%d') if maturity_date else "期間内未到達")

        elif crop_category == "麦":
            heading_date = result.get("heading_date")
            maturity_date = result.get("seijuku_date")
            st.metric(label="穂揃期・出穂日（予測）", value=heading_date.strftime('%Y/%m/%d') if heading_date else "期間内未到達")
            st.metric(label="成熟期（予測）", value=maturity_date.strftime('%Y/%m/%d') if maturity_date else "期間内未到達")

        elif crop_category == "タマネギべと病":
            first_date = result.get("first_appearance_date")
            st.metric(label="🧅 一次伝染株初発期（積算400℃）", value=first_date.strftime('%Y/%m/%d') if first_date else "期間内未到達")
            st.text(f"最終積算気温: {result.get('accumulated_temp_at_end', 0):.1f} ℃ (目標: 400.0 ℃)")

        elif crop_category == "バレイショ（春作マルチ）":
            achieved_date = result.get("target_achieved_date")
            st.metric(label="🥔 目標収量（340kg/10a）到達予測日", value=achieved_date.strftime('%Y/%m/%d') if achieved_date else "期間内未到達")
            st.text(f"最終積算温度: {result.get('accumulated_temp_at_end', 0):.1f} ℃ (目標: {result.get('target_sum_temp', 0)} ℃)")

        elif crop_category == "びわ（収穫予測）":
            harvest_date = result.get("harvest_date")
            mogegi_date = result.get("mogegi_date")
            st.metric(label=f"🍊 {inputs['variety']} の収穫予測日", value=harvest_date.strftime('%Y/%m/%d') if harvest_date else "期間内未到達")
            st.text(f"基準（茂木）の収穫予測日: {mogegi_date.strftime('%Y/%m/%d') if mogegi_date else '期間内未到達'}")
            st.text(f"品種オフセット日数: {result.get('day_offset', 0)} 日")

        elif crop_category == "ナシマルカイガラムシ（露地ビワ）":
            peak_date = result.get("peak_date")
            st.metric(label="🐛 第一世代歩行幼虫 発生ピーク予測日", value=peak_date.strftime('%Y/%m/%d') if peak_date else "期間内未到達")
            st.text(f"有効積算温度: {result.get('accumulated_gdd', 0):.1f} 日度 (目標: {result.get('target_threshold', 429)} 日度)")

        elif crop_category == "レタス（収穫予測）":
            harvest_date = result.get("harvest_date")
            st.metric(label="🥬 レタス収穫予測日", value=harvest_date.strftime('%Y/%m/%d') if harvest_date else "期間内未到達")
            st.text(f"選択モデル: {result.get('model_type')}")
            st.text(f"目標玉径: {result.get('target_diameter')} cm")
            st.text(f"目標積算温度: {result.get('target_accumulated_temp', 0):.1f} ℃")
            st.text(f"到達時積算温度: {result.get('actual_accumulated_temp', 0):.1f} ℃")

        # ---------------------------------------------------------
        # 📥 気象データのCSVダウンロード機能
        # ---------------------------------------------------------
        st.markdown("---")
        st.subheader("📥 使用した気象データの確認・ダウンロード")
        st.markdown("今回の予測計算で使用した期間の気象データ（日付・日平均気温）をCSVファイルとしてダウンロードできます。お手元のデータと比較してみてください。")

        if weather_data and isinstance(weather_data, dict):
            # 辞書データをpandasのDataFrameに変換
            weather_df = pd.DataFrame(list(weather_data.items()), columns=["日付", "日平均気温(℃)"])
            weather_df["日付"] = pd.to_datetime(weather_df["日付"]).dt.date
            weather_df = weather_df.sort_values("日付").reset_index(drop=True)

            # データフレームのプレビュー表示
            st.dataframe(weather_df, use_container_width=True, height=200)

            # CSVに変換
            csv_data = weather_df.to_csv(index=False, encoding="utf-8-sig")

            # ダウンロードボタン
            st.download_button(
                label="📥 気象データCSVをダウンロード",
                data=csv_data,
                file_name=f"weather_data_{crop_category}_{datetime.date.today()}.csv",
                mime="text/csv",
                use_container_width=True
            )

else:
    st.info("👆 上の条件と地点を設定したら、「🚀 生育・発生予測を実行」ボタンを押してください。")