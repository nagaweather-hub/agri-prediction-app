# -*- coding: utf-8 -*-
"""
Created on Tue Jul 28 15:45:51 2026

@author: user
"""

# -*- coding: utf-8 -*-
# -*- coding: utf-8 -*-
import datetime
import folium  # ← ここを追加
from geopy.geocoders import Nominatim
import pandas as pd
import streamlit as st
from streamlit_folium import st_folium
from streamlit_js_eval import get_geolocation

# 独立させたモジュールをインポート
from modules.rice_predictor import RICE_VARIETY_PARAMS, predict_rice_growth
from modules.weather_api import fetch_real_weather_dict


# ---------------------------------------------------------
# ページ基本設定
# ---------------------------------------------------------
st.set_page_config(
    page_title="水稲生育予測システム",
    page_icon="🌾",
    layout="wide",
    initial_sidebar_state="expanded",
)

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
  if loc and "coords" in loc:
    st.session_state["lat"] = loc["coords"]["latitude"]
    st.session_state["lon"] = loc["coords"]["longitude"]
    st.session_state["location_label"] = (
        f"現在地 (緯度:{st.session_state['lat']:.4f},"
        f" 経度:{st.session_state['lon']:.4f})"
    )
  else:
    # 取得できない場合のデフォルト（長崎県諫早市）
    st.session_state["lat"] = 32.8343
    st.session_state["lon"] = 130.0241
    st.session_state["location_label"] = "長崎県諫早市"

# ---------------------------------------------------------
# タイトル・ヘッダー
# ---------------------------------------------------------
st.title("🌾 水稲生育予測システム")
st.markdown(
    "地図での位置選択や住所検索、リアルタイム気象データから生育ステージを予測します。"
)
st.divider()

# ---------------------------------------------------------
# サイドバー：基本設定（品種・移植日など）
# ---------------------------------------------------------
st.sidebar.header("⚙️ 予測条件設定")

variety = st.sidebar.selectbox("品種", list(RICE_VARIETY_PARAMS.keys()))

current_year = datetime.date.today().year
default_transplant = datetime.date(current_year, 4, 15)

transplant_date = st.sidebar.date_input(
    "移植日（田植え日）",
    value=default_transplant,
    min_value=datetime.date(2020, 1, 1),
    max_value=datetime.date(current_year + 1, 12, 31),
)

st.sidebar.divider()
run_prediction = st.sidebar.button(
    "🚀 生育予測を実行", type="primary", use_container_width=True
)

# ---------------------------------------------------------
# メイン画面：地点選択エリア（住所検索 ＆ 大きな地図）
# ---------------------------------------------------------
st.subheader("📍 予測地点の選択")

col_search, col_info = st.columns([2, 1])
with col_search:
  input_address = st.text_input(
      "町単位の住所・地名で検索", value=st.session_state["location_label"]
  )
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
        st.error(
            "❌ 見つかりませんでした。少し広めの地名でお試しください。"
        )

with col_info:
  st.markdown(f"**現在の設定地**")
  st.text(
      f"緯度: {st.session_state['lat']:.4f}\n経度:"
      f" {st.session_state['lon']:.4f}"
  )

# 地図の表示
st.markdown("👇 **地図上をクリックすると、その場所が選択されます**")
m = folium.Map(
    location=[st.session_state["lat"], st.session_state["lon"]], zoom_start=14
)
folium.Marker(
    [st.session_state["lat"], st.session_state["lon"]],
    popup=st.session_state["location_label"],
    icon=folium.Icon(color="green", icon="info-sign"),
).add_to(m)

map_data = st_folium(m, width="100%", height=400, key="main_map")

if map_data and map_data.get("last_clicked"):
  clicked_lat = map_data["last_clicked"]["lat"]
  clicked_lon = map_data["last_clicked"]["lng"]
  if (
      clicked_lat != st.session_state["lat"]
      or clicked_lon != st.session_state["lon"]
  ):
    st.session_state["lat"] = clicked_lat
    st.session_state["lon"] = clicked_lon
    st.session_state["location_label"] = (
        f"緯度:{clicked_lat:.4f}, 経度:{clicked_lon:.4f}"
    )
    st.rerun()

