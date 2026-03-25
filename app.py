st.markdown("---")
l2, r2 = st.columns([1, 1])
with l2:
    st.subheader("💰 Budget Annuo vs Cumulativo")
    fig_fin = go.Figure()
    fig_fin.add_trace(go.Bar(x=anni_sim, y=budgets, name="Annuo (€)", marker_color='#81C784'))
    fig_fin.add_trace(go.Scatter(x=anni_sim, y=np.cumsum(budgets), name="Cumulativo (€)", line=dict(color='#1a73e8', width=3), yaxis="y2"))
    fig_fin.update_layout(
        height=400, 
        yaxis2=dict(overlaying="y", side="right", tickfont_size=CHART_FONT_SIZE),
        legend=dict(orientation="h", y=1.1, font_size=CHART_FONT_SIZE),
        xaxis=dict(tickfont_size=CHART_FONT_SIZE),
        yaxis=dict(tickfont_size=CHART_FONT_SIZE)
    )
    st.plotly_chart(fig_fin, use_container_width=True)
with r2:
    st.subheader("📊 Ripartizione Ettari Finale (2030)")
    fig_pie = go.Figure(data=[go.Pie(labels=list(ettari_per_anno[-1].keys()), values=list(ettari_per_anno[-1].values()), hole=.4)])
    fig_pie.update_traces(textfont_size=CHART_FONT_SIZE)
    fig_pie.update_layout(height=400, legend=dict(font_size=CHART_FONT_SIZE))
    st.plotly_chart(fig_pie, use_container_width=True)
