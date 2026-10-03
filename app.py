import os, pandas as pd, plotly.express as px, streamlit as st

EF, BF = "expenses.csv", "budgets.csv"
st.set_page_config(page_title="手機記帳與預算本", page_icon="💰", initial_sidebar_state="collapsed")
CATS = ["🍔 飲食", "🛒 日常用品", "🚗 交通出行", "🎮 娛樂休閒", "👔 服飾美容", "📱 數位訂閱", "🏥 醫療健康", "📦 其他"]

def load_e(): return pd.read_csv(EF) if os.path.exists(EF) else pd.DataFrame(columns=["日期", "類別", "金額", "備忘錄"])
def load_b(): return pd.read_csv(BF) if os.path.exists(BF) else pd.DataFrame(columns=["年月", "總收入", "類別", "預算金額"])

df_exp, df_bud = load_e(), load_b()
if not df_exp.empty and "日期" in df_exp.columns: df_exp["日期"] = pd.to_datetime(df_exp["日期"])

st.title("💰 記帳與預算管家")
t1, t2, t3, t4 = st.tabs(["➕ 新增記帳", "🎯 預算規劃", "📊 結算與分析", "📋 明細管理"])

with t1:
    st.subheader("新增支出")
    with st.form("a_form", clear_on_submit=True):
        d = st.date_input("日期")
        c = st.selectbox("類別", CATS)
        a = st.number_input("金額 (NTD)", min_value=1, step=10, value=100)
        n = st.text_input("備忘錄", placeholder="備註（選填）")
        if st.form_submit_button("新增這筆支出", use_container_width=True):
            df_exp = pd.concat([df_exp, pd.DataFrame([{"日期": pd.to_datetime(d), "類別": c, "金額": a, "備忘錄": n}])], ignore_index=True)
            df_exp.to_csv(EF, index=False)
            st.success("已儲存支出！")
            st.rerun()

with t2:
    st.subheader("🎯 每月收入與預算設定")
    cy, cm = st.columns(2)
    y = cy.number_input("年份", min_value=2020, max_value=2030, value=pd.Timestamp.now().year)
    m = cm.number_input("月份", min_value=1, max_value=12, value=pd.Timestamp.now().month)
    ym = f"{y}-{m:02d}"
    ex_b = df_bud[df_bud["年月"] == ym]
    inc_val = float(ex_b["總收入"].iloc[0]) if not ex_b.empty else 50000.0
    with st.form("b_form"):
        inc = st.number_input("💵 本月預估總收入", min_value=0.0, step=1000.0, value=inc_val)
        st.markdown("---")
        cb = {}
        for cat in CATS:
            v = float(ex_b[ex_b["類別"] == cat]["預算金額"].iloc[0]) if not ex_b.empty and not ex_b[ex_b["類別"] == cat].empty else 0.0
            cb[cat] = st.number_input(f"{cat} 預算", min_value=0.0, step=500.0, value=v, key=f"b_{cat}")
        if st.form_submit_button("儲存預算設定", use_container_width=True):
            df_bud = pd.concat([df_bud[df_bud["年月"] != ym], pd.DataFrame([{"年月": ym, "總收入": inc, "類別": cat, "預算金額": bv} for cat, bv in cb.items()])], ignore_index=True)
            df_bud.to_csv(BF, index=False)
            st.success(f"已儲存 {ym} 預算！")
            st.rerun()

with t3:
    st.subheader("📊 月度預算 vs 實際支出結算")
    if df_exp.empty: st.info("尚無記帳資料！")
    else:
        df_exp["年月"] = pd.to_datetime(df_exp["日期"]).dt.strftime("%Y-%m")
        sel_ym = st.selectbox("選擇結算月份", sorted(df_exp["年月"].unique(), reverse=True))
        m_exp, m_bud = df_exp[df_exp["年月"] == sel_ym], df_bud[df_bud["年月"] == sel_ym]
        act_tot = m_exp["金額"].sum()
        inc_m = m_bud["總收入"].iloc[0] if not m_bud.empty else 0.0
        bud_tot = m_bud["預算金額"].sum() if not m_bud.empty else 0.0
        m1, m2, m3 = st.columns(3)
        m1.metric("本月總收入", f"${inc_m:,.0f}")
        m2.metric("本月總支出", f"${act_tot:,.0f}")
        m3.metric("本月預估結餘", f"${inc_m - act_tot:,.0f}")
        st.markdown("---")
        an_df = pd.DataFrame({"類別": CATS}).merge(m_exp.groupby("類別")["金額"].sum().reset_index(), on="類別", how="left").fillna(0).rename(columns={"金額": "實際支出"})
        an_df = an_df.merge(m_bud[["類別", "預算金額"]], on="類別", how="left").fillna(0) if not m_bud.empty else an_df.assign(預算金額=0.0)
        an_df["差異"] = an_df["預算金額"] - an_df["實際支出"]
        for _, r in an_df.iterrows():
            pct = min(r["實際支出"] / r["預算金額"], 1.0) if r["預算金額"] > 0 else (1.0 if r["實際支出"] > 0 else 0.0)
            c1, c2 = st.columns([1, 1])
            c1.write(f"**{r['類別']}**: 實 ${r['實際支出']:,.0f} / 預 ${r['預算金額']:,.0f}")
            c2.progress(pct)
        if act_tot > 0:
            st.plotly_chart(px.pie(an_df[an_df["實際支出"] > 0], values="實際支出", names="類別", hole=0.4), use_container_width=True)

with t4:
    st.subheader("📋 歷史支出紀錄")
    if not df_exp.empty:
        st.dataframe(df_exp[["日期", "類別", "金額", "備忘錄"]], hide_index=True, use_container_width=True)
