import React, { useEffect, useState } from 'react';
import { Alert, Space, Tag } from 'antd';
import api from '../services/api';
import PageBanner from '../components/PageBanner';
import PaperCard from '../components/PaperCard';

export default function Settings() {
  const [health, setHealth] = useState(null);
  const [llm, setLlm] = useState(null);

  useEffect(() => {
    api.health().then(setHealth).catch(() => setHealth(null));
    api.llmStatus().then(setLlm).catch(() => setLlm(null));
  }, []);

  return (
    <div>
      <PageBanner
        title="设置"
        subtitle="服务状态与基础说明"
        quote="不立绝言，不构成医、法、投建议。"
      />
      <Space direction="vertical" size={16} style={{ width: '100%' }}>
        <PaperCard title="服务状态">
          <Space size="middle" wrap>
            <Tag color={health?.status === 'ok' ? 'green' : 'red'}>
              后端 {health?.status || 'unknown'}
            </Tag>
            <Tag color={health?.db_ready ? 'green' : 'red'}>
              SQLite {health?.db_ready ? '就绪' : '未就绪'}
            </Tag>
            <Tag color={llm?.available ? 'green' : 'red'}>
              AI {llm?.available ? `就绪（${llm.provider} · ${llm.model}）` : '未配置'}
            </Tag>
          </Space>
          {!llm?.available && (
            <Alert
              style={{ marginTop: 12 }}
              type="warning"
              showIcon
              message="AI 当前未配置可用 API Key"
              description={
                <span>
                  请在项目根 <code>.env</code> 中设置 DEEPSEEK_API_KEY / OPENAI_API_KEY / ANTHROPIC_API_KEY 等任一项后重启后端。
                  本系统永远不会向前端返回密钥原文。
                </span>
              }
            />
          )}
        </PaperCard>

        <PaperCard title="安全与边界">
          <ul style={{ paddingLeft: 18, color: 'var(--ml-text)', lineHeight: 1.9 }}>
            <li>不构成 <b>医疗 / 法律 / 投资 / 重大人生决策</b> 建议；涉及上述话题请咨询持证专业人士。</li>
            <li>不使用「必定 / 一定 / 注定」等绝对化措辞，避免恐吓性预言。</li>
            <li>每次回答会自动追加固定免责声明。</li>
            <li>命盘为简化算法演示；真实严谨排盘需考虑节气 / 立春 / 真太阳时。</li>
          </ul>
        </PaperCard>
      </Space>
    </div>
  );
}
