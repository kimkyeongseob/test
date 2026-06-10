import os
import requests
import streamlit as st
import pandas as pd
import plotly.express as px
from dotenv import load_dotenv

load_dotenv()

st.set_page_config(page_title="사업장별 비용 현황 대시보드", layout="wide")

@st.cache_data
def load_data():
    df = pd.read_csv("data/비용통합현황.csv")
    return df

df = load_data()

st.title("📊 사업장별 주요 비용 사용현황 대시보드")

# ── 사이드바 필터 ─────────────────────────────
st.sidebar.header("필터")

locations = sorted(df["사업장"].unique())
selected_locations = st.sidebar.multiselect("사업장 선택", locations, default=locations)

months = sorted(df["월"].unique())
selected_months = st.sidebar.select_slider(
    "기간 선택", options=months, value=(months[0], months[-1])
)

categories = sorted(df["비용항목"].unique())
selected_categories = st.sidebar.multiselect("비용항목 선택", categories, default=categories)

# ── 데이터 필터링 ─────────────────────────────
mask = (
    df["사업장"].isin(selected_locations)
    & df["비용항목"].isin(selected_categories)
    & (df["월"] >= selected_months[0])
    & (df["월"] <= selected_months[1])
)
fdf = df[mask]

if fdf.empty:
    st.warning("선택한 조건에 해당하는 데이터가 없습니다.")
    st.stop()

# ── KPI ─────────────────────────────
col1, col2, col3, col4 = st.columns(4)

total_cost = fdf["금액"].sum()
n_months = fdf["월"].nunique()
avg_monthly = total_cost / n_months if n_months else 0

# 전월 대비 증감률 (선택 기간 마지막 두 달 비교)
sorted_months = sorted(fdf["월"].unique())
if len(sorted_months) >= 2:
    last_total = fdf[fdf["월"] == sorted_months[-1]]["금액"].sum()
    prev_total = fdf[fdf["월"] == sorted_months[-2]]["금액"].sum()
    mom_change = (last_total - prev_total) / prev_total * 100 if prev_total else 0
else:
    mom_change = 0

top_location = fdf.groupby("사업장")["금액"].sum().idxmax()

col1.metric("총 비용", f"{total_cost:,.0f} 만원")
col2.metric("월 평균 비용", f"{avg_monthly:,.0f} 만원")
col3.metric("전월 대비 증감", f"{mom_change:+.1f}%")
col4.metric("최대 비용 사업장", top_location)

st.divider()

# ── 사업장별 월간 추이 ─────────────────────────────
st.subheader("📈 사업장별 월간 비용 추이")
trend_df = fdf.groupby(["월", "사업장"])["금액"].sum().reset_index()
fig_trend = px.line(
    trend_df, x="월", y="금액", color="사업장", markers=True,
    labels={"금액": "비용 (만원)"}
)
st.plotly_chart(fig_trend, use_container_width=True)

# ── 비용항목 구성 + 히트맵 ─────────────────────────────
col_left, col_right = st.columns(2)

with col_left:
    st.subheader("🥧 비용항목별 구성 비율")
    cat_df = fdf.groupby("비용항목")["금액"].sum().reset_index()
    fig_pie = px.pie(cat_df, names="비용항목", values="금액", hole=0.4)
    st.plotly_chart(fig_pie, use_container_width=True)

with col_right:
    st.subheader("🔥 사업장 × 비용항목 히트맵")
    heatmap_df = fdf.groupby(["사업장", "비용항목"])["금액"].sum().reset_index()
    pivot_heatmap = heatmap_df.pivot(index="사업장", columns="비용항목", values="금액")
    fig_heatmap = px.imshow(
        pivot_heatmap, text_auto=".0f", aspect="auto",
        color_continuous_scale="YlOrRd",
        labels=dict(color="금액(만원)")
    )
    st.plotly_chart(fig_heatmap, use_container_width=True)

# ── 사업장별 비교 (그룹 바) ─────────────────────────────
st.subheader("📊 사업장별 비용항목 비교")
selected_month_for_bar = st.selectbox("비교할 월 선택", sorted_months, index=len(sorted_months) - 1)
bar_df = fdf[fdf["월"] == selected_month_for_bar]
fig_bar = px.bar(
    bar_df, x="사업장", y="금액", color="비용항목", barmode="group",
    labels={"금액": "비용 (만원)"}
)
st.plotly_chart(fig_bar, use_container_width=True)

st.divider()

# ── 상세 테이블 ─────────────────────────────
st.subheader("📋 상세 데이터 (피벗 테이블)")
pivot_table = fdf.pivot_table(
    index="사업장", columns="월", values="금액", aggfunc="sum", fill_value=0
)
st.dataframe(pivot_table.style.format("{:,.0f}"), use_container_width=True)

csv = fdf.to_csv(index=False).encode("utf-8-sig")
st.download_button(
    label="필터링된 데이터 CSV 다운로드",
    data=csv,
    file_name="filtered_cost_data.csv",
    mime="text/csv",
)

st.divider()

# ── AI 데이터 Q&A ─────────────────────────────
st.subheader("🤖 AI에게 데이터 질문하기")

api_key = os.getenv("GEMINI_API_KEY") or st.secrets.get("GEMINI_API_KEY")

if not api_key:
    st.info("GEMINI_API_KEY가 설정되지 않았습니다. .env 파일에 키를 입력해주세요.")
else:
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    for role, message in st.session_state.chat_history:
        with st.chat_message(role):
            st.markdown(message)

    user_question = st.chat_input("현재 필터링된 데이터에 대해 질문해보세요")

    if user_question:
        st.session_state.chat_history.append(("user", user_question))
        with st.chat_message("user"):
            st.markdown(user_question)

        data_summary = fdf.to_csv(index=False)
        prompt = (
            "당신은 비용 데이터 분석을 도와주는 어시스턴트입니다. "
            "아래는 현재 대시보드에서 필터링된 비용 데이터(CSV)입니다. "
            "이 데이터를 바탕으로 사용자의 질문에 한국어로 답변하세요.\n\n"
            f"[데이터]\n{data_summary}\n\n"
            f"[질문]\n{user_question}"
        )

        with st.chat_message("assistant"):
            with st.spinner("답변 생성 중..."):
                try:
                    url = (
                        "https://generativelanguage.googleapis.com/v1beta/models/"
                        "gemini-flash-latest:generateContent"
                    )
                    res = requests.post(
                        url,
                        params={"key": api_key},
                        json={"contents": [{"parts": [{"text": prompt}]}]},
                        timeout=30,
                    )
                    res.raise_for_status()
                    answer = res.json()["candidates"][0]["content"]["parts"][0]["text"]
                except Exception as e:
                    answer = f"오류가 발생했습니다: {e}"
                st.markdown(answer)

        st.session_state.chat_history.append(("assistant", answer))
