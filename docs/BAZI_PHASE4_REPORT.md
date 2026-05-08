# 八字规则引擎 v3 报告（Phase 4）

> 生成日期：2026-05-08  
> 版本：bazi-rules-v3.0.0 / prompt-version 4.0.0  
> 测试结果：215 项全通过

---

## 一、Phase 4 解决了什么

| Phase 3 (v2) 不支持 | Phase 4 (v3) 新增 |
|--------------------|-------------------|
| 仅识别"合"的关系，不判断是否真合化 | **合化成功判定**：月令支持 + 透干 + 无破 三条件 |
| 缺少调候用神视角 | **调候用神**：基于《穷通宝鉴》5×4 简化表 |
| 大运/流年与命局无交互分析 | **流年大运动态合冲**：六合/六冲/六害/三合/半合 |
| 缺少天干五合识别 | **天干五合**：甲己/乙庚/丙辛/丁壬/戊癸 |

---

## 二、新增模块

### 1. 调候用神 — `backend/domain/bazi_climate.py`

基于季节（spring/summer/autumn/winter）+ 日主五行 的 **5×4 = 20 条** 简化表：

```
寒月（亥子丑）：日主普遍喜火 → confidence=high
暑月（巳午未）：日主普遍喜水 → confidence=high
春月（寅卯辰）：木旺，看日主 → confidence=medium
秋月（申酉戌）：金旺，看日主 → confidence=medium 或 low
```

并提供 `merge_with_useful_gods()` 与 v2 喜用神交叉验证：
- `consensus_three_way`：调候 ∩ 旺衰法 ∩ 格局法
- `climate_pattern_conflict`：调候喜某五行但格局法忌之

### 2. 合化成功判定 — `backend/domain/bazi_relations.py::analyze_combination_transformation`

判定流程（每项合）：

| 条件 | 分数 |
|-----|------|
| 月令藏干含合化神五行 | +2 |
| 四柱天干透合化神五行 | +1 |
| 合的成员被冲 | 立即破合 |

| score | 结论 | confidence |
|-------|------|------------|
| ≥3 | 真合化 | high |
| 2 | 真合化 | medium |
| 1 | 合而不化 | medium |
| 0 | 合而不化 | low |
| 被冲 | 破合 | medium |

支持类型：六合 / 三合 / 天干五合（半合不计）

### 3. 流年大运动态交互 — `backend/domain/bazi_relations.py::analyze_dynamic_relations`

输入：`current_dayun_ganzhi`、`liunian_ganzhi`  
输出：每个动支与四柱地支的关系列表 + 大运↔流年自身关系

支持识别：
- 六合 / 六冲 / 六害 / 无礼之刑 / 自刑
- 三合（动支 + 2 原局支）
- 半合（动支 + 1 原局支）

---

## 三、整合入口 — `analyze_chart_v3`

```python
analyze_chart_v3(chart) → {
    "version": "bazi-rules-v3.0.0",
    "rule_engine_version": "3.0.0",
    # v2 字段全保留
    "wuxing_power", "strength", "relations", "pattern", "useful_gods",
    "overall_confidence", "warnings",
    # v3 新增
    "climate":              {"day_wx", "season", "primary_useful", "secondary_useful", "confidence", "note", "evidence"},
    "climate_merged":       {"consensus_three_way", "climate_pattern_conflict", ...},
    "transformation":       {"checked": [...], "summary_note"},
    "dynamic_relations":    {"dayun": {...}, "liunian": {...}, "dayun_liunian": [...]},
}
```

`analyze_chart()` (v1 别名) 内部已切换到 v3，**v2 字段全部向后兼容**。

---

## 四、Prompt 注入示例（戊土生酉月，1999-08-14 22:30）

```
▸ 调候用神（《穷通宝鉴》简化, conf=low）：主用=火、木
  · 秋土秉令而泄于金，喜火生扶或木疏。
  · 三法共识喜用：火
  ⚠ 调候与格局法存在冲突，需结合大运流年综合判断

▸ 合化判定（识别 3 项合，均为合而不化或破合。）
  · 六合 寅·亥 → 合化木 [合而不化/破合, conf=low]
  · 天干五合 癸·戊 → 合化火 [合而不化/破合, conf=low]

▸ 大运/流年动态交互：
  · [大运庚午] 动支午与day支寅半合火
  · [流年丙午] 动支午与day支寅半合火
```

