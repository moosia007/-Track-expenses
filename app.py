import streamlit as st
import pandas as pd
import plotly.express as px
from supabase import create_client, Client

# 1. 連接 Supabase 雲端資料庫
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

st.set_page_config(
    page_title="手機記帳與預算本", page_icon="💰", initial_sidebar_state="collapsed"
)

# 預設支出類別列表
CATEGORIES = [
    "🍔 飲食",
    "🛒 日常用品",
    "🚗 交通出行",
    "🎮 娛樂休閒",
    "👔 服飾美容",
    "📱 數位訂閱",
    "🏥 醫療健康",
    "📦 其他",
]

st.title("💰 記帳與預算管家")

# 2. 個人身分識別 (Email 帳號隔離)
user_email = st.text_input("🔑 請輸入您的 Email 作為專屬帳號標籤：", value="").strip().lower()

if not user_email:
    st.info("👋 請先在上方輸入您的 Email，系統將載入您的專屬記帳與預算資料庫！")
else:
    st.success(f"目前使用帳號：`{user_email}`")
    st.markdown("---")

    # 四個功能頁籤
    tab1, tab2, tab3, tab4 = st.tabs(
        ["➕ 新增記帳", "🎯 預算規劃", "📊 結算與分析", "📋 明細管理"]
    )

    # ----------------- Tab 1: 新增記帳 -----------------
    with tab1:
        st.subheader("新增支出")
        with st.form("add_form", clear_on_submit=True):
            date_input = st.date_input("日期")
            category_input = st.selectbox("類別", CATEGORIES)
            amount_input = st.number_input(
                "金額 (NTD)", min_value=1, step=10, value=100
            )
            note_input = st.text_input("備忘錄", placeholder="備註（選填）")

            submit_button = st.form_submit_button(
                "新增這筆支出", use_container_width=True
            )

            if submit_button:
                data = {
                    "user_email": user_email,
                    "date": str(date_input),
                    "category": category_input,
                    "amount": amount_input,
                    "note": note_input
                }
                supabase.table("expenses").insert(data).execute()
                st.success("已儲存支出！")
                st.rerun()

    # ----------------- Tab 2: 預算規劃 -----------------
    with tab2:
        st.subheader("🎯 每月收入與預算設定")

        c_y, c_m = st.columns(2)
        selected_year = c_y.number_input(
            "年份", min_value=2020, max_value=2030, value=pd.Timestamp.now().year
        )
        selected_month = c_m.number_input(
            "月份", min_value=1, max_value=12, value=pd.Timestamp.now().month
        )
        ym_key = f"{selected_year}-{selected_month:02d}"

        # 安全讀取該使用者、該年月的預算
        try:
            bud_resp = supabase.table("budgets").select("*").eq("user_email", user_email).eq("ym", ym_key).execute()
            existing_bud = pd.DataFrame(bud_resp.data) if bud_resp.data else pd.DataFrame()
        except Exception:
            existing_bud = pd.DataFrame()

        init_income = (
            float(existing_bud["income"].iloc[0]) if not existing_bud.empty and "income" in existing_bud.columns else 50000.0
        )

        with st.form("budget_form"):
            income_input = st.number_input(
                "💵 本月預估總收入", min_value=0.0, step=1000.0, value=init_income
            )
            st.markdown("---")
            st.write("💡 **各類別預算分配**：")

            cat_budgets = {}
            for cat in CATEGORIES:
                cat_val = 0.0
                if not existing_bud.empty and "category" in existing_bud.columns and "budget_amount" in existing_bud.columns:
                    match = existing_bud[existing_bud["category"] == cat]
                    if not match.empty:
                        cat_val = float(match["budget_amount"].iloc[0])

                cat_budgets[cat] = st.number_input(
                    f"{cat} 預算", min_value=0.0, step=500.0, value=cat_val, key=f"bud_{cat}"
                )

            total_alloc_budget = sum(cat_budgets.values())
            st.info(f"當前分配預算總計：NT$ {total_alloc_budget:,.0f}")

            save_bud_btn = st.form_submit_button(
                "儲存預算設定", use_container_width=True
            )

            if save_bud_btn:
                supabase.table("budgets").delete().eq("user_email", user_email).eq("ym", ym_key).execute()
                new_bud_rows = []
                for cat, bud_val in cat_budgets.items():
                    new_bud_rows.append(
                        {
                            "user_email": user_email,
                            "ym": ym_key,
                            "income": income_input,
                            "category": cat,
                            "budget_amount": bud_val,
                        }
                    )
                supabase.table("budgets").insert(new_bud_rows).execute()
                st.success(f"已儲存 {ym_key} 的預算設定！")
                st.rerun()

    # 安全從 Supabase 讀取支出全量資料
    try:
        exp_resp = supabase.table("expenses").select("*").eq("user_email", user_email).order("date", descending=True).execute()
        df_exp = pd.DataFrame(exp_resp.data) if exp_resp.data else pd.DataFrame()
    except Exception:
        df_exp = pd.DataFrame()

    if not df_exp.empty and "date" in df_exp.columns:
        df_exp["date"] = pd.to_datetime(df_exp["date"])
        df_exp["年月"] = df_exp["date"].dt.strftime("%Y-%m")

    # ----------------- Tab 3: 結算與分析 -----------------
    with tab3:
        st.subheader("📊 月度預算 vs 實際支出結算")

        if df_exp.empty or "年月" not in df_exp.columns:
            st.info("尚無記帳資料，請先新增支出！")
        else:
            available_months = sorted(df_exp["年月"].unique(), reverse=True)
            sel_ym = st.selectbox("選擇結算月份", available_months)

            m_exp = df_exp[df_exp["年月"] == sel_ym]

            try:
                b_resp = supabase.table("budgets").select("*").eq("user_email", user_email).eq("ym", sel_ym).execute()
                m_bud = pd.DataFrame(b_resp.data) if b_resp.data else pd.DataFrame()
            except Exception:
                m_bud = pd.DataFrame()

            actual_total_exp = m_exp["amount"].sum() if not m_exp.empty else 0.0
            income_val = float(m_bud["income"].iloc[0]) if not m_bud.empty and "income" in m_bud.columns else 0.0
            total_budget_val = float(m_bud["budget_amount"].sum()) if not m_bud.empty and "budget_amount" in m_bud.columns else 0.0

            col_a, col_b, col_c = st.columns(3)
            col_a.metric("本月總收入", f"NT$ {income_val:,.0f}")
            col_b.metric("本月預算", f"NT$ {total_budget_val:,.0f}")
            col_c.metric("實際總支出", f"NT$ {actual_total_exp:,.0f}", delta=f"{total_budget_val - actual_total_exp:,.0f} (剩餘預算)")

            st.markdown("---")
            col_chart1, col_chart2 = st.columns(2)
            with col_chart1:
                if not m_exp.empty:
                    fig_pie = px.pie(m_exp, values="amount", names="category", title="本月支出類別占比", hole=0.4)
                    st.plotly_chart(fig_pie, use_container_width=True)
                else:
                    st.info("本月尚無支出")

            with col_chart2:
                if not m_exp.empty:
                    cat_summary = m_exp.groupby("category")["amount"].sum().reset_index()
                    if not m_bud.empty and "category" in m_bud.columns and "budget_amount" in m_bud.columns:
                        merged_df = pd.merge(m_bud[["category", "budget_amount"]], cat_summary, on="category", how="left").fillna(0)
                        merged_df.columns = ["類別", "預算金額", "實際支出"]
                        merged_df["差額 (預算-實際)"] = merged_df["預算金額"] - merged_df["實際支出"]
                        st.write("📋 **各類別預算執行狀況**")
                        st.dataframe(merged_df, use_container_width=True)
                    else:
                        st.warning("⚠️ 該月份尚未設定預算，可前往「🎯 預算規劃」進行設定！")

    # ----------------- Tab 4: 明細管理 -----------------
    with tab4:
        st.subheader("📋 歷史支出明細與管理")

        if df_exp.empty:
            st.info("目前沒有任何支出紀錄。")
        else:
            for _, row in df_exp.iterrows():
                r_col1, r_col2, r_col3, r_col4, r_col5 = st.columns([2, 2, 2, 3, 1])
                r_col1.write(f"📅 {row['date'].strftime('%Y-%m-%d')}")
                r_col2.write(f"{row['category']}")
                r_col3.write(f"💵 **${row['amount']:,.0f}**")
                r_col4.write(f"💬 {row.get('note', '-') or '-'}")
                
                if r_col5.button("🗑️", key=f"del_{row['id']}"):
                    supabase.table("expenses").delete().eq("id", row["id"]).execute()
                    st.toast("已成功刪除該筆紀錄！")
                    st.rerun()
