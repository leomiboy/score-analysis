import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection

# --- 1. 網頁設定 ---
st.set_page_config(page_title="學生多科錯題分析", layout="wide")
st.title("📊 學生各科錯題知識點分析系統")
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
        
        # 解析結構 (假設所有科目格式一致)
        # Row 1 (Index 0): 題號
        # Row 3 (Index 2): 知識點
        # Row 6 (Index 5) Start: 學生資料
        
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
            # 判斷邏輯：不為 "-", 不為空
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
    # 先讀取國文科來建立學生名單下拉選單
    df_main = conn.read(worksheet="國文", ttl=0, header=None)
    student_list_raw = df_main.iloc[5:, 1] # B欄
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
            
            # 呼叫上面的函式進行分析
            result_df, error_msg = get_student_errors(subject, selected_student)
            
            if error_msg:
                if "找不到" in error_msg:
                    st.warning(f"在 {subject} 科找不到此學生的資料 (可能是缺考或名單不一致)。")
                else:
                    st.error(f"資料讀取失敗: {error_msg}")
            
            elif result_df is not None and not result_df.empty:
                # 顯示錯題數
                st.warning(f"⚠️ 共發現 {len(result_df)} 題錯題")
                
                # 顯示表格
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
                
                # 顯示重點標籤
                tags = result_df["需加強觀念 (知識點)"].unique()
                tag_html = ""
                for tag in tags:
                    tag_html += f'<span style="background-color:#ff4b4b; color:white; padding:4px 8px; border-radius:5px; margin-right:5px; font-size:0.9em;">{tag}</span>'
                st.markdown(f"**重點複習：** {tag_html}", unsafe_allow_html=True)
                
            else:
                # 全對的情況
                st.success(f"🎉 太棒了！{subject}科全對，沒有錯題！")

else:
    st.info("👈 請從左側選單選擇學生姓名。")