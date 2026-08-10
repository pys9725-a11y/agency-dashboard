import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import re

# ==========================================
# 1. 페이지 설정 및 커스텀 CSS 스타일링
# ==========================================
st.set_page_config(
    page_title="대리점 서비스 평가 대시보드",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 대형 화면에 맞춘 큰 폰트 및 카드 스타일링
st.markdown("""
<style>
    html, body, [class*="css"] {
        font-size: 18px !important;
    }
    .stMetric {
        background: linear-gradient(135deg, #ffffff 0%, #f8f9fa 100%);
        padding: 20px;
        border-radius: 12px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        border: 1px solid #e9ecef;
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }
    .stMetric:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 12px rgba(0,0,0,0.1);
    }
    .stMetric label {
        font-size: 1.1rem !important;
        font-weight: 600 !important;
        color: #495057 !important;
    }
    .stMetric [data-testid="stMetricValue"] {
        font-size: 2.2rem !important;
        font-weight: 700 !important;
        color: #1b4965 !important;
    }
    .highlight-card {
        background-color: #eef6fc;
        padding: 15px;
        border-left: 5px solid #2980b9;
        border-radius: 5px;
        margin-bottom: 20px;
    }
</style>
""", unsafe_allow_html=True)


# ==========================================
# 2. 유틸리티 함수 (시간 변환 & 레이더 차트)
# ==========================================
def parse_time_to_seconds(val):
    """시간/기간 형태의 데이터나 초 단위 숫자를 초(seconds)로 변환"""
    if pd.isna(val):
        return 0.0
    if isinstance(val, (int, float)):
        return float(val)
    val_str = str(val).strip()
    
    # "X시간 Y분 Z초" 또는 "HH:MM:SS" 파싱
    h, m, s = 0, 0, 0
    if ':' in val_str:
        parts = val_str.split(':')
        if len(parts) == 3:
            h, m, s = map(float, parts)
        elif len(parts) == 2:
            m, s = map(float, parts)
        return h * 3600 + m * 60 + s
    
    # 한글 시간 표현식 파싱
    h_match = re.search(r'(\d+)\s*시간', val_str)
    m_match = re.search(r'(\d+)\s*분', val_str)
    s_match = re.search(r'(\d+)\s*초', val_str)
    
    if h_match: h = float(h_match.group(1))
    if m_match: m = float(m_match.group(1))
    if s_match: s = float(s_match.group(1))
    
    if h_match or m_match or s_match:
        return h * 3600 + m * 60 + s
        
    try:
        return float(val_str)
    except ValueError:
        return 0.0

def format_time_duration(seconds):
    """초(seconds)를 'X시간 Y분 Z초' 포맷으로 변경"""
    if pd.isna(seconds) or seconds <= 0:
        return "0초"
    seconds = int(seconds)
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    
    res = []
    if hours > 0: res.append(f"{hours}시간")
    if minutes > 0: res.append(f"{minutes}분")
    if secs > 0 or len(res) == 0: res.append(f"{secs}초")
    return " ".join(res)

def create_radar_chart(agent_row, overall_df, eval_cols, max_scores_dict):
    """대리점별 7개 평가 지표 레이더 차트 (대리점 vs 전체 평균 달성율 비교)"""
    categories = eval_cols

    # 1. 선택 대리점 지표별 달성율(%)
    agent_scores = []
    for col in categories:
        val = agent_row[col]
        m_val = max_scores_dict.get(col, 100)
        pct = (val / m_val * 100) if m_val > 0 else 0
        agent_scores.append(pct)

    # 2. 전체 대리점 평균 지표별 달성율(%)
    avg_scores = []
    for col in categories:
        avg_val = overall_df[col].mean()
        m_val = max_scores_dict.get(col, 100)
        pct = (avg_val / m_val * 100) if m_val > 0 else 0
        avg_scores.append(pct)

    # Plotly 레이더 차트 닫힘 구조 생성 (첫 항목을 마지막에 추가)
    categories_closed = categories + [categories[0]]
    agent_scores_closed = agent_scores + [agent_scores[0]]
    avg_scores_closed = avg_scores + [avg_scores[0]]

    fig = go.Figure()

    # 전체 평균 트레이스 (회색 배경)
    fig.add_trace(go.Scatterpolar(
        r=avg_scores_closed,
        theta=categories_closed,
        fill='toself',
        name='전체 평균',
        line_color='#BDC3C7',
        fillcolor='rgba(189, 195, 199, 0.3)'
    ))

    # 선택 대리점 트레이스 (파란색 강조)
    fig.add_trace(go.Scatterpolar(
        r=agent_scores_closed,
        theta=categories_closed,
        fill='toself',
        name=agent_row['대리점명'],
        line_color='#2980B9',
        fillcolor='rgba(41, 128, 185, 0.4)'
    ))

    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, 100],
                suffix='%'
            )
        ),
        showlegend=True,
        title=dict(
            text=f"<b>{agent_row['대리점명']} vs 전체 평균 지표 균형 (달성율 %)</b>",
            font=dict(size=18)
        ),
        height=480,
        margin=dict(l=50, r=50, t=60, b=50)
    )

    return fig


