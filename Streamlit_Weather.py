import streamlit as st
import requests
import pandas as pd
import numpy as np
import plotly.graph_objects as go 

# (API_KEY, BASE_URL, GEO_URL, WEATHER_TRANSLATION, contains_hangul 함수 등은 동일)
API_KEY = "f2907b0b1e074198de1ba6fb1928665f"
BASE_URL = "http://api.openweathermap.org/data/2.5/forecast"
GEO_URL = "http://api.openweathermap.org/geo/1.0/direct"

WEATHER_TRANSLATION = {
    "clear sky": "맑음", "few clouds": "구름 조금", "scattered clouds": "구름 많음",
    "broken clouds": "구름 낌", "overcast clouds": "흐림", "light rain": "약한 비",
    "moderate rain": "보통 비", "heavy intensity rain": "폭우", "very heavy rain": "강한 폭우",
    "extreme rain": "극심한 비", "freezing rain": "진눈깨비", "light snow": "약한 눈",
    "snow": "눈", "heavy snow": "함박눈", "sleet": "진눈깨비", "shower rain": "소나기",
    "thunderstorm": "천둥 번개", "mist": "안개", "smoke": "연기", "haze": "안개",
    "sand": "모래", "dust": "황사/먼지", "fog": "짙은 안개", "squalls": "돌풍",
    "tornado": "태풍",
}

def contains_hangul(text):
    for char in text:
        if 0xAC00 <= ord(char) <= 0xD7A3:
            return True
    return False

# --- Streamlit 앱 제목 ---
st.title("날씨 앱 제목: 간편 날씨 예보 🌤️")
st.markdown("---")

# --- 국가, 지역 등 지명 입력 부분 ---
city_name = st.text_input("국가, 지역 등 지명 입력", "서울", help="도시 이름(한국어/영어)을 입력해 주세요 (예: 서울, Incheon, London)")

# API 호출을 위한 버튼
if st.button("날씨 정보 가져오기"):
    if not API_KEY or API_KEY == "YOUR_OPENWEATHERMAP_API_KEY":
        st.error("OpenWeatherMap API Key를 설정해 주세요.")
    elif city_name:
        
        search_query = city_name
        if contains_hangul(city_name):
            search_query = f"{city_name},KR"

        # 1. 도시 이름으로 위도, 경도 가져오기
        try:
            geo_params = {'q': search_query, 'limit': 1, 'appid': API_KEY}
            geo_response = requests.get(GEO_URL, params=geo_params).json()
            
            if not geo_response:
                st.error(f"'{city_name}'에 대한 지리 정보를 찾을 수 없습니다. 도시 이름을 영어로 다시 시도해 보세요.")
                st.stop()

            lat = geo_response[0]['lat']
            lon = geo_response[0]['lon']
            
        except Exception as e:
            st.error(f"지리 정보 조회 중 오류 발생: {e}")
            st.stop()


        # 2. 날씨 예보 데이터 가져오기
        try:
            weather_params = {'lat': lat, 'lon': lon, 'appid': API_KEY, 'units': 'metric', 'lang': 'en'}
            response = requests.get(BASE_URL, params=weather_params)
            data = response.json()

            if data.get('cod') != '200':
                st.error(f"날씨 정보를 가져오는 데 실패했습니다: {data.get('message', '알 수 없는 오류')}")
                st.stop()

        except Exception as e:
            st.error(f"날씨 API 호출 중 오류 발생: {e}")
            st.stop()


        # --- 구글 지도 맵 (st.map 활용) ---
        st.subheader("구글 지도 맵: 입력 지역 표시 🗺️")
        map_data = pd.DataFrame({'lat': [lat], 'lon': [lon]})
        st.map(map_data, zoom=10)
        st.caption(f"**현재 지도 중심:** 위도 {lat:.2f}, 경도 {lon:.2f}")

        st.markdown("---")


        # --- 현재 날씨 및 일주일 날씨 ---
        display_city_name = geo_response[0].get('local_names', {}).get('ko', city_name)
        st.subheader(f"📍 {display_city_name} 날씨 정보")

        current_weather = data['list'][0]
        current_desc_en = current_weather['weather'][0]['description']
        current_desc_kr = WEATHER_TRANSLATION.get(current_desc_en, current_desc_en)
        current_temp = current_weather['main']['temp']
        current_humidity = current_weather['main']['humidity']
        
        st.metric(label="현재 온도", value=f"{current_temp:.1f} °C", delta=current_desc_kr)
        st.write(f"**습도:** {current_humidity}%")
        
        st.markdown(f"**외부 사이트 연결:** [OpenWeatherMap 예보 보기](https://openweathermap.org/city/{data['city']['id']})")

        st.markdown("---")

        # --- 일주일 날씨를 표로 분석해서 보여줌 (numpy 및 pandas 활용) ---
        st.subheader("일주일 날씨 요약 (5일 예보 기반)")
        
        forecast_list = data['list']

        # 데이터프레임으로 변환
        df = pd.DataFrame(
            [{
                '날짜/시간': pd.to_datetime(item['dt_txt']),
                '날짜': pd.to_datetime(item['dt_txt']).strftime('%Y-%m-%d'),
                '시간': pd.to_datetime(item['dt_txt']).strftime('%H:%M'),
                '예상온도 (°C)': item['main']['temp'],
                '체감온도 (°C)': item['main']['feels_like'],
                '습도 (%)': item['main']['humidity'],
                '날씨': WEATHER_TRANSLATION.get(item['weather'][0]['description'], item['weather'][0]['description'])
            } for item in forecast_list]
        )
        
        # 일별 최고/최저 온도 계산 및 요약 (NumPy 사용)
        daily_summary = df.groupby('날짜').agg(
            최고온도=('예상온도 (°C)', np.max),
            최저온도=('예상온도 (°C)', np.min),
            평균습도=('습도 (%)', np.mean),
            주요날씨=('날씨', lambda x: x.mode()[0])
        ).reset_index()

        daily_summary['평균습도'] = daily_summary['평균습도'].round(1).astype(str) + ' %'
        daily_summary['최고온도'] = daily_summary['최고온도'].round(1).astype(str) + ' °C'
        daily_summary['최저온도'] = daily_summary['최저온도'].round(1).astype(str) + ' °C'
        daily_summary.rename(columns={'날짜': '날짜'}, inplace=True)

        st.dataframe(daily_summary, use_container_width=True)
        
        st.markdown("---")

        ## 시간대별 상세 예보 그래프 (Plotly 사용 - 일별 눈금, 수평)
        st.subheader("시간대별 상세 예보 그래프 (일별 눈금, 수평)")

        fig = go.Figure()

        fig.add_trace(go.Scatter(x=df['날짜/시간'], y=df['예상온도 (°C)'], mode='lines', name='예상온도 (°C)'))
        fig.add_trace(go.Scatter(x=df['날짜/시간'], y=df['체감온도 (°C)'], mode='lines', name='체감온도 (°C)'))

        # --- [오류 해결 부분] X축 레이아웃: tickformat을 간단한 '%m-%d'로 변경 ---
        fig.update_layout(
            xaxis=dict(
                # 월-일만 표시하여 수평으로도 텍스트가 겹치지 않도록 가장 깔끔한 형식 사용
                tickformat="%m-%d",      
                dtick="d1",              # 눈금 간격을 1일(day) 단위로 고정
                tickangle=0,             # 텍스트 각도를 0도로 설정 (수평)
            ),
            yaxis_title="온도 (°C)",
            hovermode="x unified",
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1
            )
        )

        st.plotly_chart(fig, use_container_width=True)

    else:
        st.warning("도시 이름을 입력해 주세요.")