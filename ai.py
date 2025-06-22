import sys, re, time
from openai import OpenAI
from openai.types.chat import ChatCompletion
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QLabel, QLineEdit, QPushButton, QComboBox, QSpinBox, QTextEdit,
                             QFrame)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtGui import QTextCursor, QFont
import pyttsx3
import datetime

CSS_STYLE = """
body{font-family:'Microsoft YaHei';background:#f8f9fa;line-height:1.6;margin:0;padding:20px;max-width:1200px;margin:0 auto}
.header{text-align:center;margin-bottom:30px;border-bottom:2px solid #dee2e6;padding-bottom:20px}
.title{font-size:28px;color:#343a40;margin-bottom:10px}
.info{color:#6c757d;font-size:16px;margin-bottom:5px}
.round{background:#e9ecef;border-radius:5px;padding:15px;margin-bottom:20px}
.round-title{font-size:20px;color:#495057;margin-bottom:15px;padding-bottom:10px;border-bottom:1px solid #ced4da}
.pro{background:#fff8e1;border-left:4px solid #ffc107;padding:15px;margin-bottom:15px;border-radius:5px;box-shadow:0 2px 4px rgba(0,0,0,0.1)}
.con{background:#e3f2fd;border-left:4px solid #2196f3;padding:15px;margin-bottom:15px;border-radius:5px;box-shadow:0 2px 4px rgba(0,0,0,0.1)}
.judge{background:#e8f5e9;border-left:4px solid #4caf50;padding:15px;margin-bottom:15px;border-radius:5px;box-shadow:0 2px 4px rgba(0,0,0,0.1)}
.final{background:#f3e5f5;border-left:4px solid #9c27b0;padding:15px;margin-bottom:15px;border-radius:5px;box-shadow:0 2px 4px rgba(0,0,0,0.1)}
.side-title{font-weight:bold;margin-bottom:10px;color:#495057;font-size:18px;display:flex;align-items:center}
.side-title::before{content:"•";margin-right:10px;font-size:24px;color:#ff9800}
.con .side-title::before{color:#2196f3}
.judge .side-title::before{color:#4caf50}
.final .side-title::before{color:#9c27b0}
.content{font-size:16px;color:#37474f;line-height:1.7}
.result{background:#e1f5fe;padding:25px;border-radius:10px;margin-top:30px;text-align:center;box-shadow:0 4px 6px rgba(0,0,0,0.1)}
.winner{font-size:28px;font-weight:bold;color:#f44336;margin:15px 0}
.vote-result{font-size:20px;margin:10px 0;font-weight:bold}
.thinking{text-align:center;padding:40px;color:#78909c;font-size:18px;font-style:italic}
.divider{margin:20px 0;border-top:1px dashed #ccc}
"""


