"""课程内容：每一章 = 先预测的选择题 + 讲解 + 本章要装载的示例程序。

讲解里的方括号标签表示证据强弱：
  【源码】 直接从原仓库的 Verilog / Logisim 文件里读到的事实
  【通识】 计算机组成课本里的公认知识
  【推断】 根据源码线索推出来、但仓库没有明说的结论
"""

import random

from cpu_core import (AFS_NAMES, MNEMONIC, RSS_NAMES, bits, display_char)

LOGIC_PROGRAM = """\
LD  $1, 12       # R1 = 1100
LD  $2, 10       # R2 = 1010
XOR $3, $1, $2   # 不同为 1  -> 0110
AND $4, $1, $2   # 都是 1 才为 1 -> 1000
OR  $5, $1, $2   # 有一个 1 就为 1 -> 1110
"""

ADD_PROGRAM = """\
LD  $1, 3
LD  $2, 5
ADD $3, $1, $2   # 3 + 5 = 8
SUB $4, $2, $1   # 5 - 3 = 2
SUB $5, $1, $2   # 3 - 5 = ?  4 位里装不下负数
LD  $6, 15
LD  $7, 1
ADD $6, $6, $7   # 15 + 1 = ?  溢出
"""

HELLO_PROGRAM = """\
LD  $1, 4        # 'H' = 0x48 = 100 1000
LD  $2, 8
DISP $1, $2      # 显示 'H'
LD  $2, 9        # 'I' = 0x49
DISP $1, $2      # 显示 'I'
LD  $1, 2        # '!' = 0x21
LD  $2, 1
DISP $1, $2      # 显示 '!'
"""

REGFILE_PROGRAM = """\
LD  $4, 3        # R4 = 3
LD  $1, 1        # R1 = 1
SUB $4, $4, $1   # 同一个 R4 既读又写
SUB $4, $4, $1
MOV $0, $4       # R0 也能写（和 SPARC 的 %g0 不同）
"""

