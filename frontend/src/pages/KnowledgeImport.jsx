import React, { useEffect, useMemo, useState } from 'react';
import { Alert, App as AntdApp, Button, Descriptions, Empty, Form, Input, Select, Space, Spin, Table, Tag } from 'antd';
import dayjs from 'dayjs';
import utc from 'dayjs/plugin/utc';
import api from '../services/api';
import PageBanner from '../components/PageBanner';
import PaperCard from '../components/PaperCard';

dayjs.extend(utc);

const fmtLocal = (ts) => ts ? dayjs.utc(ts).local().format('YYYY-MM-DD HH:mm') : '—';

const STRATEGIES = [
  { value: 'skip', label: 'skip 跳过同名书' },
  { value: 'overwrite', label: 'overwrite 覆盖同名书' },
  { value: 'append', label: 'append 追加片段' },
];

export default function KnowledgeImport() {
  const { message } = AntdApp.useApp();
  const [singleForm] = Form.useForm();
  const [folderForm] = Form.useForm();
  const [busy, setBusy] = useState(false);
  const [logsLoading, setLogsLoading] = useState(false);
  const [sampleLoading, setSampleLoading] = useState(false);
  const [qualityLoading, setQualityLoading] = useState(false);
  const [logs, setLogs] = useState([]);
  const [sample, setSample] = useState(null);
  const [quality, setQuality] = useState(null);
  const [result, setResult] = useState(null);
  const [error, setError] = useState('');

  async function loadLogs() {
    setLogsLoading(true);
    try {
      setLogs(await api.getKnowledgeImportLogs({ limit: 50 }));
    } catch (e) {
      message.error(e.message || '读取导入日志失败');
      setLogs([]);
    } finally {
      setLogsLoading(false);
    }
  }

  async function loadSample() {
    setSampleLoading(true);
    try {
      setSample(await api.getKnowledgeImportSampleFormat());
    } catch (e) {
      message.error(e.message || '读取示例格式失败');
      setSample(null);
    } finally {
      setSampleLoading(false);
    }
  }

  async function loadQuality() {
    setQualityLoading(true);
    try {
      setQuality(await api.getKnowledgeQualityCheck());
    } catch (e) {
      message.error(e.message || '读取质量检查失败');
      setQuality(null);
    } finally {
      setQualityLoading(false);
    }
  }

  useEffect(() => {
    singleForm.setFieldsValue({
      file_path: 'backend/data/books_p0/01_zhouyi.json',
      duplicate_strategy: 'skip',
    });
    folderForm.setFieldsValue({
      folder_path: 'backend/data/books_p0',
      duplicate_strategy: 'skip',
    });
    loadLogs();
    loadSample();
    loadQuality();
  }, []);

  async function runImport(type) {
    setBusy(true);
    setError('');
    try {
      const values = type === 'single'
        ? await singleForm.validateFields()
        : await folderForm.validateFields();
      const res = type === 'single'
        ? await api.importKnowledgeBookJson(values)
        : await api.importKnowledgeFolder(values);
      setResult(res);
      message.success('导入任务已完成');
      loadLogs();
      loadQuality();
    } catch (e) {
      const msg = e.message || '导入失败';
      setError(msg);
      message.error(msg);
    } finally {
      setBusy(false);
    }
  }

  const logColumns = [
    { title: '时间', dataIndex: 'created_at', width: 150, render: fmtLocal },
    { title: '类型', dataIndex: 'import_type', width: 120, render: (v) => <Tag>{v}</Tag> },
    { title: '策略', dataIndex: 'duplicate_strategy', width: 120 },
    { title: '状态', dataIndex: 'status', width: 120, render: (v) => <Tag color={v === 'success' ? 'green' : v === 'partial_success' ? 'orange' : 'red'}>{v}</Tag> },
    { title: '总书籍', dataIndex: 'books_total', width: 80 },
    { title: '新增', dataIndex: 'books_inserted', width: 80 },
    { title: '跳过', dataIndex: 'books_skipped', width: 80 },
    { title: '片段', dataIndex: 'chunks_inserted', width: 80 },
    { title: '路径', dataIndex: 'file_path', ellipsis: true, render: (_, r) => r.file_path || r.folder_path || '—' },
    { title: '错误', dataIndex: 'error_message', ellipsis: true, render: (v) => v || '—' },
  ];

  const reportCoverage = useMemo(() => (
    Object.values(quality?.by_report_type || {}).sort((a, b) => a.report_type.localeCompare(b.report_type))
  ), [quality]);

  const categoryRows = useMemo(() => (
    (quality?.by_category || []).slice().sort((a, b) => a.category_code.localeCompare(b.category_code))
  ), [quality]);

  const categoryColumns = [
    { title: '类目', dataIndex: 'category_code', width: 90 },
    { title: '书籍', dataIndex: 'books_count', width: 80 },
    { title: '分片', dataIndex: 'chunks_count', width: 80 },
    {
      title: '样例书籍',
      dataIndex: 'sample_books',
      ellipsis: true,
      render: (books) => (books || []).map((b) => b.title).join('、') || '—',
    },
  ];

  const reportColumns = [
    { title: '报告类型', dataIndex: 'report_type', width: 210 },
    { title: '覆盖分片', dataIndex: 'chunks_count', width: 90 },
    { title: '模块命中', dataIndex: 'exact_module_chunks_count', width: 90 },
    { title: '类目命中', dataIndex: 'mapped_category_chunks_count', width: 90 },
    { title: '书籍', dataIndex: 'books_count', width: 80 },
    {
      title: '映射类目',
      dataIndex: 'mapped_categories',
      width: 160,
      render: (items) => (items || []).join('、') || '—',
    },
    {
      title: '样例书籍',
      dataIndex: 'sample_books',
      ellipsis: true,
      render: (books) => (books || []).map((b) => b.title).join('、') || '—',
    },
  ];

  return (
    <div>
      <PageBanner
        title="古籍导入"
        subtitle="标准 JSON 古籍单本导入、目录批量导入与导入日志"
        quote="先定格式，再入典籍。"
        extra={
          <Space>
            <Button onClick={loadQuality}>刷新质量检查</Button>
            <Button onClick={loadLogs}>刷新日志</Button>
          </Space>
        }
      />

      {error ? <Alert type="error" showIcon message={error} style={{ marginBottom: 18 }} /> : null}

      <Space direction="vertical" size={18} style={{ width: '100%' }}>
        <PaperCard title="单本 JSON 导入">
          <Form form={singleForm} layout="inline">
            <Form.Item name="file_path" rules={[{ required: true, message: '请输入 JSON 文件路径' }]} style={{ minWidth: 420 }}>
              <Input placeholder="backend/data/books_p0/01_zhouyi.json" />
            </Form.Item>
            <Form.Item name="duplicate_strategy" rules={[{ required: true }]} style={{ minWidth: 190 }}>
              <Select options={STRATEGIES} />
            </Form.Item>
            <Button type="primary" loading={busy} onClick={() => runImport('single')}>导入单本</Button>
          </Form>
        </PaperCard>

        <PaperCard title="知识库质量检查">
          {qualityLoading ? (
            <div style={{ display: 'flex', justifyContent: 'center', padding: 28 }}><Spin /></div>
          ) : !quality ? (
            <Empty description="暂无质量检查结果" image={Empty.PRESENTED_IMAGE_SIMPLE} />
          ) : (
            <Space direction="vertical" size={16} style={{ width: '100%' }}>
              <Descriptions bordered size="small" column={4}>
                <Descriptions.Item label="书籍数">{quality.books_count}</Descriptions.Item>
                <Descriptions.Item label="分片数">{quality.chunks_count}</Descriptions.Item>
                <Descriptions.Item label="空原文分片">{quality.empty_chunks_count}</Descriptions.Item>
                <Descriptions.Item label="字段不完整分片">{quality.incomplete_chunks_count}</Descriptions.Item>
                <Descriptions.Item label="缺失报告类型" span={2}>
                  {(quality.missing_report_types || []).length ? (
                    <Space wrap>
                      {quality.missing_report_types.map((item) => <Tag color="red" key={item}>{item}</Tag>)}
                    </Space>
                  ) : <Tag color="green">覆盖充足</Tag>}
                </Descriptions.Item>
                <Descriptions.Item label="重复书籍" span={2}>
                  {(quality.duplicate_books || []).length ? (
                    <Space wrap>
                      {quality.duplicate_books.map((item) => <Tag color="orange" key={item.title}>{item.title} x{item.count}</Tag>)}
                    </Space>
                  ) : <Tag color="green">无重复</Tag>}
                </Descriptions.Item>
                <Descriptions.Item label="低覆盖类目" span={4}>
                  {(quality.low_coverage_categories || []).length ? (
                    <Space wrap>
                      {quality.low_coverage_categories.map((item) => (
                        <Tag color="orange" key={item.category_code}>{item.category_code}：{item.chunks_count}</Tag>
                      ))}
                    </Space>
                  ) : <Tag color="green">覆盖充足</Tag>}
                </Descriptions.Item>
              </Descriptions>

              <Table
                title={() => '按报告类型覆盖'}
                rowKey="report_type"
                size="small"
                dataSource={reportCoverage}
                columns={reportColumns}
                pagination={{ pageSize: 6 }}
                locale={{ emptyText: <Empty description="暂无报告类型覆盖数据" image={Empty.PRESENTED_IMAGE_SIMPLE} /> }}
              />

              <Table
                title={() => '按分类统计'}
                rowKey="category_code"
                size="small"
                dataSource={categoryRows}
                columns={categoryColumns}
                pagination={{ pageSize: 8 }}
                locale={{ emptyText: <Empty description="暂无分类统计" image={Empty.PRESENTED_IMAGE_SIMPLE} /> }}
              />
            </Space>
          )}
        </PaperCard>

        <PaperCard title="目录批量导入">
          <Form form={folderForm} layout="inline">
            <Form.Item name="folder_path" rules={[{ required: true, message: '请输入目录路径' }]} style={{ minWidth: 420 }}>
              <Input placeholder="backend/data/books_p0" />
            </Form.Item>
            <Form.Item name="duplicate_strategy" rules={[{ required: true }]} style={{ minWidth: 190 }}>
              <Select options={STRATEGIES} />
            </Form.Item>
            <Button type="primary" loading={busy} onClick={() => runImport('folder')}>批量导入</Button>
          </Form>
        </PaperCard>

        <PaperCard title="导入结果">
          {!result ? (
            <Empty description="尚未执行导入" image={Empty.PRESENTED_IMAGE_SIMPLE} />
          ) : (
            <Descriptions bordered size="small" column={4}>
              <Descriptions.Item label="状态">{result.ok ? '完成' : '部分完成'}</Descriptions.Item>
              <Descriptions.Item label="总书籍">{result.books_total ?? '—'}</Descriptions.Item>
              <Descriptions.Item label="新增书籍">{result.books_inserted ?? 0}</Descriptions.Item>
              <Descriptions.Item label="跳过书籍">{result.books_skipped ?? 0}</Descriptions.Item>
              <Descriptions.Item label="新增片段">{result.chunks_inserted ?? 0}</Descriptions.Item>
              <Descriptions.Item label="日志状态">{result.log?.status || '—'}</Descriptions.Item>
              <Descriptions.Item label="错误" span={2}>{(result.errors || []).join('；') || result.log?.error_message || '—'}</Descriptions.Item>
            </Descriptions>
          )}
        </PaperCard>

        <PaperCard title="导入日志" extra={`共 ${logs.length} 条`}>
          {logsLoading ? (
            <div style={{ display: 'flex', justifyContent: 'center', padding: 28 }}><Spin /></div>
          ) : logs.length === 0 ? (
            <Empty description="暂无导入日志" image={Empty.PRESENTED_IMAGE_SIMPLE} />
          ) : (
            <Table rowKey="id" size="small" dataSource={logs} columns={logColumns} pagination={{ pageSize: 8 }} />
          )}
        </PaperCard>

        <PaperCard title="示例 JSON 格式">
          {sampleLoading ? (
            <Spin />
          ) : sample ? (
            <Input.TextArea
              readOnly
              rows={18}
              value={JSON.stringify(sample, null, 2)}
              style={{ fontFamily: 'Consolas, monospace' }}
            />
          ) : (
            <Empty description="暂无示例格式" image={Empty.PRESENTED_IMAGE_SIMPLE} />
          )}
        </PaperCard>
      </Space>
    </div>
  );
}
