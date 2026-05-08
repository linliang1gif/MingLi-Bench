# 八字规则引擎 v2 实施报告

> 生成日期：2026-05-08  
> 版本：bazi-rules-v2.0.0  
> 测试结果：118 项全通过（1.33s）

---

## 一、v2 解决了什么问题

| v1 问题 | v2 修复 |
|---------|---------|
| 五行只做简单计数（天干+地支本气） | 加权力量模型：区分月令/本气/中气/余气/通根 |
| 旺衰仅靠 help/drain 粗估 | 基于五行力量的精确计算：同类/异类占比 + 季节/通根/帮扶三维修正 |
| 格局判断不考虑合冲刑害 | 地支关系自动识别，月令被冲自动降级 + 加 break_factor |
| 喜用神两法对比粗糙 | 完整双轨输出 + 综合建议 + conflict_notes + 分级 confidence |
| 无 AI 输出校验 | 后置校验器：禁止词/错误大运/错误本命年/改四柱/绝对化措辞 |
| 无信心级别约束 | overall_confidence 注入 Prompt，low 时 AI 必须表达谨慎 |

---

## 二、五行权重模型

```
位置          主气    中气    余气
月令          30      15      7
其他地支      12      6       3
天干透出      8       —       —
通根加权      5       —       —
```

输出示例（小滕 戊土日主）：
```
木=30.0  火=6.0  土=24.0  金=30.0  水=33.0
```

文件：`backend/domain/bazi_strength.py` → `calculate_wuxing_power(chart)`

---

## 三、旺衰评分逻辑

```
base_score = same_power / (same_power + opposite_power) × 100

修正 = season_score + root_score + support_score
  - season_score: 得令 +8 / 印生 +5 / 失令 -3
  - root_score: 坐根 +6 / 坐印根 +3
  - support_score: 每帮扶天干 +3 / 每耗泄天干 -2

final_score = clamp(base + 修正, 0, 100)
```

分级：

| 分数 | 级别 | 备注 |
|------|------|------|
| ≥75 | 身强 | 异类极弱时标"疑似从强" |
| 60-74 | 偏强 | |
| 45-59 | 中和 | 附 uncertainty 标记 |
| 35-44 | 偏弱 | |
| 20-34 | 身弱 | |
| <20 | 身弱/疑似从弱 | 同类极弱时标"疑似从弱" |

文件：`backend/domain/bazi_strength.py` → `calculate_day_master_strength_v2(chart)`

---

## 四、地支关系

支持 7 种关系：

| 类型 | 规则 |
|------|------|
| 六合 | 子丑/寅亥/卯戌/辰酉/巳申/午未 |
| 六冲 | 子午/丑未/寅申/卯酉/辰戌/巳亥 |
| 三合 | 申子辰水/寅午戌火/巳酉丑金/亥卯未木 |
| 半合 | 三合缺一位时标注 |
| 三会 | 寅卯辰木/巳午未火/申酉戌金/亥子丑水 |
| 六害 | 子未/丑午/寅巳/卯辰/申亥/酉戌 |
| 三刑 | 无恩(寅巳申)/恃势(丑未戌)/无礼(子卯)/自刑(辰午酉亥) |

初版只识别关系，不过度推断吉凶。合冲影响格局时仅作为 evidence/break_factor。

文件：`backend/domain/bazi_relations.py` → `analyze_branch_relations(chart)`

---

## 五、格局判断逻辑

1. 取月令本气对应十神
2. 本气透干 → 高信心取格
3. 本气不透，中气/余气透干 → 中/低信心
4. 本气为比劫 → 建禄格/月劫格
5. 月令被冲 → confidence 降级 + break_factor
6. 各格局专项规则：
   - 正官格忌伤官/七杀混杂
   - 七杀格喜食神制杀/印化杀
   - 食神格忌枭印夺食
   - 伤官格喜生财/配印，忌见官
   - 财格忌比劫争财
   - 印格忌财星坏印

文件：`backend/domain/bazi_pattern.py` → `analyze_pattern_v2(chart, strength, relations)`

---

## 六、喜用神冲突处理

### 双轨输出
- **旺衰扶抑法**：身弱喜印比，身强喜食伤财官
- **格局法**：按格局类型专项推断

