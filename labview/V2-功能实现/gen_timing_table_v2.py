# -*- coding: utf-8 -*-
"""V2 完整版：贴近现实的十字路口全灯组仿真配时与灯态生成器。

与 V1 的关系：
  V1 = 4 个机动车主灯组的基准方案（labview/V1/gen_timing_table.py）
  V2 = 在其基础上补全非机动车灯、8 个人行灯头、渠化与证据分级；机动车主灯态与 V1 逐秒一致。

所有「待现场确认」项都做成下面的可调参数，改完重跑即刷新全部 CSV 并做一致性校验。
零依赖（仅标准库），不需要 LabVIEW 运行时。
"""
import csv
from pathlib import Path

HERE = Path(__file__).resolve().parent
V1_CSV = HERE.parent / "V1-demo" / "逐秒核对表.csv"

# ==========================================================================
# 唯一定义处：配时与假设参数（改这里，其余全自动）
# ==========================================================================

# (相位名, 机动车灯组, 纯绿灯 s, 黄灯 s) —— 与 V1 完全一致，来源 summary.md
PHASES = [
    ("南北直行", "MV_NS_TH", 46, 4),
    ("南北左转", "MV_NS_LT", 26, 4),
    ("东西直行", "MV_EW_TH", 60, 5),
    ("东西左转", "MV_EW_LT", 25, 5),
]

ALL_RED_S = 0              # 每个黄灯片后的全红秒数；0 = 基准方案不含全红
BIKE_YELLOW_FOLLOW = False # 非机动车灯在机动车黄灯期间是否也显示黄灯；False = 转红（保守）
PED_PHASE_RULE = "parallel_straight"  # 行人放行规则：与同向直行机动车平行放行
PED_FLASH_S = 0            # 行人绿灯末尾绿闪秒数；0 = 不启用（启用会额外增加时间片）
PED_MIN_GREEN_S = 0        # 行人最短过街绿灯约束；0 = 不校验，建议现场复核后设 20~25
PED_ENDS_INDEPENDENT = False  # 同一斑马线两端灯头是否独立控制；False = 默认同步（待现场确认）
MV_AUX_HEADS = 0           # 额外机动车辅助灯头数（如北进口八车道的近侧辅助灯），默认不计

# 行人放行所跟随的机动车直行相位。现场复核后逐组改这里即可。
PED_GREEN_PHASE = {
    "N": "MV_EW_TH",  # 北侧斑马线：横穿主干路，行人东西向走
    "S": "MV_EW_TH",  # 南侧斑马线：同上
    "E": "MV_NS_TH",  # 东侧斑马线：横穿次干路，行人南北向走
    "W": "MV_NS_TH",  # 西侧斑马线：同上
}

# 现场秒表截图读数（某日 21:18—21:23，单位 s）
# 截图为 iPhone 秒表「分段」列表：绿色=最快分段，红色=最慢分段，非相位标记
STOPWATCH_LAPS = [
    (1, 30.41, "左转相位 ≈30 s", "与设定 30 s 吻合"),
    (2, 50.88, "南北直行 ≈50 s", "与设定 50 s 吻合"),
    (3, 30.95, "左转相位 ≈30 s", "与设定 30 s 吻合"),
    (4, 61.84, "东西直行 ≈60 s", "与设定纯绿 60 s 吻合"),
    (5, 3.96, "黄灯 ≈4 s", "最快分段（绿色高亮），与南北黄 4 s 吻合"),
    (6, 35.22, "疑似 30 s 相位 + 起止误差", "手动计时偏差，不作为设定依据"),
    (7, 52.00, "南北直行 ≈50 s", "与设定 50 s 吻合"),
    (8, 30.91, "左转相位 ≈30 s", "与设定 30 s 吻合"),
    (9, 65.98, "东西直行 ≈65 s", "与设定绿+黄 65 s 吻合"),
    (10, 83.57, "疑似漏按导致两段合并", "最慢分段（红色高亮），不作为设定依据"),
    (11, 4.23, "黄灯 ≈4 s", "与南北黄 4 s 吻合"),
    (12, 31.09, "左转相位 ≈30 s", "与设定 30 s 吻合"),
    (13, 61.03, "东西直行 ≈60 s", "与设定纯绿 60 s 吻合"),
    (14, 3.98, "黄灯 ≈4 s", "与南北黄 4 s 吻合"),
    (15, 9.64, "计时收尾片段", "录像/计时结束，不作为设定依据"),
]
STOPWATCH_TOTAL_DISPLAY = 555.76  # 表头 09:15.76

# ==========================================================================
# 灯态编码
# ==========================================================================
RED, GREEN, YELLOW, FLASH = 0, 1, 2, 3
COLOR_CN = {RED: "红", GREEN: "绿", YELLOW: "黄", FLASH: "绿闪"}

