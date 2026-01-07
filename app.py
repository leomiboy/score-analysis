import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
import time

# --- 1. 網頁設定與 CSS ---
st.set_page_config(page_title="909班複習考分析", layout="wide")

st.markdown("""
<style>
    /* 加大分頁標籤 (Tabs) 的字體與舒適度 */
    button[data-baseweb="tab"] {
        font-size: 22px !important;
        font-weight: 700 !important;
        padding: 10px 20px !important;
    }
    
    /* 隱藏 Streamlit 預設的 dataframe 索引欄 */
    thead tr th:first-child {display:none}
    tbody th {display:none}
    
    /* 調整總覽頁面的標題間距 */
    .subject-header {
        margin-top: 20px;
        margin-bottom: 10px;
        padding-bottom: 5px;
        border-bottom: 2px solid #f0f2f6;
        color: #0e1117;
    }
</style>
""", unsafe_allow_html=True)

st.title("📊 909班第2次複習考1-4冊各科錯題知識點分析系統")
st.markdown("---")

# --- 2. 連接 Google Sheets ---
conn = st.connection("gsheets", type=GSheetsConnection)
SUBJECTS = ["國文", "英文", "數學", "社會", "自然"]

# --- 3. 智慧型讀取函式 (含重試機制) ---
@st.cache_data(ttl=600)
def load_sheet_data(sheet_name):
    max_retries = 5
    delay = 2
    for attempt in range(max_retries):
        try:
            df = conn.read(worksheet=sheet_name, header=None)
            return df
        except Exception as e:
            error_msg = str(e)
            if "429" in error_msg:
                if attempt < max_retries - 1:
                    time.sleep(delay * (attempt + 1))
                    continue
                else:
                    st.error(f"讀取「{sheet_name}」失敗，系統忙碌中，請過幾分鐘再試。")
                    return None
            else:
                st.error(f"讀取「{sheet_name}」發生未知錯誤：{error_msg}")
                return None
    return None

# --- 4. 核心分析函式 ---
def get_student_data(sheet_name, student_name):
    df = load_sheet_data(sheet_name)
    if df is None:
        return None, "讀取失敗"

    try:
        question_numbers = df.iloc[0, 2:].values
        knowledge_points = df.iloc[2, 2:].values
        
        student_data = df.iloc[5:, 1:].reset_index(drop=True)
        student_data.columns = ["Name"] + [i for i in range(len(student_data.columns)-1)]
        
        student_row = student_data[student_data["Name"] == student_name]
        
        if student_row.empty:
            return None, "找不到資料"
            
        student_row = student_row.iloc[0]
        
        error_list = []
        for answer, knowledge, q_num in zip(student_row[1:], knowledge_points, question_numbers):
            ans_str = str(answer).strip()
            if ans_str != "-" and pd.notna(answer) and ans_str != "":
                try:
                    q_num_sort = int(q_num)
                except:
                    q_num_sort = 999
                
                error_list.append({
                    "題號": q_num,
                    "題號排序用": q_num_sort,
                    "誤選答案": ans_str,
                    "知識點": knowledge
                })
        
        return pd.DataFrame(error_list), None

    except Exception as e:
        return None, str(e)

def generate_knowledge_cards_html(df, min_errors=1):
    if df is None or df.empty:
        return None # 回傳 None 方便外部判斷

    grouped = df.groupby("知識點").apply(lambda x: pd.Series({
        "count": len(x),
        "q_list": sorted(x["題號"].tolist(), key=lambda k: int(k) if str(k).isdigit() else 999),
        "first_q_sort": x["題號排序用"].min()
    })).reset_index()

    grouped = grouped[grouped["count"] >= min_errors]
    
    if grouped.empty:
        return None # 回傳 None 代表沒有符合條件的項目

    grouped = grouped.sort_values(by=["count", "first_q_sort"], ascending=[False, True])

    html_content = ""
    for _, row in grouped.iterrows():
        count = row["count"]
        knowledge = row["知識點"]
        q_list_str = ", ".join([str(q) for q in row["q_list"]])
        display_text = f"(第{q_list_str}題) {knowledge}"

        if count >= 2:
            bg_color = "#c62828"
            border_color = "#c62828"
        else:
            bg_color = "#ff7043"
            border_color = "#ff7043"

        html_content += f"""
        <div style="display: flex; align-items: stretch; margin-bottom: 10px;">
            <div style="
                background-color: {bg_color};
                color: white;
                width: 50px;
                flex-shrink: 0;
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 24px;
                font-weight: 900;
                font-style: italic;
                border-radius: 8px 0 0 8px;
                border: 2px solid {bg_color};
            ">
                {count}
            </div>
            <div style="
                background-color: white;
                color: #333;
                flex-grow: 1;
                padding: 8px 12px;
                border: 2px solid {border_color};
                border-left: none;
                border-radius: 0 8px 8px 0;
                display: flex;
                align-items: center;
                font-size: 16px;
                font-weight: bold;
            ">
                {display_text}
            </div>
        </div>
        """
    return html_content