> 这正是命理上的关键解读：身弱戊土遇大运/流年午火 + 半合火 → 真正的"用神被引动"信号。

---

## 五、文件清单

### 新增

| 文件 | 行数 | 职责 |
|------|------|------|
| `backend/domain/bazi_climate.py` | ~140 | 调候表 + merge_with_useful_gods |
| `tests/test_bazi_phase4.py` | ~210 | 调候 + 合化 + 动态 + v3 整合（28 项） |
| `docs/BAZI_PHASE4_REPORT.md` | 本文 | Phase 4 报告 |

### 修改

| 文件 | 变更 |
|------|------|
| `backend/domain/bazi_relations.py` | +TIAN_GAN_HE / +analyze_tiangan_he / +analyze_combination_transformation / +analyze_dynamic_relations / 半合检测 |
| `backend/domain/bazi_rules.py` | +analyze_chart_v3；analyze_chart 切至 v3 |
| `backend/services/prompt_service.py` | PROMPT_VERSION 4.0.0；注入调候/合化/动态块 |
| `tests/test_bazi_accuracy.py` | rule_engine_version 兼容 2.0.0 / 3.0.0 |
| `tests/test_bazi_rules_v2.py` | backward_compat 改为字段层校验 |

---

## 六、测试 & 评估

```bash
.venv/Scripts/python.exe -m pytest tests/ -v
```
**215 passed in 2.08s**

| 测试文件 | 项数 |
|---------|------|
| test_bazi_accuracy.py | 51 |
| test_bazi_rules_v2.py | 26 |
| test_bazi_relations.py | 21 |
| test_ai_output_validator.py | 20 |
| test_bazi_case_loader.py | 19 |
| test_bazi_rule_evaluator.py | 25 |
| test_bazi_quality_gate.py | 13 |
| test_bazi_ai_output_evaluation.py | 13 |
| **test_bazi_phase4.py** | **27** |
| 总计 | **215** |

```bash
.venv/Scripts/python.exe scripts/check_bazi_quality_gate.py
```
✅ **质量门禁通过**（avg=100, pass_rate=100%, AI dry-run self-test ✓）

---

## 七、已知边界（仍未支持）

1. **暗合暗冲**：地支藏干层面的隐性关系
2. **从格 / 化格的最终确认**：仍只标"疑似"
3. **十神生克的具体强度量化**（如"七杀有制"vs"七杀无制"的程度）
4. **流年与大运叠加共振**（如双午临身弱戊土的具体力度）
5. **调候 5×4 简表**：未实现《穷通宝鉴》逐月详查（120 条）
6. **特殊神煞**：贵人、桃花、空亡等（用户明确不要）

---

## 八、当前规则引擎可信度评估

| 维度 | 程序事实 | 命理判断 | 推论 |
|------|---------|----------|------|
| 排盘 | ✅ 准 | — | — |
| 十神映射 | ✅ 准 | — | — |
| 五行加权力量 | ✅ 算法稳定 | 阈值是工程化选择 | — |
| 旺衰评分 | ✅ 算法稳定 | 阈值是工程化选择 | — |
| 地支关系识别 | ✅ 准 | — | — |
| **合化判定** | — | — | ⚠ 简化模型 |
| **调候用神** | — | — | ⚠ 简表，非《穷通宝鉴》全本 |
| **流年大运动态** | ✅ 关系识别准 | — | ⚠ 影响程度未量化 |
| 喜用神 | ✅ 算法稳定 | 流派分歧大 | ⚠ allow_conflict |

> v3 把"合化/调候/动态"明确标为**推论层**，confidence 较低时 prompt 要求 AI 表达为"倾向"而非断言。

---

## 九、下一阶段建议

**如果项目目标是"自己用 / 朋友看"**：到此可以停了，已经够用。

**如果要进一步**：

| 优先级 | 项 | 说明 |
|-------|---|------|
| 高 | 邀请命理师审核 standard_cases.json | 工程已不缺，缺专业校准 |
| 中 | 扩 5 例反例（规则应判错的盘）| 让评估能反映规则改进 |
| 中 | 调候表逐月细化（5×12=60 条）| 替换当前 5×4 简表 |
| 低 | 流年大运合化共振量化 | 给"用神被引动"打分 |
| 低 | 暗合暗冲 | 复杂但提升不大 |

**永远不做**：
- 神煞核心化
- 宣传准确率
- AI 自标 expected
- 自动付费包装
- 把低信心当确定结论