### 冲突检测
```python
conflict = (ws_useful ∩ gj_avoid) ∪ (ws_avoid ∩ gj_useful) ≠ ∅
```

### 综合建议
- 共识优先 → 取两法交集
- 无共识 → 取高信心一方
- 有冲突 → confidence 封顶 medium
- 中和/不确定/疑似从格 → confidence 封顶 low

文件：`backend/domain/bazi_useful_gods.py` → `infer_useful_gods_v2(chart, strength, pattern, relations)`

---

## 七、AI 输出校验器

| 检查项 | 严重度 | 触发动作 |
|--------|--------|---------|
| 禁止词（必定/注定/一定发财...） | error | retry |
| 绝对化模式（必定会/注定要...） | warning | warn |
| 引用不存在的大运干支 | error | retry |
| 错误本命年 | error | retry |
| 自行修改四柱 | error | retry |
| 错误十神关系 | warning | warn |
| 健康/投资/法律绝对建议 | error | retry |

初版只检测和日志，不自动重试。

文件：`backend/services/ai_output_validator.py` → `validate_bazi_ai_output(text, chart, rule_result)`

---

## 八、当前仍不能保证的边界

1. **合化成功判断** — 六合是否真正合化取决于环境（月令、天干透出），当前仅识别合的关系，未判断合化成功与否
2. **从格确认** — 标记"疑似从格"但不自动确认，需命理师介入
3. **暗合/暗冲** — 未实现地支藏干之间的暗合暗冲
4. **神煞体系** — 未纳入，也不建议作为核心判断依据
5. **调候用神** — 未实现《穷通宝鉴》调候体系
6. **流年大运交互** — 未计算流年与大运的合冲关系
7. **AI 解释深度** — 取决于 LLM 本身对命理的理解

---

## 九、文件清单

### 新增文件

| 文件 | 职责 |
|------|------|
| `backend/domain/bazi_strength.py` | 五行加权力量模型 + 日主旺衰 v2 |
| `backend/domain/bazi_relations.py` | 地支关系分析（六合/冲/三合/会/害/刑/自刑） |
| `backend/domain/bazi_pattern.py` | 格局判断 v2（月令+透干+合冲影响） |
| `backend/domain/bazi_useful_gods.py` | 喜用神 v2（双轨+冲突+综合建议） |
| `backend/services/ai_output_validator.py` | AI 输出后置校验器 |
| `tests/test_bazi_rules_v2.py` | 规则引擎 v2 测试（26 项） |
| `tests/test_bazi_relations.py` | 地支关系测试（21 项） |
| `tests/test_ai_output_validator.py` | AI 校验器测试（20 项） |

### 修改文件

| 文件 | 变更 |
|------|------|
| `backend/domain/bazi_rules.py` | 新增 `analyze_chart_v2`，`analyze_chart` 切换至 v2 |
| `backend/services/prompt_service.py` | PROMPT_VERSION=3.0.0，`_format_rule_analysis` 支持 v2 结构，新增信心约束 |
| `tests/test_bazi_accuracy.py` | 版本号 1.0.0→2.0.0 |

---

## 十、测试命令 & 结果

```bash
.venv/Scripts/python.exe -m pytest tests/test_bazi_accuracy.py tests/test_bazi_rules_v2.py tests/test_bazi_relations.py tests/test_ai_output_validator.py -v
```

```
118 passed in 1.33s
```

| 测试文件 | 项数 | 结果 |
|---------|------|------|
| test_bazi_accuracy.py | 51 | ✅ 全通过 |
| test_bazi_rules_v2.py | 26 | ✅ 全通过 |
| test_bazi_relations.py | 21 | ✅ 全通过 |
| test_ai_output_validator.py | 20 | ✅ 全通过 |

---

## 十一、下一阶段建议

### Phase 4（可选）
1. **合化成功判断** — 六合在月令条件下是否真正化成
2. **调候用神** — 实现《穷通宝鉴》体系
3. **流年大运交互** — 计算大运与流年的合冲
4. **AI 输出自动重试** — 校验不通过时自动重试（带限制）

### Phase 5（可选）
1. **标准案例回归库** — 20+ 已知案例含专业标注
2. **暗合暗冲** — 地支藏干层面的隐性关系
3. **从格/化格识别** — 提升极端盘判断能力