# --- 5. 取得學生名單 ---
try:
    df_main = load_sheet_data("國文")
    if df_main is not None:
        student_list = df_main.iloc[5:, 1].dropna().unique().tolist()
    else:
        st.stop()
except Exception as e:
    st.error(f"程式執行錯誤: {e}")
    st.stop()

# --- 6. 網頁互動介面 ---

selected_student = st.sidebar.selectbox("🔍 請選擇學生姓名：", student_list)
st.sidebar.markdown("---")
st.sidebar.info("💡 **五科總覽**：僅顯示錯 2 題以上的重點項目。\n\n💡 **各科分頁**：顯示該科所有錯題詳情。")

if selected_student:
    st.header(f"👤 學生：{selected_student}")
    
    all_tabs = ["五科總覽"] + SUBJECTS
    tabs = st.tabs(all_tabs)
    
    # --- A. 五科總覽 (垂直版面) ---
    with tabs[0]:
        st.subheader("🏆 重點複習總覽 (僅列出錯 2 題以上)")
        
        for subject in SUBJECTS:
            # 顯示科目標題
            st.markdown(f"<h3 class='subject-header'>📘 {subject}</h3>", unsafe_allow_html=True)
            
            df_error, msg = get_student_data(subject, selected_student)
            
            has_content = False
            if df_error is not None and not df_error.empty:
                # 產生 HTML (min_errors=2)
                cards_html = generate_knowledge_cards_html(df_error, min_errors=2)
                
                if cards_html:
                    st.markdown(cards_html, unsafe_allow_html=True)
                    has_content = True
            
            # 如果該科沒有錯2題以上的項目，顯示鼓勵文字
            if not has_content:
                st.caption(f"👏 {subject}科表現良好，無錯 2 題以上之知識點。")

    # --- B. 各科詳細 ---
    for i, subject in enumerate(SUBJECTS):
        with tabs[i+1]:
            st.subheader(f"📖 {subject}科 完整分析")
            
            df_error, msg = get_student_data(subject, selected_student)
            
            if msg:
                st.warning(f"訊息: {msg}")
            elif df_error is not None and not df_error.empty:
                
                st.markdown("### 📌 重點複習 (依錯誤次數排序)")
                st.markdown("以下數字代表該知識點的**錯題數量**，括號內為**題號**：")
                
                cards_html = generate_knowledge_cards_html(df_error, min_errors=1)
                if cards_html:
                    st.markdown(cards_html, unsafe_allow_html=True)
                else:
                    st.info("無錯題資料")
                
                st.markdown("---")
                
                st.warning(f"⚠️ 共發現 {len(df_error)} 題錯題，詳細列表如下：")
                
                display_df = df_error[["題號", "誤選答案", "知識點"]].copy()
                
                st.dataframe(
                    display_df, 
                    hide_index=True, 
                    use_container_width=True,
                    column_config={
                        "題號": st.column_config.TextColumn("題號", width="small"),
                        "誤選答案": st.column_config.TextColumn("誤選", width="small"),
                        "知識點": st.column_config.TextColumn("需加強觀念", width="large"),
                    }
                )
            else:
                st.success(f"🎉 {subject}科全對，太強了！")

else:
    st.info("👈 請從左側選單選擇學生姓名。")