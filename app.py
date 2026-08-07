import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="대리점 서비스 평가 대시보드", layout="wide")
st.title("📊 대리점 서비스 평가 및 데이터 입력 현황")

# 엑셀 파일 업로드
uploaded_file = st.file_uploader("월별 서비스 평가 엑셀 파일을 업로드하세요", type=["xlsx"])

if uploaded_file:
    try:
        # 엑셀의 '평가' 시트, 4번째 행(header=3)을 열 제목으로 읽기
        df = pd.read_excel(uploaded_file, sheet_name='평가', header=3)
        
        # 열 이름 공백 및 줄바꿈 정리
        df.columns = df.columns.astype(str).str.replace('\n', '').str.strip()
        
        # 주요 수치 데이터 숫자로 강제 변환
        numeric_cols = ['총 점수', '총접수건', '미방문', '미입력', '방문', '입력건', 
                        '입력율(%)', '1시간이내예약건', '예약율(%)', '재방문건수', 
                        '재방문율(%)', '불만건수', '서비스불만율(%)', '방문율']
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')

        # ------------------ 1. 사장님 보고용 시각화 ------------------
        left_col, right_col = st.columns(2)
        
        # 두 그래프에 동일한 지사 색상 팔레트 사용
        color_palette = px.colors.qualitative.Plotly
        
        # [왼쪽] 지사별 평균 서비스 점수
        with left_col:
            st.subheader("🏢 지사별 평균 서비스 점수")
            if '지사' in df.columns and '총 점수' in df.columns:
                branch_avg = df.groupby("지사", as_index=False)['총 점수'].mean()
                fig2 = px.bar(
                    branch_avg, 
                    x="지사", 
                    y="총 점수", 
                    color="지사",
                    color_discrete_sequence=color_palette,  # 공통 색상 적용
                    text_auto='.1f',
                    title="지사별 서비스 평가 평균 점수"
                )
                st.plotly_chart(fig2, use_container_width=True)

        # [오른쪽] 미입력 건수 vs 총 점수
        with right_col:
            st.subheader("💡 미입력 건수 vs 총 점수")
            if '미입력' in df.columns and '총 점수' in df.columns:
                fig1 = px.scatter(
                    df, x="미입력", y="총 점수", 
                    color="지사" if "지사" in df.columns else None,
                    color_discrete_sequence=color_palette,  # 공통 색상 적용
                    hover_name="방문 대리점" if "방문 대리점" in df.columns else None,
                    size="총접수건" if "총접수건" in df.columns else None,
                    title="미입력 건수가 점수 하락에 미치는 영향 (점 크기: 총접수건)"
                )
                st.plotly_chart(fig1, use_container_width=True)

        # ------------------ 2. 표 출력을 위한 데이터 % 포맷팅 ------------------
        display_df = df.copy()
        
        # AI열(방문율) 및 백분율 컬럼 % 변환 처리
        percent_cols = ['방문율', '입력율(%)', '예약율(%)', '재방문율(%)', '서비스불만율(%)']
        for p_col in percent_cols:
            if p_col in display_df.columns:
                display_df[p_col] = display_df[p_col].apply(
                    lambda x: f"{x*100:.1f}%" if pd.notnull(x) and x <= 1.0 else (f"{x:.1f}%" if pd.notnull(x) else "")
                )

        # ------------------ 3. 집중 관리 대상 모니터링 ------------------
        col_a, col_b = st.columns(2)
        
        with col_a:
            st.subheader("📉 미입력 건수 상위 대리점")
            if '방문 대리점' in df.columns and '미입력' in df.columns:
                top_unentered = display_df.sort_values(by='미입력', ascending=False)[
                    [c for c in ['지사', '방문 대리점', '총접수건', '미입력', '방문율', '총 점수'] if c in display_df.columns]
                ].head(10)
                st.dataframe(top_unentered, use_container_width=True, hide_index=True)
                
        with col_b:
            st.subheader("⚠️ 서비스 불만율 상위 대리점")
            if '방문 대리점' in df.columns and '서비스불만율(%)' in df.columns:
                top_dissatisfied = display_df.sort_values(by='서비스불만율(%)', ascending=False)[
                    [c for c in ['지사', '방문 대리점', '불만건수', '서비스불만율(%)', '방문율', '총 점수'] if c in display_df.columns]
                ].head(10)
                st.dataframe(top_dissatisfied, use_container_width=True, hide_index=True)

        # ------------------ 4. 전체 대리점 상세 조회 ------------------
        st.markdown("---")
        st.subheader("🔍 대리점별 전체 항목 조회")
        if '지사' in display_df.columns:
            selected_branch = st.selectbox("지사를 선택하세요", ["전체"] + list(display_df["지사"].dropna().unique()))
            filtered_df = display_df if selected_branch == "전체" else display_df[display_df["지사"] == selected_branch]
            st.dataframe(filtered_df, use_container_width=True)
        else:
            st.dataframe(display_df, use_container_width=True)

    except ValueError:
        st.error("⚠️ 업로드한 엑셀 파일 안에 '[평가]' 라는 이름의 시트(Sheet)가 존재하지 않습니다.")
    except Exception as e:
        st.error(f"⚠️ 데이터를 읽는 중 오류가 발생했습니다: {e}")
