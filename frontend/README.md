# 明理 MingLi Bench · 前端骨架

新中式 / 国风学术风 / 东方数据实验室主题的命理大模型评测平台前端骨架。

## 技术栈

- React 18 + Vite 5
- Ant Design v5（通过 ConfigProvider + theme.css 双层覆盖）
- React Router v6

## 目录结构

```text
frontend/
├─ index.html
├─ package.json
├─ vite.config.js
└─ src/
   ├─ main.jsx                  入口 + AntD ConfigProvider 主题令牌
   ├─ App.jsx                   路由
   ├─ styles/
   │  ├─ theme.css              新中式 CSS 变量 + AntD 细节覆盖
   │  └─ global.css             全局工具类、占位卡、网格
   ├─ components/
   │  ├─ LogoSeal.jsx           「明理」朱砂印章 + 英文字样
   │  ├─ PaperCard.jsx          宣纸卡片
   │  ├─ StatusTag.jsx          状态标签（青松绿/琥珀橙/朱砂红/墨灰）
   │  └─ PageBanner.jsx         水墨山水 Banner（纯 SVG，无外部资源）
   ├─ layouts/
   │  └─ MainLayout.jsx         深墨左栏 + 顶部导航 + 内容区
   └─ pages/
      ├─ Dashboard.jsx          明理评测总览
      ├─ Dataset.jsx            命理题库
      ├─ Astro.jsx              命盘数据（四柱卡片）
      ├─ Models.jsx             模型馆
      ├─ Benchmark.jsx          开卷评测
      ├─ RunDetail.jsx          评测进行中
      ├─ Results.jsx            评测结果（圆环 + 柱状占位）
      ├─ Compare.jsx            群模论衡
      └─ Reports.jsx            评测文书（卷宗风格）
```

## 启动

```powershell
cd c:\Users\liolin\Downloads\MingLi-Bench\frontend
npm install
npm run dev
```

默认地址：http://localhost:5173

## 主题色（CSS Variables）

所有颜色通过 CSS 变量统一管理，不要硬编码重复颜色。

```text
--ml-bg           #F7F1E3   宣纸米白背景
--ml-card-bg      #FFFDF6   卡片背景
--ml-text         #2B2118   主文字
--ml-text-sub     #6F6258   次文字
--ml-vermilion    #8A1F1D   朱砂红（主色）
--ml-vermilion-2  #A7352F   朱砂红 hover
--ml-bronze       #B08D57   古铜金
--ml-ink          #1F1A17   深墨色
--ml-success      #3F6B4F   青松绿
--ml-warning      #C47F2C   琥珀橙
--ml-error        #9E2A2B   错误朱砂
--ml-border       rgba(176, 141, 87, 0.25)
--ml-shadow-card  0 8px 24px rgba(43, 33, 24, 0.08)
```

## 设计原则

- **克制**：不要大红大紫，不要页游仙侠风。
- **专业**：图表使用 朱砂 / 古铜 / 青松 / 墨灰 / 琥珀，避免高饱和科技蓝。
- **东方学术感**：标题使用宋体，正文沿用系统中文字体；山水 / 印章只作为低透明点缀。
- **响应式**：≥ 1366px 桌面优先，`.ml-grid.cols-3 / cols-4` 在窄屏自动降为 2 列。

## 状态色映射（StatusTag）

| 状态                | 颜色      |
|---------------------|-----------|
| completed / passed  | 青松绿    |
| running             | 琥珀橙    |
| failed / error      | 朱砂红    |
| queued / pending    | 墨灰      |

## 后续待接入

- 真实 API（题库、命盘、模型、评测、结果、报告）
- 图表（推荐 ECharts，配色已在 `--ml-chart-1..5` 中预留）
- 用户与权限
- 国际化（zhCN 已默认接入）
