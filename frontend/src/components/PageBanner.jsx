import React from 'react';

/**
 * PageBanner —— 页面顶部水墨山水 Banner
 * 纯 CSS / SVG 实现，不引入外部图片资源：
 *  - 远山 / 中山 / 近山 三层叠加 + 弱透明
 *  - 右侧朱砂落款
 * props:
 *  - title:    主标题（宋体）
 *  - subtitle: 副标题
 *  - quote:    可选诗句 / 平台箴言
 *  - extra:    右侧操作槽
 */
export default function PageBanner({ title, subtitle, quote, extra }) {
  return (
    <div
      style={{
        position: 'relative',
        background:
          'linear-gradient(180deg, #F4F7F3 0%, #E8EDE8 100%)',
        border: '1px solid var(--ml-border)',
        borderRadius: 'var(--ml-radius-lg)',
        padding: '20px 26px',
        marginBottom: 20,
        overflow: 'hidden',
        boxShadow: 'var(--ml-shadow-soft)',
      }}
    >
      {/* 水墨山水（SVG） */}
      <svg
        viewBox="0 0 1200 240"
        preserveAspectRatio="none"
        aria-hidden
        style={{
          position: 'absolute',
          inset: 0,
          width: '100%',
          height: '100%',
          opacity: 0.18,
          pointerEvents: 'none',
        }}
      >
        <defs>
          <linearGradient id="mlMistFar" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#2B2118" stopOpacity="0.0" />
            <stop offset="100%" stopColor="#2B2118" stopOpacity="0.55" />
          </linearGradient>
          <linearGradient id="mlMistMid" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#1F1A17" stopOpacity="0.0" />
            <stop offset="100%" stopColor="#1F1A17" stopOpacity="0.85" />
          </linearGradient>
        </defs>
        {/* 远山 */}
        <path
          d="M0,180 C120,120 220,150 340,130 C470,110 560,160 700,140 C840,118 940,160 1080,135 C1140,124 1180,135 1200,138 L1200,240 L0,240 Z"
          fill="url(#mlMistFar)"
        />
        {/* 中山 */}
        <path
          d="M0,210 C140,170 240,200 380,180 C520,160 640,205 780,190 C920,175 1040,210 1200,195 L1200,240 L0,240 Z"
          fill="url(#mlMistMid)"
        />
        {/* 近坡 */}
        <path
          d="M0,232 C200,222 380,236 600,228 C820,220 1000,236 1200,228 L1200,240 L0,240 Z"
          fill="#1F1A17"
          opacity="0.5"
        />
      </svg>

      <div style={{ position: 'relative', zIndex: 1, display: 'flex', alignItems: 'center', gap: 16 }}>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div className="ml-title ml-title-lg">{title}</div>
          {subtitle && (
            <div
              className="ml-subtitle"
              style={{ marginTop: 6, fontSize: 14, color: 'var(--ml-text-sub)' }}
            >
              {subtitle}
            </div>
          )}
          {quote && (
            <div
              style={{
                marginTop: 8,
                fontFamily: 'var(--ml-font-serif)',
                fontSize: 13,
                color: 'var(--ml-bronze)',
                letterSpacing: 1,
                display: 'inline-flex',
                alignItems: 'center',
                gap: 8,
              }}
            >
              <span style={{ width: 18, height: 1, background: 'var(--ml-bronze)', opacity: 0.5 }} />
              {quote}
              <span style={{ width: 18, height: 1, background: 'var(--ml-bronze)', opacity: 0.5 }} />
            </div>
          )}
        </div>
        {extra && (
          <div style={{ flexShrink: 0, position: 'relative', zIndex: 2, alignSelf: 'flex-start' }}>
            {extra}
          </div>
        )}
      </div>
    </div>
  );
}