MV_GROUPS = ["MV_NS_TH", "MV_NS_LT", "MV_EW_TH", "MV_EW_LT"]
MV_CN = {"MV_NS_TH": "南北直行", "MV_NS_LT": "南北左转",
         "MV_EW_TH": "东西直行", "MV_EW_LT": "东西左转"}
BK_GROUPS = ["BK_NS_TH", "BK_NS_LT", "BK_EW_TH", "BK_EW_LT"]
BK_CN = {"BK_NS_TH": "南北非机直行", "BK_NS_LT": "南北非机左转",
         "BK_EW_TH": "东西非机直行", "BK_EW_LT": "东西非机左转"}
CROSSINGS = ["N", "S", "E", "W"]
CROSS_CN = {"N": "北侧斑马线", "S": "南侧斑马线", "E": "东侧斑马线", "W": "西侧斑马线"}


def pedestrian_groups():
    if PED_ENDS_INDEPENDENT:
        return [f"PW_{c}_{e}" for c in CROSSINGS for e in ("A", "B")]
    return [f"PW_{c}" for c in CROSSINGS]


PW_GROUPS = pedestrian_groups()
GROUPS = MV_GROUPS + BK_GROUPS + PW_GROUPS
GROUP_CN = dict(MV_CN)
GROUP_CN.update(BK_CN)
for g in PW_GROUPS:
    c = g.split("_")[1]
    suffix = "" if len(g.split("_")) < 3 else f"·{g.split('_')[2]}端"
    GROUP_CN[g] = CROSS_CN[c] + suffix


def build_base_slices():
    """构建时间片：每相位 绿 → 黄 → (可选)全红。"""
    slices = []
    t = 0
    for phase_name, mv_group, green, yellow in PHASES:
        for label, dur, mv_color in (("绿", green, GREEN), ("黄", yellow, YELLOW)):
            mv = {g: RED for g in MV_GROUPS}
            mv[mv_group] = mv_color
            slices.append({
                "start": t, "end": t + dur,
                "name": f"{phase_name}{label}灯",
                "phase_group": mv_group,
                "kind": "green" if mv_color == GREEN else "yellow",
                "mv": mv,
            })
            t += dur
        if ALL_RED_S > 0:
            slices.append({
                "start": t, "end": t + ALL_RED_S,
                "name": f"{phase_name}后全红",
                "phase_group": None,
                "kind": "allred",
                "mv": {g: RED for g in MV_GROUPS},
            })
            t += ALL_RED_S
    return slices, t


def pedestrian_state(group, sl):
    """行人灯态：与同向直行机动车平行放行；左转相位、黄灯、全红一律红灯。"""
    if sl["kind"] != "green":
        return RED
    c = group.split("_")[1]
    if PED_PHASE_RULE != "parallel_straight":
        raise ValueError(f"未知行人放行规则：{PED_PHASE_RULE}")
    return GREEN if PED_GREEN_PHASE[c] == sl["phase_group"] else RED


def compute_states(sl, flash=False):
    """按时间片计算全部灯组状态。flash=True 时把该片行人绿改为绿闪。"""
    st = {}

    for g in MV_GROUPS:
        st[g] = sl["mv"][g]

    # 非机动车：与同方向同功能机动车绿灯同步；黄灯行为由 BIKE_YELLOW_FOLLOW 决定
    for bk, mv in zip(BK_GROUPS, MV_GROUPS):
        v = sl["mv"][mv]
        if v == GREEN:
            st[bk] = GREEN
        elif v == YELLOW and BIKE_YELLOW_FOLLOW:
            st[bk] = YELLOW
        else:
            st[bk] = RED

    # 行人
    for g in PW_GROUPS:
        v = pedestrian_state(g, sl)
        st[g] = FLASH if (flash and v == GREEN) else v

    return st


def split_flash(slices):
    """行人绿闪 >0 时，把含行人绿的时间片尾部拆出绿闪段。"""
    if PED_FLASH_S <= 0:
        return slices
    out = []
    for sl in slices:
        has_ped_green = any(pedestrian_state(g, sl) == GREEN for g in PW_GROUPS)
        dur = sl["end"] - sl["start"]
        if has_ped_green and dur > PED_FLASH_S:
            first = dict(sl)
            first["end"] = sl["end"] - PED_FLASH_S
            first["name"] = sl["name"]
            first["_flash"] = False
            second = dict(sl)
            second["start"] = sl["end"] - PED_FLASH_S
            second["name"] = sl["name"] + "·行人绿闪"
            second["_flash"] = True
            out.extend([first, second])
        else:
            sl["_flash"] = False
            out.append(sl)
    return out


