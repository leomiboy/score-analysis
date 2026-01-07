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
            
            # 呼叫函式進行分析
            result_df, error_msg = get_student_errors(subject, selected_student)
            
            if error_msg:
                if "找不到" in error_msg:
                    st.warning(f"在 {subject} 科找不到此學生的資料 (可能是缺考或名單不一致)。")
                else:
                    st.error(f"資料讀取失敗: {error_msg}")
            
            elif result_df is not None and not result_df.empty:
                
                # --- 新增功能：重點複習排名 (移到最上方) ---
                st.markdown("### 📌 重點複習 (依錯誤次數排序)")
                
                # 計算每個知識點出現的次數
                knowledge_counts = result_df["需加強觀念 (知識點)"].value_counts()
                
                # 找出前兩名的「次數」是多少 (例如第一名錯5題，第二名錯3題)
                unique_counts = sorted(knowledge_counts.unique(), reverse=True)
                
                # 設定閾值：只要次數大於等於第二名的次數，都算前兩名
                if len(unique_counts) >= 2:
                    threshold = unique_counts[1]
                elif len(unique_counts) == 1:
                    threshold = unique_counts[0]
                else:
                    threshold = 0

                # 顯示排名列表
                for knowledge, count in knowledge_counts.items():
                    # 判斷是否為前兩名 (字體放大)
                    if count >= threshold:
                        # 放大 200% 並加粗，使用紅色強調
                        st.markdown(
                            f'<div style="font-size: 200%; font-weight: bold; color: #d32f2f; margin-bottom: 5px;">'
                            f'【{knowledge}】 共 {count} 題</div>', 
                            unsafe_allow_html=True
                        )
                    else:
                        # 正常大小
                        st.markdown(
                            f'<div style="font-size: 110%; margin-bottom: 5px;">'
                            f'【{knowledge}】 共 {count} 題</div>', 
                            unsafe_allow_html=True
                        )
                
                st.markdown("---") # 分隔線
                
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
                # 全對的情況
                st.success(f"🎉 太棒了！{subject}科全對，沒有錯題！")

else:
    st.info("👈 請從左側選單選擇學生姓名。")