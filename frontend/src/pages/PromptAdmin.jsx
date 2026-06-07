import React, { useEffect, useState } from 'react';
import { Alert, Button, Empty, Form, Input, message, Modal, Space, Switch, Table, Tag } from 'antd';
import api from '../services/api';
import AnalysisModeSelector, { AnalysisModeTag } from '../components/AnalysisModeSelector';
import PageBanner from '../components/PageBanner';
import PaperCard from '../components/PaperCard';
import MarkdownView from '../components/MarkdownView';

export default function PromptAdmin() {
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(true);
  const [initBusy, setInitBusy] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState(null);
  const [saving, setSaving] = useState(false);
  const [testModalOpen, setTestModalOpen] = useState(false);
  const [testing, setTesting] = useState(null);
  const [testBusy, setTestBusy] = useState(false);
  const [testResult, setTestResult] = useState(null);
  const [testAnalysisMode, setTestAnalysisMode] = useState('safe');
  const [form] = Form.useForm();
  const [testForm] = Form.useForm();

  function refresh() {
    setLoading(true);
    api.listPrompts()
      .then(setRows)
      .catch((e) => {
        message.error(e.message || '读取 Prompt 模板失败');
        setRows([]);
      })
      .finally(() => setLoading(false));
  }

  useEffect(refresh, []);

  async function onInit() {
    setInitBusy(true);
    try {
      const res = await api.initPrompts();
      message.success(`初始化完成，新增 ${res.inserted || 0} 条`);
      refresh();
    } catch (e) {
      message.error(e.message || '初始化失败');
    } finally {
      setInitBusy(false);
    }
  }

  function openEditor(row) {
    setEditing(row || null);
    form.setFieldsValue(row || {
      module: 'custom',
      name: '',
      version: '1.0.0',
      enabled: true,
      system_prompt: '',
      user_prompt_template: '',
      output_schema: '',
    });
    setModalOpen(true);
  }

  async function onSave() {
    const values = await form.validateFields();
    setSaving(true);
    try {
      if (editing) await api.updatePrompt(editing.id, values);
      else await api.createPrompt(values);
      message.success('已保存');
      setModalOpen(false);
      refresh();
    } catch (e) {
      message.error(e.message || '保存失败');
    } finally {
      setSaving(false);
    }
  }

  function openTester(row) {
    setTesting(row);
    setTestResult(null);
    setTestAnalysisMode('safe');
    testForm.setFieldsValue({
      input_text: '请用温和、理性的方式测试这个模板。',
      input_json: JSON.stringify({ input_json: '测试输入', question: '这个模板是否能正常输出？' }, null, 2),
    });
    setTestModalOpen(true);
  }

  async function onTestPrompt() {
    const values = await testForm.validateFields();
    let inputJson = values.input_json;
    if (inputJson && inputJson.trim()) {
      try {
        inputJson = JSON.parse(inputJson);
      } catch {
        message.error('测试 JSON 格式不正确');
        return;
      }
    } else {
      inputJson = {};
    }
    setTestBusy(true);
    try {
      setTestResult(await api.testPrompt(testing.id, {
        input_text: values.input_text || '',
        input_json: inputJson,
        analysisMode: testAnalysisMode,
      }));
    } catch (e) {
      message.error(e.message || '测试失败');
    } finally {
      setTestBusy(false);
    }
  }

  const columns = [
    { title: '模块', dataIndex: 'module', width: 150, render: (v) => <Tag color="blue">{v}</Tag> },
    { title: '名称', dataIndex: 'name', width: 220, render: (v) => <b>{v}</b> },
    { title: '版本', dataIndex: 'version', width: 100 },
    {
      title: '状态',
      dataIndex: 'enabled',
      width: 90,
      render: (v) => <Tag color={v ? 'green' : 'default'}>{v ? '启用' : '停用'}</Tag>,
    },
    {
      title: '用户模板',
      dataIndex: 'user_prompt_template',
      ellipsis: true,
    },
    {
      title: '操作',
      width: 150,
      render: (_, r) => (
        <Space>
          <Button size="small" onClick={() => openEditor(r)}>编辑</Button>
          <Button size="small" onClick={() => openTester(r)}>测试</Button>
        </Space>
      ),
    },
  ];

  return (
    <div>
      <PageBanner
        title="Prompt 管理"
        subtitle="数据库模板优先，缺失时自动回退到代码默认模板"
        quote="辞令有本，生成有据。"
        extra={
          <Space>
            <Button onClick={refresh}>刷新</Button>
            <Button onClick={() => openEditor(null)}>新增模板</Button>
            <Button type="primary" loading={initBusy} onClick={onInit}>初始化模板</Button>
          </Space>
        }
      />

      <PaperCard title="模板列表" extra={`共 ${rows.length} 个`}>
        {rows.length === 0 && !loading ? (
          <Empty description="暂无模板，点击初始化" image={Empty.PRESENTED_IMAGE_SIMPLE} />
        ) : (
          <Table
            rowKey="id"
            loading={loading}
            dataSource={rows}
            columns={columns}
            pagination={{ pageSize: 12 }}
          />
        )}
      </PaperCard>

      <Modal
        title={editing ? '编辑 Prompt 模板' : '新增 Prompt 模板'}
        open={modalOpen}
        onCancel={() => setModalOpen(false)}
        onOk={onSave}
        confirmLoading={saving}
        width={860}
        destroyOnHidden
      >
        <Form form={form} layout="vertical" preserve={false}>
          <Space style={{ width: '100%' }} size={12}>
            <Form.Item name="module" label="模块" rules={[{ required: true }]} style={{ width: 180 }}>
              <Input />
            </Form.Item>
            <Form.Item name="name" label="名称" rules={[{ required: true }]} style={{ width: 260 }}>
              <Input />
            </Form.Item>
            <Form.Item name="version" label="版本" rules={[{ required: true }]} style={{ width: 120 }}>
              <Input />
            </Form.Item>
            <Form.Item name="enabled" label="启用" valuePropName="checked" style={{ width: 80 }}>
              <Switch />
            </Form.Item>
          </Space>
          <Form.Item name="system_prompt" label="System Prompt" rules={[{ required: true }]}>
            <Input.TextArea rows={5} />
          </Form.Item>
          <Form.Item name="user_prompt_template" label="User Prompt Template" rules={[{ required: true }]}>
            <Input.TextArea rows={8} />
          </Form.Item>
          <Form.Item name="output_schema" label="输出 Schema">
            <Input.TextArea rows={3} />
          </Form.Item>
        </Form>
      </Modal>

      <Modal
        title={testing ? `测试模板 · ${testing.name}` : '测试模板'}
        open={testModalOpen}
        onCancel={() => setTestModalOpen(false)}
        onOk={onTestPrompt}
        confirmLoading={testBusy}
        width={920}
        destroyOnHidden
      >
        <Space direction="vertical" style={{ width: '100%' }} size={14}>
          <Form form={testForm} layout="vertical" preserve={false}>
            <Form.Item label="分析模式">
              <AnalysisModeSelector value={testAnalysisMode} onChange={setTestAnalysisMode} />
            </Form.Item>
            <Form.Item name="input_text" label="测试文本">
              <Input.TextArea rows={3} placeholder="输入普通测试文本" />
            </Form.Item>
            <Form.Item name="input_json" label="测试 JSON">
              <Input.TextArea rows={7} placeholder='{"question":"测试问题"}' />
            </Form.Item>
          </Form>

          {testResult && (
            <>
              <Alert
                type={(testResult.risk_check?.hits || []).length ? (testResult.analysis_mode === 'research' ? 'info' : 'warning') : 'success'}
                showIcon
                message={
                  <Space>
                    <AnalysisModeTag mode={testResult.analysis_mode || 'safe'} />
                    <span>{(testResult.risk_check?.hits || []).length ? `命中 ${testResult.risk_check?.hits?.length || 0} 个风险词` : '风控通过'}</span>
                  </Space>
                }
                description={(testResult.risk_check?.hits || [])
                  .map((h) => `${h.term}（${h.category}/${h.severity}）：${h.allowed_by_research_mode ? (h.safety_note || '研究模式允许展示') : (h.replacement_suggestion || '请改写')}`)
                  .join('；') || '未发现已启用风险词'}
              />
              <PaperCard title="原始输出">
                <MarkdownView content={testResult.raw_output} />
              </PaperCard>
              <PaperCard title="最终安全输出">
                <MarkdownView content={testResult.safe_output} />
              </PaperCard>
            </>
          )}
        </Space>
      </Modal>
    </div>
  );
}
