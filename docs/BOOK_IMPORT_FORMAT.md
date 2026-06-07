# 古籍 JSON 导入格式

V1.3.1 支持以标准 JSON 文件导入古籍书籍和内容分片。单本文件根节点必须是一个对象，`chunks` 为该书的片段数组。

## 标准格式

```json
{
  "title": "葬经",
  "alias": "葬书",
  "category_code": "13",
  "author": "郭璞",
  "dynasty": "晋",
  "version": "公版整理文本",
  "source": "本地整理",
  "copyright_status": "public_domain_or_self整理",
  "reliability_level": "A",
  "risk_level": "medium",
  "description": "风水堪舆经典之一。",
  "chunks": [
    {
      "chapter": "气感篇",
      "section": "第一段",
      "original_text": "葬者，乘生气也。",
      "explanation": "此句强调传统堪舆中对生气的重视。",
      "tags": ["阴宅", "生气", "葬法", "堪舆基础"],
      "applicable_modules": ["yinzhai_study_report", "fengshui_basic_report", "knowledge"],
      "source_ref": "葬经·气感篇"
    }
  ]
}
```

## 字段说明

| 字段 | 必填 | 说明 |
| --- | --- | --- |
| `title` | 是 | 书名，用于重复判断 |
| `alias` | 否 | 别名 |
| `category_code` | 是 | 60 大知识类目编号 |
| `author` | 否 | 作者 |
| `dynasty` | 否 | 朝代 |
| `version` | 否 | 版本说明 |
| `source` | 否 | 来源说明 |
| `copyright_status` | 否 | 版权状态，建议标明公版或自整理 |
| `reliability_level` | 否 | `A`、`B`、`C`，默认 `C` |
| `risk_level` | 否 | `low`、`medium`、`high`，默认 `medium` |
| `description` | 否 | 书籍说明 |
| `chunks` | 否 | 片段数组 |

## 片段字段

| 字段 | 必填 | 说明 |
| --- | --- | --- |
| `chapter` | 否 | 章节 |
| `section` | 否 | 小节 |
| `original_text` | 是 | 原文或自整理短句 |
| `explanation` | 否 | 自整理解释 |
| `tags` | 否 | 标签数组，接口也兼容逗号分隔字符串 |
| `applicable_modules` | 否 | 适用模块数组 |
| `source_ref` | 否 | 出处引用 |

## 重复策略

`duplicate_strategy` 支持三种：

| 策略 | 行为 |
| --- | --- |
| `skip` | 同名书已存在时跳过整本 |
| `overwrite` | 同名书已存在时更新书籍元信息，删除旧片段并重新写入 |
| `append` | 同名书已存在时更新书籍元信息，并追加新片段 |

## 核心古籍数据

内置核心古籍目录：

```text
backend/data/books_p0/
```

V1.3.1 第一批包含 20 本核心古籍：

```text
01_zhouyi.json
02_yuanhai_ziping.json
03_sanming_tonghui.json
04_ditiansui.json
05_ziping_zhenquan.json
06_qiongtong_baojian.json
07_yangzhai_sanyao.json
08_bazhai_mingjing.json
09_huangdi_zhaijing.json
10_shenshi_xuankongxue.json
11_zangjing.json
12_hanlongjing.json
13_yilongjing.json
14_qingnangjing.json
15_dili_wujue.json
16_xieji_bianfangshu.json
17_xuanze_zongjing.json
18_yuxiaji.json
19_meihua_yishu.json
20_zengshan_buyi.json
```

可通过前端“系统管理 / 古籍导入”导入，也可调用：

```text
POST /api/knowledge/import-book-json
POST /api/knowledge/import-folder
```

报告引用只使用系统检索到并保存进 `report_versions.references_json` 的来源，不允许 AI 自行虚构书名、章节和出处。

可通过：

```text
GET /api/knowledge/quality-check
```

检查当前知识库的类目覆盖、报告类型覆盖、重复书籍、空片段和低覆盖类目。
