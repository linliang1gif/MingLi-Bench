# 八字标准案例库报告（Phase 3.6）

> 生成日期：2026-05-08  
> 案例库：`backend/domain/fixtures/bazi_cases/standard_cases.json`  
> 总测试：188 项全通过

---

## 一、当前案例总数

**20 例**（从 6 例扩充至 20 例）。

## 二、案例来源类型

当前所有案例均为：

| source | source_note |
|--------|-------------|
| `manual` | 由项目团队人工标注；**未经命理师审核**，primary/accepted/rejected 标注以本团队对子平命理的工程化理解为基准 |

> ⚠️ **重要说明**：当前 `primary_strength_level` / `primary_pattern` 是基于以下流程标注的：
> 1. 用 `chart_service.compute_chart` 生成排盘
> 2. 参考规则引擎 v2 的输出
> 3. 结合月令、透干、合冲等基础知识人工调整 accepted / rejected 范围
> 4. 在 `dispute_notes` 中显式说明可能存在的流派分歧
>
> **这不能等同于命理师的专业校准结果。** 真正的标准案例库需要人工命理师审核。

---

## 三、覆盖的命局类型

### 旺衰 (primary_strength_level)

| 类型 | 案例数 | case_id |
|------|-------|---------|
| 身强 | 3 | case_008, case_016, case_018 |
| 偏强 | 4 | case_004, case_009, case_011, case_013 |
| 中和 | 2 | case_005, case_019 |
| 偏弱 | 4 | case_003, case_006, case_012, case_017 |
| 身弱 | 5 | case_001, case_002, case_007, case_010, case_014, case_015 |
| 疑似从弱 | 1 | case_020 |
| 疑似从强 | 0 | （未收录，下一阶段补充） |

### 格局 (primary_pattern)

| 类型 | 案例数 |
|------|-------|
| 建禄格 | 2 (case_003, case_015) |
| 月劫格 | 1 (case_013) |
| 正官格 | 1 (case_009) |
| 七杀格 | 4 (case_002, case_004, case_006, case_017) |
| 食神格 | 2 (case_010, case_014) |
| 伤官格 | 2 (case_001, case_020) |
| 正财格 | 1 (case_007) |
| 偏财格 | 1 (case_012) |
| 正印格 | 2 (case_005, case_008) |
| 偏印格 | 4 (case_011, case_016, case_018, case_019) |

### 特殊条件

| 条件 | 案例 |
|------|------|
| 月令被冲 | case_001（卯酉冲）、case_019（寅申冲） |
| 月令被破而身弱 | case_015（建禄遇三戊伤官泄秀） |
| 中和盘 confidence=low | case_005, case_019 |
| 疑似从格临界 | case_007（极弱）, case_020（疑似从弱）|

---

## 四、当前评估结果

### 规则引擎评估

```
.venv/Scripts/python.exe scripts/evaluate_bazi_rules.py
```

| 指标 | 数值 |
|------|------|
| 总案例数 | 20 |
| 通过案例 | 20 |
| 通过率 | **100.0%** |
| 平均分 | **100.0** |
| primary 命中 | 20/20 |
| accepted_hit | 20/20 |
| rejected_hit | 0/20 |

### AI 输出 dry-run self-test

```
.venv/Scripts/python.exe scripts/evaluate_bazi_ai_outputs.py
```

| 指标 | 数值 |
|------|------|
| fixture 样本数 | 5（1 干净 + 4 负样本） |
| self-test 通过 | 5/5 |
| 非预期 error 违规 | 0 |
| 验证器规则触发数 | 6 errors（均为预期负样本） |

### 质量门禁

```
.venv/Scripts/python.exe scripts/check_bazi_quality_gate.py
```

✅ **PASS**

---

## 五、当前失败案例

无。

但需明确说明：**100% 通过率 ≠ 真实命理准确率**。详见第六节。

---

## 六、当前规则边界

规则引擎 v2 已能处理：

- 五行加权力量（月令本气/中气/余气、天干透出、通根加分）
- 旺衰评分（同类/异类比例 + 季节/通根/帮扶修正）
- 7 种地支关系（六合/六冲/三合/半合/三会/六害/三刑/自刑）
- 月令本气/中气/余气透干取格
- 合冲对格局信心的衰减
- 喜用神双轨（旺衰法 + 格局法）+ 综合建议 + 信心分级

仍未支持：

- 合化是否成功（仅识别合的关系，未判断是否化成）
- 暗合暗冲（地支藏干层面）
- 调候用神（《穷通宝鉴》体系）
- 流年与大运的合冲互动
- 神煞（不建议作为核心判断依据）
- 真正的从格/化格确认（仅标记"疑似"）

---

## 七、为什么 100% 通过率不等于真实准确率

### ① 标注闭环风险