# ==========================================
# 3. 데이터 로딩 및 샘플 데이터 생성
# ==========================================
@st.cache_data
def load_sample_data():
    np.random.seed(42)
    branches = ['서울지사', '경기지사', '부산지사', '대구지사', '광주지사']
    agents = [f"대리점_{i+1:02d}" for i in range(50)]
    
    data = []
    for agent in agents:
        branch = np.random.choice(branches)
        total_receipts = np.random.randint(100, 1000)
        
        # 7개 평가 지표 점수 (만점 기준 설정)
        cs_score = np.random.uniform(8, 15)       # 만점 15
        response_rate = np.random.uniform(8, 15)  # 만점 15
        process_time = np.random.uniform(5, 15)   # 만점 15
        quality_score = np.random.uniform(10, 15) # 만점 15
        kindness = np.random.uniform(8, 15)       # 만점 15
        skill_score = np.random.uniform(8, 15)    # 만점 15
        compliance = np.random.uniform(5, 10)     # 만점 10
        
        total_score = sum([cs_score, response_rate, process_time, quality_score, kindness, skill_score, compliance])
        avg_time_sec = np.random.randint(300, 3600) # 평균 처리시간(초)
        
        data.append({
            '지사': branch,
            '대리점명': agent,
            '총접수건': total_receipts,
            '고객 만족도': round(cs_score, 1),
            '응대율': round(response_rate, 1),
            '처리 시간': round(process_time, 1),
            '품질 점수': round(quality_score, 1),
            '친절도': round(kindness, 1),
            '업무 숙련도': round(skill_score, 1),
            '규정 준수': round(compliance, 1),
            '총 점수': round(total_score, 1),
            '평균처리시간_초': avg_time_sec,
            '평균처리시간_표시': format_time_duration(avg_time_sec)
        })
    return pd.DataFrame(data)

df_raw = load_sample_data()

# 7개 세부 지표 및 만점 정의
eval_columns = ['고객 만족도', '응대율', '처리 시간', '품질 점수', '친절도', '업무 숙련도', '규정 준수']
max_scores = {
    '고객 만족도': 15,
    '응대율': 15,
    '처리 시간': 15,
    '품질 점수': 15,
    '친절도': 15,
    '업무 숙련도': 15,
    '규정 준수': 10
}


# ==========================================
# 4. 사이드바 - 파일 업로드 및 필터
# ==========================================
st.sidebar.title("🔍 대시보드 제어판")

uploaded_file = st.sidebar.file_uploader("CSV 데이터 파일 업로드", type=['csv'])
if uploaded_file is not None:
    df = pd.read_csv(uploaded_file)
else:
    df = df_raw.copy()

st.sidebar.markdown("---")
st.sidebar.subheader("📌 지사 및 대리점 필터")

