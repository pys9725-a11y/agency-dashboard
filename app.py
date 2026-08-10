from datetime import datetime, time
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# ------------------ 기본 페이지 설정 ------------------
st.set_page_config(page_title="대리점 서비스 평가 대시보드", layout="wide")

# ------------------ CSS 스타일링 (33% 배율 전용) ------------------
st.markdown(
    """
    <style>
        header[data-testid="stHeader"] { visibility: hidden; height: 0rem; }
        footer { visibility: hidden; }
        [data-testid="manage-app-button"], .stAppViewerBadge, div[class*="viewerBadge"] { display: none !important; }

        /* 전체 기본 폰트 및 Selectbox, Tab 강제 확대 */
        html, body, [class*="css"], .stSelectbox label, .stSelectbox div {
            font-size: 36px !important;
        }
        
        /* Selectbox 내부 텍스트 크기 */
        div[data-baseweb="select"] * {
            font-size: 32px !important;
        }

        /* 탭 버튼 폰트 크기 */
        button[data-baseweb="tab"] div {
            font-size: 32px !important;
            font-weight: bold !important;
        }

        /* 표(Dataframe) 내부 글자 및 헤더 강제 크기 확대 */
        .stDataFrame [data-testid="stTable"] div, .stDataFrame div[role="gridcell"], .stDataFrame th {
            font-size: 32px !important;
            line-height: 1.5 !important;
        }
    </style>
""",
    unsafe_allow_html=True,
)


# ------------------ 유틸리티 함수 ------------------
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


def apply_column_alignment_and_style(styler, df_cols):
    left_cols = [c for c in ["지사", "방문 대리점"] if c in df_cols]
    right_cols = [
        c
        for c in [
            "총접수건",
            "미입력",
            "1시간이내예약건",
            "재방문건수",
            "불만건수",
            "독촉건수",
        ]
        if c in df_cols
    ]

    for c in df_cols:
        if ("시간" in c or "처리" in c) and c not in ["처리시간 점수"]:
            if c not in right_cols and c not in left_cols:
                right_cols.append(c)

    center_cols = [
        c for c in df_cols if c not in left_cols and c not in right_cols
    ]

    if left_cols:
        styler = styler.set_properties(
            subset=left_cols, **{"text-align": "left"}
        )
    if right_cols:
        styler = styler.set_properties(
            subset=right_cols, **{"text-align": "right"}
        )
    if center_cols:
        styler = styler.set_properties(
            subset=center_cols, **{"text-align": "center"}
        )

    return styler


def apply_highlight_styler(df_sub, target_col, mode="top"):
    def style_cell(val):
        if mode == "top":
            return (
                "background-color: #e6f4ea; color: #137333; font-weight: bold;"
            )
        elif mode == "low":
            return (
                "background-color: #fce8e6; color: #c5221f; font-weight: bold;"
            )
        return ""

    styler = df_sub.style
    if target_col in df_sub.columns:
        styler = styler.map(style_cell, subset=[target_col])

    styler = apply_column_alignment_and_style(styler, df_sub.columns)
    return styler


def apply_overall_table_styler(df_input):
    def highlight_total_score(val):
        try:
            num = float(str(val).replace(",", "").replace("%", ""))
            if num >= 90:
                return "background-color: #e6f4ea; color: #137333; font-weight: bold;"
            elif num < 70:
                return "background-color: #fce8e6; color: #c5221f; font-weight: bold;"
        except ValueError:
            pass
        return ""

    styler = df_input.style
    if "총 점수" in df_input.columns:
        styler = styler.map(highlight_total_score, subset=["총 점수"])

    styler = apply_column_alignment_and_style(styler, df_input.columns)
    return styler


# ------------------ 애플리케이션 메인 로직 ------------------
uploaded_file = st.file_uploader(
    "월별 서비스 평가 엑셀 파일을 업로드하세요", type=["xlsx"]
)

