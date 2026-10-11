import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from cpu_core import CPU, EXAMPLE_PROGRAM, alu, assemble, disassemble  # noqa: E402


class CoreTest(unittest.TestCase):
    def test_example_program_matches_readme(self):
        cpu = CPU()
        cpu.load(assemble(EXAMPLE_PROGRAM))
        while not cpu.halted:
            cpu.step()
        # README：Expected display output: 3, 2, 4, 6, 0, 6
        self.assertEqual("".join(chr(c) for c in cpu.display), "324606")

    def test_machine_code_matches_readme(self):
        codes = [c for c, _ in assemble(EXAMPLE_PROGRAM)]
        self.assertEqual(codes[:7], [0x1000, 0x1101, 0x1203, 0x1303, 0x3023, 0x2420, 0xF441])

    def test_sub_wraps_around(self):
        self.assertEqual(alu(1, 3, 3, 5)["result"], 14)   # 3 - 5 = -2 -> 1110
        self.assertEqual(alu(0, 3, 15, 1)["result"], 0)   # 15 + 1 溢出回到 0

    def test_disassemble_roundtrip(self):
        for c, text in assemble(EXAMPLE_PROGRAM):
            self.assertEqual(assemble(disassemble(c))[0][0], c)


if __name__ == "__main__":
    unittest.main()
