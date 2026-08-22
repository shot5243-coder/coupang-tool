# -*- coding: utf-8 -*-
"""
쿠팡 소싱 통합 리포트 - 웹앱 버전 (카드형 대시보드)
- domeggook_client.py, search_trend_client.py, search_trend_by_age.py 와 같은 폴더에 둘 것
- 실행(로컬 테스트): streamlit run streamlit_app.py
- 배포: Streamlit Community Cloud에 올리면 스마트폰 브라우저로 URL 접속 가능

API 키는 화면에 직접 입력하거나, Streamlit Cloud의 "Secrets"에 미리 등록해두면
접속할 때마다 다시 입력할 필요가 없다.
"""

import datetime
import streamlit as st

import domeggook_client as dome
import search_trend_client as trend
import search_trend_by_age as age_mod

st.set_page_config(page_title="쿠팡 소싱 리포트", layout="centered")

# ---------------------------------------------------------------------------
# 약간의 카드 스타일 CSS (대시보드 느낌)
# ---------------------------------------------------------------------------
st.markdown("""
<style>
.grade-badge {
    display: inline-block; padding: 4px 14px; border-radius: 999px;
    font-weight: 700; font-size: 0.95rem; margin-top: 4px;
}
.grade-blue { background-color: #E3F2E5; color: #1E7B34; }
.grade-yellow { background-color: #FFF6DA; color: #9A6D00; }
.grade-red { background-color: #FCE4E4; color: #B3261E; }
.metric-box {
    background-color: #F7F8FA; border-radius: 12px; padding: 14px 18px;
    text-align: center; border: 1px solid #ECECEC;
}
.metric-label { font-size: 0.8rem; color: #666; margin-bottom: 4px; }
.metric-value { font-size: 1.4rem; font-weight: 700; }
.metric-grid {
    display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px;
}
@media (max-width: 480px) {
    .metric-grid { grid-template-columns: repeat(2, 1fr); }
}
.app-title {
    font-size: 1.7rem; font-weight: 800; white-space: nowrap;
    overflow-x: auto; margin-bottom: 0.2rem; text-align: center;
    color: #185FA5;
}
@media (max-width: 480px) {
    .app-title { font-size: 1.4rem; }
}
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="app-title">쿠팡 소싱 통합 리포트</div>', unsafe_allow_html=True)
st.caption("도매꾹 최저가 · 네이버 검색트렌드 · 연령대별 관심도 · 경쟁강도/기회점수를 한 화면에서 확인")

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


def metric_card(label: str, value: str):
    st.markdown(
        f'<div class="metric-box"><div class="metric-label">{label}</div>'
        f'<div class="metric-value">{value}</div></div>',
        unsafe_allow_html=True,
    )


def grade_badge(grade: str) -> str:
    cls = {"블루오션 후보": "grade-blue", "관찰 필요": "grade-yellow", "레드오션": "grade-red"}.get(grade, "grade-yellow")
    return f'<span class="grade-badge {cls}">{grade}</span>'


# ---------------------------------------------------------------------------
# 검색 (form으로 감싸면 입력창에서 Enter 키만 눌러도 바로 실행됨)
# ---------------------------------------------------------------------------
with st.form("search_form"):
    keyword = st.text_input("검색할 키워드", placeholder="예: 캠핑랜턴")
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
        trend_result = {}
        try:
            trend_result = trend.search_trend(naver_key_id, naver_key, [keyword], start_str, end_str, "month")
            trend_summary = trend.summarize(trend_result)
        except Exception as e:
            st.error(f"검색트렌드 조회 오류: {e}")

        # =====================================================================
        # 상단 대시보드 카드: 경쟁강도 / 기회점수 / 등급 (실시간 꿀통 키워드 카드 느낌)
        # =====================================================================
        st.markdown(f"### '{keyword}' 요약")

        product_count = len(items)
        search_index = trend_summary[0]["최신지수"] if trend_summary else None

        if isinstance(search_index, (int, float)) and search_index > 0:
            competition = round(product_count / search_index, 3)
            opportunity = round(search_index / (product_count + 1), 2)
            if opportunity >= 3:
                grade = "블루오션 후보"
            elif opportunity >= 1:
                grade = "관찰 필요"
            else:
                grade = "레드오션"

            metrics_html = f'''
<div class="metric-grid">
  <div class="metric-box"><div class="metric-label">도매꾹 상품수</div><div class="metric-value">{product_count}건</div></div>
  <div class="metric-box"><div class="metric-label">검색 최신지수</div><div class="metric-value">{search_index}</div></div>
  <div class="metric-box"><div class="metric-label">경쟁강도</div><div class="metric-value">{competition}</div></div>
  <div class="metric-box"><div class="metric-label">기회점수</div><div class="metric-value">{opportunity}</div></div>
</div>
'''
            st.markdown(metrics_html, unsafe_allow_html=True)

            st.markdown(f"**진입 등급:** {grade_badge(grade)}", unsafe_allow_html=True)
            st.caption("검색량 대신 검색트렌드 지수(0~100 상대값)를 사용한 참고용 지표입니다. "
                       "도매꾹은 리뷰수 데이터를 제공하지 않아 상품수만 반영했습니다.")
        else:
            st.info("검색지수가 부족해 경쟁강도/기회점수를 계산할 수 없습니다.")

        st.divider()

        # =====================================================================
        # 검색트렌드 그래프
        # =====================================================================
        st.markdown("### 검색트렌드")
        if trend_summary:
            t = trend_summary[0]
            c1, c2, c3 = st.columns(3)
            with c1:
                metric_card("최신지수", str(t["최신지수"]))
            with c2:
                metric_card("평균지수", str(t["평균지수"]))
            with c3:
                metric_card("추세", str(t["추세"]))
            groups = trend_result.get("results", [])
            if groups and groups[0].get("data"):
                chart_data = {d["period"]: d["ratio"] for d in groups[0]["data"]}
                st.line_chart(chart_data)

        st.divider()

        # =====================================================================
        # 연령대별 관심도
        # =====================================================================
        st.markdown("### 연령대별 관심도")
        with st.spinner("연령대별 관심도 조회 중..."):
            try:
                age_summary = age_mod.age_trend(naver_key_id, naver_key, keyword, start_str, end_str)
                chart_data = {r["연령대"]: r["평균지수"] for r in age_summary
                              if isinstance(r["평균지수"], (int, float))}
                if chart_data:
                    st.bar_chart(chart_data)
                valid = [r for r in age_summary if isinstance(r["평균지수"], (int, float))]
                if valid:
                    st.markdown(f"※ 가장 관심도 높은 연령대: **{valid[0]['연령대']}**")
            except Exception as e:
                st.error(f"연령대별 관심도 조회 오류: {e}")

        st.divider()

        # =====================================================================
        # 도매꾹 최저가 상품 카드 목록 (마진 계산 레이아웃)
        # =====================================================================
        st.markdown(f"### 도매꾹 최저가 상품 ({product_count}건)")
        st.caption("완전히 같은 상품끼리는 묶어서 그 안에서 저가순으로, 서로 다른 상품끼리는 등록순을 유지합니다. "
                   "그래서 전체를 봤을 때는 가격이 오름차순으로 딱 떨어지지 않을 수 있습니다.")
        if not items:
            st.info("검색된 상품이 없습니다.")
        for it in items:
            cost = it.price + it.deli_fee
            required_price = dome.calc_required_selling_price(cost)
            with st.container(border=True):
                col1, col2 = st.columns([1, 3])
                with col1:
                    if it.thumb:
                        st.image(it.thumb, use_container_width=True)
                with col2:
                    st.markdown(f"**{it.title}**")
                    cc1, cc2 = st.columns(2)
                    with cc1:
                        st.caption("원가+배송비")
                        st.markdown(f"**{cost:,}원**")
                    with cc2:
                        st.caption("목표마진(40%) 판매가")
                        if required_price:
                            st.markdown(f"**{required_price:,}원**")
                        else:
                            st.markdown("계산불가")
                    st.markdown(f"[상품 보기]({it.url})")

st.divider()
st.caption("API 키는 서버에 저장되지 않으며, 이 세션에서만 사용됩니다.")
