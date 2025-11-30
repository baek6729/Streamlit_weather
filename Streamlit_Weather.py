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

# 요일 치환 딕셔너리
weekday_map = {
    "Mon": "월", "Tue": "화", "Wed": "수", "Thu": "목", 
    "Fri": "금", "Sat": "토", "Sun": "일"
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
        msg.append(f"평균 일교차가 {d:.1f}°C로 큽니다. 아침/저녁 기온 변화에 주의하세요.")

    rain_days = (df["강수"] >= 50).sum()
    if rain_days >= len(df) / 2:
        msg.append("비 소식이 많은 주간입니다. 우산을 챙기세요.")

    if air and "list" in air:
        aqi = air["list"][0]["main"]["aqi"]
        if aqi >= 3:
            txt, _ = AQI_TEXT.get(aqi, ("알 수 없음", ""))
            msg.append(f"대기 질이 '{txt}' 수준입니다. 마스크 착용을 추천합니다.")

    return "\n\n".join(msg)

# --- Streamlit 앱 시작 ---
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

# 1. 주간 데이터 사전 계산
df = pd.DataFrame([{
    "dt": pd.to_datetime(x["dt_txt"]),
    "temp": x["main"]["temp"],
    "feel": x["main"]["feels_like"],
    "최저_raw": x["main"]["temp_min"],
    "최고_raw": x["main"]["temp_max"],
    "icon": x["weather"][0]["icon"],
    "강수": x["pop"] * 100
} for x in w["list"]])

daily = df.groupby(df["dt"].dt.date).agg(
    날짜=("dt", "first"),
    최고=("최고_raw", "max"),
    최저=("최저_raw", "min"),
    대표=("icon", lambda x: x.mode()[0]),
    강수=("강수", "mean")
).reset_index(drop=True)

# 현재 날씨 데이터 추출
now = w["list"][0]
t = now["main"]["temp"]
fl = now["main"]["feels_like"]
desc = W_DESC.get(now["weather"][0]["description"], "")
icon = fix_icon(now["weather"][0]["icon"])

# 오늘의 최고/최저 온도 추출
today_max = daily.loc[0, "최고"] if not daily.empty else None
today_min = daily.loc[0, "최저"] if not daily.empty else None

# 현재 날짜 및 시간 포맷팅
current_dt = pd.to_datetime(now["dt_txt"])
day_name_en = current_dt.strftime("%a")
day_name = weekday_map.get(day_name_en, day_name_en) 
current_date_time = current_dt.strftime(f"%m/%d({day_name}), %H시")


# --- 현재 날씨 표시 ---
col1, col2 = st.columns([1,2])
with col1:
    st.image(f"http://openweathermap.org/img/wn/{icon}@2x.png", width=100)
with col2:
    # 1. 현재 온도
    st.markdown(f"### **{int(t)}°**")
    
    # 2. 날씨 설명
    st.write(f"**{desc}**")
    
    # 3. 최대/최저 온도
    if today_max is not None:
        col3, col4, col5 = st.columns([0.4, 0.4, 1.2])
        with col3:
            st.markdown(f"**$\u2191$ {int(today_max)}°**") # ↑ 
        with col4:
            st.markdown(f"**$\u2193$ {int(today_min)}°**") # ↓ 
    
    # 4. 체감온도 (st.caption 대신 st.write로 변경하고 볼드 추가)
    st.write(f"**체감 {int(fl)}°**")
    
    # 5. 날짜요일, 시간 (st.caption 대신 st.write로 변경하고 볼드 추가)
    st.write(f"**{current_date_time}**")


# --- 시간별 예보 ---
st.subheader("시간별 예보")
tlist = w["list"][:8]
cols = st.columns(len(tlist))

for i, item in enumerate(tlist):
    with cols[i]:
        tt = pd.to_datetime(item["dt_txt"]).strftime("%H시")
        ti = item["main"]["temp"]
        p = item["pop"] * 100
        ic = fix_icon(item["weather"]씨")
fig = go.Figure()
fig.add_trace(go.Scatter(x=df["dt"], y=df["temp"], mode="lines+markers", name="온도"))
fig.add_trace(go.Scatter(x=df["dt"], y=df["feel"], mode="lines+markers", name="체감온도"))

# Plotly 레이아웃 설정 (제목, X축 수평 표시, 간격 조정 적용)
fig.update_layout(
    title={
        'text': "온도 변화", 
        'x': 0.05, 
        'xanchor': 'left',
        'y': 0.95, 
        'yanchor': 'top',
        'font': {'size': 24}
    },
    xaxis={
        'type': 'date', 
        'tickmode': 'array',
        'tickvals': daily_tick_points, 
        'ticktext': daily_labels_kr,  
        'tickangle': 0,               
        'showgrid': True,
        'zeroline': False,
        'rangeselector': None,        
        'rangeslider': {'visible': False}
    },
    margin=dict(t=30)
)
st.plotly_chart(fig, use_container_width=True)

# 주간 조언
st.subheader("주간 조언")
st.info(weekly_summary(daily, air))

# 다른 지역 조회
st.subheader("다른 지역 조회")
new_city = st.text_input("지역 입력", city)
if st.button("조회 다시"):
    load_weather(new_city)

# 지도
st.subheader("위치 지도")
st.map(pd.DataFrame({"lat": [lat], "lon": [lon]}))

