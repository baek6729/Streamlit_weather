import streamlit as st
import requests
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import datetime

# --- 설정 (변경 없음) ---
API_KEY = "f2907b0b1e074198de1ba6fb1928665f"

BASE_URL = "http://api.openweathermap.org/data/2.5/forecast"
GEO_URL = "http://api.openweathermap.org/geo/1.0/direct"
AIR_URL = "http://api.openweathermap.org/data/2.5/air_pollution"

W_DESC = {
    "clear sky": "맑음", "few clouds": "조금 구름",
    "scattered clouds": "구름 많음", "broken clouds": "흐림",
    "overcast clouds": "흐림", "light rain": "약한 비",
    "moderate rain": "비", "heavy intensity rain": "강한 비",
    "light snow": "약한 눈", "snow": "눈",
    "mist": "안개", "fog": "짙은 안개", "thunderstorm": "천둥"
}

AQI_TEXT = {
    1: ("좋음", "🟢"), 2: ("보통", "🟡"), 3: ("나쁨", "🟠"),
    4: ("매우 나쁨", "🔴"), 5: ("최악", "⚫")
}

def has_kr(s):
    return any(0xAC00 <= ord(c) <= 0xD7A3 for c in s)


def fix_icon(code):
    if not code:
        return code
    if code.endswith("n"):
        code = code[:-1] + "d"
    if code == "04d":
        return "03d"
    return code


def init_state():
    ss = st.session_state
    ss.setdefault("searched", False)
    ss.setdefault("data", None)


def load_weather(city):
    ss = st.session_state
    q = f"{city},KR" if has_kr(city) else city

    geo = requests.get(GEO_URL, params={"q": q, "limit": 1, "appid": API_KEY}).json()
    if not geo:
        st.error("지역을 찾을 수 없습니다.")
        ss.searched = False
        return

    lat, lon = geo[0]["lat"], geo[0]["lon"]
    name_kr = geo[0].get("local_names", {}).get("ko", city)

    w = requests.get(BASE_URL, params={
        "lat": lat, "lon": lon, "appid": API_KEY,
        "units": "metric", "lang": "en"
    }).json()

    air = requests.get(AIR_URL, params={
        "lat": lat, "lon": lon, "appid": API_KEY
    }).json()

    ss.data = {"name": name_kr, "lat": lat, "lon": lon, "w": w, "air": air}
    ss.searched = True
    st.rerun()


def weekly_summary(df, air):
    avg_max = df["최고"].mean()
    msg = []

    if avg_max >= 27:
        msg.append("이번 주는 더운 편입니다. 시원한 복장을 추천합니다.")
    elif avg_max >= 16:
        msg.append("날씨가 활동하기 좋습니다.")
    elif avg_max >= 5:
        msg.append("날씨가 쌀쌀한 편입니다. 가벼운 외투를 챙기세요.")
    else:
        msg.append("추운 날씨가 예상됩니다. 따뜻하게 입으세요.")

    df["일교차"] = df["최고"] - df["최저"]
    d = df["일교차"].mean()
    if d >= 10:
        msg.append(f"평균 일교차가 {d:.1f}°C로 큽니다.")

    rain_days = (df["강수"] >= 50).sum()
    if rain_days >= len(df) / 2:
        msg.append("비 소식이 많은 주간입니다. 우산을 챙기세요.")

    if air and "list" in air:
        aqi = air["list"][0]["main"]["aqi"]
        if aqi >= 3:
            txt, _ = AQI_TEXT.get(aqi, ("알 수 없음", ""))
            msg.append(f"대기 질이 '{txt}' 수준입니다. 마스크 착용을 추천합니다.")

    return "\n\n".join(msg)


# --- Streamlit 앱 시작 (변경 없음) ---
init_state()

st.title("국내 날씨 / 미세먼지")

if not st.session_state.searched:
    city_in = st.text_input("지역 입력", "서울")
    if st.button("조회"):
        load_weather(city_in)
    st.stop()

data = st.session_state.data
w = data["w"]
air = data["air"]
city = data["name"]
lat, lon = data["lat"], data["lon"]

st.header(city)

now = w["list"][0]
t = now["main"]["temp"]
fl = now["main"]["feels_like"]
desc = W_DESC.get(now["weather"][0]["description"], "")
icon = fix_icon(now["weather"][0]["icon"])

tlist = w["list"][:8]
tmin = min(x["main"]["temp_min"] for x in tlist)
tmax = max(x["main"]["temp_max"] for x in tlist)

st.markdown(
    f"""
    <div style="display:flex;align-items:center;gap:10px;">