# 지사 선택
all_branches = ['전체'] + list(df['지사'].unique())
selected_branch = st.sidebar.selectbox("지사 선택", all_branches)

# 지사에 연동된 대리점 목록 필터링
if selected_branch != '전체':
    filtered_df = df[df['지사'] == selected_branch]
else:
    filtered_df = df.copy()

all_agents = ['전체'] + list(filtered_df['대리점명'].unique())
selected_agent = st.sidebar.selectbox("대리점 선택", all_agents)

if selected_agent != '전체':
    filtered_df = filtered_df[filtered_df['대리점명'] == selected_agent]


# ==========================================
# 5. 메인 대시보드 화면
# ==========================================
st.title("📊 전국 대리점 서비스 평가 종합 대시보드")
st.markdown("전국 지사 및 대리점별 서비스 평가 지표, 세부 현황 및 대리점별 강/약점을 다각도로 분석합니다.")

# 지사별 대리점 수 배너 표출
agent_count_info = f"현재 조회 중인 대리점 수: **{len(filtered_df)}개**"
if selected_branch != '전체':
    agent_count_info += f" ({selected_branch} 소속)"
st.markdown(f"<div class='highlight-card'>{agent_count_info}</div>", unsafe_allow_html=True)

# ------------------------------------------
# 핵심 요약 KPI 카운터
# ------------------------------------------
kpi1, kpi2, kpi3, kpi4 = st.columns(4)

with kpi1:
    st.metric("총 대리점 수", f"{len(filtered_df)} 개")
with kpi2:
    avg_score = filtered_df['총 점수'].mean() if len(filtered_df) > 0 else 0
    st.metric("전체 평균 점수", f"{avg_score:.1f} 점")
with kpi3:
    branch_avg = df.groupby('지사')['총 점수'].mean()
    top_branch = branch_avg.idxmax() if len(branch_avg) > 0 else "-"
    st.metric("최고 성과 지사", top_branch, f"{branch_avg.max():.1f}점")
with kpi4:
    low_branch = branch_avg.idxmin() if len(branch_avg) > 0 else "-"
    st.metric("최저 성과 지사", low_branch, f"{branch_avg.min():.1f}점", delta_color="inverse")

st.markdown("---")

# ------------------------------------------
# 메인 분석 탭 구성
# ------------------------------------------
tab1, tab2, tab3, tab4 = st.tabs([
    "📈 지사별 종합 차트", 
    "📋 7개 평가 지표 현황", 
    "🎯 대리점 상세 리포트 (레이더 차트)", 
    "📄 전체 대리점 목록"
])

# ------------------------------------------
# TAB 1: 지사별 종합 차트
# ------------------------------------------
with tab1:
    st.subheader("지사별 평균 점수 및 접수건 대비 점수 분포")
    col1, col2 = st.columns(2)
    
    with col1:
        branch_summary = df.groupby('지사', as_index=False)['총 점수'].mean().sort_values('총 점수', ascending=False)
        fig_bar = px.bar(
            branch_summary, 
            x='지사', 
            y='총 점수', 
            text_auto='.1f',
            title="지사별 평균 평가 점수",
            color='총 점수',
            color_continuous_scale='Blues'
        )
        fig_bar.update_layout(xaxis_title="지사", yaxis_title="평균 점수", height=400)
        st.plotly_chart(fig_bar, use_container_width=True)
        
    with col2:
        fig_scatter = px.scatter(
            df, 
            x='총접수건', 
            y='총 점수', 
            color='지사',
            hover_name='대리점명',
            size='총 점수',
            title="총접수건 대비 총 점수 분포"
        )
        fig_scatter.update_layout(height=400)
        st.plotly_chart(fig_scatter, use_container_width=True)

