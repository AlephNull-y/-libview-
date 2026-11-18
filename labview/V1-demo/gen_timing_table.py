# -*- coding: utf-8 -*-
"""主干路 x 次干路固定配时基准方案：生成 LabVIEW 仿真用的时间片常量表与逐秒核对表。

只需修改 PHASES 里的纯绿灯/黄灯秒数，重新运行即可刷新两张表。
脚本内置一致性断言，配时被改错会直接报错。
零依赖，仅用 Python 标准库。
"""
import csv
from pathlib import Path

HERE = Path(__file__).resolve().parent

RED, GREEN, YELLOW = 0, 1, 2
COLOR_CN = {RED: "红", GREEN: "绿", YELLOW: "黄"}
GROUPS = ["NS_TH", "NS_LT", "EW_TH", "EW_LT"]
GROUP_CN = {
    "NS_TH": "南北直行",
    "NS_LT": "南北左转",
    "EW_TH": "东西直行",
    "EW_LT": "东西左转",
}

# (相位名, 放行灯组, 纯绿灯秒数, 黄灯秒数)
# 来源：实地勘察-20261028/record/summary.md —— 固定配时基准方案，全红按 0 s
PHASES = [
    ("南北直行", "NS_TH", 46, 4),
    ("南北左转", "NS_LT", 26, 4),
    ("东西直行", "EW_TH", 60, 5),
    ("东西左转", "EW_LT", 25, 5),
]


def build_slices():
    slices = []
    t = 0
    for phase, group, green, yellow in PHASES:
        for label, duration, color in (("绿", green, GREEN), ("黄", yellow, YELLOW)):
            states = {g: RED for g in GROUPS}
            states[group] = color
            slices.append({
                "index": len(slices) + 1,
                "start": t,
                "end": t + duration,
                "name": f"{phase}{label}灯",
                "phase": phase,
                "states": tuple(states[g] for g in GROUPS),
            })
            t += duration
    return slices, t


def verify(slices, cycle):
    assert cycle == 175, f"周期应为 175 s，实为 {cycle} s"
    assert len(slices) == 8, f"应有 8 个时间片，实为 {len(slices)}"
    assert [s["start"] for s in slices] == [0, 46, 50, 76, 80, 140, 145, 170], "时间片起点不符"
    assert [s["end"] for s in slices] == [46, 50, 76, 80, 140, 145, 170, 175], "时间片终点不符"
    for a, b in zip(slices, slices[1:]):
        assert a["end"] == b["start"], "时间片边界不连续"
    total_green = sum(s["end"] - s["start"] for s in slices if GREEN in s["states"])
    total_yellow = sum(s["end"] - s["start"] for s in slices if YELLOW in s["states"])
    assert total_green == 157, f"绿灯合计应为 157 s，实为 {total_green} s"
    assert total_yellow == 18, f"黄灯合计应为 18 s，实为 {total_yellow} s"
    assert total_green + total_yellow == cycle, "绿 + 黄 != 周期"
    for g, expected in zip(GROUPS, [46, 26, 60, 25]):
        got = sum(s["end"] - s["start"] for s in slices if s["states"][GROUPS.index(g)] == GREEN)
        assert got == expected, f"{g} 纯绿灯应为 {expected} s，实为 {got} s"
    for t in range(cycle):
        cur = next(s for s in slices if s["start"] <= t < s["end"])
        active = [c for c in cur["states"] if c != RED]
        assert len(active) == 1 and active[0] in (GREEN, YELLOW), f"t={t} 灯态非法：{cur['states']}"
    return total_green, total_yellow


def write_csv(path, header, rows):
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)


def main():
    slices, cycle = build_slices()
    green, yellow = verify(slices, cycle)

    write_csv(
        HERE / "时间片常量表.csv",
        ["时间片号(1-8)", "起始时刻s", "结束时刻s", "时间片名称", "NS_TH", "NS_LT", "EW_TH", "EW_LT"],
        [[s["index"], s["start"], s["end"], s["name"], *s["states"]] for s in slices],
    )

    rows = []
    for t in range(cycle):
        s = next(s for s in slices if s["start"] <= t < s["end"])
        rows.append([
            t, s["index"], s["name"], s["end"] - t,
            *[COLOR_CN[c] for c in s["states"]],
            *s["states"],
        ])
    write_csv(
        HERE / "逐秒核对表.csv",
        ["周期内秒t", "时间片号", "时间片名称", "本片剩余s",
         "南北直行", "南北左转", "东西直行", "东西左转",
         "NS_TH数值", "NS_LT数值", "EW_TH数值", "EW_LT数值"],
        rows,
    )

    print("PASS 全部一致性校验通过")
    print(f"周期 = {cycle} s；时间片 = {len(slices)} 个；绿灯合计 = {green} s；黄灯合计 = {yellow} s")
    print("边界数组 =", [s["start"] for s in slices])
    print("结束数组 =", [s["end"] for s in slices])
    print("切换时刻 = 0, 46, 50, 76, 80, 140, 145, 170, 175(归零)")
    print("已生成：时间片常量表.csv (8 行)、逐秒核对表.csv (175 行)")


if __name__ == "__main__":
    main()
