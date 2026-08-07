import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, time

st.set_page_config(page_title="대리점 서비스 평가 대시보드", layout="wide")

# ------------------ 전체 폰트 및 UI 요소 확대 CSS 스타일 ------------------
st.markdown("""
    <style>
        /* 1. 전체 기본 폰트 크기 확대 */
        html, body, [class*="css"] {
            font-size: 28px !important;
        }
        
        /* 2. 제목 및 헤더 폰트 크기 */
        h1 { font-size: 3.4rem !important; }
        h2 { font-size: 2.8rem !important; }
        h3 { font-size: 2.4rem !important; }
        
        /* 3. 표(Dataframe) 내부 글자 크기 */
        .stDataFrame, .stDataFrame div[role="gridcell"] {
            font-size: 26px !important;
        }
        
        /* 4. 드롭다운(Selectbox) 본문 및 라벨 글자 크기 */
        div[data-baseweb="select"] * {
            font-size: 26px !important;
        }
        div[data-widget="selectbox"] label, .stSelectbox label {
            font-size: 30px !important;
            font-weight: bold !important;
        }

        /* 5. 파일 업로더 글자 크기 */
        .stFileUploader label {
            font-size: 28px !important;
        }
        .stFileUploader section {
            padding: 2rem !important;
        }

        /* 6. 탭(Tab) 버튼 폰트 및 여백 */
        button[data-baseweb="tab"] {
            font-size: 27px !important;
            padding: 12px 24px !important;
        }
        button[data-baseweb="tab"] div {
            font-size: 27px !important;
        }
    </style>
""", unsafe_allow_html=True)

st.title("📊 대리점 서비스 평가 및 데이터 입력 현황")

# 엑셀 파일 업로드
uploaded_file = st.file_uploader("월별 서비스 평가 엑셀 파일을 업로드하세요", type=["xlsx"])

# 시간 데이터를 초(seconds) 단위 숫자로 정규화하는 함수
def parse_time_to_seconds(val):
    if pd.isna(val) or val == "" or str(val).strip() == "":
        return None
    try:
        if isinstance(val, (time, datetime)):
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

