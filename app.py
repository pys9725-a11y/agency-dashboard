import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="대리점 서비스 평가 대시보드", layout="wide")

# ------------------ 전체 폰트 및 요소 확대 CSS 스타일 적용 ------------------
st.markdown("""
    <style>
        /* 전체 기본 폰트 크기 확대 */
        html, body, [class*="css"] {
            font-size: 23px !important;
        }
        
        /* 제목 및 주요 헤더 폰트 크기 확대 */
        h1 { font-size: 2.3rem !important; }
        h2 { font-size: 2.0rem !important; }
        h3 { font-size: 1.7rem !important; }
        
        /* 표(Dataframe) 내부 글자 크기 확대 */
        .stDataFrame {
            font-size: 19px !important;
        }
        
        /* 드롭다운/선택 상자 폰트 확대 */
        div[data-baseweb="select"] {
            font-size: 19px !important;
        }

        /* 입력 폼 / 업로더 글자 확대 */
        .stFileUploader label {
            font-size: 21px !important;
        }
    </style>
""", unsafe_allow_html=True)

st.title("📊 대리점 서비스 평가 및 데이터 입력 현황")

# 엑셀 파일 업로드
uploaded_file = st.file_uploader("월별 서비스 평가 엑셀 파일을 업로드하세요", type=["xlsx"])

# 시간 변환 함수 (S열 처리용: HH:MM:SS -> X시간 Y분)
def format_time_duration(val):
    if pd.isna(val) or val == "":
        return ""
    try:
        if isinstance(val, str):
            parts = val.split(":")
            if len(parts) >= 2:
                hours = int(parts[0])
                minutes = int(parts[1])
            else:
                return str(val)
        elif hasattr(val, 'hour') and hasattr(val, 'minute'):
            hours = val.hour
            minutes = val.minute
        elif isinstance(val, pd.Timedelta):
            total_seconds = int(val.total_seconds())
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
        else:
            dt = pd.to_datetime(val)
            hours = dt.hour
            minutes = dt.minute

        if hours > 0 and minutes > 0:
            return f"{hours}시간 {minutes}분"
        elif hours > 0 and minutes == 0:
            return f"{hours}시간"
        elif hours == 0 and minutes > 0:
            return f"{minutes}분"
        else:
            return "0분"
    except Exception:
        return str(val)

