import random
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
import time
from datetime import datetime, date
import io

st.title("英単語テスト（CSV版・スマホ対応・期限付き）")

# ==== 利用期限チェック ====
limit_date = date(2025, 9, 30)  # 利用期限を 2025-09-30 に設定
today = date.today()

if today > limit_date:
    st.markdown(
        "<h2 style='color:red;'>利用期間が終了しました</h2>",
        unsafe_allow_html=True
    )
    st.stop()

# ==== 入試日設定 ====
exam_date = date(2026, 1, 17)
days_left = (exam_date - today).days

# ==== ファイルアップロード ====
col1, col2 = st.columns([3, 2])
with col1:
    uploaded_file = st.file_uploader("単語リスト（CSV, UTF-8推奨）をアップロードしてください", type=["csv"])
with col2:
    st.markdown(f"例：{limit_date}まで利用可能")
    st.markdown(f"入試まであと **{days_left} 日**")

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
if "start_time" not in ss: ss.start_time = time.time()  # 全体開始
if "history" not in ss: ss.history = []  # [(順番, 単語, 意味, 正誤, 解答時間秒)]
if "show_save_ui" not in ss: ss.show_save_ui = False
if "user_name" not in ss: ss.user_name = ""
if "counter" not in ss: ss.counter = 1   # 学習順序カウンタ
if "question_start_time" not in ss: ss.question_start_time = None  # 各問題開始時刻

# ==== 関数群 ====
def format_time(seconds: int) -> str:
    """秒を '分 秒' 形式に変換"""
    minutes = seconds // 60
    sec = seconds % 60
    if minutes > 0:
        return f"{minutes}分{sec}秒"
    else:
        return f"{sec}秒"

def next_question():
    if not ss.remaining:
        ss.current = None
        ss.phase = "done"
        return
    ss.current = random.choice(ss.remaining)
    ss.phase = "quiz"
    ss.last_outcome = None
    ss.question_start_time = time.time()  # ✅ 出題開始時間を記録

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
    ss.counter = 1
    ss.question_start_time = None

def prepare_csv():
    """学習履歴をCSVとして出力する"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{ss.user_name}_{timestamp}.csv"

    cleaned_history = []
    total_seconds = 0
    for record in ss.history:
        # ✅ 必ず5要素に揃える
        if len(record) != 5:
            record = list(record) + [""] * (5 - len(record))

        order, word, meaning, result, elapsed = record

        # ✅ elapsed を数値に揃える
        try:
            elapsed_int = int(elapsed)
        except:
            elapsed_int = 0

        total_seconds += elapsed_int
        cleaned_history.append((order, word, meaning, result, format_time(elapsed_int)))

    # ✅ DataFrame化
    history_df = pd.DataFrame(
        cleaned_history,
        columns=["順番", "単語", "意味", "正誤", "解答時間"]
    )

    # ✅ 合計時間を冒頭に追加（分 秒）
    total_time_str = format_time(total_seconds)
    total_row = pd.DataFrame(
        [["", "", "", "合計時間", total_time_str]],
        columns=["順番", "単語", "意味", "正誤", "解答時間"]
    )
    history_df = pd.concat([total_row, history_df], ignore_index=True)

    # CSVに変換
    csv_buffer = io.StringIO()
    history_df.to_csv(csv_buffer, index=False, encoding="utf-8-sig")
    csv_data = csv_buffer.getvalue().encode("utf-8-sig")

    return filename, csv_data, total_time_str

# ==== 全問終了 ====
if ss.phase == "done":
    st.success("全問正解！お疲れさまでした🎉")

    # 合計時間を計算（内部は秒）
    total_seconds = 0
    for rec in ss.history:
        if len(rec) == 5:
            try:
                total_seconds += int(rec[4])
            except:
                pass
    st.info(f"合計学習時間: {format_time(total_seconds)}")

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
        filename, csv_data, total_time_str = prepare_csv()
        st.download_button(
            label="📥 保存（ダウンロード）",
            data=csv_data,
            file_name=filename,
            mime="text/csv"
        )

# ==== 出題 ====
if ss.phase == "quiz" and ss.current:
    current = ss.current
    st.subheader(f"意味: {current['意味']}")

    with st.form("answer_form", clear_on_submit=True):
        ans = st.text_input("最初の2文字を入力（半角英数字）", max_chars=2, key="answer_box")
        submitted = st.form_submit_button("解答（Enter）")

    # 自動フォーカス
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
        status = "正解" if check_answer(ans) else "不正解"
        elapsed = int(time.time() - ss.question_start_time) if ss.question_start_time else 0

        # ✅ ss.history には int の秒数を保存する
        ss.history.append((ss.counter, current["単語"], current["意味"], status, elapsed))
        ss.counter += 1

        if status == "正解":
            ss.remaining = [q for q in ss.remaining if q != current]
            ss.last_outcome = ("correct", current["単語"])
        else:
            ss.last_outcome = ("wrong", current["単語"])

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