# 시간 변환 함수 (HH:MM:SS -> X시간 Y분)
def format_time_duration(val):
    if pd.isna(val) or val == "" or str(val).strip() == "":
        return ""
    try:
        if isinstance(val, (time, datetime)):
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
        df = pd.read_excel(uploaded_file, sheet_name='평가', header=3)
        df.columns = df.columns.astype(str).str.replace('\n', '').str.strip()
        
        if '방문 대리점' in df.columns:
            df = df.dropna(subset=['방문 대리점'])

        cols = list(df.columns)
        if len(cols) > 12: cols[12] = '조치입력 점수'
        if len(cols) > 15: cols[15] = '예약 점수'
        if len(cols) > 20: cols[20] = '처리시간 점수'
        if len(cols) > 23: cols[23] = '재방문 점수'
        if len(cols) > 26: cols[26] = '불만 점수'
        if len(cols) > 29: cols[29] = '독촉 점수'
        if len(cols) > 32: cols[32] = '고객만족도 점수'
        df.columns = cols

        numeric_cols = [
            '총 점수', '불만 점수', '예약 점수', '처리시간 점수', '조치입력 점수', '재방문 점수', '독촉 점수', '고객만족도 점수',
            '총접수건', '총접수', '미방문', '미입력', '방문 입력건', '입력건', '입력율(%)', 
            '1시간이내예약건', '예약율(%)', '재방문건수', '재방문율(%)', '불만건수', '서비스불만율(%)', 
            '독촉건수', '독촉율(%)', '합계', '총건'
        ]
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')

        s_col_name = None
        if len(df.columns) > 18:
            s_col_name = df.columns[18]
            df['_s_seconds'] = df[s_col_name].apply(parse_time_to_seconds)

        if '지사' in df.columns:
            unique_branches = sorted(df['지사'].dropna().unique())
            palette = px.colors.qualitative.Plotly
            branch_color_map = {branch: palette[i % len(palette)] for i, branch in enumerate(unique_branches)}
            branch_order = {"지사": unique_branches}
        else:
            unique_branches = []
            branch_color_map = None
            branch_order = None

        # ------------------ 사이드바 지사 필터 연동 (1번 반영) ------------------
        st.sidebar.header("🔍 대시보드 필터")
        branch_options = ["전체"] + list(unique_branches)
        selected_sidebar_branch = st.sidebar.selectbox("조회할 지사를 선택하세요", branch_options, key="sidebar_branch")

        # 필터링된 데이터프레임 생성
        if selected_sidebar_branch != "전체" and '지사' in df.columns:
            filtered_main_df = df[df['지사'] == selected_sidebar_branch]
        else:
            filtered_main_df = df.copy()

        # ------------------ 상단 KPI 요약 카드 (2번 반영) ------------------
        st.markdown("### 📌 서비스 평가 핵심 요약")
        kpi1, kpi2, kpi3, kpi4 = st.columns(4)

        total_agencies = len(filtered_main_df)
        avg_score = filtered_main_df['총 점수'].mean() if '총 점수' in filtered_main_df.columns else 0

        # 지사별 평균 점수 산출
        if '지사' in df.columns and '총 점수' in df.columns:
            branch_means = df.dropna(subset=['총 점수']).groupby("지사")['총 점수'].mean()
            best_branch = branch_means.idxmax() if not branch_means.empty else "N/A"
            best_score = branch_means.max() if not branch_means.empty else 0
            worst_branch = branch_means.idxmin() if not branch_means.empty else "N/A"
            worst_score = branch_means.min() if not branch_means.empty else 0
        else:
            best_branch, best_score, worst_branch, worst_score = "N/A", 0, "N/A", 0

        kpi1.metric("총 대리점 수", f"{total_agencies:,} 개소")
        kpi2.metric("전체 평균 점수", f"{avg_score:.2f} 점" if pd.notnull(avg_score) else "N/A")
        kpi3.metric("최고 점수 지사", f"{best_branch}", f"{best_score:.2f}점" if best_score else "")
        kpi4.metric("최저 점수 지사", f"{worst_branch}", f"{worst_score:.2f}점" if worst_score else "")

        st.markdown("---")

        # ------------------ 1. 시각화 영역 ------------------
        left_col, right_col = st.columns(2)
        
        # [왼쪽] 지사별 평균 서비스 점수 (1번 이미지 수정 반영)
        with left_col:
            st.subheader("🏢 지사별 평균 서비스 점수")
            if '지사' in filtered_main_df.columns and '총 점수' in filtered_main_df.columns:
                branch_avg = filtered_main_df.dropna(subset=['총 점수']).groupby("지사", as_index=False)['총 점수'].mean()
                if not branch_avg.empty:
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
                    fig2.update_layout(
                        font=dict(size=21),
                        # X축 라벨 크기 4px 축소(20px -> 16px) 및 기울임 방지(tickangle=0)
                        xaxis=dict(tickfont=dict(size=16), tickangle=0),
                        yaxis=dict(tickfont=dict(size=20))
                    )
                    st.plotly_chart(fig2, use_container_width=True)
                else:
                    st.info("표시할 평균 데이터가 없습니다.")

        # [오른쪽] 총 점수 vs 총접수건 (2번 이미지 수정 반영)
        with right_col:
            st.subheader("💡 총 점수 vs 총접수건")
            total_cnt_col = '총접수건' if '총접수건' in filtered_main_df.columns else ('총접수' if '총접수' in filtered_main_df.columns else None)
            
            if total_cnt_col and '총 점수' in filtered_main_df.columns:
                scatter_df = filtered_main_df.dropna(subset=[total_cnt_col, '총 점수'])
                if not scatter_df.empty:
                    fig1 = px.scatter(
                        scatter_df, x=total_cnt_col, y="총 점수", 
                        color="지사" if "지사" in scatter_df.columns else None,
                        color_discrete_map=branch_color_map,
                        category_orders=branch_order,
                        hover_name="방문 대리점" if "방문 대리점" in scatter_df.columns else None,
                        title="총접수건 대비 총 점수 분포",
                        height=550
                    )
                    
                    fig1.update_traces(marker=dict(size=10))
                    
                    fig1.update_layout(
                        font=dict(size=21),
                        xaxis=dict(tickfont=dict(size=20)),
                        yaxis=dict(tickfont=dict(size=20)),
                        # 우측 범례 텍스트 크기 4px 축소 (24px -> 20px)
                        legend=dict(
                            font=dict(size=20),
                            title=dict(font=dict(size=20))
                        )
                    )
                    st.plotly_chart(fig1, use_container_width=True)
                else:
                    st.info("표시할 분포 데이터가 없습니다.")

        # ------------------ 2. 표 서식 적용 ------------------
        display_df = filtered_main_df.copy()
        if s_col_name:
            display_df[s_col_name] = display_df[s_col_name].apply(format_time_duration)

        percent_cols = ['입력율(%)', '방문율', '예약율(%)', '재방문율(%)', '서비스불만율(%)', '독촉율(%)']
        for p_col in percent_cols:
            if p_col in display_df.columns:
                display_df[p_col] = display_df[p_col].apply(
                    lambda x: f"{x*100:.2f}%" if pd.notnull(x) and isinstance(x, (int, float)) and x <= 1.0 else (f"{x:.2f}%" if pd.notnull(x) and isinstance(x, (int, float)) else "")
                )

        for col in display_df.select_dtypes(include=['float', 'float64']).columns:
            if col not in percent_cols and col != '_s_seconds':
                display_df[col] = display_df[col].apply(lambda x: f"{x:.2f}" if pd.notnull(x) else "")

        # ------------------ 3. TOP 20 & LOW 20 ------------------
        st.markdown("---")
        
        # [행 1] 조치정보입력율 & 미입력 건수
        col_1a, col_1b = st.columns(2)
        with col_1a:
            st.subheader("📋 조치정보입력율 현황")
            tab_act_top, tab_act_low = st.tabs(["🔝 TOP 20 (점수 상위)", "🔻 LOW 20 (점수 하위)"])
            if '방문 대리점' in filtered_main_df.columns and '조치입력 점수' in filtered_main_df.columns:
                act_cols = [c for c in ['지사', '방문 대리점', '총접수건', '미방문', '미입력', '방문 입력건', '입력율(%)', '조치입력 점수', '총 점수'] if c in display_df.columns]
                valid_act_df = filtered_main_df.dropna(subset=['조치입력 점수'])
                with tab_act_top:
                    idx = valid_act_df.sort_values(by=['조치입력 점수', '총 점수'], ascending=[False, False]).index
                    st.dataframe(display_df.loc[idx, act_cols].head(20).rename(columns={'조치입력 점수': '점수'}), use_container_width=True, hide_index=True, height=450)
                with tab_act_low:
                    idx = valid_act_df.sort_values(by=['조치입력 점수', '총 점수'], ascending=[True, False]).index
                    st.dataframe(display_df.loc[idx, act_cols].head(20).rename(columns={'조치입력 점수': '점수'}), use_container_width=True, hide_index=True, height=450)

        with col_1b:
            st.subheader("📉 미입력 건수 현황")
            tab_unentered_top, tab_unentered_low = st.tabs(["🔝 TOP 20 (점수 상위)", "🔻 LOW 20 (점수 하위)"])
            if '방문 대리점' in filtered_main_df.columns and '불만 점수' in filtered_main_df.columns:
                unentered_cols = [c for c in ['지사', '방문 대리점', '총접수건', '미입력', '불만 점수', '총 점수'] if c in display_df.columns]
                valid_unentered_df = filtered_main_df.dropna(subset=['불만 점수'])
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
            if '방문 대리점' in filtered_main_df.columns and '예약 점수' in filtered_main_df.columns:
                reservation_cols = [c for c in ['지사', '방문 대리점', '1시간이내예약건', '예약율(%)', '예약 점수', '총 점수'] if c in display_df.columns]
                valid_res_df = filtered_main_df.dropna(subset=['예약 점수'])
                with tab_res_top:
                    idx = valid_res_df.sort_values(by=['예약 점수', '총 점수'], ascending=[False, False]).index
                    st.dataframe(display_df.loc[idx, reservation_cols].head(20).rename(columns={'예약 점수': '점수'}), use_container_width=True, hide_index=True, height=450)
                with tab_res_low:
                    idx = valid_res_df.sort_values(by=['예약 점수', '총 점수'], ascending=[True, False]).index
                    st.dataframe(display_df.loc[idx, reservation_cols].head(20).rename(columns={'예약 점수': '점수'}), use_container_width=True, hide_index=True, height=450)

        with col_2b:
            st.subheader("⏱️ 평균처리시간 현황")
            tab_time_top, tab_time_low = st.tabs(["🔝 TOP 20 (점수 상위)", "🔻 LOW 20 (점수 하위)"])
            if '방문 대리점' in filtered_main_df.columns and '처리시간 점수' in filtered_main_df.columns and s_col_name:
                time_cols = [c for c in ['지사', '방문 대리점', s_col_name, '처리시간 점수', '총 점수'] if c in display_df.columns]
                valid_time_df = filtered_main_df.dropna(subset=['처리시간 점수'])
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
            if '방문 대리점' in filtered_main_df.columns and '재방문 점수' in filtered_main_df.columns:
                re_cols = [c for c in ['지사', '방문 대리점', '재방문건수', '재방문율(%)', '재방문 점수', '총 점수'] if c in display_df.columns]
                valid_re_df = filtered_main_df.dropna(subset=['재방문 점수'])
                with tab_re_top:
                    idx = valid_re_df.sort_values(by=['재방문 점수', '총 점수'], ascending=[False, False]).index
                    st.dataframe(display_df.loc[idx, re_cols].head(20).rename(columns={'재방문 점수': '점수'}), use_container_width=True, hide_index=True, height=450)
                with tab_re_low:
                    idx = valid_re_df.sort_values(by=['재방문 점수', '총 점수'], ascending=[True, False]).index
                    st.dataframe(display_df.loc[idx, re_cols].head(20).rename(columns={'재방문 점수': '점수'}), use_container_width=True, hide_index=True, height=450)

        with col_3b:
            st.subheader("⚠️ 서비스 불만율 현황")
            tab_dissat_top, tab_dissat_low = st.tabs(["🔝 TOP 20 (점수 상위)", "🔻 LOW 20 (점수 하위)"])
            if '방문 대리점' in filtered_main_df.columns and '불만 점수' in filtered_main_df.columns:
                dissatisfied_cols = [c for c in ['지사', '방문 대리점', '불만건수', '서비스불만율(%)', '불만 점수', '총 점수'] if c in display_df.columns]
                valid_dissat_df = filtered_main_df.dropna(subset=['불만 점수'])
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
            if '방문 대리점' in filtered_main_df.columns and '독촉 점수' in filtered_main_df.columns:
                urge_cols = [c for c in ['지사', '방문 대리점', '독촉건수', '독촉율(%)', '독촉 점수', '총 점수'] if c in display_df.columns]
                valid_urge_df = filtered_main_df.dropna(subset=['독촉 점수'])
                with tab_urge_top:
                    idx = valid_urge_df.sort_values(by=['독촉 점수', '총 점수'], ascending=[False, False]).index
                    st.dataframe(display_df.loc[idx, urge_cols].head(20).rename(columns={'독촉 점수': '점수'}), use_container_width=True, hide_index=True, height=450)
                with tab_urge_low:
                    idx = valid_urge_df.sort_values(by=['독촉 점수', '총 점수'], ascending=[True, False]).index
                    st.dataframe(display_df.loc[idx, urge_cols].head(20).rename(columns={'독촉 점수': '점수'}), use_container_width=True, hide_index=True, height=450)

        with col_4b:
            st.subheader("😊 고객만족도 현황")
            tab_csat_top, tab_csat_low = st.tabs(["🔝 TOP 20 (점수 상위)", "🔻 LOW 20 (점수 하위)"])
            if '방문 대리점' in filtered_main_df.columns and '고객만족도 점수' in filtered_main_df.columns:
                csat_cols = [c for c in ['지사', '방문 대리점', '합계', '총건', '고객만족도 점수', '총 점수'] if c in display_df.columns]
                valid_csat_df = filtered_main_df.dropna(subset=['고객만족도 점수'])
                with tab_csat_top:
                    idx = valid_csat_df.sort_values(by=['고객만족도 점수', '총 점수'], ascending=[False, False]).index
                    st.dataframe(display_df.loc[idx, csat_cols].head(20).rename(columns={'고객만족도 점수': '점수'}), use_container_width=True, hide_index=True, height=450)
                with tab_csat_low:
                    idx = valid_csat_df.sort_values(by=['고객만족도 점수', '총 점수'], ascending=[True, False]).index
                    st.dataframe(display_df.loc[idx, csat_cols].head(20).rename(columns={'고객만족도 점수': '점수'}), use_container_width=True, hide_index=True, height=450)

        # ------------------ 4. 지사별 대리점 상세 조회 ------------------
        st.markdown("---")
        st.subheader("🏢 지사별 대리점 상세 현황 조회")
        
        branch_list = ["전체"] + list(unique_branches)

        col_sel_1a, col_sel_1b = st.columns(2)
        with col_sel_1a:
            selected_branch = st.selectbox("조치정보입력율 대리점 조회 (지사 선택)", branch_list, key="select_act")
            filtered = display_df if selected_branch == "전체" else display_df[display_df['지사'] == selected_branch]
            if '방문 대리점' in df.columns and '조치입력 점수' in df.columns:
                target_cols = [c for c in ['지사', '방문 대리점', '총접수건', '미방문', '미입력', '방문 입력건', '입력율(%)', '조치입력 점수', '총 점수'] if c in display_df.columns]
                valid_idx = filtered.dropna(subset=['조치입력 점수']).sort_values(by=['조치입력 점수', '총 점수'], ascending=[False, False]).index
                st.dataframe(filtered.loc[valid_idx, target_cols].rename(columns={'조치입력 점수': '점수'}), use_container_width=True, hide_index=True, height=430)

        with col_sel_1b:
            selected_branch = st.selectbox("미입력 대리점 조회 (지사 선택)", branch_list, key="select_unentered")
            filtered = display_df if selected_branch == "전체" else display_df[display_df['지사'] == selected_branch]
            if '방문 대리점' in df.columns and '불만 점수' in df.columns:
                target_cols = [c for c in ['지사', '방문 대리점', '총접수건', '미입력', '불만 점수', '총 점수'] if c in display_df.columns]
                valid_idx = filtered.dropna(subset=['불만 점수']).sort_values(by=['불만 점수', '총 점수'], ascending=[False, False]).index
                st.dataframe(filtered.loc[valid_idx, target_cols].rename(columns={'불만 점수': '점수'}), use_container_width=True, hide_index=True, height=430)

        col_sel_2a, col_sel_2b = st.columns(2)
        with col_sel_2a:
            selected_branch = st.selectbox("약속시간입력율 대리점 조회 (지사 선택)", branch_list, key="select_res")
            filtered = display_df if selected_branch == "전체" else display_df[display_df['지사'] == selected_branch]
            if '방문 대리점' in df.columns and '예약 점수' in df.columns:
                target_cols = [c for c in ['지사', '방문 대리점', '1시간이내예약건', '예약율(%)', '예약 점수', '총 점수'] if c in display_df.columns]
                valid_idx = filtered.dropna(subset=['예약 점수']).sort_values(by=['예약 점수', '총 점수'], ascending=[False, False]).index
                st.dataframe(filtered.loc[valid_idx, target_cols].rename(columns={'예약 점수': '점수'}), use_container_width=True, hide_index=True, height=430)

        with col_sel_2b:
            selected_branch = st.selectbox("평균처리시간 대리점 조회 (지사 선택)", branch_list, key="select_time")
            filtered = display_df if selected_branch == "전체" else display_df[display_df['지사'] == selected_branch]
            if '방문 대리점' in df.columns and '처리시간 점수' in df.columns and s_col_name:
                target_cols = [c for c in ['지사', '방문 대리점', s_col_name, '처리시간 점수', '총 점수'] if c in display_df.columns]
                valid_idx = filtered.dropna(subset=['처리시간 점수']).sort_values(by=['처리시간 점수', '총 점수'], ascending=[False, False]).index
                st.dataframe(filtered.loc[valid_idx, target_cols].rename(columns={'처리시간 점수': '점수'}), use_container_width=True, hide_index=True, height=430)

        col_sel_3a, col_sel_3b = st.columns(2)
        with col_sel_3a:
            selected_branch = st.selectbox("재방문율 대리점 조회 (지사 선택)", branch_list, key="select_re")
            filtered = display_df if selected_branch == "전체" else display_df[display_df['지사'] == selected_branch]
            if '방문 대리점' in df.columns and '재방문 점수' in df.columns:
                target_cols = [c for c in ['지사', '방문 대리점', '재방문건수', '재방문율(%)', '재방문 점수', '총 점수'] if c in display_df.columns]
                valid_idx = filtered.dropna(subset=['재방문 점수']).sort_values(by=['재방문 점수', '총 점수'], ascending=[False, False]).index
                st.dataframe(filtered.loc[valid_idx, target_cols].rename(columns={'재방문 점수': '점수'}), use_container_width=True, hide_index=True, height=430)

        with col_sel_3b:
            selected_branch = st.selectbox("서비스 불만율 대리점 조회 (지사 선택)", branch_list, key="select_dissatisfied")
            filtered = display_df if selected_branch == "전체" else display_df[display_df['지사'] == selected_branch]
            if '방문 대리점' in df.columns and '불만 점수' in df.columns:
                target_cols = [c for c in ['지사', '방문 대리점', '불만건수', '서비스불만율(%)', '불만 점수', '총 점수'] if c in display_df.columns]
                valid_idx = filtered.dropna(subset=['불만 점수']).sort_values(by=['불만 점수', '총 점수'], ascending=[False, False]).index
                st.dataframe(filtered.loc[valid_idx, target_cols].rename(columns={'불만 점수': '점수'}), use_container_width=True, hide_index=True, height=430)

        col_sel_4a, col_sel_4b = st.columns(2)
        with col_sel_4a:
            selected_branch = st.selectbox("독촉율 대리점 조회 (지사 선택)", branch_list, key="select_urge")
            filtered = display_df if selected_branch == "전체" else display_df[display_df['지사'] == selected_branch]
            if '방문 대리점' in df.columns and '독촉 점수' in df.columns:
                target_cols = [c for c in ['지사', '방문 대리점', '독촉건수', '독촉율(%)', '독촉 점수', '총 점수'] if c in display_df.columns]
                valid_idx = filtered.dropna(subset=['독촉 점수']).sort_values(by=['독촉 점수', '총 점수'], ascending=[False, False]).index
                st.dataframe(filtered.loc[valid_idx, target_cols].rename(columns={'독촉 점수': '점수'}), use_container_width=True, hide_index=True, height=430)

        with col_sel_4b:
            selected_branch = st.selectbox("고객만족도 대리점 조회 (지사 선택)", branch_list, key="select_csat")
            filtered = display_df if selected_branch == "전체" else display_df[display_df['지사'] == selected_branch]
            if '방문 대리점' in df.columns and '고객만족도 점수' in df.columns:
                target_cols = [c for c in ['지사', '방문 대리점', '합계', '총건', '고객만족도 점수', '총 점수'] if c in display_df.columns]
                valid_idx = filtered.dropna(subset=['고객만족도 점수']).sort_values(by=['고객만족도 점수', '총 점수'], ascending=[False, False]).index
                st.dataframe(filtered.loc[valid_idx, target_cols].rename(columns={'고객만족도 점수': '점수'}), use_container_width=True, hide_index=True, height=430)

        # ------------------ 5. 전체 대리점 조회 ------------------
        st.markdown("---")
        st.subheader("🔍 대리점별 전체 항목 조회")
        clean_display_df = display_df.drop(columns=['_s_seconds'], errors='ignore')
        if '지사' in clean_display_df.columns:
            selected_branch = st.selectbox("지사를 선택하세요 (전체 조회)", ["전체"] + list(unique_branches), key="select_all")
            filtered_df = clean_display_df if selected_branch == "전체" else clean_display_df[clean_display_df["지사"] == selected_branch]
            st.dataframe(filtered_df, use_container_width=True, height=520)
        else:
            st.dataframe(clean_display_df, use_container_width=True, height=520)

    except Exception as e:
        st.error(f"⚠️ 데이터를 읽는 중 오류가 발생했습니다: {e}")