def verify(slices, cycle):
    assert cycle == 175 + 4 * ALL_RED_S, f"周期异常：{cycle}"
    for a, b in zip(slices, slices[1:]):
        assert a["end"] == b["start"], f"时间片边界不连续：{a['end']} vs {b['start']}"
    assert slices[0]["start"] == 0 and slices[-1]["end"] == cycle, "首尾时刻异常"

    total_green = sum(s["end"] - s["start"] for s in slices
                      if s["kind"] == "green")
    total_yellow = sum(s["end"] - s["start"] for s in slices
                       if s["kind"] == "yellow")
    assert total_green == 157, f"绿灯合计应为 157 s，实为 {total_green}"
    assert total_yellow == 18, f"黄灯合计应为 18 s，实为 {total_yellow}"

    all_states = []
    for sl in slices:
        st = compute_states(sl, sl.get("_flash", False))
        for _ in range(sl["end"] - sl["start"]):
            all_states.append(st)

        # 机动车：绿/黄片恰好一组非红；全红片全红
        active = [g for g in MV_GROUPS if st[g] != RED]
        if sl["kind"] == "allred":
            assert not active, f"全红片仍有放行组：{sl['name']}"
        else:
            assert len(active) == 1 and st[active[0]] in (GREEN, YELLOW), \
                f"灯态非法：{sl['name']} {active}"

        # 行人灯不得在左转/黄灯/全红期间放行
        if sl["kind"] != "green":
            assert all(st[g] in (RED, FLASH) for g in PW_GROUPS), \
                f"非直行绿期间行人灯未置红：{sl['name']}"

    assert len(all_states) == cycle, "逐秒展开行数与周期不符"

    if PED_MIN_GREEN_S > 0:
        for g in PW_GROUPS:
            green_s = sum(1 for st in all_states if st[g] in (GREEN, FLASH))
            assert green_s >= PED_MIN_GREEN_S, \
                f"{g} 行人绿 {green_s}s 小于最短过街绿 {PED_MIN_GREEN_S}s"

    # 交叉校验：V2 机动车主灯态必须与 V1 逐秒一致（参数未改变周期时）
    if ALL_RED_S == 0 and PED_FLASH_S == 0 and V1_CSV.exists():
        rows = list(csv.DictReader(V1_CSV.open(encoding="utf-8-sig")))
        assert len(rows) == cycle, "V1 核对表行数与 V2 周期不符"
        v1_cols = {"MV_NS_TH": "NS_TH数值", "MV_NS_LT": "NS_LT数值",
                   "MV_EW_TH": "EW_TH数值", "MV_EW_LT": "EW_LT数值"}
        for t, (row, st) in enumerate(zip(rows, all_states)):
            for g, col in v1_cols.items():
                assert int(row[col]) == st[g], f"t={t} {g} 与 V1 不一致"
        print("  [交叉校验] V2 机动车 4 组逐秒灯态 == V1 基准表，完全一致")
    else:
        print("  [交叉校验] 已跳过（启用全红/绿闪会改变周期，或 V1 表不存在）")

    return total_green, total_yellow, all_states


def head_inventory():
    """灯头清单：(编号, 位置, 类型, 所属灯组, 证据等级, 备注)"""
    heads = []

    # 机动车灯头：每进口道 直行 + 左转 各 1（估计，待现场清点）
    for approach, cn in (("N", "北进口"), ("S", "南进口"), ("E", "东进口"), ("W", "西进口")):
        base = "MV_NS" if approach in ("N", "S") else "MV_EW"
        heads.append((f"MV_{approach}_TH", cn, "机动车直行满盘/箭头灯", f"{base}_TH",
                      "D 工程假设", "每进口 1 个主灯头；北进口八车道可能有近侧辅助灯头"))
        heads.append((f"MV_{approach}_LT", cn, "机动车左转箭头灯", f"{base}_LT",
                      "D 工程假设", "四相位含专用左转相位，按每进口 1 个左转灯头估计"))

    for i in range(MV_AUX_HEADS):
        heads.append((f"MV_AUX_{i + 1:02d}", "待现场指定", "机动车辅助灯头", "MV_NS_TH",
                      "E 待确认", "仅当现场确认存在时启用，需指定归属灯组"))

    # 非机动车灯头：南北有独立灯（实地记录），东西无独立灯
    for approach, cn in (("N", "北进口"), ("S", "南进口")):
        heads.append((f"BK_{approach}_TH", cn, "非机动车直行灯（自行车图案）", "BK_NS_TH",
                      "B 实地记录", "历史对话：南北有非机动车直行灯，绿灯逻辑同向机动车"))
        heads.append((f"BK_{approach}_LT", cn, "非机动车左转灯（自行车图案）", "BK_NS_LT",
                      "B 实地记录", "历史对话：南北有非机动车左转灯"))
    heads.append(("BK_EW_NOTE", "东/西进口", "无实体灯头（仅逻辑组）",
                  "BK_EW_TH + BK_EW_LT", "B 实地记录",
                  "东西无非机动车灯；非机动车依机动车灯通行，不计入灯头清点数"))

    # 行人灯头：4 条斑马线 × 两端 = 8
    for c in CROSSINGS:
        grp = f"PW_{c}_A" if PED_ENDS_INDEPENDENT else f"PW_{c}"
        heads.append((f"PW_{c}_A", CROSS_CN[c] + "·一端", "人行灯（红/绿人形）", grp,
                      "B 实地记录", "每条斑马线两端各 1 个灯头，共 8 个"))
        grp_b = f"PW_{c}_B" if PED_ENDS_INDEPENDENT else f"PW_{c}"
        heads.append((f"PW_{c}_B", CROSS_CN[c] + "·另一端", "人行灯（红/绿人形）", grp_b,
                      "B 实地记录", "默认与同条斑马线另一端同步；是否同步待现场确认"))

    # 右转：不受灯控，不设灯头
    heads.append(("RT_NOTE", "四个进口道", "右转不受灯控", "-", "B 实地记录",
                  "右转车全程可通行，须礼让行人/非机动车；照片可见「礼让行人」地标"))
    return heads


