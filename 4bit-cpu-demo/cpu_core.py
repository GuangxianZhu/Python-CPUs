"""4 位 CPU 的 Python 模型（不含界面）。

行为逐条对照 SimDaSong/4-bit-cpu 仓库的 src/cpu.v、alu.v、three_port_reg_file.v。
为了教学，ALU 的加法用 4 个全加器逐位串起来算（对应 Logisim 电路里的
fulladder 子电路）；Verilog 版直接写的是 `a + xorB + sub`，两者结果相同。

用法：
    cpu = CPU(); cpu.load(assemble(source))
    trace = cpu.preview()   # 只算出这一拍电路里每根线上的值，不改状态
    cpu.commit(trace)       # 相当于时钟上升沿：写寄存器、显示、PC+1
"""

# ─── 指令集 ───

OPCODES = {
    "NOP": 0x0, "LD": 0x1, "MOV": 0x2, "DISP": 0x3,
    "XOR": 0x4, "AND": 0x5, "OR": 0x6, "ADD": 0x7, "SUB": 0xF,
}
MNEMONIC = {v: k for k, v in OPCODES.items()}

# 指令译码器：opcode -> 7 位控制字，和 cpu.v 里的 case 表一模一样。
# 位：6=SUB  5:4=AFS  3:2=RSS  1=DWE  0=WE
CONTROL_ROM = {
    0x1: 0x01,  # LD
    0x2: 0x09,  # MOV
    0x3: 0x02,  # DISP
    0x4: 0x05,  # XOR
    0x5: 0x15,  # AND
    0x6: 0x25,  # OR
    0x7: 0x35,  # ADD
    0xF: 0x75,  # SUB
}

AFS_NAMES = ["XOR", "AND", "OR", "ADD/SUB"]
RSS_NAMES = ["指令里的立即数 Data", "ALU 结果", "寄存器 A 的值", "寄存器 A 的值"]


def control_signals(opcode):
    word = CONTROL_ROM.get(opcode, 0)  # 没定义的 opcode 控制字全 0，等同 NOP
    return {
        "word": word,
        "WE": word & 1,
        "DWE": (word >> 1) & 1,
        "RSS": (word >> 2) & 3,
        "AFS": (word >> 4) & 3,
        "SUB": (word >> 6) & 1,
    }


def split_fields(code):
    """把 16 位指令拆成各个字段（位置见 cpu.v 开头的 assign）。"""
    return {
        "opcode": (code >> 12) & 0xF,  # [15:12]
        "D": (code >> 8) & 0x7,        # [10:8]
        "A": (code >> 4) & 0x7,        # [6:4]
        "B": code & 0x7,               # [2:0]
        "Data": code & 0xF,            # [3:0]
    }


def bits(value, width=4):
    return format(value & ((1 << width) - 1), "0{}b".format(width))


# ─── ALU ───

def full_adder(a, b, cin):
    """一位全加器，门级写法与 fulladder.v 相同。"""
    t1 = a ^ b
    t2 = a & b
    t3 = cin & t1
    return cin ^ t1, t2 | t3  # (和, 进位)


def ripple_add(a, b, cin):
    """4 个全加器串成行波进位加法器，返回每一位的细节，方便画出来。"""
    carries = [cin]
    sums = []
    for i in range(4):
        s, c = full_adder((a >> i) & 1, (b >> i) & 1, carries[-1])
        sums.append(s)
        carries.append(c)
    result = sum(s << i for i, s in enumerate(sums))
    return result, carries  # carries[i] 是进入第 i 位的进位，carries[4] 是最高位溢出


def alu(sub, afs, a, b):
    """和 alu.v 一样：四种运算同时算出来，再由 AFS 选一个。"""
    b_in = b ^ (0xF if sub else 0)          # SUB=1 时把 B 每一位取反
    add_res, carries = ripple_add(a, b_in, sub)  # 再把 SUB 当作最低位进位 +1
    candidates = [a ^ b, a & b, a | b, add_res]
    return {
        "a": a, "b": b, "sub": sub, "afs": afs,
        "b_in": b_in, "carries": carries,
        "candidates": candidates,
        "result": candidates[afs],
    }


# ─── 汇编器 ───

class AsmError(Exception):
    pass


def _reg(tok):
    t = tok.strip().upper().lstrip("$").lstrip("R")
    if not t.isdigit() or not 0 <= int(t) <= 7:
        raise AsmError("寄存器写法不对：{}（应为 $0~$7 或 R0~R7）".format(tok))
    return int(t)


def _imm(tok):
    try:
        v = int(tok, 0)
    except ValueError:
        raise AsmError("立即数不是数字：{}".format(tok))
    if not 0 <= v <= 15:
        raise AsmError("立即数只能是 0~15（4 位），而你写了 {}".format(v))
    return v


