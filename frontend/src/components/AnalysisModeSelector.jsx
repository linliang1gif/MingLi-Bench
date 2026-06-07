import React from 'react';
import { Alert, Modal, Select, Space, Tag, Typography } from 'antd';

const { Text } = Typography;

export const ANALYSIS_MODE_OPTIONS = [
  { value: 'safe', label: '普通模式' },
  { value: 'research', label: '自用研究模式' },
];

export function analysisModeLabel(mode) {
  return mode === 'research' ? '自用研究模式' : '普通模式';
}

export function AnalysisModeTag({ mode }) {
  const isResearch = mode === 'research';
  return (
    <Tag color={isResearch ? 'volcano' : 'green'}>
      {analysisModeLabel(mode)}
    </Tag>
  );
}

export default function AnalysisModeSelector({
  value = 'safe',
  onChange,
  disabled,
  size,
  style,
  showHint = false,
}) {
  const current = value || 'safe';

  function handleChange(next) {
    if (next === 'research' && current !== 'research') {
      Modal.confirm({
        title: '切换为自用研究模式',
        content: (
          <Space direction="vertical" size={8}>
            <Text>
              自用研究模式会展示传统断语、强吉凶术语、民俗资料和流派观点。
            </Text>
            <Text type="secondary">
              内容仅供个人研究，不作为现实决策依据；不得用于恐吓、承诺结果或诱导消费。
            </Text>
          </Space>
        ),
        okText: '确认切换',
        cancelText: '取消',
        onOk: () => onChange?.('research'),
      });
      return;
    }
    onChange?.(next);
  }

  return (
    <Space direction="vertical" size={6} style={style}>
      <Select
        value={current}
        size={size}
        disabled={disabled}
        options={ANALYSIS_MODE_OPTIONS}
        onChange={handleChange}
        style={{ width: 160 }}
      />
      {showHint && current === 'research' && (
        <Alert
          type="warning"
          showIcon
          message="自用研究模式仅供个人研究，不作为现实决策依据。"
        />
      )}
    </Space>
  );
}
