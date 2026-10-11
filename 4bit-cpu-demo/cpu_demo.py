"""4 位 CPU 互动教学演示（tkinter 版）

运行：python cpu_demo.py      （只需要 Python 3.8+ 自带的 tkinter，不用装别的包）
"""

import tkinter as tk
from tkinter import font as tkfont
from tkinter import ttk
import re

from cpu_core import (AFS_NAMES, CPU, EXAMPLE_PROGRAM, AsmError, alu, assemble,
                      assemble_line, bits, control_signals, disassemble, display_char,
                      split_fields, MNEMONIC)
from lessons import CHAPTERS, PHASE_NAMES, describe_phase, make_prediction, uses

# 颜色
ACTIVE = "#e8590c"      # 这一步正在用的通路
USED = "#f4a261"        # 这条指令前几步用过的通路
LIVE = "#adb5bd"        # 有值但这条指令不用
IDLE = "#dee2e6"
INK = "#212529"
MUTED = "#868e96"
BG = "#f8f9fa"
BOX = "#ffffff"
FIELD_COLORS = {"opcode": "#c92a2a", "D": "#1971c2", "A": "#2f9e44", "B": "#7048e8", "-": "#adb5bd"}
FIELD_OF_BIT = {}
for _b in range(16):
    FIELD_OF_BIT[_b] = ("opcode" if _b >= 12 else "D" if 8 <= _b <= 10 else "A" if 4 <= _b <= 6
                        else "B" if _b <= 2 else "-")

CW, CH = 920, 480


def pad(text, width=14):
    """按显示宽度补空格（中文字符占两格），让等宽字体里的列对齐。"""
    import unicodedata
    w = sum(2 if unicodedata.east_asian_width(ch) in "WF" else 1 for ch in text)
    return text + " " * max(1, width - w)


