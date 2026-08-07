import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
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
        h1 { font-size: 3.0rem !important; }
        h2 { font-size: 2.8rem !important; }
        h3 { font-size: 2.4rem !important; }
        
        /* 3. 표(Dataframe) 내부 글자 크기 */
        .stDataFrame, .stDataFrame div[role="gridcell"] {
            font-size: 26px !important;
        }
        
        /* 4. 드롭다운 및 라디오 버튼 글자 크기 */
        div[data-baseweb="select"] * {
            font-size: 24px !important;
        }
        div[data-widget="selectbox"] label, .stSelectbox label, .stRadio label {
            font-size: 22px !important;
            font-weight: bold !important;
        }
        div[role="radiogroup"] label span {
            font-size: 24px !important;
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
            font-size: 24px !important;
            padding: 10px 20px !important;
        }
        button[data-baseweb="tab"] div {
            font-size: 24px !important;
        }
    </style>
""", unsafe_allow_html=True)

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

# 사이드바에는 화면 전환 메뉴만 단순 배치
st.sidebar.header("📌 대시보드 메뉴")
view_mode = st.sidebar.radio("화면 선택", ["📊 전체/지사 대시보드", "👤 대리점별 상세 리포트"])

# 엑셀 파일 업로드
uploaded_file = st.file_uploader("월별 서비스 평가 엑셀 파일을 업로드하세요", type=["xlsx"])

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

        if '조치입력 점수' in df.columns:
            df['조치정보입력율 점수'] = df['조치입력 점수']

        numeric_cols = [
            '총 점수', '불만 점수', '예약 점수', '처리시간 점수', '조치입력 점수', '조치정보입력율 점수', '재방문 점수', '독촉 점수', '고객만족도 점수',
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
            branch_color_map = {}
            branch_order = None

        # ------------------ 상단 타이틀 및 메인 필터 배치 ------------------
        title_col, filter_col1, filter_col2 = st.columns([2.2, 1, 1])
        
        with title_col:
            st.title("📊 대리점 서비스 평가 현황")

        branch_options = ["전체"] + list(unique_branches)
        
        with filter_col1:
            selected_branch = st.selectbox("🔍 조회할 지사 선택", branch_options, key="main_branch")

        if selected_branch != "전체" and '지사' in df.columns:
            filtered_agencies = sorted(df[df['지사'] == selected_branch]['방문 대리점'].dropna().unique())
        else:
            filtered_agencies = sorted(df['방문 대리점'].dropna().unique())

        with filter_col2:
            selected_agency = st.selectbox("🏢 조회할 대리점 선택", filtered_agencies, key="main_agency")

        st.markdown("---")

        # ------------------ 화면 1: 전체 / 지사 대시보드 ------------------
        if view_mode == "📊 전체/지사 대시보드":
            if selected_branch != "전체" and '지사' in df.columns:
                filtered_main_df = df[df['지사'] == selected_branch]
            else:
                filtered_main_df = df.copy()

            st.markdown("### 📌 서비스 평가 핵심 요약")
            kpi1, kpi2, kpi3, kpi4 = st.columns(4)

            total_agencies = len(filtered_main_df)
            avg_score = filtered_main_df['총 점수'].mean() if '총 점수' in filtered_main_df.columns else 0

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

            left_col, right_col = st.columns(2)
            with left_col:
                st.subheader("🏢 지사별 평균 서비스 점수")
                if '지사' in filtered_main_df.columns and '총 점수' in filtered_main_df.columns:
                    branch_avg = filtered_main_df.dropna(subset=['총 점수']).groupby("지사", as_index=False)['총 점수'].mean()
                    if not branch_avg.empty:
                        fig2 = px.bar(
                            branch_avg, x="지사", y="총 점수", color="지사",
                            color_discrete_map=branch_color_map, category_orders=branch_order,
                            text_auto='.2f', title="지사별 서비스 평가 평균 점수 (총 점수)", height=550
                        )
                        fig2.update_layout(
                            font=dict(size=21),
                            xaxis=dict(tickfont=dict(size=16), tickangle=0),
                            yaxis=dict(tickfont=dict(size=20))
                        )
                        st.plotly_chart(fig2, use_container_width=True)

            with right_col:
                st.subheader("💡 총 점수 vs 총접수건")
                total_cnt_col = '총접수건' if '총접수건' in filtered_main_df.columns else ('총접수' if '총접수' in filtered_main_df.columns else None)
                if total_cnt_col and '총 점수' in filtered_main_df.columns:
                    scatter_df = filtered_main_df.dropna(subset=[total_cnt_col, '총 점수'])
                    if not scatter_df.empty:
                        fig1 = px.scatter(
                            scatter_df, x=total_cnt_col, y="총 점수",
                            color="지사" if "지사" in scatter_df.columns else None,
                            color_discrete_map=branch_color_map, category_orders=branch_order,
                            hover_name="방문 대리점" if "방문 대리점" in scatter_df.columns else None,
                            title="총접수건 대비 총 점수 분포", height=550
                        )
                        fig1.update_traces(marker=dict(size=10))
                        fig1.update_layout(
                            font=dict(size=21),
                            xaxis=dict(tickfont=dict(size=20)),
                            yaxis=dict(tickfont=dict(size=20)),
                            legend=dict(font=dict(size=20), title=dict(font=dict(size=20)))
                        )
                        st.plotly_chart(fig1, use_container_width=True)

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

            # ------------------ 8개 항목 전체 현황 (8개 탭) ------------------
            st.markdown("---")
            st.subheader("📋 8개 평가 지표별 세부 현황 (TOP 20 & LOW 20)")
            
            tabs = st.tabs([
                "1. 조치입력 점수", "2. 조치정보입력율", "3. 약속시간 점수", "4. 처리시간 점수",
                "5. 재방문 점수", "6. 불만 점수", "7. 독촉 점수", "8. 고객만족도 점수"
            ])

            indicators_info = [
                ("조치입력 점수", ['지사', '방문 대리점', '총접수건', '조치입력 점수', '총 점수']),
                ("입력율(%)", ['지사', '방문 대리점', '총접수건', '미입력', '입력율(%)', '조치입력 점수', '총 점수']),
                ("예약 점수", ['지사', '방문 대리점', '총접수건', '1시간이내예약건', '예약율(%)', '예약 점수', '총 점수']),
                ("처리시간 점수", ['지사', '방문 대리점', '총접수건', s_col_name, '처리시간 점수', '총 점수'] if s_col_name else ['지사', '방문 대리점', '처리시간 점수', '총 점수']),
                ("재방문 점수", ['지사', '방문 대리점', '총접수건', '재방문건수', '재방문율(%)', '재방문 점수', '총 점수']),
                ("불만 점수", ['지사', '방문 대리점', '총접수건', '불만건수', '서비스불만율(%)', '불만 점수', '총 점수']),
                ("독촉 점수", ['지사', '방문 대리점', '총접수건', '독촉건수', '독촉율(%)', '독촉 점수', '총 점수']),
                ("고객만족도 점수", ['지사', '방문 대리점', '총접수건', '고객만족도 점수', '총 점수'])
            ]

            for i, (col_key, target_cols) in enumerate(indicators_info):
                with tabs[i]:
                    sub_cols = [c for c in target_cols if c in display_df.columns]
                    if col_key in filtered_main_df.columns:
                        sort_col = col_key
                        valid_sub_df = filtered_main_df.dropna(subset=[sort_col])
                        
                        top_tab, low_tab = st.tabs(["🔝 TOP 20 (상위)", "🔻 LOW 20 (하위)"])
                        with top_tab:
                            idx_top = valid_sub_df.sort_values(by=[sort_col, '총 점수'], ascending=[False, False]).index
                            st.dataframe(display_df.loc[idx_top, sub_cols].head(20), use_container_width=True, hide_index=True, height=400)
                        with low_tab:
                            idx_low = valid_sub_df.sort_values(by=[sort_col, '총 점수'], ascending=[True, False]).index
                            st.dataframe(display_df.loc[idx_low, sub_cols].head(20), use_container_width=True, hide_index=True, height=400)
                    else:
                        st.info(f"'{col_key}' 관련 데이터 항목을 찾을 수 없습니다.")

            st.markdown("---")
            st.subheader("🔍 대리점별 전체 항목 조회")
            clean_display_df = display_df.drop(columns=['_s_seconds'], errors='ignore')
            st.dataframe(clean_display_df, use_container_width=True, height=520)

        # ------------------ 화면 2: 대리점별 상세 리포트 ------------------
        elif view_mode == "👤 대리점별 상세 리포트":
            if not selected_agency:
                st.warning("상단 검색 창에서 대리점을 선택해 주세요.")
            else:
                agency_row = df[df['방문 대리점'] == selected_agency]
                
                if agency_row.empty:
                    st.info("선택한 대리점의 데이터가 존재하지 않습니다.")
                else:
                    agency_data = agency_row.iloc[0]
                    agency_branch = agency_data.get('지사', '미지정')
                    
                    st.markdown(f"## 🏢 [{agency_branch}] **{selected_agency}** 평가 상세 리포트")
                    
                    total_agencies_count = len(df)
                    overall_rank = df['총 점수'].rank(ascending=False, method='min')[agency_row.index[0]] if '총 점수' in df.columns else None
                    
                    branch_agencies = df[df['지사'] == agency_branch] if agency_branch != '미지정' else df
                    branch_agencies_count = len(branch_agencies)
                    branch_rank = branch_agencies['총 점수'].rank(ascending=False, method='min')[agency_row.index[0]] if '총 점수' in df.columns else None

                    # 1. 상단 요약 카드
                    c1, c2, c3, c4 = st.columns(4)
                    c1.metric("총 점수", f"{agency_data.get('총 점수', 0):.2f} 점")
                    c2.metric("지사 내 순위", f"{int(branch_rank)}위 / {branch_agencies_count}개" if pd.notnull(branch_rank) else "N/A")
                    c3.metric("전체 순위", f"{int(overall_rank)}위 / {total_agencies_count}개" if pd.notnull(overall_rank) else "N/A")
                    
                    tot_receipt = agency_data.get('총접수건', agency_data.get('총접수', 0))
                    c4.metric("총 접수건수", f"{int(tot_receipt):,} 건" if pd.notnull(tot_receipt) else "0 건")

                    st.markdown("---")

                    # 2. 8개 평가 지표 현황 카드
                    st.markdown("### 📋 8개 평가 지표별 세부 성과 현황")
                    
                    m1, m2, m3, m4 = st.columns(4)
                    m1.metric("1. 조치입력 점수", f"{agency_data.get('조치입력 점수', 0):.2f} 점")

                    act_rate = agency_data.get('입력율(%)', 0)
                    act_rate_str = f"{act_rate*100:.1f}%" if pd.notnull(act_rate) and act_rate <= 1.0 else f"{act_rate:.1f}%"
                    unentered_cnt = agency_data.get('미입력', 0)
                    unentered_str = f"{int(unentered_cnt):,}건" if pd.notnull(unentered_cnt) else "0건"
                    m2.metric("2. 조치정보입력율", f"{agency_data.get('조치정보입력율 점수', 0):.2f} 점", f"입력율: {act_rate_str} (미입력: {unentered_str})")

                    res_rate = agency_data.get('예약율(%)', 0)
                    res_rate_str = f"{res_rate*100:.1f}%" if pd.notnull(res_rate) and res_rate <= 1.0 else f"{res_rate:.1f}%"
                    m3.metric("3. 약속시간 점수", f"{agency_data.get('예약 점수', 0):.2f} 점", f"예약율: {res_rate_str}")

                    avg_t = agency_data.get(s_col_name, "") if s_col_name else ""
                    m4.metric("4. 처리시간 점수", f"{agency_data.get('처리시간 점수', 0):.2f} 점", f"평균: {format_time_duration(avg_t)}")

                    m5, m6, m7, m8 = st.columns(4)
                    re_rate = agency_data.get('재방문율(%)', 0)
                    re_rate_str = f"{re_rate*100:.1f}%" if pd.notnull(re_rate) and re_rate <= 1.0 else f"{re_rate:.1f}%"
                    m5.metric("5. 재방문 점수", f"{agency_data.get('재방문 점수', 0):.2f} 점", f"재방문율: {re_rate_str}")

                    dis_rate = agency_data.get('서비스불만율(%)', 0)
                    dis_rate_str = f"{dis_rate*100:.1f}%" if pd.notnull(dis_rate) and dis_rate <= 1.0 else f"{dis_rate:.1f}%"
                    m6.metric("6. 불만 점수", f"{agency_data.get('불만 점수', 0):.2f} 점", f"불만율: {dis_rate_str}")

                    urg_rate = agency_data.get('독촉율(%)', 0)
                    urg_rate_str = f"{urg_rate*100:.1f}%" if pd.notnull(urg_rate) and urg_rate <= 1.0 else f"{urg_rate:.1f}%"
                    m7.metric("7. 독촉 점수", f"{agency_data.get('독촉 점수', 0):.2f} 점", f"독촉율: {urg_rate_str}")

                    m8.metric("8. 고객만족도 점수", f"{agency_data.get('고객만족도 점수', 0):.2f} 점")

                    st.markdown("---")

                    # 3. 평균 대비 세부 항목 점수 비교 차트
                    st.markdown("### 📊 평균 대비 세부 항목 점수 비교")
                    
                    score_cols = [
                        '조치입력 점수', '조치정보입력율 점수', '예약 점수', 
                        '처리시간 점수', '재방문 점수', '불만 점수', '독촉 점수', '고객만족도 점수'
                    ]
                    
                    col_display_names = [
                        '조치입력 점수', '조치정보입력율', '예약 점수', 
                        '처리시간 점수', '재방문 점수', '불만 점수', '독촉 점수', '고객만족도 점수'
                    ]

                    available_indices = [i for i, c in enumerate(score_cols) if c in df.columns]
                    x_labels = [col_display_names[i] for i in available_indices]
                    actual_cols = [score_cols[i] for i in available_indices]

                    if actual_cols:
                        agency_scores = [agency_data.get(c, 0) for c in actual_cols]
                        branch_avg_scores = [branch_agencies[c].mean() for c in actual_cols]
                        total_avg_scores = [df[c].mean() for c in actual_cols]

                        all_vals = total_avg_scores + branch_avg_scores + agency_scores
                        max_y = (max(all_vals) * 1.18) if all_vals else 25

                        branch_color = branch_color_map.get(agency_branch, '#F59E0B')

                        fig_comp = go.Figure()

                        fig_comp.add_trace(go.Bar(
                            x=x_labels,
                            y=total_avg_scores,
                            name="전체 평균",
                            marker_color='#94A3B8',
                            text=[f"{v:.2f}" for v in total_avg_scores],
                            textposition='outside',
                            textfont=dict(size=15, weight='bold')
                        ))

                        fig_comp.add_trace(go.Bar(
                            x=x_labels,
                            y=branch_avg_scores,
                            name=f"{agency_branch} 평균",
                            marker_color=branch_color,
                            text=[f"{v:.2f}" for v in branch_avg_scores],
                            textposition='outside',
                            textfont=dict(size=15, weight='bold')
                        ))

                        fig_comp.add_trace(go.Bar(
                            x=x_labels,
                            y=agency_scores,
                            name=f"{selected_agency}",
                            marker_color='#2563EB',
                            text=[f"{v:.2f}" for v in agency_scores],
                            textposition='outside',
                            textfont=dict(size=16, weight='bold')
                        ))

                        fig_comp.update_layout(
                            barmode='group',
                            bargap=0.20,
                            bargroupgap=0.06,
                            title=dict(
                                text=f"<b>[{selected_agency}] 주요 항목별 점수 비교</b>",
                                font=dict(size=24, color='#1E293B')
                            ),
                            height=580,
                            margin=dict(l=20, r=20, t=60, b=40),
                            plot_bgcolor='white',
                            paper_bgcolor='white',
                            font=dict(size=18, family="Malgun Gothic, Apple SD Gothic Neo, sans-serif"),
                            xaxis=dict(
                                tickfont=dict(size=16, color='#334155'),
                                showgrid=False
                            ),
                            yaxis=dict(
                                title="점수",
                                title_font=dict(size=18, color='#334155'),
                                tickfont=dict(size=16, color='#64748B'),
                                gridcolor='#F1F5F9',
                                range=[0, max_y]
                            ),
                            legend=dict(
                                orientation="h",
                                yanchor="bottom",
                                y=1.02,
                                xanchor="right",
                                x=1,
                                font=dict(size=17),
                                bgcolor='rgba(255,255,255,0.8)'
                            )
                        )
                        st.plotly_chart(fig_comp, use_container_width=True)

    except Exception as e:
        st.error(f"⚠️ 데이터를 읽는 중 오류가 발생했습니다: {e}")