`primary_strength_level` 和 `primary_pattern` 是基于**当前规则引擎输出**标注的。
即"规则引擎说什么 → 我标什么 → 规则引擎跑过 → 100% 通过"。
这只能证明 **schema 自洽**，不能证明命理准确性。

### ② accepted 范围对人工标注的迁就

`accepted_strength_levels` 通常包含 primary 周边的 1-2 个相邻级别（如 身弱 + 偏弱），
这是为了容纳流派分歧，但也意味着规则引擎只要"差不多对"就能通过。

### ③ 喜用神维度宽容度高

`accepted_useful_elements` 通常包含 3-4 个五行（旺衰法 + 格局法的合集），
规则引擎几乎总能命中其中至少一个。

### ④ 缺少"反例"

当前案例没有"规则引擎应该错"的故意压测样本。
真正的测试集应该包含一些"规则会判错的盘"，用于检测改进效果。

### ⑤ 命理本身有流派分歧

旺衰扶抑 vs 调候 vs 格局 vs 神峰通考 等流派对同一盘可能给出不同结论，
单一标注无法代表全部专业意见。

---

## 八、仍需人工命理师校准的字段

按优先级降序：

### 高优先级
- [ ] `primary_strength_level` — 旺衰主结论
- [ ] `primary_pattern` — 格局主结论
- [ ] `rejected_strength_levels` — 明确不可接受的旺衰级别
- [ ] `rejected_patterns` — 明确不可接受的格局名

### 中优先级
- [ ] `accepted_useful_elements` — 喜用五行的"专业共识范围"（应收紧）
- [ ] `accepted_avoid_elements` — 忌避五行的"专业共识范围"
- [ ] `dispute_notes` — 各案例已知的流派分歧点

### 低优先级
- [ ] `confidence` — 案例本身的标注信心（有些应升级为 high，有些应降为 low）

---

## 九、下一阶段建议

### Phase 3.7（推荐路径）
1. **邀请命理师审核 standard_cases.json** —— 每个案例至少 2 位独立命理师交叉确认
2. **加入 5 例"反例"** —— 规则引擎应明显判错的极端盘，作为改进信号
3. **加入 3 例疑似从强** —— 当前缺失，需手工挑选典型从强样本
4. **CI 集成质量门禁** —— 把 `check_bazi_quality_gate.py` 接入 GitHub Actions / 类似 CI
5. **AI live 模式回归** —— 在 staging 环境定期跑 `--live`，监控 LLM 输出违规率趋势

### Phase 4（可选）
- 合化成功判断
- 调候用神
- 流年大运交互合冲

### 永远不做的事
- 把 AI 自标注当作专业标准
- 宣传准确率
- 自动付费包装
- 把神煞作为核心判断依据
- 强行把低信心案例当作高信心使用

---

## 十、文件清单（Phase 3.6 新增/修改）

### 新增

| 文件 | 职责 |
|------|------|
| `backend/domain/fixtures/bazi_cases/ai_output_samples.json` | AI 输出 fixture（5 个 dry-run 样本，含 expected_outcome） |
| `scripts/evaluate_bazi_ai_outputs.py` | AI 输出回归脚本（--dry-run / --live） |
| `scripts/check_bazi_quality_gate.py` | 质量门禁 |
| `tests/test_bazi_quality_gate.py` | 质量门禁测试（13 项） |
| `tests/test_bazi_ai_output_evaluation.py` | AI 输出评估测试（13 项） |
| `docs/BAZI_STANDARD_CASES_REPORT.md` | 本报告 |
| `reports/bazi_ai_output_evaluation_report.json` | AI 评估报告（数据） |
| `reports/bazi_ai_output_evaluation_report.md` | AI 评估报告（人类可读） |

### 修改

| 文件 | 变更 |
|------|------|
| `backend/domain/fixtures/bazi_cases/standard_cases.json` | 6 例 → 20 例，schema 升级（primary_*, rejected_*, dispute_notes） |
| `backend/domain/bazi_case_loader.py` | 新 schema 字段校验 |
| `backend/domain/bazi_rule_evaluator.py` | 支持 primary/accepted/rejected，新增 hit_breakdown / dispute_reason |
| `backend/services/ai_output_validator.py` | 收紧十神归属正则，避免假阳性 |
| `tests/test_bazi_rule_evaluator.py` | 新增 TestPhase36Schema 类（6 项） |

### 测试命令 & 结果

```bash
.venv/Scripts/python.exe -m pytest tests/ -v
```
**188 passed in 2.07s**

| 测试文件 | 项数 |
|---------|------|
| test_bazi_accuracy.py | 51 |
| test_bazi_rules_v2.py | 26 |
| test_bazi_relations.py | 21 |
| test_ai_output_validator.py | 20 |
| test_bazi_case_loader.py | 19 |
| test_bazi_rule_evaluator.py | 25 (含 6 项 Phase 3.6) |
| test_bazi_quality_gate.py | 13 |
| test_bazi_ai_output_evaluation.py | 13 |
| **总计** | **188** |
