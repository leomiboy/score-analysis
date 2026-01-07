import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection

# --- 1. 網頁設定 ---
st.set_page_config(page_title="909班複習考分析", layout="wide")
st.title("📊 909班第2次複習考1-4冊各科錯題知識點分析系統")
st.markdown("---")

# --- 2. 連接 Google Sheets ---
conn = st.connection("gsheets", type=GSheetsConnection)

# 定義科目與對應的工作表名稱
SUBJECTS = ["國文", "英文", "數學", "社會", "自然"]

# --- 3. 核心分析函式 ---
def get_student_errors(sheet_name, student_name):
    """
    讀取指定工作表，並回傳該學生的錯題 DataFrame
    """
    try:
        # 讀取指定的工作表
        df = conn.read(worksheet=sheet_name, ttl=0, header=None)
        
        # 解析結構
        question_numbers = df.iloc[0, 2:].values
        knowledge_points = df.iloc[2, 2:].values
        
        # 整理學生資料區塊
        student_data = df.iloc[5:, 1:].reset_index(drop=True)
        student_data.columns = ["Name"] + [i for i in range(len(student_data.columns)-1)]
        
        # 找到該學生
        student_row = student_data[student_data["Name"] == student_name]
        
        if student_row.empty:
            return None, "找不到該學生資料"
            
        student_row = student_row.iloc[0]
        
        # 篩選錯題
        error_data = []
        for answer, knowledge, q_num in zip(student_row[1:], knowledge_points, question_numbers):
            ans_str = str(answer).strip()
            if ans_str != "-" and pd.notna(answer) and ans_str != "":
                error_data.append({
                    "題號": q_num,
                    "誤選答案": ans_str,
                    "需加強觀念 (知識點)": knowledge
                })
                
        return pd.DataFrame(error_data), None

    except Exception as e:
        return None, f"讀取錯誤: {e}"

# --- 4. 取得學生名單 (以國文科為準) ---
try:
    df_main = conn.read(worksheet="國文", ttl=0, header=None)
    student_list_raw = df_main.iloc[5:, 1]
    student_list = student_list_raw.dropna().unique().tolist()
except Exception as e:
    st.error(f"無法讀取「國文」工作表以建立名單，請確認工作表名稱是否正確。\n錯誤訊息: {e}")
    st.stop()

# --- 5. 網頁互動介面 ---

# 側邊欄
selected_student = st.sidebar.selectbox("🔍 請選擇學生姓名：", student_list)
st.sidebar.markdown("---")
st.sidebar.info("💡 切換上方分頁可查看不同科目")

if selected_student:
    st.header(f"👤 學生：{selected_student}")
    
    # 建立 5 個分頁籤
    tabs = st.tabs(SUBJECTS)
    
    # 迴圈處理每一個科目
    for i, subject in enumerate(SUBJECTS):
        with tabs[i]:
            st.subheader(f"📖 {subject}科 分析結果")
            
            # 呼叫函式進行分析
            result_df, error_msg = get_student_errors(subject, selected_student)
            
            if error_msg:
                if "找不到" in error_msg:
                    st.warning(f"在 {subject} 科找不到此學生的資料。")
                else:
                    st.error(f"資料讀取失敗: {error_msg}")
            
            elif result_df is not None and not result_df.empty:
                
                # --- 重點複習區塊 (美化版) ---
                st.markdown("### 📌 重點複習 (依錯誤次數排序)")
                st.markdown("以下數字代表該知識點的**錯題數量**：")
                
                # 計算每個知識點出現的次數
                knowledge_counts = result_df["需加強觀念 (知識點)"].value_counts()
                
                # 遍歷每一個知識點，生成美化的 HTML
                for knowledge, count in knowledge_counts.items():
                    
                    # 設定顏色邏輯
                    if count >= 2:
                        # 深紅色 (錯2題以上)
                        bg_color = "#c62828" 
                        border_color = "#c62828"
                    else:
                        # 淺紅色/橘色 (錯1題)
                        bg_color = "#ff7043" 
                        border_color = "#ff7043"
                    
                    # 生成 HTML 卡片
                    # 修正重點：justify-content: center; (CSS語法修正)
                    st.markdown(
                        f"""
                        <div style="display: flex; align-items: stretch; margin-bottom: 12px;">
                            <!-- 左側數字區塊 -->
                            <div style="
                                background-color: {bg_color};
                                color: white;
                                width: 60px;
                                flex-shrink: 0;
                                display: flex;
                                align-items: center;
                                justify-content: center;
                                font-size: 28px;
                                font-weight: 900;
                                font-style: italic;
                                border-radius: 10px 0 0 10px;
                                border: 2px solid {bg_color};
                            ">
                                {count}
                            </div>
                            <!-- 右側文字區塊 -->
                            <div style="
                                background-color: white;
                                color: #333;
                                flex-grow: 1;
                                padding: 10px 15px;
                                border: 2px solid {border_color};
                                border-left: none;
                                border-radius: 0 10px 10px 0;
                                display: flex;
                                align-items: center;
                                font-size: 18px;
                                font-weight: bold;
                                box-shadow: 2px 2px 5px rgba(0,0,0,0.1);
                            ">
                                {knowledge}
                            </div>
                        </div>
                        """, 
                        unsafe_allow_html=True
                    )
                
                st.markdown("---")
                
                # --- 顯示錯題總數警告 ---
                st.warning(f"⚠️ 共發現 {len(result_df)} 題錯題，詳細列表如下：")
                
                # --- 顯示詳細表格 ---
                st.dataframe(
                    result_df, 
                    hide_index=True, 
                    use_container_width=True,
                    column_config={
                        "題號": st.column_config.TextColumn("題號", width="small"),
                        "誤選答案": st.column_config.TextColumn("誤選", width="small"),
                        "需加強觀念 (知識點)": st.column_config.TextColumn("需加強觀念", width="large"),
                    }
                )
                
            else:
                st.success(f"🎉 太棒了！{subject}科全對，沒有錯題！")

else:
    st.info("👈 請從左側選單選擇學生姓名。")