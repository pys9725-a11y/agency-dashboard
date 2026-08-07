import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="대리점 서비스 평가 대시보드", layout="wide")
st.title("📊 대리점 서비스 평가 및 데이터 입력 현황")

# 엑셀 파일 업로드
uploaded_file = st.file_uploader("월별 서비스 평가 엑셀 파일을 업로드하세요", type=["xlsx"])

if uploaded_file:
    try:
        # '평가' 시트 읽기 (3번째 행을 제목으로 지정)
        df = pd.read_excel(uploaded_file, sheet_name='평가', header=2)
        
        # 열 이름 공백 및 줄바꿈 정리
        df.columns = df.columns.astype(str).str.replace('\n', '').str.strip()
        
        # 열 이름 자동 검색
        score_col = '총 점수' if '총 점수' in df.columns else '점수'

        # 숫자가 아닌 문자나 에러값(#DIV/0! 등)을 결측치(NaN)로 변환
        if score_col in df.columns:
            df[score_col] = pd.to_numeric(df[score_col], errors='coerce')
        if '미입력' in df.columns:
            df['미입력'] = pd.to_numeric(df['미입력'], errors='coerce').fillna(0)
        if '입력률(%)' in df.columns:
            df['입력률(%)'] = pd.to_numeric(df['입력률(%)'], errors='coerce')

        # ------------------ 1. 상단 핵심 지표 (KPI) ------------------
        col1, col2, col3, col4 = st.columns(4)
        
        if score_col in df.columns and not df[score_col].dropna().empty:
            avg_score = df[score_col].mean()
            col1.metric("전사 평균 점수", f"{avg_score:.1f}점")
        else:
            col1.metric("전사 평균 점수", "데이터 없음")
            
        if '미입력' in df.columns:
            col2.metric("총 미입력 건수", f"{int(df['미입력'].sum())}건")
            
        if '입력률(%)' in df.columns and not df['입력률(%)'].dropna().empty:
            col3.metric("입력률 100% 대리점 비중", f"{(df['입력률(%)'] == 1).mean() * 100:.1f}%")
            
        if '등급' in df.columns:
            d_count = (df['등급'].astype(str).str.strip() == 'D').sum()
            col4.metric("최하위 등급(D) 대리점 수", f"{d_count}개소")
        
        st.markdown("---")
        
        # ------------------ 2. 사장님 보고용 시각화 ------------------
        left_col, right_col = st.columns(2)
        
        with left_col:
            st.subheader("💡 데이터 미입력 건수 vs 서비스 점수")
            if '미입력' in df.columns and score_col in df.columns:
                fig1 = px.scatter(
                    df, x="미입력", y=score_col, 
                    color="지사" if "지사" in df.columns else None,
                    hover_name="방문 대리점" if "방문 대리점" in df.columns else None,
                    title="미입력 건수가 점수 하락에 미치는 영향"
                )
                st.plotly_chart(fig1, use_container_width=True)
                
        with right_col:
            st.subheader("🏢 지사별 평균 서비스 점수")
            if '지사' in df.columns and score_col in df.columns:
                branch_avg = df.groupby("지사", as_index=False)[score_col].mean()
                fig2 = px.bar(branch_avg, x="지사", y=score_col, color=score_col, text_auto='.1f')
                st.plotly_chart(fig2, use_container_width=True)

        # ------------------ 3. 대리점 상세 현황 ------------------
        st.subheader("🔍 대리점별 세부 항목 조회")
        if '지사' in df.columns:
            selected_branch = st.selectbox("지사를 선택하세요", ["전체"] + list(df["지사"].dropna().unique()))
            filtered_df = df if selected_branch == "전체" else df[df["지사"] == selected_branch]
            st.dataframe(filtered_df, use_container_width=True)
        else:
            st.dataframe(df, use_container_width=True)

    except ValueError:
        st.error("⚠️ 업로드한 엑셀 파일 안에 '[평가]' 라는 이름의 시트(Sheet)가 존재하지 않습니다. 시트 이름을 확인해 주세요.")
