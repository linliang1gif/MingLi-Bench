# 八字 AI 输出回归评估报告

> 生成时间：2026-05-08 23:34:36
> 模式：**dry-run**

---

## 一、总体结果

- 总样本数：**5**
- 通过：**5**
- 失败：**0**
- 通过率：**100.0%**
- 错误违规：**6**
- 警告违规：**1**

## 二、违规类型统计

| 类型 | 出现次数 |
|------|---------|
| forbidden_phrase | 2 |
| medical_legal_absolute | 2 |
| absolute_language | 1 |
| invalid_dayun | 1 |
| wrong_pillar | 1 |

## 三、样本明细

| case_id | label | passed | action | 主要违规 |
|---------|-------|--------|--------|---------|
| case_001 | clean_sample | ✅ | pass | — |
| case_001 | violation_absolute | ✅ | retry | 出现禁止词「必定」; 出现禁止词「注定」 |
| case_001 | violation_wrong_dayun | ✅ | retry | 引用了不存在的大运干支「甲午」 |
| case_001 | violation_wrong_pillar | ✅ | retry | AI 将年柱写为甲子，实际应为己卯 |
| case_001 | violation_medical | ✅ | retry | 健康/法律/投资绝对建议「建议购买比特币」; 健康/法律/投资绝对建议「打官司一定」 |

## 四、最常见问题

- **forbidden_phrase**：出现 2 次
- **medical_legal_absolute**：出现 2 次
- **absolute_language**：出现 1 次