CHAPTERS = [
    {
        "title": "0. 全景：这台 CPU 由哪几块组成",
        "quiz": {
            "q": "要让 CPU 完成“把 R3 和 R1 相加，结果放进 R3”，一条指令里至少要写清楚哪些信息？",
            "options": [
                "只要写“做加法”就够了",
                "做什么运算、两个数从哪两个寄存器来、结果放到哪个寄存器",
                "只要写 3 和 1 这两个数",
                "只要写结果放在哪里",
            ],
            "answer": 1,
            "why": "CPU 自己什么都不知道，指令必须把“做什么、数从哪来、结果去哪”全写出来。"
                   "这台 CPU 的指令正好分成这几块：opcode（做什么）、A 和 B（数从哪来）、D（结果去哪）。",
        },
        "body": """\
## 先说清楚：它不是 SPARC
【源码】这个仓库（SimDaSong/4-bit-cpu）是作者自己设计的一台“玩具”CPU：数据只有 4 位，指令 16 位，8 个寄存器，一共 9 条指令。真正的 SPARC 是 Sun 公司的 32/64 位商用处理器架构，复杂得多。最后一章会专门对比两者差在哪。
它小，反而适合入门：每一根线都能看清楚。

## 上面那张图是什么
图里就是这台 CPU 的全部零件，一条指令依次流过它们：
  ① PC + 程序存储器：PC 记着“现在执行第几条”，从存储器里取出那条 16 位指令
  ② 指令译码器：看指令的前 4 位（opcode），翻译成一组开关信号（控制信号）
  ③ 寄存器堆：8 个 4 位的小格子 R0~R7，按指令里的地址读出两个数 A、B
  ④ ALU：对 A、B 做运算（异或 / 与 / 或 / 加减）
  ⑤ 写回选择器（MUX）：决定把哪个结果写回寄存器
  另外还有一个显示器，用 DISP 指令往上面打字

## 怎么用这个程序
· 每章先答一道选择题再看讲解，猜错了也没关系，带着疑问看讲解记得更牢。
· 点下方的“下一小步”，一条指令会拆成 5 小步，图上橙色的线就是这一步正在用的通路。
· 勾选“执行前先让我预测”，每条指令执行前都会先让你猜结果。

【说明】“5 小步”是为了讲解拆开的。真实电路是单周期的：在一个时钟周期里所有部件同时工作，周期结束的那一刻（时钟上升沿）才把结果写进寄存器。第 8 章会细讲。
""",
        "program": None,
    },
    {
        "title": "1. 二进制和 4 位数",
        "quiz": {
            "q": "这台 CPU 的寄存器是 4 位的。一个 4 位寄存器最大能存多大的数？",
            "options": ["9", "15", "16", "99"],
            "answer": 1,
            "why": "4 位二进制最大是 1111 = 8+4+2+1 = 15。能表示的数是 0~15，一共 16 个。",
        },
        "body": """\
## 为什么用二进制
电路里一根线只有两种状态：有电（1）和没电（0）。所以 CPU 里所有东西都是用 0 和 1 表示的。【通识】

## 4 位数怎么读
每一位有一个“权重”，从右往左是 1、2、4、8：
    1 0 1 1
    8 4 2 1   →  8 + 0 + 2 + 1 = 11
4 根线能表示 0000 ~ 1111，也就是 0 ~ 15。

## 十六进制：4 位的简写
4 位正好可以用一个十六进制数字表示：0~9 照常写，10~15 写成 A~F。
所以 16 位的指令可以写成 4 个十六进制数字，比如 0x7331 = 0111 0011 0011 0001。下一章就要拆这种数字。

## 装不下怎么办
【源码】这台 CPU 所有数据都只有 4 位。15 + 1 算出来是 10000（5 位），最高那一位没地方放，直接丢掉，结果变成 0000。这叫“溢出回绕”，第 7 章会在 ALU 里亲眼看到。
""",
        "program": None,
    },
    {
        "title": "2. 指令：16 位的命令",
        "quiz": {
            "q": "机器码 0x7331 是哪条指令？（提示：第一个十六进制数字是 opcode，7 代表 ADD）",
            "options": ["ADD $3, $3, $1", "ADD $7, $3, $3", "LD $3, 31", "SUB $3, $3, $1"],
            "answer": 0,
            "why": "0x7331 = 0111 0011 0011 0001。opcode=0111 是 ADD，D=011 是 R3，A=011 是 R3，B=001 是 R1，"
                   "所以是 R3 ← R3 + R1。",
        },
        "body": """\
## 指令的格式
【源码】cpu.v 里是这样拆的（数字是位的编号，15 在最左）：
    位:   15-12   11   10-8   7   6-4   3   2-0
         opcode   -     D     -    A    -    B
opcode 4 位：做什么运算（一共定义了 9 种）
D 3 位：结果写到哪个寄存器（3 位刚好能数 0~7，对应 R0~R7）
A、B 各 3 位：两个操作数从哪个寄存器读
标“-”的位没有用到，随便是 0 还是 1 都不影响。

## 一个例外：LD 的立即数
LD $3, 3 要把数字 3 直接写进 R3，这个 3 放在最低 4 位 [3:0]，叫 Data（立即数）。
【源码】Data 和 B 用的是同一块位置：硬件同时把最低几位接到了“B 地址”和“Data”两根线上，至于用哪个，交给后面的写回选择器决定。所以 LD 的立即数可以是 0~15（4 位），而寄存器地址只用 3 位。

## 9 条指令
    0000 NOP   什么都不做
    0001 LD    Rd ← Data
    0010 MOV   Rd ← Ra
    0011 DISP  把 Ra、Rb 送到显示器
    0100 XOR   Rd ← Ra 异或 Rb
    0101 AND   Rd ← Ra 与 Rb
    0110 OR    Rd ← Ra 或 Rb
    0111 ADD   Rd ← Ra + Rb
    1111 SUB   Rd ← Ra - Rb

点“指令拆解器”，自己输入机器码或者汇编试试。
""",
        "program": None,
        "actions": ["decoder_tool"],
    },
    {
        "title": "3. PC 和取指令",
        "quiz": {
            "q": "PC（程序计数器）里存的是什么？",
            "options": ["下一条要执行的指令在存储器里的位置（地址）", "指令本身", "上一次的运算结果", "寄存器的个数"],
            "answer": 0,
            "why": "PC 只存一个“地址”，像书签一样告诉 CPU 现在读到第几行。指令本身放在程序存储器里。",
        },
        "body": """\
## 取指令
每个周期开始，PC 里的数被当成地址送进程序存储器，存储器把那一格里的 16 位指令送出来。周期结束时 PC 加 1，下一个周期就取下一条。【通识】

## 这个仓库里的 PC 在哪
【源码】Logisim 电路里有一个计数器（Counter）当 PC，一个 16 位的 ROM 存程序，内容就是示例程序的 1000 1101 1203 …
【源码】Verilog 版本里没有 PC，也没有程序存储器：测试文件 cpu_tb.v 每 10ns 直接把下一条指令塞给 CPU。这个演示程序按 Logisim 的样子画了 PC 和存储器。

## 一个重要的缺口
这台 CPU 没有任何跳转指令，PC 只会一直加 1。这意味着程序只能从头走到尾，不能循环、不能“如果……就……”。真正的 CPU 都有跳转，最后一章再说。
""",
        "program": None,
    },
    {
        "title": "4. 译码器：把 opcode 翻译成开关",
        "quiz": {
            "q": "在硬件里，ADD 和 SUB 两条指令只有一根控制线不一样。你猜是哪一根？",
            "options": ["WE（要不要写寄存器）", "SUB（ALU 要不要做减法）", "RSS（写回选哪个数据）", "DWE（要不要显示）"],
            "answer": 1,
            "why": "ADD 的控制字是 011 0101，SUB 是 111 0101，只有最高位 SUB 不同。"
                   "加法和减法用的是同一个加法器，SUB=1 时把 B 取反再加 1，就变成了减法（第 7 章细讲）。",
        },
        "body": """\
## 控制信号
后面的寄存器堆、ALU、选择器都不认识“ADD”这个词，它们只看几根开关线：
    WE   1 位  寄存器写使能：1 = 这次要写寄存器
    DWE  1 位  显示写使能：1 = 这次要往显示器输出
    RSS  2 位  写回选择：00 立即数 Data，01 ALU 结果，10 寄存器 A
    AFS  2 位  ALU 功能：00 XOR，01 AND，10 OR，11 加/减
    SUB  1 位  1 = 减法
译码器的工作就是：看 opcode，输出这 7 根线该是 0 还是 1。

## 它其实是一张表
【源码】cpu.v 里就是一个 case 表；Logisim 版更直接，用一块 ROM 存这张表（PROM for Inst Decoder），opcode 当地址去查。
    指令  opcode  SUB AFS RSS DWE WE
    NOP   0000     0  00  00   0   0
    LD    0001     0  00  00   0   1
    MOV   0010     0  00  10   0   1
    DISP  0011     0  00  00   1   0
    XOR   0100     0  00  01   0   1
    AND   0101     0  01  01   0   1
    OR    0110     0  10  01   0   1
    ADD   0111     0  11  01   0   1
    SUB   1111     1  11  01   0   1
没写在表里的 opcode（1000~1110）查出来全是 0，效果等于 NOP。【源码】

用“下一小步”走到第 ② 步，看图上的控制信号怎么变。
""",
        "program": None,
        "actions": ["decoder_tool"],
    },
    {
        "title": "5. 寄存器堆：8 个小格子",
        "quiz": {
            "q": "SUB $4, $4, $1 里，同一个 R4 既要被读又要被写。在一个时钟周期里能做到吗？",
            "options": [
                "不能，读写会冲突，结果是乱的",
                "能：整个周期里读出的是旧值，算好的新值等到周期结束的时钟沿才写进去",
                "能，因为 CPU 会自动多等一个周期",
                "不能，必须拆成两条指令",
            ],
            "answer": 1,
            "why": "读是“随时在读”（组合电路），写只在时钟上升沿那一瞬间发生。所以整个周期里 ALU 看到的都是 R4 的旧值，"
                   "边沿到来时才把新值存进去。",
        },
        "body": """\
## 三个端口
【源码】three_port_reg_file.v：8 个 4 位寄存器，两个读端口（A、B）加一个写端口（D），所以叫“三端口寄存器堆”。

## 读：8 选 1 选择器
每个读端口是一个 8 选 1 的选择器（MUX）：8 个寄存器的值都接进来，3 位地址决定把哪一个送出去。读端口一直在工作，地址一变输出马上跟着变。

## 写：3-8 译码器 + 时钟
写地址 D（3 位）先经过 3-8 译码器，变成 8 根线里只有 1 根是 1（比如 D=100 → 第 4 根）。再和 WE 做“与”，只有 WE=1 时这根线才真的打开。
到时钟上升沿那一刻，被打开的那个寄存器把写入数据存进去，其它 7 个不动。【源码】

## 和 SPARC 的一个小区别
【源码】这里的 R0 是普通寄存器，可以写。【通识】SPARC 的 %g0（以及 MIPS 的 $zero）是读出来永远为 0 的特殊寄存器。本章示例程序最后一条 MOV $0, $4 可以验证这一点。
""",
        "program": REGFILE_PROGRAM,
    },
    {
        "title": "6. ALU（上）：逻辑运算",
        "quiz": {
            "q": "4 XOR 2 等于多少？（XOR：两位不同得 1，相同得 0）",
            "options": ["6", "0", "2", "4"],
            "answer": 0,
            "why": "4 = 0100，2 = 0010，逐位比较：0≠0? 否→0，1≠0→1，0≠1→1，0=0→0，得 0110 = 6。",
        },
        "body": """\
## 逐位运算
XOR、AND、OR 都是一位一位分别算的，4 位就是 4 个小门电路并排：
    A   B  | XOR  AND  OR
    0   0  |  0    0    0
    0   1  |  1    0    1
    1   0  |  1    0    1
    1   1  |  0    1    1

## ALU 的秘密：四种都算，最后挑一个
【源码】alu.v 里，XOR、AND、OR、加/减四个结果是同时算出来的，然后用一个 4 选 1 的选择器，按 AFS 挑一个输出。
这在硬件里很常见：多算几种不花时间（它们是并排同时进行的），挑选比“先判断再算”简单。
图里 ALU 方框中会同时列出四个结果，被选中的那个高亮。

装载本章程序，一步步看 12 和 10 做三种运算的结果；也可以打开“ALU 实验台”自己试。
""",
        "program": LOGIC_PROGRAM,
        "actions": ["alu_tool"],
    },
    {
        "title": "7. ALU（下）：加法器和减法",
        "quiz": {
            "q": "在这台 4 位 CPU 上执行 3 - 5，结果寄存器里会是多少？",
            "options": ["-2", "0", "14", "CPU 报错"],
            "answer": 2,
            "why": "减法是 3 + (5 取反) + 1 = 0011 + 1010 + 1 = 1110 = 14。"
                   "4 位里没有负号，1110 在“补码”的读法里正好代表 -2，但 CPU 自己并不知道，它只存了 1110。",
        },
        "body": """\
## 全加器：一位加法
一位加法有三个输入：A 的这一位、B 的这一位、低位送上来的进位；输出“和”与“进位”。
【源码】fulladder.v 就是它：和 = A XOR B XOR 进位，进位 = (A AND B) OR (进位 AND (A XOR B))。

## 串起来：行波进位加法器
4 个全加器排成一排，每一位的进位送给更高一位，像波浪一样往左传，所以叫“行波进位”。
【源码】Logisim 版的 ALU 用的就是 fulladder 子电路；Verilog 版直接写了 a + xorB + sub，结果一样。这个演示程序按全加器逐位算，方便你看每一位的进位。

## 减法 = 取反再加 1
【源码】SUB=1 时，B 的每一位先和 1 异或（等于取反），同时 SUB 这个 1 被当成最低位的进位加进去：
    A - B  =  A + (B 取反) + 1
这就是“补码”。好处是减法不需要单独的电路，一个加法器两用。【通识】

## 溢出：多出来的位直接丢掉
15 + 1 = 10000，第 5 位没地方放，结果变 0000。3 - 5 得到 1110 = 14。
【源码】这台 CPU 没有标志位（没有“进位标志”“负数标志”），所以程序无法知道刚才溢出了。真实 CPU 都会记下这些标志。

打开“ALU 实验台”，选 SUB，看每一位的进位是怎么传的。
""",
        "program": ADD_PROGRAM,
        "actions": ["alu_tool"],
    },
    {
        "title": "8. 写回选择器和一个完整的时钟周期",
        "quiz": {
            "q": "执行 LD $2, 3（把数字 3 放进 R2）的时候，ALU 在干什么？",
            "options": [
                "关掉了，不工作",
                "照常在计算，但它的结果被写回选择器丢掉了",
                "帮忙把 3 送进寄存器",
                "在计算 PC + 1",
            ],
            "answer": 1,
            "why": "ALU 是一直接着电的组合电路，输入一变它就算。LD 时 RSS=00，写回选择器选的是立即数 Data，ALU 的结果没人要，就被丢掉了。",
        },
        "body": """\
## 写回选择器
【源码】cpu.v 里写的是 mux_4to1(data, aluRes, a, a, rss, …)，四个输入是：
    RSS=00 → 指令里的立即数 Data   （LD 用）
    RSS=01 → ALU 的结果            （XOR/AND/OR/ADD/SUB 用）
    RSS=10 → 寄存器 A 的值          （MOV 用）
    RSS=11 → 也是寄存器 A 的值      （没有指令用到）
选出来的数送回寄存器堆的写端口。写不写，由 WE 决定。

## 单周期：所有事情在一拍里完成
【源码】README 写明这是单周期设计。时钟周期开始后，信号像水一样从左往右流：指令 → 译码 → 读寄存器 → ALU → 选择器，直到所有线上的值稳定。周期结束时的时钟上升沿，寄存器把选择器的输出存进去，PC 加 1。
这个程序里的“5 小步”是把这一次流动按顺序拆开给你看，不是 5 个时钟周期。

## 时钟能有多快？
【通识】时钟周期必须比最慢的那条路径还长，否则值还没稳定就被存进去了。这条最慢的路径叫“关键路径”，这里大概是 读寄存器 → 加法器（进位要传 4 位）→ 选择器。【推断】这个仓库没有给出时序数据。
真实 CPU 为了跑得更快，把一条指令拆到好几个周期、让多条指令重叠着走，这就是“流水线”。
""",
        "program": None,
    },
    {
        "title": "9. DISP 和 ASCII 显示器",
        "quiz": {
            "q": "示例程序每次显示数字前，都先执行 LD $2, 3，再 DISP $2, $x。你猜为什么偏偏是 3？",
            "options": [
                "3 是显示器的编号",
                "ASCII 码里字符 '0'~'9' 的编码是 0x30~0x39，高位正好是 3",
                "随便选的，换成别的也一样",
                "表示让数字显示 3 次",
            ],
            "answer": 1,
            "why": "显示器认的是 ASCII 码。'4' 的 ASCII 码是 0x34 = 011 0100：高 3 位来自 R2（=3），低 4 位来自 Rx（=4）。",
        },
        "body": """\
## DISP 做了什么
【源码】README 说 DISP 把 (Ra, Rb) 显示在 ASCII 显示器上；Logisim 电路里有一个 TTY（字符终端）元件，DWE 就是它的写使能。
【推断，证据较强】TTY 吃 7 位 ASCII 码：Ra 的低 3 位当高位，Rb 的 4 位当低位。示例程序的注释（DISP '3'、DISP '2'）和总是先 LD $2, 3 都和这个推断吻合。仓库没有用文字明说这个拼法。

## ASCII 是什么
【通识】ASCII 给每个字符编了一个 7 位的号码：'0' 是 0x30，'A' 是 0x41，'H' 是 0x48，空格是 0x20。
所以想显示 'H'：高 3 位 = 4，低 4 位 = 8，执行 LD $1,4 / LD $2,8 / DISP $1,$2 即可。本章程序会打出 HI!。

## 两个版本的区别
【源码】Verilog 版里 DWE 信号算出来了但没接到任何东西，CPU 只是把 A、B 两个读端口的值输出到模块外面；作者的网页版则只把 Rb 当数字打印出来。显示字符只在 Logisim 版里真正发生。
""",
        "program": HELLO_PROGRAM,
    },
    {
        "title": "10. 自由实验：自己写程序",
        "quiz": {
            "q": "R1 = 15，执行 ADD $1, $1, $1 之后，R1 是多少？",
            "options": ["30", "14", "15", "0"],
            "answer": 1,
            "why": "15 + 15 = 30 = 11110，只保留低 4 位 1110 = 14。",
        },
        "body": """\
## 怎么写
点“编辑程序”，一行一条指令，# 后面是注释。寄存器写 $0~$7 或 R0~R7，立即数 0~15。

## 挑战题
1. 只用 LD 和 DISP，在显示器上打出 OK（'O'=0x4F，'K'=0x4B）。
2. 只允许用一次 LD $1, 1，用加法算出 8 放进 R2。（提示：1+1=2，2+2=4……）
3. 不用 LD，把 R3 清零。（提示：一个数和自己 XOR 是多少？）
4. 算 7 - 9，先自己预测结果再运行。
5. 打出你名字的首字母。

记得勾选“执行前先让我预测”，每一步都先猜再看。
""",
        "program": None,
        "actions": ["editor"],
    },
    {
        "title": "11. 它离真正的 CPU（比如 SPARC）还差什么",
        "quiz": {
            "q": "只用这台 CPU 的 9 条指令，能写出“把某件事重复做 10 次”的循环吗？",
            "options": [
                "能，多写几条 ADD 就行",
                "不能：没有跳转指令，PC 只会加 1，程序没法回到前面",
                "能，用 SUB 倒着数到 0",
                "能，用 MOV 把 PC 改掉",
            ],
            "answer": 1,
            "why": "循环需要“跳回去”，也就是改 PC。这台 CPU 的 PC 只能加 1，也没有比较结果的标志位，所以不能循环，也不能做判断。"
                   "把代码复制 10 遍不算真正的循环。",
        },
        "body": """\
## 对比表
下面 SPARC 那一列是【通识】（SPARC V8 / V9 规范里的公开内容），左边一列是【源码】。
    项目        这台 4 位 CPU        SPARC
    数据宽度    4 位                 V8 是 32 位，V9 是 64 位
    寄存器      8 个                 寄存器窗口：每次能看到 32 个，%g0 恒为 0
    内存访问    没有                 ld / st 指令（只有它们能访问内存）
    跳转分支    没有                 有条件分支，还有“延迟槽”
    标志位      没有                 N Z V C 四个条件码
    执行方式    单周期               流水线
    指令长度    16 位                32 位

## 如果要给它加一个“跳转”
【推断】最少需要：一个新 opcode（比如 1000 = JMP），指令里放目标地址，再在 PC 前面加一个选择器——平时选 PC+1，执行 JMP 时选指令里的地址。译码器的表多一列控制这个选择器。
再加一个“结果为 0”标志位和一个“为 0 才跳”的指令，就能写循环了。这正是真实 CPU 一步步变复杂的方式。

## 学到这里你已经知道
指令是一串有格式的 0 和 1；译码器把它翻成开关；寄存器堆负责存取；ALU 负责计算，加减用同一个加法器；选择器决定数据走哪条路；时钟沿决定什么时候“存档”。
所有 CPU，包括 SPARC 和你手机里的芯片，都是这些零件的放大版。
""",
        "program": None,
    },
]


