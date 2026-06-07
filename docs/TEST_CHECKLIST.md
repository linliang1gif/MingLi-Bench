# V1.4.0 回归测试清单

## 后端基础检查

- [ ] 数据库已备份到 `backend/storage/mingli.db.bak-YYYYMMDD-HHMMSS`
- [ ] `.\.venv\Scripts\python.exe -m compileall backend` 通过
- [ ] `GET /api/health` 返回 `status: ok`
- [ ] `GET /api/system/check` 返回 `version: V1.4.0`
- [ ] `GET /api/system/check` 返回数据库存在、核心表存在、备份数量和最近备份列表
- [ ] `POST /api/system/backup-db` 可生成新备份
- [ ] `GET /api/system/test-cases` 可读取测试样例

## 前端构建

- [ ] `npm run build` 通过
- [ ] 打开 `http://127.0.0.1:5173/` 无空白页
- [ ] 左侧菜单分组完整，底部显示 `V1.4.0`
- [ ] 左侧菜单高度不足时可在侧栏内滚动

## 命理分析

- [ ] AI 问命页面可进入
- [ ] 命主档案可查看
- [ ] 命主可创建并保存
- [ ] 命盘分析可选择命主并生成/读取命盘
- [ ] 报告中心可生成报告
- [ ] 报告列表可筛选类型、搜索关键词、排序
- [ ] 点击“查看详情”可进入报告详情
- [ ] 历史记录页面可进入
- [ ] 案例审核页面可进入

## 知识库与系统管理

- [ ] 知识类目页面可进入
- [ ] 古籍知识库可展示书籍列表
- [ ] 古籍书籍可按类目、可信度、风险级别筛选
- [ ] `/knowledge-import` 页面可进入
- [ ] `POST /api/knowledge/import-book-json` 可导入 `backend/data/books_p0/01_zhouyi.json`
- [ ] `POST /api/knowledge/import-folder` 可导入 `backend/data/books_p0`
- [ ] `GET /api/knowledge/import-logs` 可返回导入日志
- [ ] `GET /api/knowledge/import-sample-format` 可返回标准 JSON 示例
- [ ] `GET /api/knowledge/quality-check` 可返回覆盖统计
- [ ] 20 本核心古籍每本至少 20 个 chunks
- [ ] 古籍检索可按关键词、类目、书籍、标签、适用模块、可信度、风险级别组合检索
- [ ] 古籍检索可返回片段、书名、章节、小节、标签、适用模块、出处
- [ ] 古籍检索结果可复制引用信息
- [ ] 报告中心可按“有引用/无引用”筛选
- [ ] 报告详情可展示 `references_json`
- [ ] Prompt 管理可查看模板
- [ ] Prompt 测试按钮可执行或返回明确错误
- [ ] 风险词管理可查看风险词
- [ ] 风险检测可返回命中结果

## 风水与传统工具

- [ ] 房屋档案页面可进入
- [ ] 罗盘测向可转换角度并保存记录
- [ ] 阳宅基础报告可生成或返回明确错误
- [ ] `GET /api/xuankong/period?year=2026` 返回下元9运、`period_number=9`
- [ ] `POST /api/xuankong/calculate` 使用 `facing_degree=180` 返回向午、坐子
- [ ] `/xuankong` 页面可选择房屋、输入年份和角度并展示九宫格
- [ ] 房屋缺少主门角度时，使用主门朝向会提示补充或改用手动角度
- [ ] 玄空飞星报告可生成并跳转报告详情
- [ ] 报告中心可筛选“玄空飞星报告”
- [ ] `/fengshui-photo` 页面可进入
- [ ] 手机浏览器可看到拍照入口
- [ ] jpg/png/webp 图片可上传并预览
- [ ] `POST /api/fengshui-photo/analyze` 返回结构化 JSON
- [ ] 用户校正表单可填写
- [ ] 拍照风水报告可生成并跳转报告详情
- [ ] 报告中心可筛选“拍照风水报告”
- [ ] `DELETE /api/fengshui-photo/records/{id}` 可删除记录
- [ ] 择日黄历页面可进入
- [ ] 起名工具页面可进入
- [ ] 测字灵签页面可进入

## 系统自检

- [ ] 系统版本显示为 `V1.4.0`
- [ ] LLM 状态显示 Provider 和模型，或显示未配置
- [ ] 数据库路径可复制
- [ ] 核心表状态显示正常
- [ ] 备份文件数量和最近 10 个备份文件显示正常
- [ ] 测试样例按模块分组显示
- [ ] 异常提示为空时显示友好 Empty
