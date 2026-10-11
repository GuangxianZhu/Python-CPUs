# 4 位 CPU 互动教学演示

基于开源项目 [SimDaSong/4-bit-cpu](https://github.com/SimDaSong/4-bit-cpu)（MIT 许可）做的 Python 教学程序，给高中水平的初学者一步步看懂一台 CPU：从整体架构到每一根线。

> 注意：原项目**不是 SPARC CPU**，而是作者自己设计的 4 位玩具 CPU（9 条指令、8 个寄存器、没有跳转和内存访问）。第 11 章专门对比它和 SPARC 的差别。

## 运行

```bash
python cpu_demo.py
```

只需要 Python 3.8 以上，用的是自带的 tkinter，不需要安装任何包。
Windows 和 macOS 上从 python.org 下载的 Python 都自带 tkinter；Linux 上如果报 `No module named tkinter`，装一下 `python3-tk`。
窗口最好有 1400 像素宽。

## 里面有什么

| 部分 | 说明 |
|---|---|
| 数据通路图 | PC、程序存储器、16 位指令（按字段上色）、译码器和控制信号、8 个寄存器、ALU、写回选择器、ASCII 显示器 |
| 下一小步 | 一条指令拆成 ① 取指 ② 译码 ③ 读寄存器 ④ 运算 ⑤ 写回，橙色线是这一步在用的通路，灰色线“有值但没人用” |
| 执行前先让我预测 | 勾上以后，每条指令执行前先出一道四选一，猜完再一步步看电路怎么算出来 |
| 12 章讲解 | 每章先出一道选择题让学生预测，答完才显示讲解；讲解里用【源码】【通识】【推断】标出证据强弱 |
| 小工具 | 指令拆解器（输入机器码或汇编看字段和控制信号）、ALU 实验台（逐位看全加器进位）、程序编辑器 |

章节：全景 → 二进制 → 指令格式 → PC 与取指 → 译码器 → 寄存器堆 → ALU 逻辑运算 → 加法器与减法 → 写回与单周期 → DISP 与 ASCII → 自由实验 → 和 SPARC 的差距

## 文件

```
cpu_demo.py        界面（tkinter）
cpu_core.py        CPU 模型：汇编器、译码器、全加器 ALU、寄存器堆（不依赖界面）
lessons.py         章节内容、每一小步的文字说明、预测题生成
tests/test_core.py               单元测试：python -m unittest tests/test_core.py
tests/verify_against_verilog.py  用原仓库的 Verilog 做标准答案逐条对比
```

## 和原电路一致吗

`cpu_core.py` 的行为对照原仓库 `src/cpu.v`、`alu.v`、`three_port_reg_file.v` 编写。
`tests/verify_against_verilog.py` 用 Icarus Verilog 跑原仓库的 Verilog，随机生成 3000 条指令（包括未定义的 opcode 和没用到的位）逐条对比两个读端口和 8 个寄存器，结果 0 处不一致。

```bash
git clone https://github.com/SimDaSong/4-bit-cpu
python tests/verify_against_verilog.py 4-bit-cpu/src
```

## 需要知道的简化和假设

- **“5 小步”是教学拆分。** 原电路是单周期的：一个时钟周期里所有部件同时工作，周期结束的时钟上升沿才写寄存器。程序里第 ⑤ 步才真正改寄存器，对应这个时钟沿。
- **PC 和程序存储器按 Logisim 版画。** Verilog 版没有 PC，指令由测试文件直接喂进去。
- **DISP 的字符拼法是推断。** 把 Ra 的低 3 位和 Rb 的 4 位拼成 7 位 ASCII 码，是根据 Logisim 里的 TTY 元件和示例程序推出来的，仓库没有用文字写明。Verilog 版里 DWE 没有连到任何东西；作者的网页版只把 Rb 当数字打印。
- **ALU 按全加器逐位算**（对应 Logisim 的 fulladder 子电路），Verilog 版写的是 `a + xorB + sub`，两者结果相同。
