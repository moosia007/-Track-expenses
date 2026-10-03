import streamlit as st
import pandas as pd
import plotly.express as px
from supabase import create_client, Client

# 1. 連接 Supabase 雲端資料庫
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

st.set_page_config(page_title="個人雲端記帳本", page_icon="💰", layout="centered")

# 2. 個人身分識別與紀錄管理
st.title("💰 個人雲端記帳本")

user_email = st.text_input("請輸入您的 Email 作為專屬帳號標籤：", value="").strip().lower()

if not user_email:
    st.warning("請先輸入您的 Email 才能開始使用專屬帳本！")
else:
    st.success(f"目前使用帳號：`{user_email}`")
    st.markdown("---")

    # 3. 新增記帳（儲存時附帶 user_email）
    with st.form("add_expense_form", clear_on_submit=True):
        st.subheader("➕ 新增支出")
        date = st.date_input("日期")
        category = st.selectbox("類別", ["餐飲", "交通", "娛樂", "日常", "其他"])
        amount = st.number_input("金額", min_value=0.0, step=1.0)
        note = st.text_input("備註")
        submit = st.form_submit_button("新增紀錄")

        if submit:
            if amount <= 0:
                st.error("請輸入大於 0 的金額！")
            else:
                data = {
                    "user_email": user_email,
                    "date": str(date),
                    "category": category,
                    "amount": amount,
                    "note": note
                }
                supabase.table("expenses").insert(data).execute()
                st.success("成功新增紀錄！")
                st.rerun()

    # 4. 讀取與顯示紀錄（只讀取該使用者的資料）
    st.subheader("📋 歷史紀錄")
    response = supabase.table("expenses").select("*").eq("user_email", user_email).execute()
    records = response.data

    if records:
        df = pd.DataFrame(records)
        st.dataframe(df[["date", "category", "amount", "note"]], use_container_width=True)

        # 圖表分析
        fig = px.pie(df, values="amount", names="category", title="支出分類統計")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("目前還沒有任何記帳紀錄，趕快新增第一筆吧！")
