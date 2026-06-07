# V1.4.0 数据库说明

## V1.4 新增表

| 表名 | 说明 |
| --- | --- |
| `yinzhai_study_records` | 阴宅研究记录，保存研究标题、类型、位置备注、坐山/向首角度、二十四山、龙穴砂水向、形势环境、研究备注、结果 JSON 和关联报告 |
| `tianxing_fengshui_records` | 天星风水查询记录，保存角度、二十四山、天星映射 JSON、输入 JSON 和关联报告 |

V1.4 仍使用 `Base.metadata.create_all` 创建缺失表，不删除旧表，不清空旧数据。阴宅与天星报告继续写入 `reports`、`report_versions`，并在 `report_versions.references_json` 中保存古籍引用。

数据库文件：

```text
backend/storage/mingli.db
```

数据库类型：SQLite。

## 核心表

| 表名 | 说明 |
| --- | --- |
| `subjects` | 命主档案，保存昵称、性别、出生日期、出生时间、出生地、历法、经度、关注主题和备注 |
| `charts` | 命盘缓存，保存八字、五行和摘要 |
| `chat_sessions` | AI 对话会话 |
| `chat_messages` | AI 对话消息和风险检测结果 |
| `reports` | 分析报告主表 |
| `report_versions` | 报告版本快照，保存输入、结果、Markdown、模型、风险检测和 `references_json` 引用 |
| `case_feedbacks` | 标准案例反馈和审核信息 |

## 知识库表

| 表名 | 说明 |
| --- | --- |
| `knowledge_categories` | 60 大知识类目 |
| `knowledge_books` | 古籍书籍条目，包含类目、作者、朝代、版权状态、可信度、风险级别和说明 |
| `knowledge_chunks` | 古籍内容分片，包含原文、解释、标签、适用模块和出处 |
| `knowledge_import_logs` | 古籍 JSON 导入日志，保存导入类型、路径、重复策略、统计结果、状态和错误信息 |

## 系统管理表

| 表名 | 说明 |
| --- | --- |
| `prompt_templates` | 前端可管理的 Prompt 模板 |
| `risk_terms` | AI 输出风险词和替代表达建议 |

## 风水与传统工具表

| 表名 | 说明 |
| --- | --- |
| `house_profiles` | 房屋档案 |
| `compass_records` | 罗盘测向记录 |
| `xuan_kong_records` | 玄空飞星基础盘计算记录，保存三元九运、坐向、九宫星盘和完整结果 |
| `photo_analysis_records` | 拍照风水识别记录，保存图片路径、AI 识别结果、用户校正和关联报告 |
| `date_selection_records` | 择日记录 |
| `naming_records` | 起名记录 |
| `divination_records` | 测字和灵签记录 |

## 初始化与迁移

后端启动时会执行：

```text
backend/db/init_db.py
```

当前逻辑：

- 通过 SQLAlchemy `Base.metadata.create_all` 创建缺失表。
- 对少量历史字段执行轻量列迁移。
- 不自动删除表。
- 不自动清空数据。

## 维护注意

- 修改模型后需要同步更新本文件。
- 结构性迁移前必须备份数据库。
- 不建议直接编辑 SQLite 文件；如需手工维护，请先复制一份备份。
