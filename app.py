import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
import time # 引入時間模組，用來控制讀取速度

# --- 1. 網頁設定與 CSS ---
st.set_page_config(page_title="909班複習考分析", layout="wide")

st.markdown("""
<style>
    button[data-baseweb="tab"] {
        font-size: 22px !important;
        font-weight: 700 !important;
        padding: 10px 20px !important;
    }
    .scrollable-container {
        height: 550px;
        overflow-y: auto;
        overflow-x: auto;
        padding-right: 10px;
        padding-bottom: 10px;
        border: 1px solid #f0f2f6;
        border-radius: 8px;
        background-color: #ffffff;
    }
    thead tr th:first-child {display:none}
    tbody th {display:none}
</style>
""", unsafe_allow_html=True)

st.title("📊 909班第2次複習考1-4冊各科錯題知識點分析系統")
st.markdown("---")

# --- 2. 連接 Google Sheets ---
conn = st.connection("gsheets", type=GSheetsConnection)
SUBJECTS = ["國文", "英文", "數學", "社會", "自然"]

# --- 3. 智慧型讀取函式 (加入自動重試機制) ---
@st.cache_data(ttl=600)
def load_sheet_data(sheet_name):
    """
    讀取資料，若遇到 429 錯誤 (讀太快)，會自動等待並重試
    """
    max_retries = 5  # 最多重試 5 次
    delay = 2        # 每次等待 2 秒
    
    for attempt in range(max_retries):
        try:
            # 嘗試讀取
            df = conn.read(worksheet=sheet_name, header=None)
            return df
            
        except Exception as e:
            error_msg = str(e)
            # 如果錯誤訊息包含 429 (Quota exceeded)，代表太快了
            if "429" in error_msg:
                if attempt < max_retries - 1:
                    # 顯示一個小小的等待訊息 (只在後台運作)
                    time.sleep(delay * (attempt + 1)) # 越試越慢 (2s, 4s, 6s...)
                    continue # 重新執行迴圈
                else:
                    st.error(f"讀取「{sheet_name}」失敗，系統忙碌中，請過幾分鐘再試。")
                    return None
            else:
                # 如果是其他錯誤 (例如找不到工作表)，直接報錯
                st.error(f"讀取「{sheet_name}」發生未知錯誤：{error_msg}")
                return None
    return None

# --- 4. 核心分析函式 ---
def get_student_data(sheet_name, student_name):
    # 呼叫上面的智慧讀取函式
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
        return "<div style='color:gray; padding:10px;'>無錯題資料</div>"

    grouped = df.groupby("知識點").apply(lambda x: pd.Series({
        "count": len(x),
        "q_list": sorted(x["題號"].tolist(), key=lambda k: int(k) if str(k).isdigit() else 999),
        "first_q_sort": x["題號排序用"].min()
    })).reset_index()

    grouped = grouped[grouped["count"] >= min_errors]
    
    if grouped.empty:
        return "<div style='color:gray; padding:10px;'>無符合條件的項目</div>"

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
        <div style="display: flex; align-items: stretch; margin-bottom: 10px; min-width: 200px;">
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
                white-space: nowrap;
            ">
                {display_text}
            </div>
        </div>
        """
    return html_content

# --- 5. 取得學生名單 ---
try:
    # 這裡也會使用智慧讀取
    df_main = load_sheet_data("國文")
    
    if df_main is not None:
        student_list = df_main.iloc[5:, 1].dropna().unique().tolist()
    else:
        st.stop() # 停止執行
        
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
    
    # --- A. 五科總覽 ---
    with tabs[0]:
        st.subheader("🏆 重點複習總覽 (僅列出錯 2 題以上)")
        st.caption("※ 欄位內可上下滑動查看更多，左右滑動查看完整文字")
        
        cols = st.columns(5)
        
        for i, subject in enumerate(SUBJECTS):
            with cols[i]:
                st.markdown(f"<h4 style='text-align: center;'>{subject}</h4>", unsafe_allow_html=True)
                
                df_error, msg = get_student_data(subject, selected_student)
                
                if df_error is not None and not df_error.empty:
                    cards_html = generate_knowledge_cards_html(df_error, min_errors=2)
                else:
                    cards_html = "<div style='text-align:center; color:#aaa;'>無重點項目</div>"
                
                st.markdown(
                    f"""
                    <div class="scrollable-container">
                        {cards_html}
                    </div>
                    """, 
                    unsafe_allow_html=True
                )

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
                st.markdown(cards_html, unsafe_allow_html=True)
                
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