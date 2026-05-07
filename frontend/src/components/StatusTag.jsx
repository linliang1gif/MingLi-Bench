import React from 'react';
import { Tag } from 'antd';

/**
 * StatusTag —— 评测/任务状态标签
 * 颜色映射：
 *  - completed / passed → 青松绿
 *  - running            → 琥珀橙
 *  - failed / error     → 朱砂红
 *  - queued / pending   → 墨灰
 */
const MAP = {
  completed: { label: '已完成', bg: 'rgba(63, 107, 79, 0.12)', border: 'rgba(63, 107, 79, 0.45)', color: '#3F6B4F' },
  passed:    { label: '通过',   bg: 'rgba(63, 107, 79, 0.12)', border: 'rgba(63, 107, 79, 0.45)', color: '#3F6B4F' },
  running:   { label: '进行中', bg: 'rgba(196, 127, 44, 0.12)', border: 'rgba(196, 127, 44, 0.45)', color: '#C47F2C' },
  failed:    { label: '失败',   bg: 'rgba(158, 42, 43, 0.10)',  border: 'rgba(158, 42, 43, 0.45)',  color: '#9E2A2B' },
  error:     { label: '异常',   bg: 'rgba(158, 42, 43, 0.10)',  border: 'rgba(158, 42, 43, 0.45)',  color: '#9E2A2B' },
  queued:    { label: '排队中', bg: 'rgba(111, 98, 88, 0.10)',  border: 'rgba(111, 98, 88, 0.40)',  color: '#6F6258' },
  pending:   { label: '待开始', bg: 'rgba(111, 98, 88, 0.10)',  border: 'rgba(111, 98, 88, 0.40)',  color: '#6F6258' },
};

export default function StatusTag({ status = 'pending', text }) {
  const cfg = MAP[status] || MAP.pending;
  return (
    <Tag
      style={{
        background: cfg.bg,
        borderColor: cfg.border,
        color: cfg.color,
        margin: 0,
      }}
    >
      <span
        className="ml-dot"
        style={{ background: cfg.color, marginRight: 6, opacity: 0.9 }}
      />
      {text || cfg.label}
    </Tag>
  );
}
