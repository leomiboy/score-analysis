import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection

# --- 1. 網頁設定 ---
st.set_page_config(page_title="學生成績錯題分析", layout="wide")
st.title("📊 學生錯題知識點分析系統")
st.markdown("---")

# --- 2. 連接 Google Sheets ---
# 這裡會自動去讀取 Streamlit Secrets 裡的設定
conn = st.connection("gsheets", type=GSheetsConnection)

try:
    # 讀取整份表格，不設 header，我們手動處理
    # ttl=0 代表不快取，每次重新整理都抓最新資料
    df = conn.read(worksheet="工作表1", ttl=0, header=None) 
except Exception as e:
    st.error("無法讀取資料，請檢查：\n1. Google Sheet 是否已共用給服務帳戶 email？\n2. Secrets 設定是否正確？")
    st.stop()

# --- 3. 資料處理邏輯 (根據你的截圖結構) ---
# 試算表結構假設：
# Row 1 (Index 0): 題號 (1, 2, 3...)
# Row 3 (Index 2): 測驗內涵/知識點 (連詞運用, 成語的使用...)
# Row 6 (Index 5) 開始: 學生資料
# Col B (Index 1): 姓名
# Col C (Index 2) 開始: 題目答案

try:
    # 提取標題資訊
    question_numbers = df.iloc[0, 2:].values  # 第1列的題號
    knowledge_points = df.iloc[2, 2:].values  # 第3列的知識點

    # 提取學生資料 (從第6列開始，取 B欄以後)
    # reset_index 讓索引重新從 0 開始
    student_data_raw = df.iloc[5:, 1:].reset_index(drop=True)
    
    # 重新命名欄位：第一欄是 Name，後面是題目索引 0, 1, 2...
    new_columns = ["Name"] + [i for i in range(len(student_data_raw.columns)-1)]
    student_data_raw.columns = new_columns

except Exception as e:
    st.error(f"資料格式解析錯誤，請檢查試算表結構是否變更。\n錯誤訊息: {e}")
    st.stop()

# --- 4. 網頁互動介面 ---

# 側邊欄：選擇學生
# 過濾掉空值 (NaN) 的姓名
student_list = student_data_raw["Name"].dropna().unique().tolist()
selected_student = st.sidebar.selectbox("🔍 請選擇學生姓名：", student_list)

if selected_student:
    st.header(f"👤 學生：{selected_student}")
    
    # 找到該學生的那一列資料
    student_row = student_data_raw[student_data_raw["Name"] == selected_student].iloc[0]
    
    # 準備一個清單來存錯題
    error_data = []
    
    # 遍歷每一題
    # zip 函數把「學生答案」、「知識點」、「題號」打包在一起處理
    # student_row[1:] 代表該學生的所有答案 (排除姓名)
    for answer, knowledge, q_num in zip(student_row[1:], knowledge_points, question_numbers):
        
        # 判斷邏輯：
        # 1. 答案不是 "-" (破折號代表對)
        # 2. 答案不是空值 (避免讀到後面空白的格子)
        # 3. 答案不是空白字串
        ans_str = str(answer).strip()
        if ans_str != "-" and pd.notna(answer) and ans_str != "":
            error_data.append({
                "題號": q_num,
                "誤選答案": ans_str,
                "需加強觀念 (知識點)": knowledge
            })
    
    # --- 顯示結果 ---
    if len(error_data) > 0:
        st.warning(f"⚠️ 共發現 {len(error_data)} 題錯題")
        
        # 轉成 DataFrame 顯示表格
        result_df = pd.DataFrame(error_data)
        
        # 顯示漂亮的表格
        st.dataframe(
            result_df, 
            hide_index=True, 
            use_container_width=True
        )
        
        # 額外功能：顯示重點標籤
        st.subheader("📌 重點複習關鍵字")
        tags = result_df["需加強觀念 (知識點)"].unique()
        
        # 用漂亮的標籤顯示
        tag_html = ""
        for tag in tags:
            tag_html += f'<span style="background-color:#ff4b4b; color:white; padding:4px 8px; border-radius:5px; margin-right:5px;">{tag}</span>'
        st.markdown(tag_html, unsafe_allow_html=True)
        
    else:
        st.balloons()
        st.success("🎉 太棒了！全對，沒有錯題！")

else:
    st.info("👈 請從左側選單選擇學生姓名以查看分析。")