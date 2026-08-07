import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="대리점 서비스 평가 대시보드", layout="wide")

# ==============================================================================
# 🛠️ [엑셀 좌표 설정 구역] - 표 수정 및 관리를 위해 자유롭게 변경하세요.
# ==============================================================================
# 엑셀 열 알파벳(A=0, B=1, C=2...)을 파이썬 인덱스 숫자로 변환하는 함수
def col2idx(col_str):
    num = 0
    for c in col_str.upper():
        num = num * 26 + (ord(c) - ord('A')) + 1
    return num - 1

# [주요 열 좌표 정의] (4행 기준)
# A4: 지사, B4: 방문 대리점, C4: 총접수건, E4: 미입력, F4: 입력율, L4: 방문율, M4: 총 점수 등
COL_BRANCH = col2idx('A')      # A4 (지사)
COL_AGENCY = col2idx('B')      # B4 (방문 대리점)
COL_TOTAL_CNT = col2idx('C')   # C4 (총접수건)
COL_UNENTERED = col2idx('E')    # E4 (미입력)
COL_SCORE = col2idx('M')       # M4 (총 점수 / 점수)

# [% 서식 적용할 엑셀 열 알파벳 목록]
PERCENT_COL_LETTERS = ['F', 'L', 'O', 'Q', 'AC'] 

# [TOP 10 및 지사별 조회 표에 표시할 열 순서 (알파벳 좌표)]
# 왼쪽 표: 미입력 상위 (지사, 방문대리점, 총접수건, 미입력, 방문율, 총점수)
TARGET_LETTERS_UNENTERED = ['A', 'B', 'C', 'E', 'L', 'M']

# 오른쪽 표: 불만율 상위 (지사, 방문대리점, 불만건수, 서비스불만율, 방문율, 총점수)
TARGET_LETTERS_DISSATISFIED = ['A', 'B', 'W', 'AC', 'L', 'M'] 
# ==============================================================================

# ------------------ 전체 폰트 및 요소 확대 CSS 스타일 적용 ------------------
st.markdown("""
    <style>
        html, body, [class*="css"] { font-size: 19px !important; }
        h1 { font-size: 2.3rem !important; }
        h2 { font-size: 1.8rem !important; }
        h3 { font-size: 1.5rem !important; }
        .stDataFrame { font-size: 16px !important; }
        div[data-baseweb="select"] { font-size: 18px !important; }
        .stFileUploader label { font-size: 18px !important; }
    </style>
""", unsafe_allow_html=True)

st.title("📊 대리점 서비스 평가 및 데이터 입력 현황")

# 엑셀 파일 업로드
uploaded_file = st.file_uploader("월별 서비스 평가 엑셀 파일을 업로드하세요", type=["xlsx"])

# 시간 변환 함수 (S열: HH:MM:SS -> X시간 Y분)
def format_time_duration(val):
    if pd.isna(val) or val == "":
        return ""
    try:
        if isinstance(val, str):
            parts = val.split(":")
            if len(parts) >= 2:
                hours, minutes = int(parts[0]), int(parts[1])
            else:
                return str(val)
        elif hasattr(val, 'hour') and hasattr(val, 'minute'):
            hours, minutes = val.hour, val.minute
        elif isinstance(val, pd.Timedelta):
            total_seconds = int(val.total_seconds())
            hours, minutes = total_seconds // 3600, (total_seconds % 3600) // 60
        else:
            dt = pd.to_datetime(val)
            hours, minutes = dt.hour, dt.minute

        if hours > 0 and minutes > 0:
            return f"{hours}시간 {minutes}분"
        elif hours > 0:
            return f"{hours}시간"
        elif minutes > 0:
            return f"{minutes}분"
        else:
            return "0분"
    except Exception:
        return str(val)

# 인덱스 번호로 안전하게 실제 열 이름(문자열)을 찾아주는 함수
def get_col_name(df_obj, idx):
    if 0 <= idx < len(df_obj.columns):
        return df_obj.columns[idx]
    return None

