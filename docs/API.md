# V1.4.0 API 清单

所有接口默认前缀为 `/api`。

## 系统

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/health` | 基础健康检查 |
| GET | `/llm/status` | LLM Provider 和模型状态 |
| GET | `/system/check` | 系统自检，返回版本、数据库、备份、表状态和统计数 |
| POST | `/system/backup-db` | 手动备份 SQLite 数据库 |
| GET | `/system/test-cases` | 读取 V1.0 测试样例 |

## 命主与命盘

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/subjects` | 命主列表 |
| POST | `/subjects` | 创建命主 |
| GET | `/subjects/{subject_id}` | 命主详情 |
| DELETE | `/subjects/{subject_id}` | 删除命主 |
| POST | `/subjects/{subject_id}/chart` | 生成命盘 |
| GET | `/subjects/{subject_id}/chart` | 获取命盘 |
| GET | `/chart/preview` | 临时命盘预览 |

## 对话与历史

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| POST | `/chat` | 普通 AI 对话 |
| POST | `/chat/stream` | SSE 流式 AI 对话 |
| GET | `/chat/sessions` | 对话会话列表 |
| GET | `/chat/sessions/{session_id}` | 对话会话详情 |
| GET | `/history` | 历史记录 |

## 报告

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| POST | `/reports/generate` | 生成分析报告 |
| GET | `/reports` | 报告列表，兼容 `subject_id`、`has_references` 参数 |
| GET | `/reports/{report_id}` | 报告详情 |
| GET | `/reports/{report_id}/versions` | 报告版本列表 |
| GET | `/reports/{report_id}/versions/{version_id}` | 报告版本详情 |

## 知识库

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| POST | `/categories/init` | 初始化 60 大知识类目 |
| GET | `/categories` | 知识类目列表 |
| POST | `/knowledge/init` | 初始化古籍样例 |
| GET | `/knowledge/books` | 书籍列表，支持 `query`、`category_code`、`reliability_level`、`risk_level` |
| POST | `/knowledge/books` | 新增书籍 |
| GET | `/knowledge/books/{book_id}` | 书籍详情 |
| POST | `/knowledge/chunks` | 新增内容片段 |
| GET | `/knowledge/books/{book_id}/chunks` | 书籍片段列表 |
| POST | `/knowledge/search` | 古籍片段检索，支持 `query`、`category_code`、`book_id`、`tags`、`applicable_module`、`reliability_level`、`risk_level`、`limit` |
| POST | `/knowledge/import-book-json` | 导入单本标准 JSON 古籍 |
| POST | `/knowledge/import-folder` | 批量导入目录下的标准 JSON 古籍 |
| GET | `/knowledge/import-logs` | 导入日志列表 |
| GET | `/knowledge/import-sample-format` | 获取标准 JSON 示例格式 |
| GET | `/knowledge/quality-check` | 知识库质量检查，返回书籍、分片、类目、报告类型覆盖、重复书籍和空片段统计 |

## Prompt 与风险词

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| POST | `/prompts/init` | 初始化 Prompt 模板 |
| GET | `/prompts` | Prompt 模板列表 |
| POST | `/prompts` | 创建 Prompt 模板 |
| PUT | `/prompts/{template_id}` | 更新 Prompt 模板 |
| POST | `/prompts/{template_id}/test` | 测试 Prompt 模板 |
| POST | `/risk-terms/init` | 初始化风险词 |
| GET | `/risk-terms` | 风险词列表 |
| POST | `/risk/check` | 文本风险检测 |

## 风水与传统工具

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/houses` | 房屋档案列表 |
| POST | `/houses` | 创建房屋档案 |
| GET | `/houses/{house_id}` | 房屋档案详情 |
| GET | `/houses/{house_id}/compass-records` | 房屋测向记录 |
| POST | `/houses/{house_id}/set-main-door-from-record/{record_id}` | 从测向记录设置大门朝向 |
| POST | `/compass/convert` | 角度转八方、二十四山 |
| POST | `/compass/records` | 创建罗盘测向记录 |
| GET | `/compass/records` | 罗盘测向记录列表 |
| DELETE | `/compass/records/{record_id}` | 删除罗盘测向记录 |
| POST | `/fengshui/basic-report` | 生成阳宅基础报告 |
| GET | `/xuankong/period?year=2026` | 查询年份所属三元九运 |
| POST | `/xuankong/calculate` | 计算玄空飞星基础盘；有 `house_id` 时保存记录 |
| POST | `/xuankong/report` | 生成玄空飞星报告并写入报告中心 |
| GET | `/xuankong/records?house_id=1` | 查询玄空飞星计算记录 |
| POST | `/fengshui-photo/upload` | multipart 上传房间图片并创建拍照识别记录 |
| POST | `/fengshui-photo/analyze` | 分析图片对象，当前无多模态时返回可校正 mock 结构 |
| POST | `/fengshui-photo/report` | 基于图片识别与用户校正生成拍照风水报告 |
| GET | `/fengshui-photo/records?house_id=1` | 查询拍照识别记录 |
| DELETE | `/fengshui-photo/records/{record_id}` | 删除拍照识别记录并尽量删除图片文件 |
| POST | `/date-selection/wedding` | 婚嫁择日 |
| POST | `/date-selection/move-in` | 入宅择日 |
| POST | `/date-selection/opening` | 开业择日 |
| POST | `/date-selection/renovation` | 装修择日 |
| POST | `/date-selection/bed` | 安床择日 |
| POST | `/naming/baby` | 宝宝起名 |
| POST | `/naming/company` | 公司起名 |
| POST | `/naming/shop` | 店铺起名 |
| POST | `/naming/brand` | 品牌起名 |
| POST | `/divination/word` | 测字 |
| POST | `/divination/lottery` | 灵签 |

## 案例反馈

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/cases` | 标准案例列表 |
| GET | `/cases/{case_id}` | 标准案例详情 |
| POST | `/cases/{case_id}/feedback` | 提交案例反馈 |
| GET | `/feedbacks` | 反馈列表 |
| GET | `/feedbacks/summary` | 反馈统计 |

## V1.4 阴宅与天星风水

### 阴宅研究

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| POST | `/yinzhai/records` | 创建阴宅研究记录，保存龙、穴、砂、水、向、形势环境和坐向角度 |
| GET | `/yinzhai/records?house_id=1` | 查询阴宅研究记录 |
| GET | `/yinzhai/records/{record_id}` | 查询单条阴宅研究记录 |
| DELETE | `/yinzhai/records/{record_id}` | 删除阴宅研究记录 |
| POST | `/yinzhai/report` | 生成阴宅研究报告，写入 `reports` 和 `report_versions`，保存 `references_json` |

### 天星风水

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/tianxing/mappings` | 查询 V1.4 二十四山天星基础映射表 |
| GET | `/tianxing/lookup?degree=180` | 按角度或二十四山查询天星映射，不保存记录 |
| POST | `/tianxing/query` | 查询并保存天星风水记录 |
| GET | `/tianxing/records?house_id=1` | 查询天星风水记录 |
| GET | `/tianxing/records/{record_id}` | 查询单条天星风水记录 |
| DELETE | `/tianxing/records/{record_id}` | 删除天星风水记录 |
| POST | `/tianxing/report` | 生成天星风水报告，写入 `reports` 和 `report_versions`，保存 `references_json` |

V1.4 边界：阴宅与天星功能只做传统文化研究、堪舆资料整理和环境记录，不做墓地吉凶强断，不提供改葬、迁坟、法事化解或诱导消费建议。
