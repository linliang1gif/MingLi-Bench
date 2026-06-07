# 命理评测平台 V1.3.1

命理评测平台是一个自用的传统文化与命理分析工具台。V1.3.1 版本在 V1.3 古籍知识库基础上，扩展第一批 20 本核心古籍，并加入知识库质量检查，用于保障主要报告类型都有稳定古籍引用。

## 技术栈

后端：

- FastAPI
- SQLAlchemy
- SQLite
- lunar-python
- OpenAI 兼容 LLM 调用

前端：

- React 18
- Vite
- Ant Design
- dayjs

数据库：

- `backend/storage/mingli.db`

## 启动方式

后端：

```powershell
cd "C:\Users\liolin\Documents\算命项目\命理评测平台"
.\.venv\Scripts\python.exe -m uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```

前端：

```powershell
cd "C:\Users\liolin\Documents\算命项目\命理评测平台\frontend"
npm run dev
```

访问：

```text
前端：http://127.0.0.1:5173/
后端文档：http://127.0.0.1:8000/api/docs
系统自检：http://127.0.0.1:5173/system-check
古籍导入：http://127.0.0.1:5173/knowledge-import
```

## 手机访问

同一局域网下，电脑启动后端和前端时需要监听 `0.0.0.0`：

```powershell
cd "C:\Users\liolin\Documents\算命项目\命理评测平台"
.\.venv\Scripts\python.exe -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

```powershell
cd "C:\Users\liolin\Documents\算命项目\命理评测平台\frontend"
$env:VITE_API_BASE_URL="http://电脑局域网IP:8000"
npm run dev -- --host 0.0.0.0 --port 5173
```

手机浏览器访问：

```text
http://电脑局域网IP:5173
```

拍照识别页面：

```text
http://电脑局域网IP:5173/fengshui-photo
```

## 古籍导入

标准 JSON 格式见：

```text
docs/BOOK_IMPORT_FORMAT.md
```

内置样例目录：

```text
backend/data/books_p0/
```

支持单本导入、目录批量导入、导入日志查看，以及 `skip`、`overwrite`、`append` 三种重复策略。报告生成时会从知识库检索引用，并把真实引用保存到 `report_versions.references_json`。

## 目录结构

```text
backend/
  api/              FastAPI 路由
  core/             配置与版本号
  data/             种子数据与测试样例
  db/               SQLAlchemy 模型、Session、建表初始化
  domain/           命理、风水、择日、起名、测字等规则
  prompts/          默认 Prompt Markdown
  services/         业务服务
  storage/          SQLite 数据库与备份文件

frontend/
  src/
    components/     通用组件
    layouts/        主布局和侧边栏
    pages/          页面
    services/       API 封装
    styles/         主题样式

docs/               项目文档
```

## 维护原则

- 不直接提交 `.env` 或 API Key。
- 修改前先备份 `backend/storage/mingli.db`。
- 新增接口后同步更新 `docs/API.md`。
- 数据库结构变化需同步更新 `docs/DATABASE.md`。
- 封版回归按 `docs/TEST_CHECKLIST.md` 执行。
