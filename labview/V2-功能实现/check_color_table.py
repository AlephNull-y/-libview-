# -*- coding: utf-8 -*-
"""
V2 自检：直接读 .vi 文件里的 COLOR 8×12 常量表，与《时间片常量表V2.csv》基准逐格比对。

用法（在 V2-完整版 目录下）：
    python check_color_table.py                     # 默认检查 十字路口仿真V2.vi
    python check_color_table.py 某个.vi             # 指定文件

原理：LabVIEW 把数组常量的数值以大端 I32 存在 VI 内部（先 zlib 压缩），
在解压后的数据里找到「8 行 12 列」尺寸头，紧跟着 96 个值就是 COLOR。
不依赖 LabVIEW、不需要打开 VI，只读文件。
"""
import sys, os, zlib, re, struct

try:                       # 控制台是 GBK 时也不至于崩
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_VI = os.path.join(HERE, "十字路口仿真V2.vi")

COLS = ["MV_NS_TH", "MV_NS_LT", "MV_EW_TH", "MV_EW_LT",
        "BK_NS_TH", "BK_NS_LT", "BK_EW_TH", "BK_EW_LT",
        "PW_N", "PW_S", "PW_E", "PW_W"]
SLICE_NAMES = ["片1 南北直行绿", "片2 南北直行黄", "片3 南北左转绿", "片4 南北左转黄",
               "片5 东西直行绿", "片6 东西直行黄", "片7 东西左转绿", "片8 东西左转黄"]

# 基准：时间片常量表V2.csv
SPEC = [
    [1, 0, 0, 0, 1, 0, 0, 0, 0, 0, 1, 1],
    [2, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    [0, 1, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0],
    [0, 2, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    [0, 0, 1, 0, 0, 0, 1, 0, 1, 1, 0, 0],
    [0, 0, 2, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 0],
    [0, 0, 0, 2, 0, 0, 0, 0, 0, 0, 0, 0],
]
SPEC_FLAT = [x for row in SPEC for x in row]


def inflate_blocks(data):
    """VI 内部的数据块是 zlib 压缩的，全部解出来。"""
    out = []
    for i in range(len(data) - 2):
        if data[i] == 0x78 and data[i + 1] in (0x01, 0x9C, 0xDA):
            d = zlib.decompressobj()
            try:
                buf = d.decompress(data[i:i + 4000000])
            except Exception:
                continue
            if len(buf) > 32:
                out.append((i, buf))
    return out


def find_tables(data):
    """找尺寸头 (8,12)，其后紧跟 96 个大端 I32。返回去重后的 [(offset, [96 values])]。"""
    found = []
    header = struct.pack(">i", 8) + struct.pack(">i", 12)
    for _, buf in inflate_blocks(data):
        for m in re.finditer(re.escape(header), buf):
            p = m.start()
            if p % 4:
                continue
            start = p + 8
            if start + 96 * 4 > len(buf):
                continue
            vals = list(struct.unpack_from(">" + "i" * 96, buf, start))
            if sum(1 for v in vals if v in (0, 1, 2)) >= 90:
                found.append((start, vals))
    uniq = []
    for start, vals in found:
        if not any(vals == v for _, v in uniq):
            uniq.append((start, vals))
    return uniq


def main():
    vi = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_VI
    if not os.path.exists(vi):
        print(f"[错误] 找不到文件：{vi}")
        return 2
    data = open(vi, "rb").read()
    tables = find_tables(data)
    print(f"文件：{vi}  ({len(data)} 字节)")
    if not tables:
        print("[警告] 没在 VI 里找到 8×12 的数组常量 —— COLOR 可能还没拉宽，或不是 I32 数值类型。")
        return 2

    ok_all = True
    for start, vals in tables:
        print(f"\nCOLOR 表（数据偏移 {start}），列号 1~12 对应：")
        print("  " + "  ".join(f"{i+1}={c}" for i, c in enumerate(COLS[:6])))
        print("  " + "  ".join(f"{i+7}={c}" for i, c in enumerate(COLS[6:])))
        print("\n" + "行".ljust(4) + "".join(f"{i+1:>7}" for i in range(12)) + "   时间片")
        diffs = []
        for r in range(8):
            cells = []
            for c in range(12):
                got, exp = vals[r * 12 + c], SPEC[r][c]
                if got == exp:
                    cells.append(f"{got:>7}")
                else:
                    cells.append(f"{f'{got}!={exp}':>7}")
                    diffs.append((r, c, got, exp))
            print(f"r{r}  " + "".join(cells) + f"   {SLICE_NAMES[r]}")
        print()
        if not diffs:
            print("[通过] COLOR 与基准表 8×12 逐格一致。")
        else:
            ok_all = False
            print(f"[不一致] 有 {len(diffs)} 处与基准不同（表格里写成 当前值!=应为，格式即 实际!=正确）：")
            for r, c, got, exp in diffs:
                print(f"  第 {r+1} 行（{SLICE_NAMES[r]}）× 第 {c+1} 列 {COLS[c]}："
                      f"现在是 {got}，应为 {exp}")
    return 0 if ok_all and all(vals == SPEC_FLAT for _, vals in tables) else 1


if __name__ == "__main__":
    sys.exit(main())
