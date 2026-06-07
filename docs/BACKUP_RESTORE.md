# 数据库备份与恢复

## 备份位置

主数据库：

```text
backend/storage/mingli.db
```

备份文件：

```text
backend/storage/mingli.db.bak-YYYYMMDD-HHMMSS
```

## 自动展示

系统自检接口会返回：

```json
{
  "backups": {
    "count": 6,
    "latest": ["mingli.db.bak-20260606-221731"]
  }
}
```

前端 `/system-check` 会展示备份总数和最近 10 个备份文件名。

## 手动备份

方式一：前端操作。

```text
系统管理 -> 系统自检 -> 立即备份数据库
```

方式二：调用接口。

```powershell
curl.exe -X POST http://127.0.0.1:8000/api/system/backup-db
```

方式三：PowerShell 复制。

```powershell
cd "C:\Users\liolin\Documents\算命项目\命理评测平台"
$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
Copy-Item "backend\storage\mingli.db" "backend\storage\mingli.db.bak-$stamp"
```

## 手动恢复

1. 停止后端服务。
2. 再备份一次当前数据库，避免误覆盖后无法回退。
3. 用目标备份覆盖 `backend/storage/mingli.db`。
4. 重新启动后端。
5. 打开 `/system-check` 确认数据库存在、核心表存在、统计数正常。

示例：

```powershell
cd "C:\Users\liolin\Documents\算命项目\命理评测平台"

$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
Copy-Item "backend\storage\mingli.db" "backend\storage\mingli.db.before-restore-$stamp"

Copy-Item "backend\storage\mingli.db.bak-20260606-221731" "backend\storage\mingli.db" -Force
```

## 注意事项

- 不要把 `backend/storage/mingli.db` 或备份文件提交到远程仓库。
- 恢复前必须停止后端，避免 SQLite 写入冲突。
- V1.0 不提供自动删除备份功能，只展示数量和最近 10 个文件。
- 如需长期归档，请把重要备份复制到独立硬盘、NAS 或云盘。
