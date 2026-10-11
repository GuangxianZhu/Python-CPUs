"""用原仓库的 Verilog 当“标准答案”，随机生成指令逐条对比 Python 模型。

需要 Icarus Verilog（iverilog / vvp）和原仓库代码：
    git clone https://github.com/SimDaSong/4-bit-cpu
    python tests/verify_against_verilog.py 4-bit-cpu/src
"""
import os
import random
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from cpu_core import CPU  # noqa: E402

TB = r"""
`include "cpu.v"
module vtb;
  reg [15:0] code; reg clk, clr; wire [3:0] a, b;
  reg [15:0] mem [0:%(n)d];
  integer i;
  cpu uut(code, clk, clr, a, b);
  initial begin
    $readmemh("%(hex)s", mem);
    clk = 0; clr = 0; code = 0;
    #1 clr = 1; #1 clr = 0; #1;
    for (i = 0; i < %(n)d; i = i + 1) begin
      code = mem[i]; #1;
      $write("%%0d %%0d", a, b);          // 时钟沿之前两个读端口的值
      clk = 1; #1;
      $display(" %%0d %%0d %%0d %%0d %%0d %%0d %%0d %%0d",
        uut.uut2.reg1, uut.uut2.reg2, uut.uut2.reg3, uut.uut2.reg4,
        uut.uut2.reg5, uut.uut2.reg6, uut.uut2.reg7, uut.uut2.reg8);
      clk = 0; #1;
    end
    $finish;
  end
endmodule
"""


def main(src_dir, n=3000, seed=1):
    rng = random.Random(seed)
    # 一半用合法 opcode，一半完全随机（含未定义 opcode 和“没用到”的位）
    legal = [0x0, 0x1, 0x2, 0x3, 0x4, 0x5, 0x6, 0x7, 0xF]
    codes = []
    for _ in range(n):
        c = rng.randrange(1 << 16)
        if rng.random() < 0.7:
            c = (c & 0x0FFF) | rng.choice(legal) << 12
        codes.append(c)

    with tempfile.TemporaryDirectory() as tmp:
        hexf = os.path.join(tmp, "prog.hex")
        with open(hexf, "w") as fh:
            fh.write("\n".join("%04x" % c for c in codes))
        tbf = os.path.join(tmp, "vtb.v")
        with open(tbf, "w") as fh:
            fh.write(TB % {"n": n, "hex": hexf})
        out = os.path.join(tmp, "vtb.vvp")
        subprocess.check_call(["iverilog", "-I", src_dir, "-o", out, tbf])
        lines = subprocess.check_output(["vvp", out], cwd=tmp, text=True).splitlines()
    lines = [l for l in lines if l and l[0].isdigit()]

    cpu = CPU()
    cpu.load([(c, "") for c in codes])
    bad = 0
    for i, line in enumerate(lines):
        nums = list(map(int, line.split()))
        t = cpu.step()
        mine = [t["a_val"], t["b_val"]] + cpu.regs
        if mine != nums:
            bad += 1
            if bad <= 5:
                print("不一致 #%d 指令 %04X: verilog=%s python=%s" % (i, codes[i], nums, mine))
    print("对比 %d 条指令，不一致 %d 条" % (len(lines), bad))
    return 0 if bad == 0 and len(lines) == n else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "4-bit-cpu/src"))