if uploaded_file:
    try:
        df = pd.read_excel(uploaded_file, sheet_name="평가", header=3)
        df.columns = df.columns.astype(str).str.replace("\n", "").str.strip()

        if "방문 대리점" in df.columns:
            df = df.dropna(subset=["방문 대리점"])

        cols = list(df.columns)
        if len(cols) > 12:
            cols[12] = "조치입력 점수"
        if len(cols) > 15:
            cols[15] = "예약 점수"
        if len(cols) > 20:
            cols[20] = "처리시간 점수"
        if len(cols) > 23:
            cols[23] = "재방문 점수"
        if len(cols) > 26:
            cols[26] = "불만 점수"
        if len(cols) > 29:
            cols[29] = "독촉 점수"
        if len(cols) > 32:
            cols[32] = "고객만족도 점수"
        df.columns = cols

        if "조치입력 점수" in df.columns:
            df["조치정보입력율 점수"] = df["조치입력 점수"]

        numeric_cols = [
            "총 점수",
            "불만 점수",
            "예약 점수",
            "처리시간 점수",
            "조치입력 점수",
            "조치정보입력율 점수",
            "재방문 점수",
            "독촉 점수",
            "고객만족도 점수",
            "총접수건",
            "총접수",
            "미방문",
            "미입력",
            "방문 입력건",
            "입력건",
            "입력율(%)",
            "1시간이내예약건",
            "예약율(%)",
            "재방문건수",
            "재방문율(%)",
            "불만건수",
            "서비스불만율(%)",
            "독촉건수",
            "독촉율(%)",
            "합계",
            "총건",
        ]
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")

        s_col_name = None
        if len(df.columns) > 18:
            s_col_name = df.columns[18]
            df["_s_seconds"] = df[s_col_name].apply(parse_time_to_seconds)

        if "지사" in df.columns:
            unique_branches = sorted(df["지사"].dropna().unique())
            palette = px.colors.qualitative.Plotly
            branch_color_map = {
                branch: palette[i % len(palette)]
                for i, branch in enumerate(unique_branches)
            }
            branch_order = {"지사": unique_branches}
        else:
            unique_branches = []
            branch_color_map = {}
            branch_order = None

        # ------------------ 상단 타이틀 및 메인 필터 수평 배치 ------------------
        title_col, filter_col1, filter_col2 = st.columns([2.2, 1, 1])

        with title_col:
            st.markdown(
                "<h1 style='font-size: 52px; font-weight: bold;'>📊 대리점 서비스 평가 현황</h1>",
                unsafe_allow_html=True,
            )

        branch_options = ["전체"] + list(unique_branches)

        with filter_col1:
            selected_branch = st.selectbox(
                "🔍 조회할 지사 선택", branch_options, key="main_branch"
            )

        if selected_branch != "전체" and "지사" in df.columns:
            filtered_agencies = sorted(
                df[df["지사"] == selected_branch]["방문 대리점"]
                .dropna()
                .unique()
            )
        else:
            filtered_agencies = sorted(df["방문 대리점"].dropna().unique())

        with filter_col2:
            selected_agency = st.selectbox(
                "🏢 조회할 대리점 선택",
                filtered_agencies,
                key="main_agency",
            )

        # ------------------ 지사별 대리점 개수 표출 배너 ------------------
        if "지사" in df.columns and "방문 대리점" in df.columns:
            branch_counts = df.groupby("지사")["방문 대리점"].nunique()
            counts_text = " &nbsp;|&nbsp; ".join(
                [f"<b>{b}</b>: {c}개소" for b, c in branch_counts.items()]
            )
            st.markdown(
                f"""
                <div style='background-color: #f8fafc; border: 3px solid #cbd5e1; padding: 20px; border-radius: 16px; margin-top: 10px; margin-bottom: 25px; font-size: 36px; color: #1e293b;'>
                    🏢 <b>지사별 대리점 현황:</b> {counts_text}
                </div>
                """,
                unsafe_allow_html=True,
            )

        st.markdown("---")

        # ------------------ 전체 / 지사 대시보드 영역 ------------------
        if selected_branch != "전체" and "지사" in df.columns:
            filtered_main_df = df[df["지사"] == selected_branch]
        else:
            filtered_main_df = df.copy()

        st.markdown(
            "<h2 style='font-size: 44px; font-weight: bold;'>📌 서비스 평가 핵심 요약</h2>",
            unsafe_allow_html=True,
        )

        total_agencies = len(filtered_main_df)
        avg_score = (
            filtered_main_df["총 점수"].mean()
            if "총 점수" in filtered_main_df.columns
            else 0
        )

        if "지사" in df.columns and "총 점수" in df.columns:
            branch_means = (
                df.dropna(subset=["총 점수"]).groupby("지사")["총 점수"].mean()
            )
            best_branch = (
                branch_means.idxmax() if not branch_means.empty else "N/A"
            )
            best_score = branch_means.max() if not branch_means.empty else 0
            worst_branch = (
                branch_means.idxmin() if not branch_means.empty else "N/A"
            )
            worst_score = branch_means.min() if not branch_means.empty else 0
        else:
            best_branch, best_score, worst_branch, worst_score = (
                "N/A",
                0,
                "N/A",
                0,
            )

        best_diff = best_score - avg_score
        worst_diff = worst_score - avg_score

        # 커스텀 초대형 KPI 카드 출력 함수
        def render_custom_kpi(label, val, sub_text=""):
            st.markdown(
                f"""
            <div style="background: #ffffff; border: 3px solid #cbd5e1; border-radius: 16px; padding: 20px; box-shadow: 0 4px 10px rgba(0,0,0,0.05);">
                <div style="font-size: 32px; font-weight: bold; color: #475569;">{label}</div>
                <div style="font-size: 48px; font-weight: 800; color: #0f172a; margin-top: 5px;">{val}</div>
                {"<div style='font-size: 26px; color: #2563eb; margin-top: 5px;'>" + sub_text + "</div>" if sub_text else ""}
            </div>
            """,
                unsafe_allow_html=True,
            )

        k1, k2, k3, k4 = st.columns(4)
        with k1:
            render_custom_kpi("총 대리점 수", f"{total_agencies:,} 개소")
        with k2:
            render_custom_kpi(
                "전체 평균 점수",
                f"{avg_score:.2f} 점" if pd.notnull(avg_score) else "N/A",
            )
        with k3:
            render_custom_kpi(
                "최고 점수 지사",
                f"{best_branch} {best_score:.2f}점",
                f"평균대비 {best_diff:+.2f}점",
            )
        with k4:
            render_custom_kpi(
                "최저 점수 지사",
                f"{worst_branch} {worst_score:.2f}점",
                f"평균대비 {worst_diff:+.2f}점",
            )

        st.markdown("<br>", unsafe_allow_html=True)

        left_col, right_col = st.columns(2)
        with left_col:
            st.markdown(
                "<h3 style='font-size: 38px; font-weight: bold;'>🏢 지사별 평균 서비스 점수</h3>",
                unsafe_allow_html=True,
            )
            if (
                "지사" in filtered_main_df.columns
                and "총 점수" in filtered_main_df.columns
            ):
                branch_avg = (
                    filtered_main_df.dropna(subset=["총 점수"])
                    .groupby("지사", as_index=False)["총 점수"]
                    .mean()
                )
                if not branch_avg.empty:
                    fig2 = px.bar(
                        branch_avg,
                        x="지사",
                        y="총 점수",
                        color="지사",
                        color_discrete_map=branch_color_map,
                        category_orders=branch_order,
                        text_auto=".2f",
                        height=650,
                    )
                    # 차트 내 폰트 파이썬 직접 확대
                    fig2.update_layout(
                        font=dict(size=32),
                        xaxis=dict(
                            tickfont=dict(size=32),
                            title=dict(font=dict(size=36)),
                        ),
                        yaxis=dict(
                            tickfont=dict(size=32),
                            title=dict(font=dict(size=36)),
                        ),
                    )
                    fig2.update_traces(textfont_size=32)
                    st.plotly_chart(fig2, use_container_width=True)

        with right_col:
            st.markdown(
                "<h3 style='font-size: 38px; font-weight: bold;'>💡 총 점수 vs 총접수건</h3>",
                unsafe_allow_html=True,
            )
            total_cnt_col = (
                "총접수건"
                if "총접수건" in filtered_main_df.columns
                else (
                    "총접수" if "총접수" in filtered_main_df.columns else None
                )
            )
            if total_cnt_col and "총 점수" in filtered_main_df.columns:
                scatter_df = filtered_main_df.dropna(
                    subset=[total_cnt_col, "총 점수"]
                )
                if not scatter_df.empty:
                    fig1 = px.scatter(
                        scatter_df,
                        x=total_cnt_col,
                        y="총 점수",
                        color="지사" if "지사" in scatter_df.columns else None,
                        color_discrete_map=branch_color_map,
                        category_orders=branch_order,
                        hover_name=(
                            "방문 대리점"
                            if "방문 대리점" in scatter_df.columns
                            else None
                        ),
                        height=650,
                    )
                    fig1.update_traces(marker=dict(size=22))
                    fig1.update_layout(
                        font=dict(size=32),
                        xaxis=dict(
                            tickfont=dict(size=32),
                            title=dict(font=dict(size=36)),
                        ),
                        yaxis=dict(
                            tickfont=dict(size=32),
                            title=dict(font=dict(size=36)),
                        ),
                        legend=dict(
                            font=dict(size=28), title=dict(font=dict(size=32))
                        ),
                    )
                    st.plotly_chart(fig1, use_container_width=True)

        display_df = filtered_main_df.copy()
        if s_col_name:
            display_df[s_col_name] = display_df[s_col_name].apply(
                format_time_duration
            )

        percent_cols = [
            "입력율(%)",
            "방문율",
            "예약율(%)",
            "재방문율(%)",
            "서비스불만율(%)",
            "독촉율(%)",
        ]
        for p_col in percent_cols:
            if p_col in display_df.columns:
                display_df[p_col] = display_df[p_col].apply(
                    lambda x: (
                        f"{x*100:.2f}%"
                        if pd.notnull(x)
                        and isinstance(x, (int, float))
                        and x <= 1.0
                        else (
                            f"{x:.2f}%"
                            if pd.notnull(x) and isinstance(x, (int, float))
                            else ""
                        )
                    )
                )

        for col in display_df.select_dtypes(
            include=["float", "float64"]
        ).columns:
            if col not in percent_cols and col != "_s_seconds":
                display_df[col] = display_df[col].apply(
                    lambda x: f"{x:.2f}" if pd.notnull(x) else ""
                )

        # ------------------ 7개 평가 지표 세부 현황 (TOP 20 & LOW 20) ------------------
        st.markdown("---")
        st.markdown(
            "<h2 style='font-size: 44px; font-weight: bold;'>📋 7개 평가 지표별 세부 현황 (TOP 20 & LOW 20)</h2>",
            unsafe_allow_html=True,
        )

        indicators_info = [
            (
                "1. 조치정보입력율",
                "조치입력 점수",
                [
                    "지사",
                    "방문 대리점",
                    "총접수건",
                    "미입력",
                    "입력율(%)",
                    "조치입력 점수",
                    "총 점수",
                ],
            ),
            (
                "2. 약속시간입력율",
                "예약 점수",
                [
                    "지사",
                    "방문 대리점",
                    "총접수건",
                    "1시간이내예약건",
                    "예약율(%)",
                    "예약 점수",
                    "총 점수",
                ],
            ),
            (
                "3. 평균처리시간",
                "처리시간 점수",
                [
                    "지사",
                    "방문 대리점",
                    "총접수건",
                    s_col_name,
                    "처리시간 점수",
                    "총 점수",
                ]
                if s_col_name
                else ["지사", "방문 대리점", "처리시간 점수", "총 점수"],
            ),
            (
                "4. 재방문율",
                "재방문 점수",
                [
                    "지사",
                    "방문 대리점",
                    "총접수건",
                    "재방문건수",
                    "재방문율(%)",
                    "재방문 점수",
                    "총 점수",
                ],
            ),
            (
                "5. 서비스불만율",
                "불만 점수",
                [
                    "지사",
                    "방문 대리점",
                    "총접수건",
                    "불만건수",
                    "서비스불만율(%)",
                    "불만 점수",
                    "총 점수",
                ],
            ),
            (
                "6. 독촉율",
                "독촉 점수",
                [
                    "지사",
                    "방문 대리점",
                    "총접수건",
                    "독촉건수",
                    "독촉율(%)",
                    "독촉 점수",
                    "총 점수",
                ],
            ),
            (
                "7. 고객만족도",
                "고객만족도 점수",
                [
                    "지사",
                    "방문 대리점",
                    "총접수건",
                    "고객만족도 점수",
                    "총 점수",
                ],
            ),
        ]

        for i in range(0, len(indicators_info), 2):
            col1, col2 = st.columns(2)

            title_name1, col_key1, target_cols1 = indicators_info[i]
            with col1:
                st.markdown(
                    f"<h3 style='font-size: 36px; font-weight: bold;'>📌 {title_name1}</h3>",
                    unsafe_allow_html=True,
                )
                sub_cols1 = [
                    c for c in target_cols1 if c in display_df.columns
                ]
                if col_key1 in filtered_main_df.columns:
                    valid_sub_df1 = filtered_main_df.dropna(subset=[col_key1])
                    top_tab1, low_tab1 = st.tabs(
                        ["🔝 TOP 20 (우수)", "🔻 LOW 20 (주의)"]
                    )
                    with top_tab1:
                        idx_top1 = valid_sub_df1.sort_values(
                            by=[col_key1, "총 점수"], ascending=[False, False]
                        ).index
                        styled_top1 = apply_highlight_styler(
                            display_df.loc[idx_top1, sub_cols1].head(20),
                            col_key1,
                            mode="top",
                        )
                        st.dataframe(
                            styled_top1,
                            use_container_width=True,
                            hide_index=True,
                            height=550,
                        )
                    with low_tab1:
                        idx_low1 = valid_sub_df1.sort_values(
                            by=[col_key1, "총 점수"], ascending=[True, False]
                        ).index
                        styled_low1 = apply_highlight_styler(
                            display_df.loc[idx_low1, sub_cols1].head(20),
                            col_key1,
                            mode="low",
                        )
                        st.dataframe(
                            styled_low1,
                            use_container_width=True,
                            hide_index=True,
                            height=550,
                        )

            if i + 1 < len(indicators_info):
                title_name2, col_key2, target_cols2 = indicators_info[i + 1]
                with col2:
                    st.markdown(
                        f"<h3 style='font-size: 36px; font-weight: bold;'>📌 {title_name2}</h3>",
                        unsafe_allow_html=True,
                    )
                    sub_cols2 = [
                        c for c in target_cols2 if c in display_df.columns
                    ]
                    if col_key2 in filtered_main_df.columns:
                        valid_sub_df2 = filtered_main_df.dropna(
                            subset=[col_key2]
                        )
                        top_tab2, low_tab2 = st.tabs(
                            ["🔝 TOP 20 (우수)", "🔻 LOW 20 (주의)"]
                        )
                        with top_tab2:
                            idx_top2 = valid_sub_df2.sort_values(
                                by=[col_key2, "총 점수"],
                                ascending=[False, False],
                            ).index
                            styled_top2 = apply_highlight_styler(
                                display_df.loc[idx_top2, sub_cols2].head(20),
                                col_key2,
                                mode="top",
                            )
                            st.dataframe(
                                styled_top2,
                                use_container_width=True,
                                hide_index=True,
                                height=550,
                            )
                        with low_tab2:
                            idx_low2 = valid_sub_df2.sort_values(
                                by=[col_key2, "총 점수"],
                                ascending=[True, False],
                            ).index
                            styled_low2 = apply_highlight_styler(
                                display_df.loc[idx_low2, sub_cols2].head(20),
                                col_key2,
                                mode="low",
                            )
                            st.dataframe(
                                styled_low2,
                                use_container_width=True,
                                hide_index=True,
                                height=550,
                            )

            st.markdown("---")

        # ------------------ 대리점별 상세 리포트 영역 ------------------
        if selected_agency:
            agency_row = df[df["방문 대리점"] == selected_agency]
            if not agency_row.empty:
                agency_data = agency_row.iloc[0]
                agency_branch = agency_data.get("지사", "미지정")

                st.markdown(
                    f"<h2 style='font-size: 44px; font-weight: bold;'>🏢 [{agency_branch}] <u>{selected_agency}</u> 평가 상세 리포트</h2>",
                    unsafe_allow_html=True,
                )

                total_agencies_count = len(df)
                overall_rank = (
                    df["총 점수"].rank(ascending=False, method="min")[
                        agency_row.index[0]
                    ]
                    if "총 점수" in df.columns
                    else None
                )

                branch_agencies = (
                    df[df["지사"] == agency_branch]
                    if agency_branch != "미지정"
                    else df
                )
                branch_agencies_count = len(branch_agencies)
                branch_rank = (
                    branch_agencies["총 점수"].rank(
                        ascending=False, method="min"
                    )[agency_row.index[0]]
                    if "총 점수" in df.columns
                    else None
                )

                c1, c2, c3, c4 = st.columns(4)
                with c1:
                    render_custom_kpi(
                        "총 점수", f"{agency_data.get('총 점수', 0):.2f} 점"
                    )
                with c2:
                    render_custom_kpi(
                        "지사 내 순위",
                        (
                            f"{int(branch_rank)}위 / {branch_agencies_count}개"
                            if pd.notnull(branch_rank)
                            else "N/A"
                        ),
                    )
                with c3:
                    render_custom_kpi(
                        "전체 순위",
                        (
                            f"{int(overall_rank)}위 / {total_agencies_count}개"
                            if pd.notnull(overall_rank)
                            else "N/A"
                        ),
                    )
                with c4:
                    tot_receipt = agency_data.get(
                        "총접수건", agency_data.get("총접수", 0)
                    )
                    render_custom_kpi(
                        "총 접수건수",
                        (
                            f"{int(tot_receipt):,} 건"
                            if pd.notnull(tot_receipt)
                            else "0 건"
                        ),
                    )

                st.markdown("---")

                # 만점 대비 달성률 차트
                st.markdown(
                    "<h3 style='font-size: 38px; font-weight: bold;'>📊 만점 대비 세부 항목 달성 현황</h3>",
                    unsafe_allow_html=True,
                )

                max_score_dict = {
                    "조치정보입력율": 15,
                    "약속시간입력율": 25,
                    "평균처리시간": 15,
                    "재방문율": 15,
                    "서비스불만율": 15,
                    "독촉율": 10,
                    "고객만족도": 5,
                }
                metrics_color_config = [
                    {"main": "#8B5CF6", "bg": "#DDD6FE"},
                    {"main": "#F59E0B", "bg": "#FDE68A"},
                    {"main": "#EF4444", "bg": "#FECACA"},
                    {"main": "#10B981", "bg": "#A7F3D0"},
                    {"main": "#3B82F6", "bg": "#BFDBFE"},
                    {"main": "#6B7280", "bg": "#E5E7EB"},
                    {"main": "#EC4899", "bg": "#FBCFE8"},
                ]
                score_cols = [
                    "조치정보입력율 점수",
                    "예약 점수",
                    "처리시간 점수",
                    "재방문 점수",
                    "불만 점수",
                    "독촉 점수",
                    "고객만족도 점수",
                ]
                col_display_names = [
                    "조치정보입력율",
                    "약속시간입력율",
                    "평균처리시간",
                    "재방문율",
                    "서비스불만율",
                    "독촉율",
                    "고객만족도",
                ]

                available_indices = [
                    i for i, c in enumerate(score_cols) if c in df.columns
                ]
                x_labels = [col_display_names[i] for i in available_indices]
                actual_cols = [score_cols[i] for i in available_indices]

                if actual_cols:
                    achieved_pct_list = []
                    remaining_pct_list = []
                    text_labels = []
                    top_labels = []

                    for idx, c in enumerate(actual_cols):
                        name = x_labels[idx]
                        max_s = max_score_dict.get(name, 15)
                        val = (
                            float(agency_data.get(c, 0))
                            if pd.notnull(agency_data.get(c, 0))
                            else 0.0
                        )
                        pct = (val / max_s) * 100 if max_s > 0 else 0

                        achieved_pct_list.append(pct)
                        remaining_pct_list.append(max(0, 100 - pct))
                        text_labels.append(
                            f"<b>{val:.2f}점</b><br>({pct:.1f}%)"
                        )
                        top_labels.append(f"{max_s}점")

                    main_colors = [
                        metrics_color_config[i % len(metrics_color_config)][
                            "main"
                        ]
                        for i in range(len(x_labels))
                    ]
                    bg_colors = [
                        metrics_color_config[i % len(metrics_color_config)][
                            "bg"
                        ]
                        for i in range(len(x_labels))
                    ]

                    fig_comp = go.Figure()
                    fig_comp.add_trace(
                        go.Bar(
                            x=x_labels,
                            y=achieved_pct_list,
                            name="획득 비율",
                            marker_color=main_colors,
                            text=text_labels,
                            textposition="inside",
                            insidetextanchor="middle",
                            textfont=dict(
                                size=32, color="white", family="Arial Black"
                            ),
                        )
                    )
                    fig_comp.add_trace(
                        go.Bar(
                            x=x_labels,
                            y=remaining_pct_list,
                            name="미획득 비율",
                            marker_color=bg_colors,
                            text=top_labels,
                            textposition="outside",
                            textfont=dict(
                                size=30, color="#475569", weight="bold"
                            ),
                        )
                    )

                    fig_comp.update_layout(
                        barmode="stack",
                        showlegend=False,
                        height=680,
                        margin=dict(l=20, r=20, t=40, b=40),
                        plot_bgcolor="white",
                        paper_bgcolor="white",
                        font=dict(size=32),
                        xaxis=dict(
                            tickfont=dict(
                                size=32, color="#334155", weight="bold"
                            )
                        ),
                        yaxis=dict(
                            title="만점 대비 달성률 (%)",
                            title_font=dict(size=32),
                            tickfont=dict(size=30),
                            range=[0, 115],
                        ),
                    )
                    st.plotly_chart(fig_comp, use_container_width=True)

        # ------------------ 전체 대리점 목록 조회 표 ------------------
        st.markdown("---")
        st.markdown(
            "<h2 style='font-size: 44px; font-weight: bold;'>🔍 대리점별 전체 항목 조회</h2>",
            unsafe_allow_html=True,
        )
        clean_display_df = display_df.drop(
            columns=["_s_seconds"], errors="ignore"
        )
        styled_overall_df = apply_overall_table_styler(clean_display_df)
        st.dataframe(styled_overall_df, use_container_width=True, height=650)

    except Exception as e:
        st.error(f"⚠️ 데이터를 읽는 중 오류가 발생했습니다: {e}")
