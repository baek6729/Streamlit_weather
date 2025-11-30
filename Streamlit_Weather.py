# --- 시간별 예보 (HTML 제거, Streamlit 기본 위젯만 사용, 중앙 정렬) ---
st.subheader("시간별 예보")

tlist = w["list"][:8]

# gap="small" → 컬럼 사이 여백 줄여서 더 UI가 촘촘하고 정돈되어 보이도록
cols = st.columns(len(tlist), gap="small")

for i, item in enumerate(tlist):
    with cols[i]:
        # 각 컬럼을 하나의 컨테이너로 묶어 세로정렬을 균일하게 만듦
        with st.container():
            tt = pd.to_datetime(item["dt_txt"]).strftime("%H시")
            ti = item["main"]["temp"]
            p = item["pop"] * 100
            ic = fix_icon(item["weather"][0]["icon"])

            # 1) 시간
            st.caption(f"{tt}")

            # 2) 아이콘 (가운데 정렬 느낌을 위해 width만 사용)
            st.image(
                f"http://openweathermap.org/img/wn/{ic}.png",
                width=40
            )

            # 3) 온도
            st.markdown(f"**{int(ti)}°**")

            # 4) 강수 확률
            st.caption(f"💧 {int(p)}%")