class App:
    def __init__(self, root):
        self.root = root
        root.title("4 位 CPU 互动教学 —— 一步步看懂一台 CPU")
        root.configure(bg=BG)
        base = tkfont.nametofont("TkDefaultFont")
        base.configure(size=11)
        self.f_small = base.copy()
        self.f_small.configure(size=9)
        self.f_bold = base.copy()
        self.f_bold.configure(weight="bold")
        self.f_big = base.copy()
        self.f_big.configure(size=14, weight="bold")
        self.f_mono = tkfont.nametofont("TkFixedFont").copy()
        self.f_mono.configure(size=10)
        self.f_mono_big = self.f_mono.copy()
        self.f_mono_big.configure(size=12, weight="bold")

        self.cpu = CPU()
        self.source = EXAMPLE_PROGRAM
        self.cpu.load(assemble(self.source))
        self.trace = None      # 正在执行的那条指令的“电路快照”
        self.phase = -1        # -1 = 还没开始这一条；0~4 = 五小步
        self.running = False
        self.pending_pred = None
        self.chapter = 0

        self._build()
        self.show_chapter(0)
        self.redraw()

    # ─── 布局 ───

    def _build(self):
        left = tk.Frame(self.root, bg=BG)
        left.grid(row=0, column=0, sticky="nsew", padx=(10, 5), pady=10)
        right = tk.Frame(self.root, bg=BG)
        right.grid(row=0, column=1, sticky="nsew", padx=(5, 10), pady=10)
        self.root.columnconfigure(1, weight=1)
        self.root.rowconfigure(0, weight=1)

        self.canvas = tk.Canvas(left, width=CW, height=CH, bg=BOX, highlightthickness=1,
                                highlightbackground="#ced4da")
        self.canvas.pack()

        self.phase_label = tk.Label(left, text="", bg=BG, fg=INK, justify="left", anchor="w",
                                    wraplength=CW, height=3)
        self.phase_label.pack(fill="x", pady=(6, 4))

        bar = tk.Frame(left, bg=BG)
        bar.pack(fill="x")
        self.btn_step = ttk.Button(bar, text="下一小步 ▶", command=self.next_phase)
        self.btn_step.pack(side="left")
        self.btn_instr = ttk.Button(bar, text="执行整条指令 ⏭", command=self.finish_instruction)
        self.btn_instr.pack(side="left", padx=4)
        self.btn_run = ttk.Button(bar, text="连续运行", command=self.toggle_run)
        self.btn_run.pack(side="left")
        ttk.Button(bar, text="重置", command=self.reset).pack(side="left", padx=4)
        ttk.Button(bar, text="编辑程序…", command=self.open_editor).pack(side="left")
        self.predict_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(bar, text="执行前先让我预测", variable=self.predict_var).pack(side="left", padx=12)
        self.legend = tk.Label(bar, bg=BG, fg=MUTED, font=self.f_small,
                               text="橙色＝这一步在用   浅橙＝刚才用过   灰色＝有值但没人用")
        self.legend.pack(side="right")

        # 执行前预测
        self.pred_frame = tk.LabelFrame(left, text=" 先猜一猜 ", bg=BG, fg=INK, padx=8, pady=4)
        self.pred_q = tk.Label(self.pred_frame, bg=BG, fg=INK, anchor="w", justify="left", wraplength=CW - 30)
        self.pred_q.pack(fill="x")
        self.pred_opts = tk.Frame(self.pred_frame, bg=BG)
        self.pred_opts.pack(fill="x")
        self.pred_var = tk.IntVar(value=-1)
        self.pred_buttons = []
        for i in range(4):
            rb = tk.Radiobutton(self.pred_opts, variable=self.pred_var, value=i, bg=BG, anchor="w",
                                font=self.f_mono_big)
            rb.pack(side="left", padx=(0, 18))
            self.pred_buttons.append(rb)
        pb = tk.Frame(self.pred_frame, bg=BG)
        pb.pack(fill="x", pady=(2, 0))
        ttk.Button(pb, text="确定", command=self.answer_prediction).pack(side="left")
        ttk.Button(pb, text="跳过", command=lambda: self.answer_prediction(skip=True)).pack(side="left", padx=4)
        self.pred_fb = tk.Label(pb, bg=BG, fg=INK, anchor="w", justify="left", wraplength=CW - 180)
        self.pred_fb.pack(side="left", padx=8, fill="x")

        # 右边：课程
        nav = tk.Frame(right, bg=BG)
        nav.pack(fill="x")
        ttk.Button(nav, text="◀", width=3, command=lambda: self.show_chapter(self.chapter - 1)).pack(side="left")
        self.chap_box = ttk.Combobox(nav, state="readonly", values=[c["title"] for c in CHAPTERS], width=34)
        self.chap_box.pack(side="left", padx=4, fill="x", expand=True)
        self.chap_box.bind("<<ComboboxSelected>>", lambda e: self.show_chapter(self.chap_box.current()))
        ttk.Button(nav, text="▶", width=3, command=lambda: self.show_chapter(self.chapter + 1)).pack(side="left")

        right.bind("<Configure>", self._on_resize)
        quiz = tk.LabelFrame(right, text=" 先预测，再看讲解 ", bg=BG, fg=INK, padx=8, pady=6)
        quiz.pack(fill="x", pady=(8, 6))
        self.quiz_q = tk.Label(quiz, bg=BG, fg=INK, justify="left", anchor="w", wraplength=380, font=self.f_bold)
        self.quiz_q.pack(fill="x")
        self.quiz_var = tk.IntVar(value=-1)
        self.quiz_buttons = []
        for i in range(4):
            rb = tk.Radiobutton(quiz, variable=self.quiz_var, value=i, bg=BG, anchor="w", justify="left",
                                wraplength=360)
            rb.pack(fill="x")
            self.quiz_buttons.append(rb)
        qb = tk.Frame(quiz, bg=BG)
        qb.pack(fill="x", pady=(4, 0))
        ttk.Button(qb, text="提交答案", command=self.answer_quiz).pack(side="left")
        ttk.Button(qb, text="直接看讲解", command=lambda: self.answer_quiz(skip=True)).pack(side="left", padx=4)
        self.quiz_fb = tk.Label(quiz, bg=BG, justify="left", anchor="w", wraplength=380)
        self.quiz_fb.pack(fill="x", pady=(4, 0))

        self.actions = tk.Frame(right, bg=BG)
        self.actions.pack(fill="x")

        body_frame = tk.Frame(right, bg=BG)
        body_frame.pack(fill="both", expand=True, pady=(6, 0))
        self.body = tk.Text(body_frame, wrap="char", bg=BOX, fg=INK, relief="flat", padx=10, pady=8,
                            width=40, font="TkDefaultFont", highlightthickness=1, highlightbackground="#ced4da", spacing1=2)
        sb = ttk.Scrollbar(body_frame, command=self.body.yview)
        self.body.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self.body.pack(side="left", fill="both", expand=True)
        self.body.tag_configure("h", font=self.f_big, spacing1=10, spacing3=4)
        self.body.tag_configure("mono", font=self.f_mono, lmargin1=8, lmargin2=8)
        self.body.tag_configure("src", foreground="#1971c2", font=self.f_bold)
        self.body.tag_configure("gen", foreground="#2f9e44", font=self.f_bold)
        self.body.tag_configure("inf", foreground="#e8590c", font=self.f_bold)
        self.body.tag_configure("hidden", foreground=MUTED)

    def _on_resize(self, event):
        w = max(event.width - 40, 200)
        self.quiz_q.config(wraplength=w)
        self.quiz_fb.config(wraplength=w)
        for rb in self.quiz_buttons:
            rb.config(wraplength=w - 30)

    # ─── 课程 ───

    def show_chapter(self, i):
        if not 0 <= i < len(CHAPTERS):
            return
        self.chapter = i
        ch = CHAPTERS[i]
        self.chap_box.current(i)
        q = ch["quiz"]
        self.quiz_q.config(text=q["q"])
        self.quiz_var.set(-1)
        for rb, opt, letter in zip(self.quiz_buttons, q["options"], "ABCD"):
            rb.config(text="{}. {}".format(letter, opt), state="normal", fg=INK)
        self.quiz_fb.config(text="")
        self._set_body(None)
        for w in self.actions.winfo_children():
            w.destroy()
        if ch.get("program"):
            ttk.Button(self.actions, text="装载本章示例程序",
                       command=lambda: self.load_source(ch["program"])).pack(side="left", padx=(0, 4))
        names = {"decoder_tool": ("指令拆解器", self.open_decoder_tool),
                 "alu_tool": ("ALU 实验台", self.open_alu_tool),
                 "editor": ("编辑程序", self.open_editor)}
        for key in ch.get("actions", []):
            label, cmd = names[key]
            ttk.Button(self.actions, text=label, command=cmd).pack(side="left", padx=(0, 4))
        if ch.get("program"):
            self.load_source(ch["program"])

    def answer_quiz(self, skip=False):
        q = CHAPTERS[self.chapter]["quiz"]
        pick = self.quiz_var.get()
        if not skip and pick < 0:
            self.quiz_fb.config(text="先选一个答案（猜错也没关系）。", fg=MUTED)
            return
        for i, rb in enumerate(self.quiz_buttons):
            rb.config(state="disabled", disabledforeground="#2f9e44" if i == q["answer"] else MUTED)
        if skip:
            head, color = "正确答案是 {}。".format("ABCD"[q["answer"]]), INK
        elif pick == q["answer"]:
            head, color = "答对了！", "#2f9e44"
        else:
            head, color = "不对，正确答案是 {}。".format("ABCD"[q["answer"]]), "#c92a2a"
        self.quiz_fb.config(text=head + q["why"], fg=color)
        self._set_body(CHAPTERS[self.chapter]["body"])

    def _set_body(self, text):
        b = self.body
        b.config(state="normal")
        b.delete("1.0", "end")
        if text is None:
            b.insert("end", "先回答上面的选择题，讲解就会出现在这里。\n\n"
                            "猜错完全没关系：先有一个自己的预期，再看到结果，记得最牢。", "hidden")
        else:
            for line in text.splitlines():
                if line.startswith("## "):
                    b.insert("end", line[3:] + "\n", "h")
                    continue
                tag = "mono" if line.startswith("    ") else ()
                pos = 0
                for m in re.finditer(r"【[^】]*】", line):
                    b.insert("end", line[pos:m.start()], tag)
                    t = m.group()
                    kind = "src" if "源码" in t else "inf" if "推断" in t else "gen"
                    b.insert("end", t, kind)
                    pos = m.end()
                b.insert("end", line[pos:] + "\n", tag)
        b.config(state="disabled")
        b.yview_moveto(0)

    # ─── 执行控制 ───

    def load_source(self, src):
        self.stop_run()
        self.source = src
        self.cpu.load(assemble(src))
        self._clear_step()
        self.redraw()

    def reset(self):
        self.stop_run()
        self.cpu.reset()
        self._clear_step()
        self.redraw()

    def _clear_step(self):
        self.trace = None
        self.phase = -1
        self.pending_pred = None
        self.pred_frame.pack_forget()

    def next_phase(self):
        if self.pending_pred:
            return
        if self.phase == 4 or self.trace is None:
            if self.cpu.halted:
                self.phase_label.config(text="程序已经执行完了。点“重置”从头再来，或者“编辑程序…”写新的。")
                return
            self.trace = self.cpu.preview()
            self.phase = -1
            if self.predict_var.get() and not self.running:
                self.ask_prediction()
                return
        self.phase += 1
        if self.phase == 4:
            self.cpu.commit(self.trace)  # 时钟上升沿
        self.redraw()

    def finish_instruction(self):
        if self.pending_pred:
            return
        if self.phase == 4 or self.trace is None:
            self.next_phase()
            if self.pending_pred or self.trace is None:
                return
        while self.phase < 4:
            self.next_phase()

    def toggle_run(self):
        if self.running:
            self.stop_run()
        else:
            self.running = True
            self.btn_run.config(text="暂停")
            self._tick()

    def _tick(self):
        if not self.running:
            return
        if self.cpu.halted and (self.phase == 4 or self.trace is None):
            self.stop_run()
            return
        self.next_phase()
        self.root.after(450, self._tick)

    def stop_run(self):
        self.running = False
        self.btn_run.config(text="连续运行")

    # ─── 预测 ───

    def ask_prediction(self):
        p = make_prediction(self.trace)
        self.pending_pred = p
        self.pred_q.config(text=p["q"])
        self.pred_var.set(-1)
        for rb, opt in zip(self.pred_buttons, p["options"]):
            rb.config(text=opt, state="normal", fg=INK)
            rb.pack_configure()
        self.pred_fb.config(text="")
        self.pred_frame.pack(fill="x", pady=(8, 0))
        self.phase_label.config(text="先预测这条指令的结果，再一步步看电路是怎么算出来的。")
        self.redraw(keep_label=True)

    def answer_prediction(self, skip=False):
        p = self.pending_pred
        if p is None:
            return
        pick = self.pred_var.get()
        if not skip and pick < 0:
            self.pred_fb.config(text="先选一个。", fg=MUTED)
            return
        for i, rb in enumerate(self.pred_buttons):
            rb.config(state="disabled", disabledforeground="#2f9e44" if i == p["answer"] else MUTED)
        right = p["options"][p["answer"]]
        if skip:
            self.pred_fb.config(text="答案是 {}。接着点“下一小步”看它是怎么来的。".format(right), fg=INK)
        elif pick == p["answer"]:
            self.pred_fb.config(text="猜对了！点“下一小步”验证一下电路是不是这么算的。", fg="#2f9e44")
        else:
            self.pred_fb.config(text="答案是 {}。点“下一小步”，看看电路实际怎么走，哪里和你想的不一样。"
                                .format(right), fg="#c92a2a")
        self.pending_pred = None

    # ─── 画图 ───

    def redraw(self, keep_label=False):
        c = self.canvas
        c.delete("all")
        t, ph = self.trace, self.phase
        u = uses(t) if t else {}
        if t:
            u["A2"] = bool(t["ctrl"]["WE"] and t["ctrl"]["RSS"] >= 2)  # MOV：寄存器 A 直接送去写回
        regs = self.cpu.regs

        def style(name, phases):
            """phases: 这根线在第几步被用到。返回 (颜色, 粗细)。"""
            if t is None or ph < 0:
                return IDLE, 2
            used = u.get(name, name != "_")
            if used and ph in phases:
                return ACTIVE, 4
            if used and ph > min(phases):
                return USED, 3
            if ph >= min(phases):
                return LIVE, 2
            return IDLE, 2

        def wire(points, name, phases, label=None, lpos=None, anchor="w", arrow=True):
            col, w = style(name, phases)
            c.create_line(*points, fill=col, width=w, arrow="last" if arrow else None,
                          arrowshape=(9, 10, 4), joinstyle="round")
            if label and t is not None and ph >= min(phases):
                x, y = lpos or points[-2:]
                c.create_text(x, y, text=label, anchor=anchor, fill=INK if col in (ACTIVE, USED) else MUTED,
                              font=self.f_small)

        def box(x0, y0, x1, y1, title, hot=False):
            c.create_rectangle(x0, y0, x1, y1, fill=BOX, outline=ACTIVE if hot else "#868e96",
                               width=3 if hot else 1.5)
            c.create_text((x0 + x1) / 2, y0 + 12, text=title, font=self.f_bold, fill=INK)

        # PC
        box(20, 12, 110, 62, "PC", hot=(ph == 0))
        pc_show = t["pc"] if t else self.cpu.pc
        c.create_text(65, 44, text=str(pc_show), font=self.f_mono_big, fill=INK)
        wire((65, 62, 65, 88), "pc", (0,), "地址", (70, 76))

        # 程序存储器
        box(20, 88, 220, 318, "程序存储器", hot=(ph == 0))
        prog = self.cpu.program
        start = max(0, min(pc_show - 4, len(prog) - 11))
        for k, (code, text) in enumerate(prog[start:start + 11]):
            addr = start + k
            y = 118 + k * 18
            cur = addr == pc_show
            if cur:
                c.create_rectangle(24, y - 9, 216, y + 9, fill="#fff4e6", outline="")
            c.create_text(28, y, anchor="w", font=self.f_mono, fill=INK if cur else MUTED,
                          text="{:2d} {:04X} {}".format(addr, code, text))
        if not prog:
            c.create_text(120, 200, text="（空）", fill=MUTED)
        wire((220, 110, 236, 110, 236, 34, 252, 34), "fetch", (0,))

        # 指令
        x0 = 252
        code = t["code"] if t else 0
        for i in range(16):
            bit = 15 - i
            fld = FIELD_OF_BIT[bit]
            x = x0 + i * 38
            col = FIELD_COLORS[fld]
            c.create_rectangle(x, 16, x + 36, 50, fill=col if t else "#f1f3f5", outline="white")
            if t:
                c.create_text(x + 18, 33, text=str((code >> bit) & 1), fill="white", font=self.f_mono_big)
            c.create_text(x + 18, 8, text=str(bit), fill=MUTED, font=self.f_small)
        for name, lo_i, hi_i in (("opcode", 0, 3), ("D", 5, 7), ("A", 9, 11), ("B / Data", 12, 15)):
            xm = x0 + (lo_i + hi_i + 1) * 19
            c.create_text(xm, 60, text=name, fill=FIELD_COLORS.get(name.split()[0], INK), font=self.f_small)
        if t:
            c.create_text(x0 + 16 * 38 + 6, 33, anchor="w", font=self.f_mono_big, fill=INK,
                          text="{:04X}".format(code))

        f = t["fields"] if t else None
        ctrl = t["ctrl"] if t else None

        # 译码器
        wire((328, 68, 328, 100), "op", (1,), f and bits(f["opcode"]), (333, 84))
        box(252, 100, 400, 140, "指令译码器", hot=(ph == 1))
        c.create_text(326, 130, text=f and MNEMONIC.get(f["opcode"], "未定义") or "", font=self.f_small,
                      fill=MUTED)
        box(252, 150, 400, 318, "控制信号", hot=(ph == 1))
        wire((326, 140, 326, 150), "op", (1,), arrow=False)
        sigs = [("WE", "写寄存器"), ("DWE", "显示"), ("RSS", "写回选"), ("AFS", "ALU 做"), ("SUB", "减法")]
        for k, (s, desc) in enumerate(sigs):
            y = 180 + k * 27
            val = ""
            if t and ph >= 1:
                v = ctrl[s]
                val = bits(v, 2) if s in ("RSS", "AFS") else str(v)
            hot = t is not None and ph >= 1 and ctrl[s] != 0
            c.create_text(262, y, anchor="w", text=s, font=self.f_mono_big, fill=ACTIVE if hot else INK)
            c.create_text(312, y, anchor="w", text=val, font=self.f_mono_big, fill=ACTIVE if hot else INK)
            c.create_text(345, y, anchor="w", text=desc, font=self.f_small, fill=MUTED)

        # 寄存器堆
        RX0, RX1 = 450, 600
        box(RX0, 100, RX1, 420, "寄存器堆", hot=(ph in (2, 4) and t is not None and (u["A"] or u["D"])))
        for i in range(8):
            y = 138 + i * 33
            fill = BOX
            note = ""
            if t and ph >= 2:
                if i == f["A"] and u["A"]:
                    fill = "#ebfbee"
                if i == f["B"] and u["B"]:
                    fill = "#f3f0ff" if fill == BOX else "#e6fcf5"
            if t and ph == 4 and u["D"] and i == f["D"]:
                fill = "#e7f5ff"
                if t["old_value"] != regs[i]:
                    note = "←{}".format(t["old_value"])
            c.create_rectangle(RX0 + 8, y - 13, RX1 - 8, y + 13, fill=fill, outline="#dee2e6")
            c.create_text(RX0 + 16, y, anchor="w", text="R{}".format(i), font=self.f_bold, fill=INK)
            c.create_text(RX0 + 52, y, anchor="w", text=bits(regs[i]), font=self.f_mono_big, fill=INK)
            c.create_text(RX0 + 108, y, anchor="w", text=str(regs[i]) + note, font=self.f_mono, fill=INK)
            tags = []
            if t and ph >= 2 and i == f["A"]:
                tags.append(("A", FIELD_COLORS["A"]))
            if t and ph >= 2 and i == f["B"]:
                tags.append(("B", FIELD_COLORS["B"]))
            if t and ph >= 4 and i == f["D"] and u["D"]:
                tags.append(("D", FIELD_COLORS["D"]))
            for k, (tg, col) in enumerate(tags):
                c.create_text(RX1 - 14 - k * 12, y, text=tg, fill=col, font=self.f_bold)

        # 地址线
        wire((x0 + 6.5 * 38, 68, x0 + 6.5 * 38, 100), "D", (4,), f and "D={}".format(f["D"]), (x0 + 6.5 * 38 + 4, 82))
        ax = x0 + 10.5 * 38
        wire((ax, 68, ax, 76, 545, 76, 545, 100), "A", (2,), f and "A={}".format(f["A"]), (ax + 4, 72))
        bx = x0 + 14.5 * 38
        wire((bx, 68, bx, 88, 580, 88, 580, 100), "B", (2,), f and "B={}".format(f["B"]), (bx + 4, 80))

        # ALU
        AX0, AX1 = 660, 770
        a_val = t["a_val"] if t else 0
        b_val = t["b_val"] if t else 0
        wire((RX1, 200, AX0, 200), "alu", (2, 3), t and "A={}".format(a_val), (RX1 + 6, 192))
        wire((RX1, 330, AX0, 330), "alu", (2, 3), t and "B={}".format(b_val), (RX1 + 6, 322))
        hot_alu = t is not None and ph == 3
        c.create_polygon(AX0, 160, AX1, 205, AX1, 325, AX0, 370, AX0, 285, AX0 + 18, 265, AX0, 245,
                         fill=BOX, outline=ACTIVE if hot_alu else "#868e96", width=3 if hot_alu else 1.5)
        c.create_text(AX0 + 50, 180, text="ALU", font=self.f_bold, fill=INK)
        if t and ph >= 3:
            al = t["alu"]
            names = ["XOR", "AND", "OR", "SUB" if al["sub"] else "ADD"]
            for k in range(4):
                y = 222 + k * 22
                sel = k == al["afs"] and u["alu"]
                c.create_text(AX0 + 32, y, anchor="w", font=self.f_bold if sel else self.f_small,
                              fill=ACTIVE if sel else MUTED,
                              text="{} {}".format(names[k], al["candidates"][k]))
        if t and ph >= 1:
            c.create_text(AX0 + 50, 388, text="AFS={} SUB={}".format(bits(ctrl["AFS"], 2), ctrl["SUB"]),
                          font=self.f_small, fill=ACTIVE if ph == 1 else MUTED)

        # 写回选择器
        MX0, MX1 = 830, 870
        hot_mux = t is not None and ph == 4
        c.create_polygon(MX0, 150, MX1, 175, MX1, 355, MX0, 380, fill=BOX,
                         outline=ACTIVE if hot_mux else "#868e96", width=3 if hot_mux else 1.5)
        c.create_text(850, 140, text="写回选择", font=self.f_small, fill=INK)
        if t and ph >= 1:
            c.create_text(850, 394, text="RSS={}".format(bits(ctrl["RSS"], 2)), font=self.f_small,
                          fill=ACTIVE if ph == 1 else MUTED)
        ins_y = [190, 250, 310, 350]
        rss = ctrl["RSS"] if t else -1
        for k, y in enumerate(ins_y):
            c.create_text(MX0 + 8, y, text=str(k), font=self.f_small,
                          fill=ACTIVE if (t and ph == 4 and k == rss) else MUTED)
        # 输入 0：Data（立即数）
        dx = x0 + 15.5 * 38
        wire((dx, 68, dx, 128, 800, 128, 800, 190, MX0, 190), "data", (2, 4),
             f and "Data={}".format(f["Data"]), (dx + 4, 112))
        # 输入 1：ALU 结果
        wire((AX1, 265, 800, 265, 800, 250, MX0, 250), "alu", (3, 4) if rss == 1 else (3,),
             t and str(t["alu"]["result"]), (AX1 + 4, 257))
        # 输入 2、3：寄存器 A
        wire((625, 200, 625, 400, 805, 400, 805, 310, MX0, 310), "A2", (2, 4),
             t and "A={}".format(a_val), (630, 392))
        wire((805, 350, MX0, 350), "_", (2,))
        # 输出 → 写端口
        wd = t["write_data"] if t else 0
        wire((MX1, 265, 900, 265, 900, 452, 525, 452, 525, 420), "D", (4,),
             t and "写入数据={}".format(wd), (690, 444))
        if t and ph >= 1:
            c.create_text(RX0 + 4, 434, anchor="w", text="WE={}".format(ctrl["WE"]), font=self.f_small,
                          fill=ACTIVE if ph in (1, 4) and ctrl["WE"] else MUTED)

        # 显示器
        box(20, 340, 400, 468, "显示器（ASCII 终端）", hot=(t is not None and ph == 4 and u["disp"]))
        txt = "".join(display_char(ch) for ch in self.cpu.display)
        c.create_text(36, 395, anchor="w", text=txt + "▌", font=self.f_mono_big, fill="#2b8a3e")
        if t and ph >= 1:
            c.create_text(390, 455, anchor="e", text="DWE={}".format(ctrl["DWE"]), font=self.f_small,
                          fill=ACTIVE if ph in (1, 4) and ctrl["DWE"] else MUTED)
        wire((RX0, 380, 400, 380), "disp", (2, 4), arrow=True)
        if t and ph >= 2:
            c.create_text(405, 368, anchor="w", text="A,B", font=self.f_small, fill=MUTED)

        # 时钟周期计数和阶段条
        for k, nm in enumerate(PHASE_NAMES):
            x = 440 + k * 94
            on = t is not None and k == ph
            done = t is not None and k < ph
            c.create_rectangle(x, 462, x + 90, 478, fill=ACTIVE if on else USED if done else "#f1f3f5",
                               outline="")
            c.create_text(x + 45, 470, text=nm, font=self.f_small, fill="white" if on else INK)

        if not keep_label:
            if t is None or ph < 0:
                if self.cpu.halted:
                    msg = "程序执行完了。点“重置”从头再来。"
                else:
                    msg = ("准备执行第 {} 条指令：{}。点“下一小步”开始，一条指令拆成 5 小步。"
                           .format(self.cpu.pc, self.cpu.program[self.cpu.pc][1]))
                self.phase_label.config(text=msg)
            else:
                self.phase_label.config(text=describe_phase(t, ph))

    # ─── 小工具窗口 ───

    def open_editor(self):
        win = tk.Toplevel(self.root)
        win.title("编辑程序")
        win.configure(bg=BG)
        tk.Label(win, bg=BG, fg=MUTED, justify="left",
                 text="一行一条指令，# 后面是注释。寄存器 $0~$7，立即数 0~15。\n"
                      "可用指令：NOP  LD  MOV  DISP  XOR  AND  OR  ADD  SUB").pack(anchor="w", padx=10, pady=(10, 4))
        txt = tk.Text(win, width=56, height=20, font=self.f_mono, undo=True)
        txt.pack(padx=10, fill="both", expand=True)
        txt.insert("1.0", self.source)
        err = tk.Label(win, bg=BG, fg="#c92a2a", justify="left", anchor="w")
        err.pack(fill="x", padx=10)

        def do_load():
            try:
                self.load_source(txt.get("1.0", "end"))
            except AsmError as e:
                err.config(text=str(e))
                return
            win.destroy()

        bar = tk.Frame(win, bg=BG)
        bar.pack(fill="x", padx=10, pady=10)
        ttk.Button(bar, text="装载并关闭", command=do_load).pack(side="left")
        ttk.Button(bar, text="恢复示例程序",
                   command=lambda: (txt.delete("1.0", "end"), txt.insert("1.0", EXAMPLE_PROGRAM))).pack(side="left", padx=4)

    def open_decoder_tool(self):
        win = tk.Toplevel(self.root)
        win.title("指令拆解器")
        win.configure(bg=BG)
        tk.Label(win, bg=BG, text="输入 4 位十六进制机器码（如 7331）或一条汇编（如 SUB $4, $4, $1）：").pack(
            anchor="w", padx=10, pady=(10, 2))
        var = tk.StringVar(value="7331")
        ent = ttk.Entry(win, textvariable=var, font=self.f_mono_big, width=30)
        ent.pack(anchor="w", padx=10)
        cv = tk.Canvas(win, width=700, height=90, bg=BOX, highlightthickness=0)
        cv.pack(padx=10, pady=8)
        out = tk.Label(win, bg=BG, justify="left", anchor="w", font=self.f_mono)
        out.pack(fill="x", padx=10, pady=(0, 10))

        def update(*_):
            s = var.get().strip()
            cv.delete("all")
            code = None
            try:
                if re.fullmatch(r"(0x)?[0-9a-fA-F]{1,4}", s):
                    code = int(s, 16)
                else:
                    code = assemble_line(s)
            except AsmError as e:
                out.config(text=str(e), fg="#c92a2a")
                return
            if code is None:
                out.config(text="", fg=INK)
                return
            for i in range(16):
                bit = 15 - i
                fld = FIELD_OF_BIT[bit]
                x = 10 + i * 42
                cv.create_rectangle(x, 22, x + 40, 62, fill=FIELD_COLORS[fld], outline="white")
                cv.create_text(x + 20, 42, text=str((code >> bit) & 1), fill="white", font=self.f_mono_big)
                cv.create_text(x + 20, 12, text=str(bit), fill=MUTED, font=self.f_small)
            for name, lo_i, hi_i in (("opcode", 0, 3), ("D", 5, 7), ("A", 9, 11), ("B / Data", 12, 15)):
                cv.create_text(10 + (lo_i + hi_i + 1) * 21, 76, text=name,
                               fill=FIELD_COLORS.get(name.split()[0], INK), font=self.f_small)
            f = split_fields(code)
            ctl = control_signals(f["opcode"])
            out.config(fg=INK, text=(
                "机器码 0x{:04X}  =  {}\n"
                "opcode = {} → {}\n"
                "D = {} (R{})   A = {} (R{})   B = {} (R{})   Data = {} ({})\n"
                "译码器输出控制字 {}：SUB={} AFS={} RSS={} DWE={} WE={}"
            ).format(code, disassemble(code), bits(f["opcode"]), MNEMONIC.get(f["opcode"], "未定义（当 NOP）"),
                     bits(f["D"], 3), f["D"], bits(f["A"], 3), f["A"], bits(f["B"], 3), f["B"],
                     bits(f["Data"]), f["Data"], bits(ctl["word"], 7), ctl["SUB"], bits(ctl["AFS"], 2),
                     bits(ctl["RSS"], 2), ctl["DWE"], ctl["WE"]))

        var.trace_add("write", update)
        update()

    def open_alu_tool(self):
        win = tk.Toplevel(self.root)
        win.title("ALU 实验台")
        win.configure(bg=BG)
        top = tk.Frame(win, bg=BG)
        top.pack(anchor="w", padx=10, pady=10)
        a_var, b_var, op_var = tk.IntVar(value=3), tk.IntVar(value=5), tk.StringVar(value="SUB")
        tk.Label(top, text="A =", bg=BG).pack(side="left")
        ttk.Spinbox(top, from_=0, to=15, textvariable=a_var, width=4, command=lambda: update()).pack(side="left")
        tk.Label(top, text="  B =", bg=BG).pack(side="left")
        ttk.Spinbox(top, from_=0, to=15, textvariable=b_var, width=4, command=lambda: update()).pack(side="left")
        tk.Label(top, text="  运算", bg=BG).pack(side="left")
        cb = ttk.Combobox(top, values=["XOR", "AND", "OR", "ADD", "SUB"], textvariable=op_var, width=6,
                          state="readonly")
        cb.pack(side="left")
        out = tk.Label(win, bg=BOX, justify="left", anchor="nw", font=self.f_mono, padx=12, pady=10)
        out.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        def update(*_):
            try:
                a, b = a_var.get() & 15, b_var.get() & 15
            except tk.TclError:
                return
            op = op_var.get()
            afs = {"XOR": 0, "AND": 1, "OR": 2, "ADD": 3, "SUB": 3}[op]
            sub = 1 if op == "SUB" else 0
            r = alu(sub, afs, a, b)
            sp = lambda v: "  ".join(bits(v))
            lines = [pad("  第几位") + "3  2  1  0",
                     pad("  A = {:2d}".format(a)) + sp(a),
                     pad("  B = {:2d}".format(b)) + sp(b)]
            if afs < 3:
                rule = {0: "两位不同 → 1", 1: "两位都是 1 → 1", 2: "有一个 1 → 1"}[afs]
                lines += ["  " + "─" * 30,
                          pad("  " + op) + "{}   （逐位：{}）".format(sp(r["result"]), rule)]
            else:
                cs = r["carries"]
                if sub:
                    lines.append(pad("  B 取反") + "{}   （SUB=1：每位和 1 异或）".format(sp(r["b_in"])))
                lines += [pad("  进位") + "{}   （送进这一位的进位；最低位进位 = SUB = {}）".format(
                              "  ".join(str(cs[i]) for i in (3, 2, 1, 0)), sub),
                          "  " + "─" * 30,
                          pad("  结果") + "{}   = {}".format(sp(r["result"]), r["result"]),
                          "  最高位进位 c4 = {} {}".format(cs[4], "（被丢掉）" if cs[4] else "")]
                exact = a - b if sub else a + b
                if exact != r["result"]:
                    lines.append("  数学上应是 {}，但 4 位只能存 0~15，所以得到 {}。".format(exact, r["result"]))
                lines.append("")
                lines.append("  每一位是一个全加器：和 = A XOR B XOR 进位，进位 = (A AND B) OR (进位 AND (A XOR B))")
            lines.append("")
            lines.append("  ALU 四路同时算出：XOR={} AND={} OR={} {}={}，AFS={} 选第 {} 路".format(
                *r["candidates"][:3], "SUB" if sub else "ADD", r["candidates"][3], bits(afs, 2), afs))
            out.config(text="\n".join(lines))

        for v in (a_var, b_var, op_var):
            v.trace_add("write", update)
        update()


def main():
    root = tk.Tk()
    w = min(1420, root.winfo_screenwidth() - 20)
    h = min(800, root.winfo_screenheight() - 80)
    root.geometry("{}x{}+10+10".format(w, h))
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