if uploaded_file:
    try:
        # 엑셀의 '평가' 시트, 4번째 행(header=3)을 열 제목으로 읽기
        df = pd.read_excel(uploaded_file, sheet_name='평가', header=3)
        df.columns = df.columns.astype(str).str.replace('\n', '').str.strip()
        
        # 주요 수치 컬럼명 좌표 매핑
        col_branch = get_col_name(df, COL_BRANCH)
        col_agency = get_col_name(df, COL_AGENCY)
        col_unentered = get_col_name(df, COL_UNENTERED)
        col_score = get_col_name(df, COL_SCORE)
        col_total_cnt = get_col_name(df, COL_TOTAL_CNT)

        # 수치형 변환
        for c in df.columns:
            df[c] = pd.to_numeric(df[c], errors='ignore')

        # 지사별 색상 설정
        if col_branch and col_branch in df.columns:
            unique_branches = sorted(df[col_branch].dropna().unique())
            palette = px.colors.qualitative.Plotly
            branch_color_map = {branch: palette[i % len(palette)] for i, branch in enumerate(unique_branches)}
            branch_order = {col_branch: unique_branches}
        else:
            branch_color_map, branch_order = None, None

        # ------------------ 1. 시각화 영역 ------------------
        left_col, right_col = st.columns(2)
        
        with left_col:
            st.subheader("🏢 지사별 평균 서비스 점수")
            if col_branch and col_score:
                branch_avg = df.groupby(col_branch, as_index=False)[col_score].mean()
                fig2 = px.bar(
                    branch_avg, x=col_branch, y=col_score, color=col_branch,
                    color_discrete_map=branch_color_map, category_orders=branch_order,
                    text_auto='.2f', title="지사별 서비스 평가 평균 점수", height=550
                )
                fig2.update_layout(font=dict(size=15))
                st.plotly_chart(fig2, use_container_width=True)

        with right_col:
            st.subheader("💡 미입력 건수 vs 총 점수")
            if col_unentered and col_score:
                fig1 = px.scatter(
                    df, x=col_unentered, y=col_score, color=col_branch,
                    color_discrete_map=branch_color_map, category_orders=branch_order,
                    hover_name=col_agency, size=col_total_cnt if col_total_cnt else None,
                    title="미입력 건수가 점수 하락에 미치는 영향", height=550
                )
                fig1.update_layout(font=dict(size=15))
                st.plotly_chart(fig1, use_container_width=True)

        # ------------------ 2. 표 서식 포맷팅 ------------------
        display_df = df.copy()
        
        # S열 (19번째 열, index 18) 시간 포맷 적용
        s_col = get_col_name(display_df, col2idx('S'))
        if s_col:
            display_df[s_col] = display_df[s_col].apply(format_time_duration)

        # % 서식 적용 (알파벳 좌표 기반)
        percent_cols = [get_col_name(display_df, col2idx(let)) for let in PERCENT_COL_LETTERS]
        percent_cols = [c for c in percent_cols if c is not None]

        for p_col in percent_cols:
            display_df[p_col] = display_df[p_col].apply(
                lambda x: f"{x*100:.2f}%" if pd.notnull(x) and isinstance(x, (int, float)) and x <= 1.0 else (f"{x:.2f}%" if pd.notnull(x) and isinstance(x, (int, float)) else "")
            )

        # 기타 실수 데이터 소수점 2자리 포맷팅
        for col in display_df.select_dtypes(include=['float', 'float64']).columns:
            if col not in percent_cols:
                display_df[col] = display_df[col].apply(lambda x: f"{x:.2f}" if pd.notnull(x) else "")

        # ------------------ 3. 집중 관리 대상 (상위 10개) ------------------
        st.markdown("---")
        col_a, col_b = st.columns(2)
        
        # 알파벳 좌표를 실제 열 이름으로 변환하는 헬퍼 함수
        def letters_to_cols(letters):
            cols = [get_col_name(display_df, col2idx(l)) for l in letters]
            return [c for c in cols if c is not None and c in display_df.columns]

        target_cols_a = letters_to_cols(TARGET_LETTERS_UNENTERED)
        target_cols_b = letters_to_cols(TARGET_LETTERS_DISSATISFIED)

        with col_a:
            st.subheader("📉 미입력 건수 상위 대리점 (TOP 10)")
            if col_unentered and target_cols_a:
                top_unentered = display_df.sort_values(by=col_unentered, ascending=False)[target_cols_a].head(10)
                st.dataframe(top_unentered, use_container_width=True, hide_index=True, height=430)
                
        with col_b:
            st.subheader("⚠️ 서비스 불만율 상위 대리점 (TOP 10)")
            dis_col = get_col_name(display_df, col2idx('AC')) # 불만율 AC열
            if dis_col and target_cols_b:
                top_dissatisfied = display_df.sort_values(by=dis_col, ascending=False)[target_cols_b].head(10)
                st.dataframe(top_dissatisfied, use_container_width=True, hide_index=True, height=430)

        # ------------------ 4. 지사별 상세 조회 ------------------
        st.markdown("---")
        st.subheader("🏢 지사별 대리점 상세 현황 조회")
        
        col_select_a, col_select_b = st.columns(2)
        branch_list = ["전체"] + list(df[col_branch].dropna().unique()) if col_branch else ["전체"]

        with col_select_a:
            selected_branch_unentered = st.selectbox("지사 선택 (미입력 대리점 조회)", branch_list, key="select_unentered")
            filtered_unentered = display_df if selected_branch_unentered == "전체" else display_df[display_df[col_branch] == selected_branch_unentered]
            if col_unentered and target_cols_a:
                unentered_result = filtered_unentered.sort_values(by=col_unentered, ascending=False)[target_cols_a]
                st.dataframe(unentered_result, use_container_width=True, hide_index=True, height=430)

        with col_select_b:
            selected_branch_dissatisfied = st.selectbox("지사 선택 (서비스 불만율 대리점 조회)", branch_list, key="select_dissatisfied")
            filtered_dissatisfied = display_df if selected_branch_dissatisfied == "전체" else display_df[display_df[col_branch] == selected_branch_dissatisfied]
            dis_col = get_col_name(display_df, col2idx('AC'))
            if dis_col and target_cols_b:
                dissatisfied_result = filtered_dissatisfied.sort_values(by=dis_col, ascending=False)[target_cols_b]
                st.dataframe(dissatisfied_result, use_container_width=True, hide_index=True, height=430)

        # ------------------ 5. 전체 대리점 상세 조회 ------------------
        st.markdown("---")
        st.subheader("🔍 대리점별 전체 항목 조회")
        if col_branch:
            selected_branch = st.selectbox("지사를 선택하세요 (전체 조회)", ["전체"] + list(display_df[col_branch].dropna().unique()), key="select_all")
            filtered_df = display_df if selected_branch == "전체" else display_df[display_df[col_branch] == selected_branch]
            st.dataframe(filtered_df, use_container_width=True, height=520)
        else:
            st.dataframe(display_df, use_container_width=True, height=520)

    except ValueError:
        st.error("⚠️ 업로드한 엑셀 파일 안에 '[평가]' 라는 이름의 시트(Sheet)가 존재하지 않습니다.")
    except Exception as e:
        st.error(f"⚠️ 데이터를 읽는 중 오류가 발생했습니다: {e}")
