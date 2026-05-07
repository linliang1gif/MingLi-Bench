import React from 'react';
import { Card } from 'antd';

/**
 * PaperCard —— 宣纸卡片
 * 在 AntD Card 基础上叠加新中式语义：
 * - title 使用宋体
 * - extra 古铜金色
 * - 默认 16px 圆角 / 淡金描边 / 弱阴影（在 theme.css 中定义）
 */
export default function PaperCard({ title, extra, children, style, bodyStyle, ...rest }) {
  return (
    <Card
      title={
        title ? (
          <span
            style={{
              fontFamily: 'var(--ml-font-serif)',
              fontSize: 16,
              letterSpacing: 1,
              color: 'var(--ml-text)',
            }}
          >
            {title}
          </span>
        ) : undefined
      }
      extra={
        extra ? (
          <span style={{ color: 'var(--ml-bronze)', fontSize: 13 }}>{extra}</span>
        ) : undefined
      }
      style={style}
      bodyStyle={{ padding: 18, ...bodyStyle }}
      {...rest}
    >
      {children}
    </Card>
  );
}