# ─── 每一小步的文字说明 ───

PHASE_NAMES = ["① 取指", "② 译码", "③ 读寄存器", "④ 运算", "⑤ 写回"]


def uses(trace):
    """这条指令真正“用到”的通路（其它通路上照样有值，只是没人要）。"""
    c = trace["ctrl"]
    use_alu = bool(c["WE"] and c["RSS"] == 1)
    return {
        "alu": use_alu,
        "A": use_alu or bool(c["WE"] and c["RSS"] >= 2) or bool(c["DWE"]),
        "B": use_alu or bool(c["DWE"]),
        "data": bool(c["WE"] and c["RSS"] == 0),
        "D": bool(c["WE"]),
        "disp": bool(c["DWE"]),
    }


def describe_phase(t, phase):
    f, c, u = t["fields"], t["ctrl"], uses(t)
    name = MNEMONIC.get(f["opcode"], "未定义")
    if phase == 0:
        return ("① 取指：PC = {pc}，从程序存储器第 {pc} 格取出 16 位指令 0x{code:04X} = {b}，也就是 {txt}。"
                .format(pc=t["pc"], code=t["code"], b=" ".join(bits(t["code"] >> s) for s in (12, 8, 4, 0)),
                        txt=t["text"]))
    if phase == 1:
        s = ("② 译码：opcode = {op} 是 {name}。译码器查表输出控制字 {w}："
             "WE={we} DWE={dwe} RSS={rss} AFS={afs} SUB={sub}。"
             .format(op=bits(f["opcode"]), name=name, w=bits(c["word"], 7), we=c["WE"], dwe=c["DWE"],
                     rss=bits(c["RSS"], 2), afs=bits(c["AFS"], 2), sub=c["SUB"]))
        if c["WE"]:
            s += "意思是：这次要写寄存器 R{}，写回的数据选“{}”".format(f["D"], RSS_NAMES[c["RSS"]])
            if u["alu"]:
                s += "，ALU 做 {}".format("SUB（减法）" if c["SUB"] else AFS_NAMES[c["AFS"]])
            s += "。"
        elif c["DWE"]:
            s += "意思是：不写寄存器，只往显示器输出。"
        else:
            s += "所有开关都是 0：什么也不做。"
        return s
    if phase == 2:
        s = ("③ 读寄存器：地址 A = {A} → 读出 R{A} = {a}（{ab}）；地址 B = {B} → 读出 R{B} = {b}（{bb}）。"
             .format(A=f["A"], a=t["a_val"], ab=bits(t["a_val"]), B=f["B"], b=t["b_val"], bb=bits(t["b_val"])))
        if not (u["A"] or u["B"]):
            s += "这条指令用不到它们，但两个读端口一直在读，值照样出现在线上。"
        elif not u["B"]:
            s += "这条指令只用到 A。"
        if f["opcode"] == 1:
            s += "注意 LD 的立即数 Data = {} 也已经从指令最低 4 位直接引出来了。".format(f["Data"])
        return s
    if phase == 3:
        al = t["alu"]
        cand = al["candidates"]
        s = ("④ 运算：ALU 同时算出 XOR={} AND={} OR={} {}={}，AFS={} 选中 {} → {}。"
             .format(cand[0], cand[1], cand[2], "SUB" if al["sub"] else "ADD", cand[3],
                     bits(al["afs"], 2), AFS_NAMES[al["afs"]], al["result"]))
        if al["sub"] and u["alu"]:
            s += ("减法细节：{a} + ({b} 取反 = {bi}) + 1 → {a4} + {bi4} + 1，只留低 4 位 = {r}。"
                  .format(a=al["a"], b=al["b"], bi=al["b_in"], a4=bits(al["a"]), bi4=bits(al["b_in"]),
                          r=bits(al["result"])))
        elif al["afs"] == 3 and u["alu"] and al["carries"][4]:
            s += "最高位产生了进位，4 位装不下，被丢掉了（溢出回绕）。"
        if not u["alu"]:
            s += "这条指令不需要 ALU，但它照样在算，结果会被写回选择器丢掉。"
        return s
    if phase == 4:
        if c["WE"]:
            return ("⑤ 写回：选择器 RSS={} 选中“{}” = {}。时钟上升沿到来，WE=1，R{} 从 {} 变成 {}。PC 加 1 变成 {}。"
                    .format(bits(c["RSS"], 2), RSS_NAMES[c["RSS"]], t["write_data"], f["D"], t["old_value"],
                            t["write_data"], t["pc"] + 1))
        if c["DWE"]:
            return ("⑤ 输出：DWE=1，显示器收到 7 位码 {} = 0x{:02X} → 字符 '{}'（R{} 低 3 位 + R{} 4 位）。"
                    "WE=0，不写寄存器。PC 加 1 变成 {}。"
                    .format(bits(t["disp_code"], 7), t["disp_code"], display_char(t["disp_code"]), f["A"], f["B"],
                            t["pc"] + 1))
        return "⑤ 写回：WE=0、DWE=0，时钟沿到来时什么都不存。只有 PC 加 1 变成 {}。".format(t["pc"] + 1)
    return ""


