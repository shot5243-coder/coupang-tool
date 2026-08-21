# -*- coding: utf-8 -*-
"""
쿠팡 소싱 통합 리포트 - 웹앱 버전 (스마트폰 접속용)
- domeggook_client.py, search_trend_client.py, search_trend_by_age.py 와 같은 폴더에 둘 것
- 실행(로컬 테스트): streamlit run streamlit_app.py
- 배포: Streamlit Community Cloud에 올리면 스마트폰 브라우저로 URL 접속 가능

API 키는 화면에 직접 입력하거나, Streamlit Cloud의 "Secrets"에 미리 등록해두면
접속할 때마다 다시 입력할 필요가 없다 (아래 st.secrets 사용 부분 참고).
"""

import datetime
import streamlit as st

import domeggook_client as dome
import search_trend_client as trend
import search_trend_by_age as age_mod

st.set_page_config(page_title="쿠팡 소싱 리포트", page_icon="🛒", layout="centered")
st.title("쿠팡 소싱 통합 리포트")
st.caption("도매꾹 최저가 + 네이버 검색트렌드 + 연령대별 관심도를 한 번에 확인")

# ---------------------------------------------------------------------------
# API 키 입력 (Secrets에 등록해뒀으면 자동으로 채워짐)
# ---------------------------------------------------------------------------
with st.sidebar:
    st.header("API 키")

    def _secret_or_empty(key):
        try:
            return st.secrets[key]
        except Exception:
            return ""

    dome_key = st.text_input("도매꾹 API_KEY", value=_secret_or_empty("DOME_KEY"), type="password")
    naver_key_id = st.text_input("네이버 Client ID", value=_secret_or_empty("NAVER_KEY_ID"), type="password")
    naver_key = st.text_input("네이버 Client Secret", value=_secret_or_empty("NAVER_KEY"), type="password")

    st.divider()
    today = datetime.date.today()
    default_end = today - datetime.timedelta(days=1)
    default_start = default_end - datetime.timedelta(days=365)
    start_date = st.date_input("조회 시작일", value=default_start)
    end_date = st.date_input("조회 종료일", value=default_end)

# ---------------------------------------------------------------------------
# 검색 (form으로 감싸면 입력창에서 Enter 키만 눌러도 바로 실행됨)
# ---------------------------------------------------------------------------
with st.form("search_form"):
    keyword = st.text_input("🔍 검색할 키워드", placeholder="예: 캠핑랜턴")
    run = st.form_submit_button("검색 실행", type="primary", use_container_width=True)

if run:
    if not (dome_key and naver_key_id and naver_key):
        st.error("사이드바에서 API 키 3개를 먼저 입력해주세요.")
    elif not keyword.strip():
        st.error("키워드를 입력해주세요.")
    else:
        keyword = keyword.strip()
        start_str, end_str = str(start_date), str(end_date)

        # ---- 도매꾹 ----
        with st.spinner("도매꾹 검색 중..."):
            client = dome.DomeggookClient(api_key=dome_key)
            raw_items = client.search_all_pages(keyword, max_pages=2)
            items = dome.group_similar_and_sort(raw_items)[:20]

        # ---- 검색트렌드 (기회점수 계산에 먼저 필요해서 여기서 같이 조회) ----
        trend_summary = []
        try:
            trend_result = trend.search_trend(naver_key_id, naver_key, [keyword], start_str, end_str, "month")
            trend_summary = trend.summarize(trend_result)
        except Exception as e:
            st.error(f"검색트렌드 조회 오류: {e}")

        # ---- 경쟁강도 / 기회점수 ----
        st.subheader("경쟁강도 / 기회점수")
        st.caption("검색량 대신 검색트렌드 지수(0~100 상대값)를 사용한 참고용 지표입니다. "
                    "도매꾹은 리뷰수 데이터를 제공하지 않아 상품수만 반영했습니다.")
        if trend_summary and items is not None:
            search_index = trend_summary[0]["최신지수"]
            product_count = len(items)
            if isinstance(search_index, (int, float)) and search_index > 0:
                competition = round(product_count / search_index, 3)
                opportunity = round(search_index / (product_count + 1), 2)
                if opportunity >= 3:
                    grade, grade_color = "블루오션 후보", "[블루오션]"
                elif opportunity >= 1:
                    grade, grade_color = "관찰 필요", "[관찰필요]"
                else:
                    grade, grade_color = "레드오션", "[레드오션]"
                c1, c2, c3 = st.columns(3)
                c1.metric("경쟁강도", competition, help="상품수÷검색지수, 낮을수록 경쟁이 덜함")
                c2.metric("기회점수", opportunity, help="검색지수÷(상품수+1), 높을수록 선점 기회")
                c3.metric("등급", f"{grade_color} {grade}")
            else:
                st.info("검색지수가 0이라 경쟁강도/기회점수를 계산할 수 없습니다.")
        else:
            st.info("도매꾹 상품 또는 검색트렌드 데이터가 부족해 계산할 수 없습니다.")

        st.subheader(f"도매꾹 최저가 상품 ({len(items)}건)")
        if not items:
            st.info("검색된 상품이 없습니다.")
        for it in items:
            cost = it.price + it.deli_fee
            required_price = dome.calc_required_selling_price(cost)
            col1, col2 = st.columns([1, 3])
            with col1:
                if it.thumb:
                    st.image(it.thumb, width=90)
            with col2:
                st.markdown(f"**{it.title}**")
                st.write(f"원가 {it.price:,}원 + 배송비 {it.deli_fee:,}원 = **{cost:,}원**")
                if required_price:
                    st.write(f"목표마진(40%) 판매가: **{required_price:,}원**")
                st.markdown(f"[상품 보기]({it.url})")
            st.divider()

        # ---- 검색트렌드 그래프 ----
        st.subheader("검색트렌드")
        if trend_summary:
            t = trend_summary[0]
            c1, c2, c3 = st.columns(3)
            c1.metric("최신지수", t["최신지수"])
            c2.metric("평균지수", t["평균지수"])
            c3.metric("추세", t["추세"])
            groups = trend_result.get("results", [])
            if groups and groups[0].get("data"):
                chart_data = {d["period"]: d["ratio"] for d in groups[0]["data"]}
                st.line_chart(chart_data)

        # ---- 연령대별 관심도 ----
        st.subheader("연령대별 관심도")
        with st.spinner("연령대별 관심도 조회 중..."):
            try:
                age_summary = age_mod.age_trend(naver_key_id, naver_key, keyword, start_str, end_str)
                chart_data = {r["연령대"]: r["평균지수"] for r in age_summary
                              if isinstance(r["평균지수"], (int, float))}
                if chart_data:
                    st.bar_chart(chart_data)
                valid = [r for r in age_summary if isinstance(r["평균지수"], (int, float))]
                if valid:
                    st.write(f"※ 가장 관심도 높은 연령대: **{valid[0]['연령대']}**")
            except Exception as e:
                st.error(f"연령대별 관심도 조회 오류: {e}")

st.divider()
st.caption("API 키는 서버에 저장되지 않으며, 이 세션에서만 사용됩니다.")
