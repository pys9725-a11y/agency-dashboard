import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, time

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

        /* 탭(Tab) 폰트 크기 확대 */
        button[data-baseweb="tab"] {
            font-size: 20px !important;
        }
    </style>
""", unsafe_allow_html=True)

st.title("📊 대리점 서비스 평가 및 데이터 입력 현황")

# 엑셀 파일 업로드
uploaded_file = st.file_uploader("월별 서비스 평가 엑셀 파일을 업로드하세요", type=["xlsx"])

# 시간 데이터를 초(seconds) 단위 숫자로 정규화하는 함수 (정렬용)
def parse_time_to_seconds(val):
    if pd.isna(val) or val == "" or str(val).strip() == "":
        return None
    try:
        if isinstance(val, time):
            return val.hour * 3600 + val.minute * 60 + val.second
        elif isinstance(val, datetime):
            return val.hour * 3600 + val.minute * 60 + val.second
        elif isinstance(val, pd.Timedelta):
            return int(val.total_seconds())
        elif isinstance(val, str):
            parts = val.split(":")
            if len(parts) >= 2:
                return int(parts[0]) * 3600 + int(parts[1]) * 60
            return None
        else:
            dt = pd.to_datetime(val)
            return dt.hour * 3600 + dt.minute * 60 + dt.second
    except Exception:
        return None

# 시간 변환 함수 (S열 표기용: HH:MM:SS -> X시간 Y분)
def format_time_duration(val):
    if pd.isna(val) or val == "" or str(val).strip() == "":
        return ""
    try:
        if isinstance(val, time):
            hours, minutes = val.hour, val.minute
        elif isinstance(val, datetime):
            hours, minutes = val.hour, val.minute
        elif isinstance(val, pd.Timedelta):
            total_seconds = int(val.total_seconds())
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
        elif isinstance(val, str):
            parts = val.split(":")
            if len(parts) >= 2:
                hours, minutes = int(parts[0]), int(parts[1])
            else:
                return str(val)
        else:
            dt = pd.to_datetime(val)
            hours, minutes = dt.hour, dt.minute

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
        
        # '방문 대리점'이 비어 있는 기본 빈 행 제거
        if '방문 대리점' in df.columns:
            df = df.dropna(subset=['방문 대리점'])

        # 엑셀 열 절대 위치(Index) 기준 컬럼명 매핑
        cols = list(df.columns)
        
        # M4  (13번째 열 - index 12): 조치입력 점수
        # P4  (16번째 열 - index 15): 예약 점수
        # U4  (21번째 열 - index 20): 처리시간 점수
        # X4  (24번째 열 - index 23): 재방문 점수
        # AA4 (27번째 열 - index 26): 불만 점수
        # AD4 (30번째 열 - index 29): 독촉 점수
        # AG4 (33번째 열 - index 32): 고객만족도 점수
        if len(cols) > 12:
            cols[12] = '조치입력 점수'
        if len(cols) > 15:
            cols[15] = '예약 점수'
        if len(cols) > 20:
            cols[20] = '처리시간 점수'
        if len(cols) > 23:
            cols[23] = '재방문 점수'
        if len(cols) > 26:
            cols[26] = '불만 점수'
        if len(cols) > 29:
            cols[29] = '독촉 점수'
        if len(cols) > 32:
            cols[32] = '고객만족도 점수'
            
        df.columns = cols

        # 주요 수치 데이터 숫자로 강제 변환
        numeric_cols = [
            '총 점수', '불만 점수', '예약 점수', '처리시간 점수', '조치입력 점수', '재방문 점수', '독촉 점수', '고객만족도 점수',
            '총접수건', '총접수', '미방문', '미입력', '방문 입력건', '입력건', '입력율(%)', 
            '1시간이내예약건', '예약율(%)', '재방문건수', '재방문율(%)', '불만건수', '서비스불만율(%)', 
            '독촉건수', '독촉율(%)', '합계', '총건'
        ]
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')

        # S열(19번째 열) 시간 정렬용 초 단위 컬럼 생성
        s_col_name = None
        if len(df.columns) > 18:
            s_col_name = df.columns[18]
            df['_s_seconds'] = df[s_col_name].apply(parse_time_to_seconds)

        # ------------------ 지사별 색상 및 범례 순서 고정 ------------------
        if '지사' in df.columns:
            unique_branches = sorted(df['지사'].dropna().unique())
            palette = px.colors.qualitative.Plotly
            branch_color_map = {branch: palette[i % len(palette)] for i, branch in enumerate(unique_branches)}
            branch_order = {"지사": unique_branches}
        else:
            branch_color_map = None
            branch_order = None

        # ------------------ 1. 보고용 주요 시각화 ------------------
        left_col, right_col = st.columns(2)
        
        # [왼쪽] 지사별 평균 서비스 점수 (총 점수)
        with left_col:
            st.subheader("🏢 지사별 평균 서비스 점수")
            if '지사' in df.columns and '총 점수' in df.columns:
                branch_avg = df.dropna(subset=['총 점수']).groupby("지사", as_index=False)['총 점수'].mean()
                fig2 = px.bar(
                    branch_avg, 
                    x="지사", 
                    y="총 점수", 
                    color="지사",
                    color_discrete_map=branch_color_map,
                    category_orders=branch_order,
                    text_auto='.2f',
                    title="지사별 서비스 평가 평균 점수 (총 점수)",
                    height=550
                )
                fig2.update_layout(font=dict(size=15))
                st.plotly_chart(fig2, use_container_width=True)

        # [오른쪽] 총 점수 vs 총접수건
        with right_col:
            st.subheader("💡 총 점수 vs 총접수건")
            total_cnt_col = '총접수건' if '총접수건' in df.columns else ('총접수' if '총접수' in df.columns else None)
            
            if total_cnt_col and '총 점수' in df.columns:
                scatter_df = df.dropna(subset=[total_cnt_col, '총 점수'])
                fig1 = px.scatter(
                    scatter_df, x=total_cnt_col, y="총 점수", 
                    color="지사" if "지사" in scatter_df.columns else None,
                    color_discrete_map=branch_color_map,
                    category_orders=branch_order,
                    hover_name="방문 대리점" if "방문 대리점" in scatter_df.columns else None,
                    title="총접수건 대비 총 점수 분포",
                    height=550
                )
                fig1.update_layout(font=dict(size=15))
                st.plotly_chart(fig1, use_container_width=True)

        # ------------------ 2. 표 출력을 위한 데이터 서식 적용 ------------------
        display_df = df.copy()
        
        # S열(19번째 열, index=18) 평균시간/단위환산 'X시간 Y분' 포맷 적용
        if s_col_name:
            display_df[s_col_name] = display_df[s_col_name].apply(format_time_duration)

        # % 변환 처리
        percent_cols = ['입력율(%)', '방문율', '예약율(%)', '재방문율(%)', '서비스불만율(%)', '독촉율(%)']

        for p_col in percent_cols:
            if p_col in display_df.columns:
                display_df[p_col] = display_df[p_col].apply(
                    lambda x: f"{x*100:.2f}%" if pd.notnull(x) and isinstance(x, (int, float)) and x <= 1.0 else (f"{x:.2f}%" if pd.notnull(x) and isinstance(x, (int, float)) else "")
                )

        # 기타 일반 수치 데이터 소수점 2자리 포맷팅
        for col in display_df.select_dtypes(include=['float', 'float64']).columns:
            if col not in percent_cols and col != '_s_seconds':
                display_df[col] = display_df[col].apply(lambda x: f"{x:.2f}" if pd.notnull(x) else "")

        # ------------------ 3. 집중 관리 대상 모니터링 (TOP 20 & LOW 20) ------------------
        st.markdown("---")
        
        # [행 1] 조치정보입력율 & 미입력 건수
        col_1a, col_1b = st.columns(2)
        
        with col_1a:
            st.subheader("📋 조치정보입력율 현황")
            tab_act_top, tab_act_low = st.tabs(["🔝 TOP 20 (점수 상위)", "🔻 LOW 20 (점수 하위)"])
            
            if '방문 대리점' in df.columns and '조치입력 점수' in df.columns:
                act_cols = [c for c in ['지사', '방문 대리점', '총접수건', '미방문', '미입력', '방문 입력건', '입력율(%)', '조치입력 점수', '총 점수'] if c in display_df.columns]
                valid_act_df = df.dropna(subset=['조치입력 점수'])
                
                with tab_act_top:
                    idx = valid_act_df.sort_values(by=['조치입력 점수', '총 점수'], ascending=[False, False]).index
                    st.dataframe(display_df.loc[idx, act_cols].head(20).rename(columns={'조치입력 점수': '점수'}), use_container_width=True, hide_index=True, height=450)
                with tab_act_low:
                    idx = valid_act_df.sort_values(by=['조치입력 점수', '총 점수'], ascending=[True, False]).index
                    st.dataframe(display_df.loc[idx, act_cols].head(20).rename(columns={'조치입력 점수': '점수'}), use_container_width=True, hide_index=True, height=450)

        with col_1b:
            st.subheader("📉 미입력 건수 현황")
            tab_unentered_top, tab_unentered_low = st.tabs(["🔝 TOP 20 (점수 상위)", "🔻 LOW 20 (점수 하위)"])
            
            if '방문 대리점' in df.columns and '불만 점수' in df.columns:
                unentered_cols = [c for c in ['지사', '방문 대리점', '총접수건', '미입력', '불만 점수', '총 점수'] if c in display_df.columns]
                valid_unentered_df = df.dropna(subset=['불만 점수'])
                
                with tab_unentered_top:
                    idx = valid_unentered_df.sort_values(by=['불만 점수', '총 점수'], ascending=[False, False]).index
                    st.dataframe(display_df.loc[idx, unentered_cols].head(20).rename(columns={'불만 점수': '점수'}), use_container_width=True, hide_index=True, height=450)
                with tab_unentered_low:
                    idx = valid_unentered_df.sort_values(by=['불만 점수', '총 점수'], ascending=[True, False]).index
                    st.dataframe(display_df.loc[idx, unentered_cols].head(20).rename(columns={'불만 점수': '점수'}), use_container_width=True, hide_index=True, height=450)

        # [행 2] 약속시간입력율 & 평균처리시간
        col_2a, col_2b = st.columns(2)

        with col_2a:
            st.subheader("📅 약속시간입력율 현황")
            tab_res_top, tab_res_low = st.tabs(["🔝 TOP 20 (점수 상위)", "🔻 LOW 20 (점수 하위)"])
            
            if '방문 대리점' in df.columns and '예약 점수' in df.columns:
                reservation_cols = [c for c in ['지사', '방문 대리점', '1시간이내예약건', '예약율(%)', '예약 점수', '총 점수'] if c in display_df.columns]
                valid_res_df = df.dropna(subset=['예약 점수'])
                
                with tab_res_top:
                    idx = valid_res_df.sort_values(by=['예약 점수', '총 점수'], ascending=[False, False]).index
                    st.dataframe(display_df.loc[idx, reservation_cols].head(20).rename(columns={'예약 점수': '점수'}), use_container_width=True, hide_index=True, height=450)
                with tab_res_low:
                    idx = valid_res_df.sort_values(by=['예약 점수', '총 점수'], ascending=[True, False]).index
                    st.dataframe(display_df.loc[idx, reservation_cols].head(20).rename(columns={'예약 점수': '점수'}), use_container_width=True, hide_index=True, height=450)

        with col_2b:
            st.subheader("⏱️ 평균처리시간 현황")
            tab_time_top, tab_time_low = st.tabs(["🔝 TOP 20 (점수 상위)", "🔻 LOW 20 (점수 하위)"])
            
            if '방문 대리점' in df.columns and '처리시간 점수' in df.columns and s_col_name:
                time_cols = [c for c in ['지사', '방문 대리점', s_col_name, '처리시간 점수', '총 점수'] if c in display_df.columns]
                valid_time_df = df.dropna(subset=['처리시간 점수'])
                
                with tab_time_top:
                    idx = valid_time_df.sort_values(by=['처리시간 점수', '총 점수'], ascending=[False, False]).index
                    st.dataframe(display_df.loc[idx, time_cols].head(20).rename(columns={'처리시간 점수': '점수'}), use_container_width=True, hide_index=True, height=450)
                with tab_time_low:
                    idx = valid_time_df.sort_values(by=['처리시간 점수', '총 점수'], ascending=[True, False]).index
                    st.dataframe(display_df.loc[idx, time_cols].head(20).rename(columns={'처리시간 점수': '점수'}), use_container_width=True, hide_index=True, height=450)

        # [행 3] 재방문율 & 서비스 불만율
        col_3a, col_3b = st.columns(2)

        with col_3a:
            st.subheader("🔄 재방문율 현황")
            tab_re_top, tab_re_low = st.tabs(["🔝 TOP 20 (점수 상위)", "🔻 LOW 20 (점수 하위)"])
            
            if '방문 대리점' in df.columns and '재방문 점수' in df.columns:
                re_cols = [c for c in ['지사', '방문 대리점', '재방문건수', '재방문율(%)', '재방문 점수', '총 점수'] if c in display_df.columns]
                valid_re_df = df.dropna(subset=['재방문 점수'])
                
                with tab_re_top:
                    idx = valid_re_df.sort_values(by=['재방문 점수', '총 점수'], ascending=[False, False]).index
                    st.dataframe(display_df.loc[idx, re_cols].head(20).rename(columns={'재방문 점수': '점수'}), use_container_width=True, hide_index=True, height=450)
                with tab_re_low:
                    idx = valid_re_df.sort_values(by=['재방문 점수', '총 점수'], ascending=[True, False]).index
                    st.dataframe(display_df.loc[idx, re_cols].head(20).rename(columns={'재방문 점수': '점수'}), use_container_width=True, hide_index=True, height=450)

        with col_3b:
            st.subheader("⚠️ 서비스 불만율 현황")
            tab_dissat_top, tab_dissat_low = st.tabs(["🔝 TOP 20 (점수 상위)", "🔻 LOW 20 (점수 하위)"])
            
            if '방문 대리점' in df.columns and '불만 점수' in df.columns:
                dissatisfied_cols = [c for c in ['지사', '방문 대리점', '불만건수', '서비스불만율(%)', '불만 점수', '총 점수'] if c in display_df.columns]
                valid_dissat_df = df.dropna(subset=['불만 점수'])
                
                with tab_dissat_top:
                    idx = valid_dissat_df.sort_values(by=['불만 점수', '총 점수'], ascending=[False, False]).index
                    st.dataframe(display_df.loc[idx, dissatisfied_cols].head(20).rename(columns={'불만 점수': '점수'}), use_container_width=True, hide_index=True, height=450)
                with tab_dissat_low:
                    idx = valid_dissat_df.sort_values(by=['불만 점수', '총 점수'], ascending=[True, False]).index
                    st.dataframe(display_df.loc[idx, dissatisfied_cols].head(20).rename(columns={'불만 점수': '점수'}), use_container_width=True, hide_index=True, height=450)

        # [행 4] 독촉율 & 고객만족도
        col_4a, col_4b = st.columns(2)

        with col_4a:
            st.subheader("📢 독촉율 현황")
            tab_urge_top, tab_urge_low = st.tabs(["🔝 TOP 20 (점수 상위)", "🔻 LOW 20 (점수 하위)"])
            
            if '방문 대리점' in df.columns and '독촉 점수' in df.columns:
                urge_cols = [c for c in ['지사', '방문 대리점', '독촉건수', '독촉율(%)', '독촉 점수', '총 점수'] if c in display_df.columns]
                valid_urge_df = df.dropna(subset=['독촉 점수'])
                
                with tab_urge_top:
                    idx = valid_urge_df.sort_values(by=['독촉 점수', '총 점수'], ascending=[False, False]).index
                    st.dataframe(display_df.loc[idx, urge_cols].head(20).rename(columns={'독촉 점수': '점수'}), use_container_width=True, hide_index=True, height=450)
                with tab_urge_low:
                    idx = valid_urge_df.sort_values(by=['독촉 점수', '총 점수'], ascending=[True, False]).index
                    st.dataframe(display_df.loc[idx, urge_cols].head(20).rename(columns={'독촉 점수': '점수'}), use_container_width=True, hide_index=True, height=450)

        with col_4b:
            st.subheader("😊 고객만족도 현황")
            tab_csat_top, tab_csat_low = st.tabs(["🔝 TOP 20 (점수 상위)", "🔻 LOW 20 (점수 하위)"])
            
            if '방문 대리점' in df.columns and '고객만족도 점수' in df.columns:
                csat_cols = [c for c in ['지사', '방문 대리점', '합계', '총건', '고객만족도 점수', '총 점수'] if c in display_df.columns]
                valid_csat_df = df.dropna(subset=['고객만족도 점수'])
                
                with tab_csat_top:
                    idx = valid_csat_df.sort_values(by=['고객만족도 점수', '총 점수'], ascending=[False, False]).index
                    st.dataframe(display_df.loc[idx, csat_cols].head(20).rename(columns={'고객만족도 점수': '점수'}), use_container_width=True, hide_index=True, height=450)
                with tab_csat_low:
                    idx = valid_csat_df.sort_values(by=['고객만족도 점수', '총 점수'], ascending=[True, False]).index
                    st.dataframe(display_df.loc[idx, csat_cols].head(20).rename(columns={'고객만족도 점수': '점수'}), use_container_width=True, hide_index=True, height=450)


        # ------------------ 4. 지사별 대리점 상세 조회 ------------------
        st.markdown("---")
        st.subheader("🏢 지사별 대리점 상세 현황 조회")
        
        branch_list = ["전체"] + list(df['지사'].dropna().unique()) if '지사' in df.columns else ["전체"]

        # [상세 조회 행 1] 조치정보입력율 & 미입력
        col_sel_1a, col_sel_1b = st.columns(2)

        with col_sel_1a:
            selected_branch = st.selectbox("조치정보입력율 대리점 조회 (지사 선택)", branch_list, key="select_act")
            filtered = display_df if selected_branch == "전체" else display_df[display_df['지사'] == selected_branch]
            
            if '방문 대리점' in df.columns and '조치입력 점수' in df.columns:
                target_cols = [c for c in ['지사', '방문 대리점', '총접수건', '미방문', '미입력', '방문 입력건', '입력율(%)', '조치입력 점수', '총 점수'] if c in display_df.columns]
                valid_idx = df.loc[filtered.index].dropna(subset=['조치입력 점수']).sort_values(by=['조치입력 점수', '총 점수'], ascending=[False, False]).index
                st.dataframe(filtered.loc[valid_idx, target_cols].rename(columns={'조치입력 점수': '점수'}), use_container_width=True, hide_index=True, height=430)

        with col_sel_1b:
            selected_branch = st.selectbox("미입력 대리점 조회 (지사 선택)", branch_list, key="select_unentered")
            filtered = display_df if selected_branch == "전체" else display_df[display_df['지사'] == selected_branch]
            
            if '방문 대리점' in df.columns and '불만 점수' in df.columns:
                target_cols = [c for c in ['지사', '방문 대리점', '총접수건', '미입력', '불만 점수', '총 점수'] if c in display_df.columns]
                valid_idx = df.loc[filtered.index].dropna(subset=['불만 점수']).sort_values(by=['불만 점수', '총 점수'], ascending=[False, False]).index
                st.dataframe(filtered.loc[valid_idx, target_cols].rename(columns={'불만 점수': '점수'}), use_container_width=True, hide_index=True, height=430)

        # [상세 조회 행 2] 약속시간입력율 & 평균처리시간
        col_sel_2a, col_sel_2b = st.columns(2)

        with col_sel_2a:
            selected_branch = st.selectbox("약속시간입력율 대리점 조회 (지사 선택)", branch_list, key="select_res")
            filtered = display_df if selected_branch == "전체" else display_df[display_df['지사'] == selected_branch]
            
            if '방문 대리점' in df.columns and '예약 점수' in df.columns:
                target_cols = [c for c in ['지사', '방문 대리점', '1시간이내예약건', '예약율(%)', '예약 점수', '총 점수'] if c in display_df.columns]
                valid_idx = df.loc[filtered.index].dropna(subset=['예약 점수']).sort_values(by=['예약 점수', '총 점수'], ascending=[False, False]).index
                st.dataframe(filtered.loc[valid_idx, target_cols].rename(columns={'예약 점수': '점수'}), use_container_width=True, hide_index=True, height=430)

        with col_sel_2b:
            selected_branch = st.selectbox("평균처리시간 대리점 조회 (지사 선택)", branch_list, key="select_time")
            filtered = display_df if selected_branch == "전체" else display_df[display_df['지사'] == selected_branch]
            
            if '방문 대리점' in df.columns and '처리시간 점수' in df.columns and s_col_name:
                target_cols = [c for c in ['지사', '방문 대리점', s_col_name, '처리시간 점수', '총 점수'] if c in display_df.columns]
                valid_idx = df.loc[filtered.index].dropna(subset=['처리시간 점수']).sort_values(by=['처리시간 점수', '총 점수'], ascending=[False, False]).index
                st.dataframe(filtered.loc[valid_idx, target_cols].rename(columns={'처리시간 점수': '점수'}), use_container_width=True, hide_index=True, height=430)

        # [상세 조회 행 3] 재방문율 & 서비스 불만율
        col_sel_3a, col_sel_3b = st.columns(2)

        with col_sel_3a:
            selected_branch = st.selectbox("재방문율 대리점 조회 (지사 선택)", branch_list, key="select_re")
            filtered = display_df if selected_branch == "전체" else display_df[display_df['지사'] == selected_branch]
            
            if '방문 대리점' in df.columns and '재방문 점수' in df.columns:
                target_cols = [c for c in ['지사', '방문 대리점', '재방문건수', '재방문율(%)', '재방문 점수', '총 점수'] if c in display_df.columns]
                valid_idx = df.loc[filtered.index].dropna(subset=['재방문 점수']).sort_values(by=['재방문 점수', '총 점수'], ascending=[False, False]).index
                st.dataframe(filtered.loc[valid_idx, target_cols].rename(columns={'재방문 점수': '점수'}), use_container_width=True, hide_index=True, height=430)

        with col_sel_3b:
            selected_branch = st.selectbox("서비스 불만율 대리점 조회 (지사 선택)", branch_list, key="select_dissatisfied")
            filtered = display_df if selected_branch == "전체" else display_df[display_df['지사'] == selected_branch]
                
            if '방문 대리점' in df.columns and '불만 점수' in df.columns:
                target_cols = [c for c in ['지사', '방문 대리점', '불만건수', '서비스불만율(%)', '불만 점수', '총 점수'] if c in display_df.columns]
                valid_idx = df.loc[filtered.index].dropna(subset=['불만 점수']).sort_values(by=['불만 점수', '총 점수'], ascending=[False, False]).index
                st.dataframe(filtered.loc[valid_idx, target_cols].rename(columns={'불만 점수': '점수'}), use_container_width=True, hide_index=True, height=430)

        # [상세 조회 행 4] 독촉율 & 고객만족도
        col_sel_4a, col_sel_4b = st.columns(2)

        with col_sel_4a:
            selected_branch = st.selectbox("독촉율 대리점 조회 (지사 선택)", branch_list, key="select_urge")
            filtered = display_df if selected_branch == "전체" else display_df[display_df['지사'] == selected_branch]
            
            if '방문 대리점' in df.columns and '독촉 점수' in df.columns:
                target_cols = [c for c in ['지사', '방문 대리점', '독촉건수', '독촉율(%)', '독촉 점수', '총 점수'] if c in display_df.columns]
                valid_idx = df.loc[filtered.index].dropna(subset=['독촉 점수']).sort_values(by=['독촉 점수', '총 점수'], ascending=[False, False]).index
                st.dataframe(filtered.loc[valid_idx, target_cols].rename(columns={'독촉 점수': '점수'}), use_container_width=True, hide_index=True, height=430)

        with col_sel_4b:
            selected_branch = st.selectbox("고객만족도 대리점 조회 (지사 선택)", branch_list, key="select_csat")
            filtered = display_df if selected_branch == "전체" else display_df[display_df['지사'] == selected_branch]
            
            if '방문 대리점' in df.columns and '고객만족도 점수' in df.columns:
                target_cols = [c for c in ['지사', '방문 대리점', '합계', '총건', '고객만족도 점수', '총 점수'] if c in display_df.columns]
                valid_idx = df.loc[filtered.index].dropna(subset=['고객만족도 점수']).sort_values(by=['고객만족도 점수', '총 점수'], ascending=[False, False]).index
                st.dataframe(filtered.loc[valid_idx, target_cols].rename(columns={'고객만족도 점수': '점수'}), use_container_width=True, hide_index=True, height=430)

        # ------------------ 5. 전체 대리점 상세 조회 ------------------
        st.markdown("---")
        st.subheader("🔍 대리점별 전체 항목 조회")
        
        clean_display_df = display_df.drop(columns=['_s_seconds'], errors='ignore')
        
        if '지사' in clean_display_df.columns:
            selected_branch = st.selectbox("지사를 선택하세요 (전체 조회)", ["전체"] + list(clean_display_df["지사"].dropna().unique()), key="select_all")
            filtered_df = clean_display_df if selected_branch == "전체" else clean_display_df[clean_display_df["지사"] == selected_branch]
            st.dataframe(filtered_df, use_container_width=True, height=520)
        else:
            st.dataframe(clean_display_df, use_container_width=True, height=520)

    except ValueError:
        st.error("⚠️ 업로드한 엑셀 파일 안에 '[평가]' 라는 이름의 시트(Sheet)가 존재하지 않습니다.")
    except Exception as e:
        st.error(f"⚠️ 데이터를 읽는 중 오류가 발생했습니다: {e}")
