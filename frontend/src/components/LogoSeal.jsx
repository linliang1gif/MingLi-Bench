import React from 'react';

/**
 * LogoSeal —— 极简几何 logo（圆环 + 山峦 + 星点）+ MingLi AI 文字标。
 * 去中式化、不再使用朱砂红印章。
 *
 * Props：
 *   size:    整体高度像素（图形高度），默认 36
 *   compact: true 时仅显示图形，无文字
 *   theme:   'dark' (默认) 用于深色侧栏，'light' 用于浅色背景
 */
export default function LogoSeal({ size = 36, compact = false, theme = 'dark' }) {
  const isDark = theme === 'dark';
  const stroke = isDark ? '#A6BFB6' : 'var(--ml-vermilion)'; // 深底用浅竹青描线
  const dot    = isDark ? '#E0CFA6' : 'var(--ml-bronze)';    // 星点
  const sub    = isDark ? 'rgba(199, 214, 210, 0.55)' : 'var(--ml-text-sub)';
  const main   = isDark ? '#E6EFEC' : 'var(--ml-text)';

  return (
    <div
      className="ml-logo-seal"
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: 10,
        userSelect: 'none',
      }}
    >
      <svg
        width={size}
        height={size}
        viewBox="0 0 32 32"
        aria-label="MingLi AI"
        style={{ flexShrink: 0 }}
      >
        {/* 外圆环 */}
        <circle cx="16" cy="16" r="13.5" fill="none" stroke={stroke} strokeWidth="1.4" opacity="0.9" />
        {/* 远山弧线 */}
        <path
          d="M5.5 21 Q 10.5 14, 15 17 T 26.5 21"
          fill="none"
          stroke={stroke}
          strokeWidth="1.4"
          strokeLinecap="round"
          opacity="0.85"
        />
        {/* 星点 */}
        <circle cx="20.5" cy="9" r="1.6" fill={dot} />
      </svg>

      {!compact && (
        <div style={{ lineHeight: 1.1 }}>
          <div
            style={{
              fontFamily: "'Inter', -apple-system, 'PingFang SC', 'Helvetica Neue', sans-serif",
              fontSize: Math.max(15, Math.round(size * 0.46)),
              color: main,
              letterSpacing: 1.5,
              fontWeight: 600,
            }}
          >
            MingLi AI
          </div>
          <div
            style={{
              fontSize: 11,
              marginTop: 3,
              color: sub,
              letterSpacing: 1.2,
              fontFamily: 'var(--ml-font-sans)',
            }}
          >
            Personal Fortune Reading
          </div>
        </div>
      )}
    </div>
  );
}