if uploaded_file:
    try:
        # 엑셀의 '평가' 시트, 4번째 행(header=3)을 열 제목으로 읽기
        df = pd.read_excel(uploaded_file, sheet_name='평가', header=3)
        
        # 열 이름 공백 및 줄바꿈 정리
        df.columns = df.columns.astype(str).str.replace('\n', '').str.strip()
        
        # AA4 '점수(점)' 항목을 화면 표시용 '점수'로 이름 변경
        if '점수(점)' in df.columns:
            df = df.rename(columns={'점수(점)': '점수'})
        
        # 주요 수치 데이터 숫자로 강제 변환 (Y4: 불만건수, Z4: 서비스불만율(%), AA4: 점수 포함)
        numeric_cols = ['총 점수', '점수', '총접수건', '미방문', '미입력', '방문', '입력건', 
                        '입력율(%)', '1시간이내예약건', '예약율(%)', '재방문건수', 
                        '재방문율(%)', '불만건수', '서비스불만율(%)', '방문율']
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')

        # ------------------ 지사별 색상 및 범례 순서 고정 ------------------
        if '지사' in df.columns:
            unique_branches = sorted(df['지사'].dropna().unique())
            palette = px.colors.qualitative.Plotly
            branch_color_map = {branch: palette[i % len(palette)] for i, branch in enumerate(unique_branches)}
            branch_order = {"지사": unique_branches}
        else:
            branch_color_map = None
            branch_order = None

        # ------------------ 1. 사장님 보고용 시각화 ------------------
        left_col, right_col = st.columns(2)
        
        # [왼쪽] 지사별 평균 서비스 점수 (점수/총 점수)
        with left_col:
            st.subheader("🏢 지사별 평균 서비스 점수")
            target_score = '점수' if '점수' in df.columns else '총 점수'
            if '지사' in df.columns and target_score in df.columns:
                branch_avg = df.groupby("지사", as_index=False)[target_score].mean()
                fig2 = px.bar(
                    branch_avg, 
                    x="지사", 
                    y=target_score, 
                    color="지사",
                    color_discrete_map=branch_color_map,
                    category_orders=branch_order,
                    text_auto='.2f',
                    title="지사별 서비스 평가 평균 점수",
                    height=550
                )
                fig2.update_layout(font=dict(size=15))
                st.plotly_chart(fig2, use_container_width=True)

        # [오른쪽] 미입력 건수 vs 점수
        with right_col:
            st.subheader("💡 미입력 건수 vs 점수")
            if '미입력' in df.columns and target_score in df.columns:
                fig1 = px.scatter(
                    df, x="미입력", y=target_score, 
                    color="지사" if "지사" in df.columns else None,
                    color_discrete_map=branch_color_map,
                    category_orders=branch_order,
                    hover_name="방문 대리점" if "방문 대리점" in df.columns else None,
                    size="총접수건" if "총접수건" in df.columns else None,
                    title="미입력 건수가 점수 하락에 미치는 영향 (점 크기: 총접수건)",
                    height=550
                )
                fig1.update_layout(font=dict(size=15))
                st.plotly_chart(fig1, use_container_width=True)

        # ------------------ 2. 표 출력을 위한 데이터 서식 적용 ------------------
        display_df = df.copy()
        
        # 1) S열(19번째 열, index=18) 'X시간 Y분' 포맷 적용
        if len(display_df.columns) > 18:
            s_col_name = display_df.columns[18]
            display_df[s_col_name] = display_df[s_col_name].apply(format_time_duration)

        # 2) % 변환 처리 (Z4: 서비스불만율(%) 포함)
        percent_cols = ['입력율(%)', '방문율', '예약율(%)', '재방문율(%)', '서비스불만율(%)']

        for p_col in percent_cols:
            if p_col in display_df.columns:
                display_df[p_col] = display_df[p_col].apply(
                    lambda x: f"{x*100:.2f}%" if pd.notnull(x) and isinstance(x, (int, float)) and x <= 1.0 else (f"{x:.2f}%" if pd.notnull(x) and isinstance(x, (int, float)) else "")
                )

        # 3) 기타 일반 수치 데이터 소수점 2자리 포맷팅
        for col in display_df.select_dtypes(include=['float', 'float64']).columns:
            if col not in percent_cols:
                display_df[col] = display_df[col].apply(lambda x: f"{x:.2f}" if pd.notnull(x) else "")

        # ------------------ 3. 집중 관리 대상 모니터링 (상위 10개) ------------------
        st.markdown("---")
        col_a, col_b = st.columns(2)
        
        with col_a:
            st.subheader("📉 미입력 건수 상위 대리점 (TOP 10)")
            if '방문 대리점' in df.columns and '미입력' in df.columns:
                unentered_cols = [c for c in ['지사', '방문 대리점', '총접수건', '미입력', '점수', '총 점수'] if c in display_df.columns]
                top_unentered = display_df.sort_values(by='미입력', ascending=False)[unentered_cols].head(10)
                st.dataframe(top_unentered, use_container_width=True, hide_index=True, height=430)
                
        with col_b:
            st.subheader("⚠️ 서비스 불만율 상위 대리점 (TOP 10)")
            if '방문 대리점' in df.columns and '서비스불만율(%)' in df.columns:
                # Y4(불만건수), Z4(서비스불만율(%)), AA4(점수) 표 순서 적용
                dissatisfied_cols = [c for c in ['지사', '방문 대리점', '불만건수', '서비스불만율(%)', '점수', '총 점수'] if c in display_df.columns]
                top_dissatisfied = display_df.sort_values(by='서비스불만율(%)', ascending=False)[dissatisfied_cols].head(10)
                st.dataframe(top_dissatisfied, use_container_width=True, hide_index=True, height=430)

        # ------------------ 4. 지사별 대리점 상세 조회 ------------------
        st.markdown("---")
        st.subheader("🏢 지사별 대리점 상세 현황 조회")
        
        col_select_a, col_select_b = st.columns(2)
        branch_list = ["전체"] + list(df['지사'].dropna().unique()) if '지사' in df.columns else ["전체"]

        # [왼쪽] 선택 지사의 미입력 대리점 전체 목록
        with col_select_a:
            selected_branch_unentered = st.selectbox("미입력 대리점 조회 (지사 선택)", branch_list, key="select_unentered")
            filtered_unentered = display_df if selected_branch_unentered == "전체" else display_df[display_df['지사'] == selected_branch_unentered]
            
            if '방문 대리점' in df.columns and '미입력' in df.columns:
                target_cols = [c for c in ['지사', '방문 대리점', '총접수건', '미입력', '점수', '총 점수'] if c in display_df.columns]
                unentered_result = filtered_unentered.sort_values(by='미입력', ascending=False)[target_cols]
                st.dataframe(unentered_result, use_container_width=True, hide_index=True, height=430)

        # [오른쪽] 선택 지사의 서비스 불만율 대리점 전체 목록
        with col_select_b:
            selected_branch_dissatisfied = st.selectbox("서비스 불만율 대리점 조회 (지사 선택)", branch_list, key="select_dissatisfied")
            filtered_dissatisfied = display_df if selected_branch_dissatisfied == "전체" else display_df[display_df['지사'] == selected_branch_dissatisfied]
                
            if '방문 대리점' in df.columns and '서비스불만율(%)' in df.columns:
                target_cols = [c for c in ['지사', '방문 대리점', '불만건수', '서비스불만율(%)', '점수', '총 점수'] if c in display_df.columns]
                dissatisfied_result = filtered_dissatisfied.sort_values(by='서비스불만율(%)', ascending=False)[target_cols]
                st.dataframe(dissatisfied_result, use_container_width=True, hide_index=True, height=430)

        # ------------------ 5. 전체 대리점 상세 조회 ------------------
        st.markdown("---")
        st.subheader("🔍 대리점별 전체 항목 조회")
        if '지사' in display_df.columns:
            selected_branch = st.selectbox("지사를 선택하세요 (전체 조회)", ["전체"] + list(display_df["지사"].dropna().unique()), key="select_all")
            filtered_df = display_df if selected_branch == "전체" else display_df[display_df["지사"] == selected_branch]
            st.dataframe(filtered_df, use_container_width=True, height=520)
        else:
            st.dataframe(display_df, use_container_width=True, height=520)

    except ValueError:
        st.error("⚠️ 업로드한 엑셀 파일 안에 '[평가]' 라는 이름의 시트(Sheet)가 존재하지 않습니다.")
    except Exception as e:
        st.error(f"⚠️ 데이터를 읽는 중 오류가 발생했습니다: {e}")
