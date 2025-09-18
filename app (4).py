import random
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
import time
from datetime import datetime, date
import io

st.title("英単語テスト（CSV版・スマホ対応）")

# ==== 利用期限と入試カウントダウン ====
expire_date = date(2025, 9, 30)
exam_date = date(2026, 1, 17)
today = date.today()

if today <= expire_date:
    st.markdown(f"### ✅ 2025-9-30まで利用可能")
    days_left = (exam_date - today).days
    st.markdown(f"### 📝 入試まであと **{days_left}日**")
else:
    st.markdown(
        "<h3 style='color:red;'>❌ 期限が終了しました。</h3>",
        unsafe_allow_html=True
    )
    st.stop()

# ==== ファイルアップロード ====
col1, col2 = st.columns([3, 2])
with col1:
    uploaded_file = st.file_uploader("単語リスト（CSV, UTF-8推奨）をアップロードしてください", type=["csv"])
with col2:
    st.markdown("例：2025-9-30まで利用可能")

if uploaded_file is None:
    st.info("まずは CSV をアップロードしてください。")
    st.stop()

# ==== CSV読み込み ====
try:
    df = pd.read_csv(uploaded_file, encoding="utf-8")
except UnicodeDecodeError:
    df = pd.read_csv(uploaded_file, encoding="shift-jis")

if not {"単語", "意味"}.issubset(df.columns):
    st.error("CSVには『単語』『意味』列が必要です。")
    st.stop()

# ==== セッション初期化 ====
ss = st.session_state
if "remaining" not in ss: ss.remaining = df.to_dict("records")
if "current" not in ss: ss.current = None
if "phase" not in ss: ss.phase = "quiz"   # quiz / feedback / done / finished
if "last_outcome" not in ss: ss.last_outcome = None
if "start_time" not in ss: ss.start_time = time.time()
if "history" not in ss: ss.history = []
if "show_save_ui" not in ss: ss.show_save_ui = False
if "user_name" not in ss: ss.user_name = ""

def next_question():
    if not ss.remaining:
        ss.current = None
        ss.phase = "done"
        return
    ss.current = random.choice(ss.remaining)
    ss.phase = "quiz"
    ss.last_outcome = None

def check_answer(ans: str) -> bool:
    word = ss.current["単語"]
    return word.lower().startswith(ans.strip().lower())

def reset_quiz():
    ss.remaining = df.to_dict("records")
    ss.current = None
    ss.phase = "quiz"
    ss.last_outcome = None
    ss.start_time = time.time()
    ss.history = []

def prepare_csv():
    """履歴をCSVにまとめて、ダウンロード可能にする"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{ss.user_name}_{timestamp}.csv"

    elapsed = int(time.time() - ss.start_time)
    minutes = elapsed // 60
    seconds = elapsed % 60

    history_df = pd.DataFrame(ss.history, columns=["学習単語"])
    history_df["学習時間"] = f"{minutes}分{seconds}秒"

    csv_buffer = io.StringIO()
    history_df.to_csv(csv_buffer, index=False, encoding="utf-8-sig")
    csv_data = csv_buffer.getvalue().encode("utf-8-sig")

    return filename, csv_data

# ==== 全問終了 ====
if ss.phase == "done":
    st.success("全問正解！お疲れさまでした🎉")
    elapsed = int(time.time() - ss.start_time)
    minutes = elapsed // 60
    seconds = elapsed % 60
    st.info(f"所要時間: {minutes}分 {seconds}秒")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("もう一回"):
            reset_quiz()
            st.rerun()
    with col2:
        if st.button("終了"):
            ss.show_save_ui = True
            ss.phase = "finished"
            st.rerun()
    st.stop()

# ==== 終了後の保存UI ====
if ss.phase == "finished" and ss.show_save_ui:
    st.subheader("学習履歴の保存")

    ss.user_name = st.text_input("氏名を入力してください", value=ss.user_name)

    if ss.user_name:
        filename, csv_data = prepare_csv()
        st.download_button(
            label="📥 保存（ダウンロード）",
            data=csv_data,
            file_name=filename,
            mime="text/csv"
        )

# ==== 新しい問題 ====
if ss.current is None and ss.phase == "quiz":
    next_question()

# ==== 出題 ====
if ss.phase == "quiz" and ss.current:
    current = ss.current
    st.subheader(f"意味: {current['意味']}")

    with st.form("answer_form", clear_on_submit=True):
        ans = st.text_input("最初の2文字を入力（半角英数字）", max_chars=2, key="answer_box")
        submitted = st.form_submit_button("解答（Enter）")

    components.html(
        """
        <script>
        const box = window.parent.document.querySelector('input[type="text"]');
        if (box) { box.focus(); box.select(); }
        </script>
        """,
        height=0,
    )

    if submitted and ans and len(ans.strip()) == 2 and ans.isascii():
        if check_answer(ans):
            ss.remaining = [q for q in ss.remaining if q != current]
            ss.last_outcome = ("correct", current["単語"])
            ss.history.append(current["単語"])
        else:
            ss.last_outcome = ("wrong", current["単語"])
            ss.history.append(current["単語"])
        ss.phase = "feedback"
        st.rerun()

# ==== フィードバック ====
if ss.phase == "feedback" and ss.last_outcome:
    status, word = ss.last_outcome
    if status == "correct":
        st.markdown(
            f"<div style='background:#e6ffe6;padding:6px;margin:2px 0;border-radius:6px;'>正解！ {word} 🎉</div>",
            unsafe_allow_html=True,
        )
    elif status == "wrong":
        st.markdown(
            f"<div style='background:#ffe6e6;padding:6px;margin:2px 0;border-radius:6px;'>不正解！ 正解は {word}</div>",
            unsafe_allow_html=True,
        )

    st.write("下のボタンを押すか、Tabを押してからリターンを押してください。")

    if st.button("次の問題へ"):
        next_question()
        st.rerun()
