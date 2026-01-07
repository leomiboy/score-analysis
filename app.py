import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection

# --- 1. 網頁設定與 CSS 優化 ---
st.set_page_config(page_title="909班複習考分析", layout="wide")

# 自定義 CSS
st.markdown("""
<style>
    /* 1. 加大分頁標籤 (Tabs) 的字體與舒適度 */
    button[data-baseweb="tab"] {
        font-size: 22px !important;
        font-weight: 700 !important;
        padding: 10px 20px !important;
    }
    
    /* 2. 針對總覽頁面的捲動容器設定 */
    .scrollable-container {
        height: 550px; /* 設定固定高度，約可放6個項目 */
        overflow-y: auto; /* 垂直捲軸 */
        overflow-x: auto; /* 水平捲軸 */
        padding-right: 10px;
        padding-bottom: 10px;
        border: 1px solid #f0f2f6;
        border-radius: 8px;
        background-color: #ffffff;
    }
    
    /* 3. 隱藏 Streamlit 預設的 dataframe 索引欄 (如果有的話) */
    thead tr th:first-child {display:none}
    tbody th {display:none}
</style>
""", unsafe_allow_html=True)

st.title("📊 909班第2次複習考1-4冊各科錯題知識點分析系統")
st.markdown("---")

# --- 2. 連接 Google Sheets ---
conn = st.connection("gsheets", type=GSheetsConnection)

# 定義科目順序
SUBJECTS = ["國文", "英文", "數學", "社會", "自然"]

# --- 3. 核心分析函式 ---
def get_student_data(sheet_name, student_name):
    """
    讀取指定工作表，回傳該學生的原始錯題資料 (DataFrame)
    """
    try:
        df = conn.read(worksheet=sheet_name, ttl=0, header=None)
        
        # 解析結構
        # Row 1 (Index 0): 題號
        # Row 3 (Index 2): 知識點
        question_numbers = df.iloc[0, 2:].values
        knowledge_points = df.iloc[2, 2:].values
        
        # 整理學生資料
        student_data = df.iloc[5:, 1:].reset_index(drop=True)
        student_data.columns = ["Name"] + [i for i in range(len(student_data.columns)-1)]
        
        # 找到該學生
        student_row = student_data[student_data["Name"] == student_name]
        
        if student_row.empty:
            return None, "找不到資料"
            
        student_row = student_row.iloc[0]
        
        # 篩選錯題
        error_list = []
        for answer, knowledge, q_num in zip(student_row[1:], knowledge_points, question_numbers):
            ans_str = str(answer).strip()
            if ans_str != "-" and pd.notna(answer) and ans_str != "":
                # 嘗試將題號轉為數字以便排序，若無法轉則維持原樣
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
    """
    將錯題資料轉換為 HTML 卡片格式
    邏輯：
    1. 依照知識點分組
    2. 計算錯誤次數
    3. 收集該知識點的所有錯題題號
    4. 排序：先比次數(多->少)，再比第一題號(小->大)
    """
    if df is None or df.empty:
        return "<div style='color:gray; padding:10px;'>無錯題資料</div>"

    # 1. 依照知識點分組統計
    # 我們需要聚合：計數、題號列表(用於顯示)、第一題號(用於排序)
    grouped = df.groupby("知識點").apply(lambda x: pd.Series({
        "count": len(x),
        "q_list": sorted(x["題號"].tolist(), key=lambda k: int(k) if str(k).isdigit() else 999),
        "first_q_sort": x["題號排序用"].min()
    })).reset_index()

    # 2. 篩選 (例如總覽頁只看錯2題以上)
    grouped = grouped[grouped["count"] >= min_errors]
    
    if grouped.empty:
        return "<div style='color:gray; padding:10px;'>無符合條件的項目</div>"

    # 3. 排序：次數(降冪), 第一題號(升冪)
    grouped = grouped.sort_values(by=["count", "first_q_sort"], ascending=[False, True])

    html_content = ""
    
    for _, row in grouped.iterrows():
        count = row["count"]
        knowledge = row["知識點"]
        q_list_str = ", ".join([str(q) for q in row["q_list"]])
        
        # 顯示文字： (第3, 5題) 知識點名稱
        display_text = f"(第{q_list_str}題) {knowledge}"

        # 顏色邏輯
        if count >= 2:
            bg_color = "#c62828" # 深紅
            border_color = "#c62828"
        else:
            bg_color = "#ff7043" # 淺紅/橘
            border_color = "#ff7043"

        # HTML 卡片結構
        html_content += f"""
        <div style="display: flex; align-items: stretch; margin-bottom: 10px; min-width: 200px;">
            <!-- 左側數字 -->
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
            <!-- 右側文字 -->
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
                white-space: nowrap; /* 防止換行，配合水平捲軸 */
            ">
                {display_text}
            </div>
        </div>
        """
    return html_content