# ------------------------------------------
# TAB 2: 7개 평가 지표 현황
# ------------------------------------------
with tab2:
    st.subheader("7개 평가 지표별 상위 / 하위 대리점 분석")
    selected_eval_col = st.selectbox("분석할 평가 지표를 선택하세요", eval_columns)
    
    col_top, col_low = st.columns(2)
    
    with col_top:
        st.markdown(f"#### 🏆 {selected_eval_col} TOP 10 대리점")
        top_df = df.sort_values(by=selected_eval_col, ascending=False).head(10)
        st.dataframe(
            top_df[['지사', '대리점명', selected_eval_col, '총 점수']],
            use_container_width=True
        )
        
    with col_low:
        st.markdown(f"#### ⚠️ {selected_eval_col} LOW 10 대리점")
        low_df = df.sort_values(by=selected_eval_col, ascending=True).head(10)
        st.dataframe(
            low_df[['지사', '대리점명', selected_eval_col, '총 점수']],
            use_container_width=True
        )

# ------------------------------------------
# TAB 3: 대리점 상세 리포트 (레이더 차트 포함)
# ------------------------------------------
with tab3:
    st.subheader("대리점 개별 세부 리포트 & 강·약점 분석")
    
    agent_list = df['대리점명'].unique()
    target_agent = st.selectbox("분석할 대리점을 선택하세요", agent_list, key="detail_agent_select")
    
    agent_data = df[df['대리점명'] == target_agent].iloc[0]
    
    # 1. 상단 기본 메트릭 표시
    m_col1, m_col2, m_col3, m_col4 = st.columns(4)
    m_col1.metric("소속 지사", agent_data['지사'])
    m_col2.metric("총 점수", f"{agent_data['총 점수']} 점", f"{agent_data['총 점수'] - df['총 점수'].mean():.1f}점 (평균 대비)")
    m_col3.metric("총 접수건", f"{agent_data['총접수건']} 건")
    m_col4.metric("평균 처리 시간", agent_data['평균처리시간_표시'])
    
    st.markdown("---")
    
    # 2. 레이더 차트 및 지표 달성율 막대 차트
    chart_col1, chart_col2 = st.columns([1.1, 0.9])
    
    with chart_col1:
        st.markdown("#### 🕸️ 7개 평가 지표 균형 (레이더 차트)")
        # 레이더 차트 생성 함수 호출
        fig_radar = create_radar_chart(
            agent_row=agent_data,
            overall_df=df,
            eval_cols=eval_columns,
            max_scores_dict=max_scores
        )
        st.plotly_chart(fig_radar, use_container_width=True)
        
    with chart_col2:
        st.markdown("#### 🎯 지표별 만점 대비 달성율 (%)")
        achievement_data = []
        for col in eval_columns:
            score = agent_data[col]
            m_score = max_scores[col]
            pct = round((score / m_score) * 100, 1)
            achievement_data.append({'지표': col, '달성율': pct, '취득점수': score, '만점': m_score})
            
        ach_df = pd.DataFrame(achievement_data)
        
        fig_ach = px.bar(
            ach_df,
            x='달성율',
            y='지표',
            orientation='h',
            text_auto=True,
            color='달성율',
            color_continuous_scale='Blues',
            range_x=[0, 100]
        )
        fig_ach.update_layout(
            xaxis_title="달성율 (%)",
            yaxis_title="",
            height=480,
            coloraxis_showscale=False
        )
        st.plotly_chart(fig_ach, use_container_width=True)

# ------------------------------------------
# TAB 4: 전체 대리점 목록
# ------------------------------------------
with tab4:
    st.subheader("전체 대리점 데이터 목록")
    
    # 총 점수에 따른 조건부 색상 적용
    def highlight_scores(val):
        if isinstance(val, (int, float)):
            if val >= 90:
                return 'background-color: #d4edda; color: #155724; font-weight: bold;'
            elif val < 70:
                return 'background-color: #f8d7da; color: #721c24; font-weight: bold;'
        return ''

    styled_df = filtered_df.style.map(highlight_scores, subset=['총 점수'])
    st.dataframe(styled_df, use_container_width=True, height=500)