class DebateThread(QThread):
    update_status = pyqtSignal(str)
    new_content = pyqtSignal(dict)
    debate_finished = pyqtSignal(dict)

    def __init__(self, title, max_rounds, use_speech, speech_rate):
        super().__init__()
        self.title, self.max_rounds, self.use_speech, self.speech_rate = title, max_rounds, use_speech, speech_rate
        self.ns, self.debate_history, self.client, self.engine = not use_speech, [], None, None
        self.messages_r1, self.messages_r2, self.messages_judge, self.rounds = [], [], [], 1

    def run(self):
        try:
            self.setup()
            for _ in range(self.max_rounds): self.round()
            self.judges()
            self.final_speeches()
            self.update_status.emit("辩论结束！")
        except Exception as e:
            self.update_status.emit(f"出错: {str(e)}")

    def setup(self):
        self.update_status.emit("初始化中...")
        self.update_status.emit("作者:一只Hello [B站 Java的Java]")
        if not self.ns:
            try:
                self.engine = pyttsx3.init()
                self.engine.setProperty('rate', self.speech_rate)
                self.engine.setProperty('volume', 1.0)
            except:
                self.ns = True

        self.client = OpenAI(api_key="sk-d15c95847ab04501b000ce64d9ffc629", base_url="https://api.deepseek.com")

        sys_msg = {"role": "system",
                   "content": f"辩论选手，主题:{self.title}，轮数:{self.max_rounds}，反驳对方，不用markdown，多用换行"}
        self.messages_r1 = [dict(sys_msg, content=sys_msg['content'] + " 你是正方")]
        self.messages_r2 = [dict(sys_msg, content=sys_msg['content'] + " 你是反方")]
        self.messages_judge = [
            {"role": "system", "content": f"专业评委，主题:{self.title}，点评后标出胜利方: <vote 正> 或 <vote 反>"}]

        self.emit_content("系统",
                          f"主题: {self.title} | 轮次: {self.max_rounds} | 开始: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    def speak(self, text):
        if not self.ns and self.engine:
            try:
                self.engine.say(text); self.engine.runAndWait(); time.sleep(0.5)
            except:
                pass

    def call_ai(self, role):
        messages = self.messages_r1 if role == "正方" else self.messages_r2 if role == "反方" else self.messages_judge
        return self.client.chat.completions.create(model="deepseek-chat", messages=messages, stream=False)

    def round(self):
        self.update_status.emit(f"第 {self.rounds} 轮")

        # 正方发言
        self.update_status.emit("正方发言中...")
        r1 = self.call_ai("正方").choices[0].message.content
        self.emit_content("正方", r1, self.rounds)
        self.messages_r2.append({"role": "user", "content": r1})
        self.speak(r1)

        # 反方发言
        self.update_status.emit("反方发言中...")
        r2 = self.call_ai("反方").choices[0].message.content
        self.emit_content("反方", r2, self.rounds)
        self.messages_r1.append({"role": "user", "content": r2})
        self.speak(r2)

        self.messages_judge.append({"role": "user", "content": f"正方:{r1}\n\n反方:{r2}"})
        self.rounds += 1

    def judges(self):
        z = f = 0
        for i in range(1, 4):
            self.update_status.emit(f"评委 {i} 点评中...")
            comment = self.call_ai("评委").choices[0].message.content
            self.emit_content("评委", comment, judge_num=i)
            self.speak(comment)

            vote = re.search(r'<vote\s*([正反])>', comment)
            if vote: z += 1 if vote.group(1) == "正" else 0; f += 1 if vote.group(1) == "反" else 0

            for m in [self.messages_r1, self.messages_r2, self.messages_judge]:
                m.append({"role": "user", "content": f"评委{i}: {comment}"})

        result = {"正方": z, "反方": f}
        winner = "反方" if f > z else "正方" if z > f else "平局"
        self.update_status.emit(f"{winner}赢得本场胜利" if winner != "平局" else "辩论平局")

        sys_msg = "你赢了" if winner == "正方" else "你输了" if winner == "反方" else "辩论平局"
        self.messages_r1.append({"role": "system", "content": f"{sys_msg} 请发表感言"})
        self.messages_r2.append({"role": "system",
                                 "content": f"{'你赢' if winner == '反方' else '你输' if winner == '正方' else '平局'} 请发表感言"})

        self.debate_finished.emit(result)
        return result, winner

    def final_speeches(self):
        # 正方感言
        self.update_status.emit("正方发表感言...")
        r1 = self.call_ai("正方").choices[0].message.content
        self.emit_content("正方感言", r1)
        self.speak(r1)

        # 反方感言
        self.update_status.emit("反方发表感言...")
        r2 = self.call_ai("反方").choices[0].message.content
        self.emit_content("反方感言", r2)
        self.speak(r2)

    def emit_content(self, role, content, round=0, judge_num=0):
        self.debate_history.append({"role": role, "round": round, "judge_num": judge_num, "content": content})
        self.new_content.emit({"role": role, "round": round, "judge_num": judge_num, "content": content})


class DebateGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("AI辩论系统")
        self.setGeometry(100, 100, 1400, 800)

        # 主布局
        cw = QWidget()
        ml = QHBoxLayout(cw)
        ml.setContentsMargins(10, 10, 10, 10)

        # 左侧面板
        cp = QFrame()
        cp.setFixedWidth(350)
        cl = QVBoxLayout(cp)
        cl.setContentsMargins(15, 15, 15, 15)

        cl.addWidget(QLabel("辩论设置", font=QFont("Arial", 14, QFont.Bold)))

        cl.addWidget(QLabel("辩论主题:"))
        self.topic_input = QLineEdit("人工智能对人类的影响是利大于弊")
        cl.addWidget(self.topic_input)

        cl.addWidget(QLabel("辩论轮次:"))
        self.rounds_spin = QSpinBox()
        self.rounds_spin.setRange(1, 10);
        self.rounds_spin.setValue(3)
        cl.addWidget(self.rounds_spin)

        cl.addWidget(QLabel("语音设置:"))
        hl = QHBoxLayout()
        self.voice_combo = QComboBox();
        self.voice_combo.addItems(["启用", "禁用"])
        hl.addWidget(self.voice_combo)
        self.speed_spin = QSpinBox();
        self.speed_spin.setRange(100, 300);
        self.speed_spin.setValue(200);
        self.speed_spin.setPrefix("语速:")
        hl.addWidget(self.speed_spin)
        cl.addLayout(hl)

        bl = QHBoxLayout()
        self.start_btn = QPushButton("开始辩论")
        self.start_btn.setStyleSheet("background:#4CAF50;color:white;padding:8px")
        self.start_btn.clicked.connect(self.start_debate)
        bl.addWidget(self.start_btn)

        self.stop_btn = QPushButton("停止辩论")
        self.stop_btn.setStyleSheet("background:#f44336;color:white;padding:8px")
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self.stop_debate)
        bl.addWidget(self.stop_btn)
        cl.addLayout(bl)

        cl.addWidget(QLabel("状态日志:"))
        self.status_display = QTextEdit()
        self.status_display.setReadOnly(True)
        self.status_display.setStyleSheet("background:#f5f5f5;border:1px solid #ddd")
        cl.addWidget(self.status_display)

        # 右侧HTML区域
        hf = QFrame()
        hfl = QVBoxLayout(hf)

        self.web_view = QWebEngineView()
        hfl.addWidget(self.web_view)

        ml.addWidget(cp)
        ml.addWidget(hf, 1)
        self.setCentralWidget(cw)

        # 初始化
        self.debate_thread = None
        self.html_content = self.get_initial_html()
        self.update_html()

    def get_initial_html(self):
        return f"""<!DOCTYPE html><html><head><meta charset="UTF-8"><title>AI辩论系统</title><style>{CSS_STYLE}</style></head>
        <body><div class="header"><h1 class="title">AI辩论系统</h1><div class="info">等待开始</div></div>
        <div id="content-container"><div class="thinking"><p>设置参数并点击"开始辩论"</p></div></div></body></html>"""

    def start_debate(self):
        topic = self.topic_input.text().strip()
        if not topic: return self.status_display.append("请输入主题")

        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.status_display.clear()
        self.status_display.append(f"开始辩论: {topic}")

        # 初始化HTML
        self.html_content = f"""<!DOCTYPE html><html><head><meta charset="UTF-8"><title>辩论:{topic}</title><style>{CSS_STYLE}</style></head>
        <body><div class="header"><h1 class="title">实时辩论: {topic}</h1>
        <div class="info">轮次: {self.rounds_spin.value()} | 开始: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</div></div>
        <div id="content-container">"""

        self.update_html()

        # 启动线程
        self.debate_thread = DebateThread(topic, self.rounds_spin.value(), self.voice_combo.currentIndex() == 0,
                                          self.speed_spin.value())
        self.debate_thread.update_status.connect(self.update_status)
        self.debate_thread.new_content.connect(self.add_content)
        self.debate_thread.debate_finished.connect(self.debate_finished)
        self.debate_thread.start()

    def stop_debate(self):
        if self.debate_thread and self.debate_thread.isRunning():
            self.debate_thread.terminate()
            self.status_display.append("已停止")
            self.start_btn.setEnabled(True)
            self.stop_btn.setEnabled(False)
            self.html_content += "<div class='result'><div class='winner'>已停止</div></div>"
            self.update_html()

    def update_status(self, msg):
        self.status_display.append(msg)
        self.status_display.moveCursor(QTextCursor.End)

    def add_content(self, content):
        role, rnd, judge, text = content["role"], content.get("round", 0), content.get("judge_num", 0), content[
            "content"]

        if role == "系统":
            self.html_content += f'<div class="info">{text}</div>'
        elif role == "正方":
            self.html_content += f'<div class="round"><div class="round-title">第 {rnd} 轮</div><div class="pro"><div class="side-title">正方观点</div><div class="content">{text.replace("\n", "<br>")}</div></div>'
        elif role == "反方":
            self.html_content += f'<div class="con"><div class="side-title">反方观点</div><div class="content">{text.replace("\n", "<br>")}</div></div></div>'
        elif role == "评委":
            self.html_content += f'<div class="divider"></div><div class="judge"><div class="side-title">评委点评 ({judge})</div><div class="content">{text.replace("\n", "<br>")}</div></div>'
        elif "感言" in role:
            self.html_content += f'<div class="divider"></div><div class="final"><div class="side-title">{role}</div><div class="content">{text.replace("\n", "<br>")}</div></div>'

        self.update_html()

    def update_html(self):
        full_html = self.html_content + """</div><script>window.scrollTo(0,document.body.scrollHeight)</script></body></html>"""
        self.web_view.setHtml(full_html)

    def debate_finished(self, result):
        z, f = result["正方"], result["反方"]
        winner = "反方" if f > z else "正方" if z > f else "平局"
        self.status_display.append(f"结束! 正方:{z}票, 反方:{f}票, 获胜:{winner}")

        self.html_content += f"""
        <div class="result">
            <h2>最终结果</h2>
            <div class="vote-result">正方: {z}票</div>
            <div class="vote-result">反方: {f}票</div>
            <div class="winner">获胜方: {winner}</div>
        </div>"""

        self.update_html()
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = DebateGUI()
    window.show()
    sys.exit(app.exec_())