# --- 4. 取得學生名單 (以國文科為準) ---
try:
    df_main = conn.read(worksheet="國文", ttl=0, header=None)
    student_list = df_main.iloc[5:, 1].dropna().unique().tolist()
except Exception as e:
    st.error("無法讀取學生名單，請檢查 Google Sheet。")
    st.stop()

# --- 5. 網頁互動介面 ---

selected_student = st.sidebar.selectbox("🔍 請選擇學生姓名：", student_list)
st.sidebar.markdown("---")
st.sidebar.info("💡 **五科總覽**：僅顯示錯 2 題以上的重點項目。\n\n💡 **各科分頁**：顯示該科所有錯題詳情。")

if selected_student:
    st.header(f"👤 學生：{selected_student}")
    
    # 建立分頁：總覽 + 5科
    all_tabs = ["五科總覽"] + SUBJECTS
    tabs = st.tabs(all_tabs)
    
    # --- A. 處理「五科總覽」分頁 ---
    with tabs[0]:
        st.subheader("🏆 重點複習總覽 (僅列出錯 2 題以上)")
        st.caption("※ 欄位內可上下滑動查看更多，左右滑動查看完整文字")
        
        # 建立 5 欄
        cols = st.columns(5)
        
        for i, subject in enumerate(SUBJECTS):
            with cols[i]:
                st.markdown(f"<h4 style='text-align: center;'>{subject}</h4>", unsafe_allow_html=True)
                
                # 取得資料
                df_error, msg = get_student_data(subject, selected_student)
                
                # 生成 HTML (設定 min_errors=2)
                if df_error is not None and not df_error.empty:
                    cards_html = generate_knowledge_cards_html(df_error, min_errors=2)
                else:
                    cards_html = "<div style='text-align:center; color:#aaa;'>無重點項目</div>"
                
                # 放入捲動容器 (Frozen Window 效果)
                st.markdown(
                    f"""
                    <div class="scrollable-container">
                        {cards_html}
                    </div>
                    """, 
                    unsafe_allow_html=True
                )

    # --- B. 處理「各科詳細」分頁 ---
    for i, subject in enumerate(SUBJECTS):
        # 注意：tabs 索引要 +1，因為 0 是總覽
        with tabs[i+1]:
            st.subheader(f"📖 {subject}科 完整分析")
            
            df_error, msg = get_student_data(subject, selected_student)
            
            if msg:
                st.warning(f"訊息: {msg}")
            elif df_error is not None and not df_error.empty:
                
                # 1. 重點複習區 (顯示所有錯題，min_errors=1)
                st.markdown("### 📌 重點複習 (依錯誤次數排序)")
                st.markdown("以下數字代表該知識點的**錯題數量**，括號內為**題號**：")
                
                cards_html = generate_knowledge_cards_html(df_error, min_errors=1)
                st.markdown(cards_html, unsafe_allow_html=True)
                
                st.markdown("---")
                
                # 2. 詳細表格
                st.warning(f"⚠️ 共發現 {len(df_error)} 題錯題，詳細列表如下：")
                
                # 整理表格顯示欄位
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