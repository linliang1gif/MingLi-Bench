import React from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

/**
 * MarkdownView —— 用于把 AI 回复 / 报告内容渲染成排版友好的 Markdown。
 *
 * 已配置：
 * - GitHub Flavored Markdown（表格、删除线、任务列表）
 * - 不渲染原生 HTML（默认 react-markdown 行为，安全）
 * - 通过 .ml-md 类承载墨韵青瓷主题的排版样式（见 global.css）
 *
 * Props：
 *   content: string  —— Markdown 文本
 *   compact: boolean —— 紧凑模式（聊天气泡内）
 */
export default function MarkdownView({ content, compact = false }) {
  if (!content) return null;
  return (
    <div className={`ml-md${compact ? ' ml-md-compact' : ''}`}>
      <ReactMarkdown remarkPlugins={[remarkGfm]}>{content}</ReactMarkdown>
    </div>
  );
}