def assemble_line(line):
    """把一行汇编翻译成 16 位机器码；空行/注释返回 None。"""
    text = line.split("#")[0].split("//")[0].split(";")[0].strip()
    if not text:
        return None
    toks = [t for t in text.replace(",", " ").split() if t]
    op = toks[0].upper()
    args = toks[1:]
    if op not in OPCODES:
        raise AsmError("不认识的指令：{}".format(toks[0]))
    need = {"NOP": 0, "LD": 2, "MOV": 2, "DISP": 2}.get(op, 3)
    if len(args) != need:
        raise AsmError("{} 需要 {} 个操作数，这里有 {} 个".format(op, need, len(args)))
    opc = OPCODES[op] << 12
    if op == "NOP":
        return 0
    if op == "LD":
        return opc | _reg(args[0]) << 8 | _imm(args[1])
    if op == "MOV":
        return opc | _reg(args[0]) << 8 | _reg(args[1]) << 4
    if op == "DISP":
        return opc | _reg(args[0]) << 4 | _reg(args[1])
    return opc | _reg(args[0]) << 8 | _reg(args[1]) << 4 | _reg(args[2])


def assemble(source):
    """返回 [(机器码, 原文), ...]；出错时抛 AsmError，并注明行号。"""
    program = []
    for n, line in enumerate(source.splitlines(), 1):
        try:
            code = assemble_line(line)
        except AsmError as e:
            raise AsmError("第 {} 行：{}".format(n, e))
        if code is not None:
            program.append((code, disassemble(code)))
    return program


def disassemble(code):
    f = split_fields(code)
    op = MNEMONIC.get(f["opcode"])
    if op is None:
        return "??? (未定义 opcode {:X}，当 NOP)".format(f["opcode"])
    if op == "NOP":
        return "NOP"
    if op == "LD":
        return "LD $%d, %d" % (f["D"], f["Data"])
    if op == "MOV":
        return "MOV $%d, $%d" % (f["D"], f["A"])
    if op == "DISP":
        return "DISP $%d, $%d" % (f["A"], f["B"])
    return "%s $%d, $%d, $%d" % (op, f["D"], f["A"], f["B"])


# ─── CPU ───

class CPU:
    def __init__(self):
        self.program = []
        self.reset()

    def reset(self):
        self.regs = [0] * 8
        self.pc = 0
        self.display = []   # 显示器上已经输出的内容
        self.cycles = 0

    def load(self, program):
        self.program = list(program)
        self.reset()

    @property
    def halted(self):
        return self.pc >= len(self.program)

    def preview(self):
        """算出这一拍里电路每个部分的值（组合逻辑），但还不写入任何东西。"""
        if self.halted:
            return None
        code, text = self.program[self.pc]
        f = split_fields(code)
        ctrl = control_signals(f["opcode"])
        a_val = self.regs[f["A"]]     # 读端口 A：8 选 1 MUX 按地址 A 选出
        b_val = self.regs[f["B"]]     # 读端口 B
        alu_out = alu(ctrl["SUB"], ctrl["AFS"], a_val, b_val)
        mux_inputs = [f["Data"], alu_out["result"], a_val, a_val]  # cpu.v: mux_4to1(data, aluRes, a, a, ...)
        write_data = mux_inputs[ctrl["RSS"]]
        disp_code = ((a_val & 0x7) << 4) | b_val  # 送给 ASCII 显示器的 7 位
        return {
            "pc": self.pc, "code": code, "text": text,
            "fields": f, "ctrl": ctrl,
            "a_val": a_val, "b_val": b_val,
            "alu": alu_out,
            "mux_inputs": mux_inputs, "write_data": write_data,
            "old_value": self.regs[f["D"]],
            "disp_code": disp_code,
        }

    def commit(self, trace):
        """时钟上升沿：WE=1 时把写回数据存进 Rd；DWE=1 时显示；PC+1。"""
        if trace["ctrl"]["WE"]:
            self.regs[trace["fields"]["D"]] = trace["write_data"]
        if trace["ctrl"]["DWE"]:
            self.display.append(trace["disp_code"])
        self.pc += 1
        self.cycles += 1

    def step(self):
        t = self.preview()
        if t is not None:
            self.commit(t)
        return t


def display_char(code7):
    """把 7 位 ASCII 码变成能打印的字符。"""
    return chr(code7) if 32 <= code7 < 127 else "·"


EXAMPLE_PROGRAM = """\
LD  $0, 0        # R0 = 0
LD  $1, 1        # R1 = 1
LD  $2, 3        # R2 = 3（显示时当 ASCII 的高位，见第 9 章）
LD  $3, 3        # R3 = 3
DISP $2, $3      # 显示 '3'
MOV $4, $2       # R4 = R2 = 3
SUB $4, $4, $1   # R4 = 3 - 1 = 2
DISP $2, $4      # 显示 '2'
ADD $3, $3, $1   # R3 = 3 + 1 = 4
DISP $2, $3      # 显示 '4'
XOR $5, $3, $4   # R5 = 4 XOR 2 = 6
DISP $2, $5      # 显示 '6'
AND $5, $3, $4   # R5 = 4 AND 2 = 0
DISP $2, $5      # 显示 '0'
OR  $5, $3, $4   # R5 = 4 OR 2 = 6
DISP $2, $5      # 显示 '6'
"""
