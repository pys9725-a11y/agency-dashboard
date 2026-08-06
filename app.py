import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="대리점 서비스 평가 대시보드", layout="wide")
st.title("📊 대리점 서비스 평가 및 데이터 입력 현황")

# 엑셀 파일 업로드 (4번째 행을 헤더로 인식)
uploaded_file = st.file_uploader("월별 서비스 평가 엑셀 파일을 업로드하세요", type=["xlsx"])

if uploaded_file:
    # 3~4행에 걸친 제목 구조를 고려해 header=3 설정
    df = pd.read_excel(uploaded_file, header=3)
    
    # 공백 제거 및 열 이름 정형화
    df.columns = df.columns.str.strip()
    
    # ------------------ 1. 상단 핵심 지표 (KPI) ------------------
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("전사 평균 점수", f"{df['총 점수'].mean():.1f}점")
    col2.metric("총 미입력 건수", f"{int(df['미입력'].sum())}건")
    col3.metric("입력률 100% 대리점 비중", f"{(df['입력률(%)'] == 1).mean() * 100:.1f}%")
    col4.metric("최하위 등급(D) 대리점 수", f"{(df['등급'] == 'D').sum()}개소")
    
    st.markdown("---")
    
    # ------------------ 2. 사장님 보고용 시각화 ------------------
    left_col, right_col = st.columns(2)
    
    with left_col:
        st.subheader("💡 데이터 미입력 건수 vs 총 점수")
        # 미입력이 많을수록 총 점수가 깎이는 상관관계 시각화
        fig1 = px.scatter(
            df, x="미입력", y="총 점수", color="지사", hover_name="방문 대리점",
            title="미입력 건수가 점수 하락에 미치는 영향"
        )
        st.plotly_chart(fig1, use_container_width=True)
        
    with right_col:
        st.subheader("🏢 지사별 평균 서비스 점수")
        branch_avg = df.groupby("지사")["총 점수"].mean().reset_index()
        fig2 = px.bar(branch_avg, x="지사", y="총 점수", color="총 점수", text_auto='.1f')
        st.plotly_chart(fig2, use_container_width=True)

    # ------------------ 3. 대리점 상세 현황 및 미입력 케어 ------------------
    st.subheader("🔍 대리점별 세부 항목 조회")
    selected_branch = st.selectbox("지사를 선택하세요", ["전체"] + list(df["지사"].unique()))
    
    filtered_df = df if selected_branch == "전체" else df[df["지사"] == selected_branch]
    
    # 보고에 필요한 주요 컬럼만 추려서 출력
    show_cols = ["지사", "방문 대리점", "총 점수", "등급", "미입력", "입력률(%)", "약속(건)", "평균시간"]
    st.dataframe(filtered_df[show_cols], use_container_width=True)