# ─── 执行前的预测题 ───

def make_prediction(t, rng=random):
    """根据下一条指令出一道四选一的预测题。返回 dict(q, options, answer, why)。"""
    f, c, al = t["fields"], t["ctrl"], t["alu"]
    if c["WE"]:
        right = t["write_data"]
        pool = []
        if c["AFS"] == 3 and c["RSS"] == 1:
            raw = al["a"] - al["b"] if al["sub"] else al["a"] + al["b"]
            if raw != right:
                pool.append(raw)   # 不懂溢出回绕的人最容易选的答案，放在最前面
        pool += list(al["candidates"]) + [t["old_value"], t["a_val"], t["b_val"], f["Data"]]
        opts = _pick(right, pool, rng, lo=0, hi=15)
        return {
            "q": "执行 {} 之后，R{} 会变成多少？".format(t["text"], f["D"]),
            "options": [str(o) for o in opts], "answer": opts.index(right),
            "why": describe_phase(t, 3) if c["RSS"] == 1 else describe_phase(t, 4),
        }
    if c["DWE"]:
        right = display_char(t["disp_code"])
        pool = [str(t["b_val"] % 10), display_char(((t["b_val"] & 7) << 4) | t["a_val"]),
                display_char(t["disp_code"] + 1), display_char(t["disp_code"] ^ 0x10)]
        opts = _pick(right, pool, rng, chars=True)
        return {
            "q": "执行 {} 之后，显示器上会多出哪个字符？".format(t["text"]),
            "options": opts, "answer": opts.index(right),
            "why": describe_phase(t, 4),
        }
    opts = ["没有寄存器改变（只有 PC 加 1）", "R0 变成 0", "所有寄存器清零", "R{} 加 1".format(f["D"])]
    return {"q": "执行 {} 时，会发生什么？".format(t["text"]), "options": opts, "answer": 0,
            "why": describe_phase(t, 4)}


def _pick(right, pool, rng, lo=0, hi=15, chars=False):
    opts = [right]
    for p in pool:
        if p not in opts and len(opts) < 4:
            opts.append(p)
    while len(opts) < 4:
        p = chr(rng.randint(0x30, 0x5A)) if chars else rng.randint(lo, hi)
        if p not in opts:
            opts.append(p)
    rng.shuffle(opts)
    return opts
