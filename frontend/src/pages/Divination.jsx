import React, { useState } from 'react';
import { Alert, Button, Form, Input, InputNumber, message, Space, Tabs, Tag } from 'antd';
import api from '../services/api';
import AnalysisModeSelector, { AnalysisModeTag } from '../components/AnalysisModeSelector';
import PageBanner from '../components/PageBanner';
import PaperCard from '../components/PaperCard';
import MarkdownView from '../components/MarkdownView';

export default function Divination() {
  const [wordForm] = Form.useForm();
  const [lotteryForm] = Form.useForm();
  const [result, setResult] = useState(null);
  const [busy, setBusy] = useState(false);
  const [analysisMode, setAnalysisMode] = useState('safe');

  async function runWord() {
    const values = await wordForm.validateFields();
    setBusy(true);
    try {
      setResult(await api.wordDivination({ ...values, analysisMode }));
    } catch (e) {
      message.error(e.message || '测字失败');
    } finally {
      setBusy(false);
    }
  }

  async function runLottery() {
    const values = await lotteryForm.validateFields();
    setBusy(true);
    try {
      setResult(await api.lotteryDivination({ ...values, analysisMode }));
    } catch (e) {
      message.error(e.message || '抽签失败');
    } finally {
      setBusy(false);
    }
  }

  return (
    <div>
      <PageBanner title="测字灵签" subtitle="测字与灵签，只作娱乐和传统文化参考" quote="借象观心，不作强断。" />
      <PaperCard title="工具输入" style={{ marginBottom: 18 }}>
        <div style={{ marginBottom: 12 }}>
          <AnalysisModeSelector value={analysisMode} onChange={setAnalysisMode} />
        </div>
        <Tabs
          items={[
            {
              key: 'word',
              label: '测字',
              children: (
                <Form form={wordForm} layout="vertical" initialValues={{ word: '易', question: '这个项目适不适合继续做？', context: 'AI易学传统文化平台' }}>
                  <Form.Item name="word" label="字" rules={[{ required: true }]}><Input style={{ width: 160 }} /></Form.Item>
                  <Form.Item name="question" label="问题" rules={[{ required: true }]}><Input /></Form.Item>
                  <Form.Item name="context" label="背景"><Input.TextArea rows={3} /></Form.Item>
                  <Button type="primary" loading={busy} onClick={runWord}>开始测字</Button>
                </Form>
              ),
            },
            {
              key: 'lottery',
              label: '灵签',
              children: (
                <Form form={lotteryForm} layout="vertical" initialValues={{ question: '这个项目适不适合继续做？' }}>
                  <Form.Item name="question" label="问题" rules={[{ required: true }]}><Input /></Form.Item>
                  <Form.Item name="sign_no" label="签号"><InputNumber min={1} max={100} placeholder="留空随机" style={{ width: 180 }} /></Form.Item>
                  <Button type="primary" loading={busy} onClick={runLottery}>抽签解读</Button>
                </Form>
              ),
            },
          ]}
        />
      </PaperCard>

      {result && (
        <PaperCard title="解读结果" extra={result.record_id ? `记录 #${result.record_id}` : undefined}>
          <Space wrap style={{ marginBottom: 12 }}>
            <AnalysisModeTag mode={result.analysis_mode || analysisMode} />
            {result.word && <Tag color="blue">测字：{result.word}</Tag>}
            {result.sign_no && <Tag color="gold">第 {result.sign_no} 签</Tag>}
            {result.level && <Tag color="green">{result.level}</Tag>}
          </Space>
          {result.risk_check_result && (result.risk_check_result.hits || []).length > 0 && (
            <Alert
              type={result.analysis_mode === 'research' ? 'info' : 'warning'}
              showIcon
              message={result.analysis_mode === 'research' ? '研究模式风险词记录' : '输出命中风险词'}
              style={{ marginBottom: 12 }}
            />
          )}
          <MarkdownView content={result.markdown} />
        </PaperCard>
      )}
    </div>
  );
}
