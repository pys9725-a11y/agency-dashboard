# ------------------ 1. 시각화 영역 ------------------
        left_col, right_col = st.columns(2)
        
        # [왼쪽] 지사별 평균 서비스 점수 (1번 이미지 수정)
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
                fig2.update_layout(
                    font=dict(size=21),
                    # X축 라벨 크기 4px 축소(20px -> 16px) 및 기울임 방지(tickangle=0)
                    xaxis=dict(tickfont=dict(size=16), tickangle=0),
                    yaxis=dict(tickfont=dict(size=20))
                )
                st.plotly_chart(fig2, use_container_width=True)

        # [오른쪽] 총 점수 vs 총접수건 (2번 이미지 수정)
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