st.divider()

# ---------------------------------------------------------
# メイン表示エリア：予測結果
# ---------------------------------------------------------
if run_prediction:
  lat = st.session_state["lat"]
  lon = st.session_state["lon"]

  with st.spinner(
      "Google Cloudから気象データを取得してシミュレーション中..."
  ):
    end_date = transplant_date + datetime.timedelta(days=220)
    # 1. 共通モジュールで気象データを取得
    weather_data = fetch_real_weather_dict(lat, lon, transplant_date, end_date)

    if not weather_data:
      st.error(
          "❌ 気象データの取得に失敗しました。通信状況や座標を確認してください。"
      )
    else:
      # 2. 独立モジュールで水稲予測を実行
      result = predict_rice_growth(
          lat, lon, variety, transplant_date, weather_data
      )

      if "error" in result:
        st.error(result["error"])
      else:
        st.success("✅ 生育予測が完了しました！")
        st.subheader(
            f"📊 予測結果：{st.session_state['location_label']} （{variety}）"
        )

        heading_date = result.get("heading_date")
        maturity_date = result.get("seijuku_date")
        panicle_date = result.get("hogoe_date")
        drainage_date = result.get("nakaboshi_date")
        do_drainage = result.get("enable_drainage", False)

        if not heading_date:
          st.warning(
              "⚠️"
              " 期間内に出穂日に達しませんでした。データ取得期間またはパラメーターを確認してください。"
          )
        else:
          # メトリック表示
          cols = st.columns(4 if do_drainage else 3)
          idx = 0
          if do_drainage:
            with cols[idx]:
              st.metric(
                  label="💧 中干し開始日",
                  value=(
                      drainage_date.strftime("%Y/%m/%d")
                      if drainage_date
                      else "なし"
                  ),
              )
            idx += 1

          with cols[idx]:
            st.metric(
                label="🌾 穂肥日（目安）",
                value=(
                    panicle_date.strftime("%Y/%m/%d")
                    if panicle_date
                    else "計算不可"
                ),
            )
          idx += 1
          with cols[idx]:
            st.metric(
                label="🌸 出穂日（予測）",
                value=heading_date.strftime("%Y/%m/%d"),
            )
          idx += 1
          with cols[idx]:
            st.metric(
                label="🌾 成熟日・刈取適期",
                value=(
                    maturity_date.strftime("%Y/%m/%d")
                    if maturity_date
                    else "計算中"
                ),
            )

          st.divider()

          # スケジュール表
          st.subheader("📅 生育ステージ一覧")
          schedule_data = [{
              "ステージ": "移植（田植え）",
              "予測日": transplant_date.strftime("%Y/%m/%d"),
              "備考": "起算日",
          }]
          if do_drainage and drainage_date:
            schedule_data.append({
                "ステージ": "中干し開始期",
                "予測日": drainage_date.strftime("%Y/%m/%d"),
                "備考": "有効茎の調整・根腐れ防止の水抜き",
            })

          schedule_data.extend([
              {
                  "ステージ": "穂肥期",
                  "予測日": (
                      panicle_date.strftime("%Y/%m/%d")
                      if panicle_date
                      else "---"
                  ),
                  "備考": "幼穂形成期・追肥のタイミング",
              },
              {
                  "ステージ": "出穂期",
                  "予測日": heading_date.strftime("%Y/%m/%d"),
                  "備考": "水管理・病害虫防除の重要時期",
              },
              {
                  "ステージ": "成熟期",
                  "予測日": (
                      maturity_date.strftime("%Y/%m/%d")
                      if maturity_date
                      else "---"
                  ),
                  "備考": "収穫・刈り取り適期",
              },
          ])

          st.dataframe(
              pd.DataFrame(schedule_data),
              use_container_width=True,
              hide_index=True,
          )
else:
  st.info(
      "👆 上の地図で地点を選び、左サイドバーで品種と移植日を設定してから「生育予測を実行」ボタンを押してください。"
  )