def write_csv(path, header, rows):
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)


def main():
    base, cycle = build_base_slices()
    slices = split_flash(base)
    green, yellow, per_second = verify(slices, cycle)

    # 1) 时间片常量表
    write_csv(
        HERE / "时间片常量表V2.csv",
        ["片号", "起始s", "结束s", "时间片名称", "类型", *GROUPS],
        [[i + 1, s["start"], s["end"], s["name"], s["kind"],
          *[compute_states(s, s.get("_flash", False))[g] for g in GROUPS]]
         for i, s in enumerate(slices)],
    )

    # 2) 完整灯态逐秒表
    rows = []
    for si, s in enumerate(slices, start=1):
        st = compute_states(s, s.get("_flash", False))
        for t in range(s["start"], s["end"]):
            rows.append([
                t, si, s["name"], s["end"] - t,
                *[COLOR_CN[st[g]] for g in GROUPS],
                *[st[g] for g in GROUPS],
            ])
    write_csv(
        HERE / "完整灯态逐秒表.csv",
        ["周期内秒t", "片号", "时间片名称", "本片剩余s",
         *[GROUP_CN[g] + "·色" for g in GROUPS],
         *[g + "数值" for g in GROUPS]],
        rows,
    )

    # 3) 灯头清单
    heads = head_inventory()
    write_csv(
        HERE / "灯头清单.csv",
        ["灯头编号", "位置", "类型", "所属灯组", "证据等级", "备注"],
        heads,
    )

    # 4) 实测秒表分段
    lap_sum = round(sum(x[1] for x in STOPWATCH_LAPS), 2)
    write_csv(
        HERE / "实测秒表分段.csv",
        ["分段", "时长s", "归类", "说明"],
        [[n, f"{v:.2f}", k, note] for n, v, k, note in STOPWATCH_LAPS]
        + [["合计", f"{lap_sum:.2f}", "截图表头 09:15.76 = 555.76 s",
            f"逐段累加与表头差 {abs(STOPWATCH_TOTAL_DISPLAY - lap_sum):.2f} s，为显示四舍五入"]],
    )

    print("PASS V2 全部一致性校验通过")
    print(f"周期 = {cycle} s  |  时间片 = {len(slices)} 个  |  绿灯 {green} s  |  黄灯 {yellow} s  |  全红 {4 * ALL_RED_S} s")
    print(f"灯组 = {len(GROUPS)} 个（机动车 4 / 非机动车 4 / 行人 {len(PW_GROUPS)}）")
    real_heads = [h for h in heads if h[0] not in ("RT_NOTE", "BK_EW_NOTE")]
    print(f"实体灯头 = {len(real_heads)} 个（机动车 {8 + MV_AUX_HEADS} / 非机动车 4 / 人行 8）；"
          "东西向非机动车为逻辑组、无实体灯头；右转不设灯头")
    print(f"参数：ALL_RED_S={ALL_RED_S}  BIKE_YELLOW_FOLLOW={BIKE_YELLOW_FOLLOW}  "
          f"PED_FLASH_S={PED_FLASH_S}  PED_MIN_GREEN_S={PED_MIN_GREEN_S}  "
          f"PED_ENDS_INDEPENDENT={PED_ENDS_INDEPENDENT}")
    print("已生成：时间片常量表V2.csv / 完整灯态逐秒表.csv / 灯头清单.csv / 实测秒表分段.csv")


if __name__ == "__main__":
    main()
