import React, { useEffect, useState, useCallback } from 'react';
import {
  Table, Card, Tag, Button, Modal, Form, Input, Select, Rate, Space,
  Descriptions, Statistic, Row, Col, message, Spin, Typography, Radio,
} from 'antd';
import { CheckCircleOutlined, CloseCircleOutlined, QuestionCircleOutlined } from '@ant-design/icons';
import api from '../services/api';

const { Text, Title } = Typography;
const { TextArea } = Input;

const STRENGTH_OPTIONS = ['身强', '偏强', '中和', '偏弱', '身弱', '疑似从强', '疑似从弱'];
const AGREE_OPTIONS = [
  { label: '同意', value: 'agree' },
  { label: '不同意', value: 'disagree' },
  { label: '不确定', value: 'unsure' },
];

export default function CaseReview() {
  const [cases, setCases] = useState([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [page, setPage] = useState(1);
  const [filters, setFilters] = useState({});
  const [detailVisible, setDetailVisible] = useState(false);
  const [detail, setDetail] = useState(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [feedbackVisible, setFeedbackVisible] = useState(false);
  const [feedbackCaseId, setFeedbackCaseId] = useState(null);
  const [summary, setSummary] = useState(null);
  const [form] = Form.useForm();

  const loadCases = useCallback(async () => {
    setLoading(true);
    try {
      const res = await api.listCases({ ...filters, page, page_size: 15 });
      setCases(res.items || []);
      setTotal(res.total || 0);
    } catch (e) {
      message.error('加载案例失败');
    }
    setLoading(false);
  }, [filters, page]);

  const loadSummary = useCallback(async () => {
    try {
      const res = await api.feedbackSummary();
      setSummary(res);
    } catch { /* ignore */ }
  }, []);

  useEffect(() => { loadCases(); }, [loadCases]);
  useEffect(() => { loadSummary(); }, [loadSummary]);

  const openDetail = async (caseId) => {
    setDetailLoading(true);
    setDetailVisible(true);
    try {
      const res = await api.getCaseDetail(caseId);
      setDetail(res);
    } catch {
      message.error('加载详情失败');
    }
    setDetailLoading(false);
  };

  const openFeedback = (caseId) => {
    setFeedbackCaseId(caseId);
    setFeedbackVisible(true);
    form.resetFields();
  };

  const submitFeedback = async () => {
    try {
      const vals = await form.validateFields();
      await api.submitFeedback(feedbackCaseId, vals);
      message.success('反馈已提交');
      setFeedbackVisible(false);
      loadSummary();
    } catch (e) {
      if (e.errorFields) return;
      message.error('提交失败: ' + (e.message || '未知错误'));
    }
  };

  const strengthColor = (s) => {
    if (!s) return 'default';
    if (s.includes('强')) return 'volcano';
    if (s.includes('弱') || s.includes('从弱')) return 'blue';
    if (s === '中和') return 'green';
    return 'default';
  };

  const columns = [
    { title: 'ID', dataIndex: 'case_id', width: 90 },
    { title: '标题', dataIndex: 'title', ellipsis: true },
    { title: '日主', dataIndex: 'day_master', width: 60, align: 'center' },
    {
      title: '旺衰', dataIndex: 'primary_strength', width: 100, align: 'center',
      render: (v) => <Tag color={strengthColor(v)}>{v}</Tag>,
    },
    {
      title: '格局', dataIndex: 'primary_pattern', width: 100, align: 'center',
      render: (v) => <Tag>{v}</Tag>,
    },
    {
      title: '来源', dataIndex: 'source', width: 100,
      render: (v) => v === 'manual'
        ? <Tag color="green">人工</Tag>
        : <Tag color="orange">自动</Tag>,
    },
    {
      title: '操作', width: 160, align: 'center',
      render: (_, r) => (
        <Space>
          <Button size="small" onClick={() => openDetail(r.case_id)}>详情</Button>
          <Button size="small" type="primary" onClick={() => openFeedback(r.case_id)}>审核</Button>
        </Space>
      ),
    },
  ];

  return (
    <div style={{ padding: 0 }}>
      <Title level={4} style={{ marginBottom: 16 }}>案例审核与反馈</Title>

      {/* 统计卡片 */}
      {summary && (
        <Row gutter={16} style={{ marginBottom: 16 }}>
          <Col span={4}>
            <Card size="small"><Statistic title="总案例" value={total} /></Card>
          </Col>
          <Col span={4}>
            <Card size="small"><Statistic title="总反馈" value={summary.total_feedbacks} /></Card>
          </Col>
          <Col span={5}>
            <Card size="small">
              <Statistic
                title="旺衰认同率"
                value={summary.strength_agreement?.rate || 0}
                suffix="%"
                valueStyle={{ color: (summary.strength_agreement?.rate || 0) >= 80 ? '#3f8600' : '#cf1322' }}
              />
            </Card>
          </Col>
          <Col span={5}>
            <Card size="small">
              <Statistic
                title="格局认同率"
                value={summary.pattern_agreement?.rate || 0}
                suffix="%"
                valueStyle={{ color: (summary.pattern_agreement?.rate || 0) >= 80 ? '#3f8600' : '#cf1322' }}
              />
            </Card>
          </Col>
          <Col span={3}>
            <Card size="small">
              <Statistic title="待修正" value={summary.cases_needing_correction_count || 0} valueStyle={{ color: '#cf1322' }} />
            </Card>
          </Col>
          <Col span={3}>
            <Card size="small">
              <Statistic title="平均评分" value={summary.average_overall_score || '-'} suffix="/ 5" />
            </Card>
          </Col>
        </Row>
      )}

      {/* 过滤器 */}
      <Space style={{ marginBottom: 12 }}>
        <Select
          allowClear placeholder="日主" style={{ width: 80 }}
          options={'甲乙丙丁戊己庚辛壬癸'.split('').map(g => ({ value: g, label: g }))}
          onChange={(v) => { setFilters(f => ({ ...f, day_master: v })); setPage(1); }}
        />
        <Select
          allowClear placeholder="旺衰" style={{ width: 120 }}
          options={STRENGTH_OPTIONS.map(s => ({ value: s, label: s }))}
          onChange={(v) => { setFilters(f => ({ ...f, strength: v })); setPage(1); }}
        />
        <Select
          allowClear placeholder="来源" style={{ width: 100 }}
          options={[{ value: 'manual', label: '人工' }, { value: 'auto_generated', label: '自动' }]}
          onChange={(v) => { setFilters(f => ({ ...f, source: v })); setPage(1); }}
        />
      </Space>

      <Table
        dataSource={cases}
        columns={columns}
        rowKey="case_id"
        loading={loading}
        size="small"
        pagination={{
          current: page,
          pageSize: 15,
          total,
          onChange: (p) => setPage(p),
          showTotal: (t) => `共 ${t} 例`,
        }}
      />

      {/* 案例详情弹窗 */}
      <Modal
        title={detail?.case?.title || '案例详情'}
        open={detailVisible}
        onCancel={() => setDetailVisible(false)}
        footer={null}
        width={700}
      >
        {detailLoading ? <Spin /> : detail && (
          <div>
            <Descriptions bordered size="small" column={2}>
              <Descriptions.Item label="案例ID">{detail.case.case_id}</Descriptions.Item>
              <Descriptions.Item label="来源">{detail.case.source}</Descriptions.Item>
              <Descriptions.Item label="出生日期">{detail.case.input?.birth_date}</Descriptions.Item>
              <Descriptions.Item label="出生时辰">{detail.case.input?.birth_time}</Descriptions.Item>
              <Descriptions.Item label="日主" span={2}>
                <Tag color="blue" style={{ fontSize: 16 }}>{detail.case.expected?.day_master}</Tag>
              </Descriptions.Item>
            </Descriptions>

            <Title level={5} style={{ marginTop: 16 }}>四柱</Title>
            <Space size="large">
              {['year', 'month', 'day', 'hour'].map(k => {
                const p = detail.chart_pillars?.[k] || {};
                return (
                  <Card key={k} size="small" style={{ textAlign: 'center', width: 80 }}>
                    <div style={{ fontSize: 12, color: '#999' }}>{k === 'year' ? '年柱' : k === 'month' ? '月柱' : k === 'day' ? '日柱' : '时柱'}</div>
                    <div style={{ fontSize: 20, fontWeight: 'bold' }}>{p.stem}{p.branch}</div>
                  </Card>
                );
              })}
            </Space>

            <Title level={5} style={{ marginTop: 16 }}>规则引擎分析</Title>
            <Descriptions bordered size="small" column={1}>
              <Descriptions.Item label="旺衰">
                <Tag color={strengthColor(detail.rule_analysis?.strength?.strength_level)}>
                  {detail.rule_analysis?.strength?.strength_level}
                </Tag>
                <Text type="secondary"> (score: {detail.rule_analysis?.strength?.score})</Text>
              </Descriptions.Item>
              <Descriptions.Item label="格局">
                <Tag>{detail.rule_analysis?.pattern?.pattern}</Tag>
              </Descriptions.Item>
              <Descriptions.Item label="喜用神">
                {(detail.rule_analysis?.useful_gods?.final_suggestion?.useful || []).map(u =>
                  <Tag key={u} color="green">{u}</Tag>
                )}
              </Descriptions.Item>
              <Descriptions.Item label="忌避">
                {(detail.rule_analysis?.useful_gods?.final_suggestion?.avoid || []).map(u =>
                  <Tag key={u} color="red">{u}</Tag>
                )}
              </Descriptions.Item>
            </Descriptions>

            <Title level={5} style={{ marginTop: 16 }}>标注 (expected)</Title>
            <Descriptions bordered size="small" column={1}>
              <Descriptions.Item label="主旺衰">
                {detail.case.expected?.primary_strength_level}
              </Descriptions.Item>
              <Descriptions.Item label="可接受旺衰">
                {(detail.case.expected?.accepted_strength_levels || []).join(', ')}
              </Descriptions.Item>
              <Descriptions.Item label="主格局">
                {detail.case.expected?.primary_pattern}
              </Descriptions.Item>
              <Descriptions.Item label="争议说明">
                {(detail.case.expected?.dispute_notes || []).map((n, i) =>
                  <div key={i}><Text type="secondary">{n}</Text></div>
                )}
              </Descriptions.Item>
            </Descriptions>

            <div style={{ marginTop: 16, textAlign: 'right' }}>
              <Button type="primary" onClick={() => { setDetailVisible(false); openFeedback(detail.case.case_id); }}>
                提交审核意见
              </Button>
            </div>
          </div>
        )}
      </Modal>

      {/* 反馈表单弹窗 */}
      <Modal
        title={`审核案例 ${feedbackCaseId}`}
        open={feedbackVisible}
        onCancel={() => setFeedbackVisible(false)}
        onOk={submitFeedback}
        okText="提交"
        cancelText="取消"
        width={520}
      >
        <Form form={form} layout="vertical" initialValues={{ reviewer_role: 'user' }}>
          <Form.Item name="reviewer" label="审核人" rules={[{ required: true, message: '请输入姓名' }]}>
            <Input placeholder="您的姓名或标识" />
          </Form.Item>
          <Form.Item name="reviewer_role" label="身份">
            <Select options={[
              { value: 'user', label: '普通用户' },
              { value: 'expert', label: '命理爱好者' },
              { value: 'master', label: '命理师' },
            ]} />
          </Form.Item>

          <Form.Item name="strength_agree" label="旺衰判定是否同意">
            <Radio.Group options={AGREE_OPTIONS} />
          </Form.Item>
          <Form.Item name="strength_suggestion" label="建议旺衰级别（如不同意）">
            <Select allowClear placeholder="选择" options={STRENGTH_OPTIONS.map(s => ({ value: s, label: s }))} />
          </Form.Item>

          <Form.Item name="pattern_agree" label="格局判定是否同意">
            <Radio.Group options={AGREE_OPTIONS} />
          </Form.Item>
          <Form.Item name="pattern_suggestion" label="建议格局名（如不同意）">
            <Input placeholder="如：正官格、七杀格..." />
          </Form.Item>

          <Form.Item name="useful_gods_agree" label="喜用神是否同意">
            <Radio.Group options={AGREE_OPTIONS} />
          </Form.Item>
          <Form.Item name="useful_gods_note" label="喜用神修正说明">
            <TextArea rows={2} placeholder="如有不同意见请说明" />
          </Form.Item>

          <Form.Item name="overall_score" label="整体评分">
            <Rate />
          </Form.Item>
          <Form.Item name="comment" label="补充评论">
            <TextArea rows={3} placeholder="任何补充意见..." />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
