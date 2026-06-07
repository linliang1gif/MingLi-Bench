import React, { useEffect, useMemo, useState } from 'react';
import {
  Alert,
  Button,
  Descriptions,
  Empty,
  Form,
  Input,
  InputNumber,
  message,
  Popconfirm,
  Select,
  Space,
  Spin,
  Table,
  Tag,
} from 'antd';
import { useNavigate } from 'react-router-dom';
import api from '../services/api';
import AnalysisModeSelector from '../components/AnalysisModeSelector';
import PageBanner from '../components/PageBanner';
import PaperCard from '../components/PaperCard';

const mountains24 = [
  '子', '癸', '丑', '艮', '寅', '甲', '卯', '乙',
  '辰', '巽', '巳', '丙', '午', '丁', '未', '坤',
  '申', '庚', '酉', '辛', '戌', '乾', '亥', '壬',
];

export default function TianxingFengshui() {
  const navigate = useNavigate();
  const [form] = Form.useForm();
  const [houses, setHouses] = useState([]);
  const [mappings, setMappings] = useState([]);
  const [records, setRecords] = useState([]);
  const [loading, setLoading] = useState(true);
  const [querying, setQuerying] = useState(false);
  const [reportingId, setReportingId] = useState(null);
  const [result, setResult] = useState(null);
  const [record, setRecord] = useState(null);
  const [analysisMode, setAnalysisMode] = useState('safe');

  const houseId = Form.useWatch('house_id', form);
  const selectedHouse = useMemo(
    () => houses.find((house) => house.id === houseId),
    [houses, houseId],
  );

  function refreshRecords(nextHouseId = houseId) {
    return api.listTianxingRecords(nextHouseId ? { house_id: nextHouseId } : undefined)
      .then(setRecords)
      .catch((e) => {
        message.error(e.message || '读取天星记录失败');
        setRecords([]);
      });
  }

  useEffect(() => {
    setLoading(true);
    Promise.all([api.listHouses(), api.getTianxingMappings()])
      .then(([houseRows, mappingRes]) => {
        setHouses(houseRows);
        setMappings(mappingRes.mappings || []);
        form.setFieldsValue({
          house_id: houseRows[0]?.id,
          degree: houseRows[0]?.main_door_degree ?? 0,
          mountain_24: undefined,
        });
        return refreshRecords(houseRows[0]?.id);
      })
      .catch((e) => message.error(e.message || '读取天星资料失败'))
      .finally(() => setLoading(false));
  }, []);

  async function onQuery() {
    const values = await form.validateFields();
    if (values.degree == null && !values.mountain_24) {
      message.warning('请填写角度或选择二十四山');
      return;
    }
    setQuerying(true);
    try {
      const payload = {
        house_id: values.house_id,
        degree: values.degree,
        mountain_24: values.degree == null ? values.mountain_24 : undefined,
        note: values.note,
      };
      const res = await api.queryTianxing(payload);
      setResult(res.result);
      setRecord(res.record);
      await refreshRecords(values.house_id);
      message.success('天星映射已查询并保存');
    } catch (e) {
      message.error(e.message || '查询失败');
    } finally {
      setQuerying(false);
    }
  }

  async function onGenerateReport(recordId = record?.id) {
    if (!recordId) {
      message.warning('请先查询并保存一条天星记录');
      return;
    }
    setReportingId(recordId);
    try {
      const report = await api.generateTianxingReport({
        record_id: recordId,
        note: form.getFieldValue('note'),
        analysisMode,
      });
      message.success('天星风水报告已生成');
      navigate(`/reports/${report.report_id || report.id}`);
    } catch (e) {
      message.error(e.message || '生成报告失败');
    } finally {
      setReportingId(null);
    }
  }

  async function onDelete(recordId) {
    try {
      await api.deleteTianxingRecord(recordId);
      if (record?.id === recordId) setRecord(null);
      await refreshRecords();
      message.success('天星记录已删除');
    } catch (e) {
      message.error(e.message || '删除失败');
    }
  }

  const mapping = result?.mapping;
  const columns = [
    { title: '时间', dataIndex: 'created_at', width: 160, render: (v) => v ? String(v).replace('T', ' ').slice(0, 16) : '-' },
    { title: '山向', dataIndex: 'mountain_24', width: 90, render: (v) => <Tag color="blue">{v}</Tag> },
    { title: '角度', dataIndex: 'degree', width: 90, render: (v) => v == null ? '-' : `${v}°` },
    { title: '天星', dataIndex: 'tianxing', render: (v) => v?.tianxing || '-' },
    { title: '分组', dataIndex: 'tianxing', width: 120, render: (v) => v?.group || '-' },
    {
      title: '报告',
      dataIndex: 'report_id',
      width: 90,
      render: (v) => v ? <Button size="small" onClick={() => navigate(`/reports/${v}`)}>查看</Button> : '-',
    },
    {
      title: '操作',
      width: 170,
      render: (_, row) => (
        <Space>
          <Button size="small" loading={reportingId === row.id} onClick={() => onGenerateReport(row.id)}>
            生成报告
          </Button>
          <Popconfirm title="删除这条天星记录？" onConfirm={() => onDelete(row.id)}>
            <Button size="small" danger>删除</Button>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  const mappingColumns = [
    { title: '山', dataIndex: 'mountain_24', width: 70, render: (v) => <Tag>{v}</Tag> },
    { title: '天星', dataIndex: 'tianxing' },
    { title: '别名', dataIndex: 'aliases', render: (v) => (v || []).join('、') || '-' },
    { title: '分组', dataIndex: 'group' },
    { title: '五行', dataIndex: 'element', width: 70 },
    { title: '卦宫', dataIndex: 'trigram', width: 70 },
  ];

  if (loading) return <Spin />;

  return (
    <div>
      <PageBanner
        title="天星风水"
        subtitle="二十四山天星映射查询、资料记录与天星风水报告"
        quote="以山定名，以版本留痕。"
        extra={
          <Space>
            <Button onClick={onQuery} loading={querying}>查询天星</Button>
            <AnalysisModeSelector value={analysisMode} onChange={setAnalysisMode} />
            <Button
              type="primary"
              disabled={!record?.id}
              loading={reportingId === record?.id}
              onClick={() => onGenerateReport(record?.id)}
            >
              生成天星报告
            </Button>
          </Space>
        }
      />

      <Alert
        type="warning"
        showIcon
        style={{ marginBottom: 18 }}
        message="研究版边界"
        description="天星名称在不同罗盘、师承与文献中存在差异。V1.4 只做资料整理和古籍引用，不做墓地吉凶强断、改葬迁坟或法事化解建议。"
      />

      <div className="ml-grid cols-2" style={{ marginBottom: 18 }}>
        <PaperCard title="查询条件">
          <Form form={form} layout="vertical">
            <Form.Item name="house_id" label="关联房屋档案">
              <Select
                allowClear
                placeholder="可选"
                options={houses.map((house) => ({ value: house.id, label: house.name }))}
                onChange={(value) => {
                  const house = houses.find((item) => item.id === value);
                  if (house?.main_door_degree != null) {
                    form.setFieldsValue({ degree: house.main_door_degree, mountain_24: undefined });
                  }
                  setRecord(null);
                  setResult(null);
                  refreshRecords(value);
                }}
              />
            </Form.Item>
            <Space wrap size={14} align="start">
              <Form.Item name="degree" label="角度查询">
                <InputNumber min={0} max={360} precision={2} style={{ width: 150 }} />
              </Form.Item>
              <Form.Item name="mountain_24" label="二十四山查询">
                <Select
                  allowClear
                  style={{ width: 150 }}
                  options={mountains24.map((value) => ({ value, label: value }))}
                  onChange={(value) => {
                    if (value) form.setFieldsValue({ degree: undefined });
                  }}
                />
              </Form.Item>
            </Space>
            <Form.Item name="note" label="记录备注">
              <Input.TextArea rows={3} placeholder="可记录用途、资料来源、现场测点或待校勘事项。" />
            </Form.Item>
          </Form>
          {selectedHouse ? (
            <Alert type="info" showIcon message={`当前关联：${selectedHouse.name}`} />
          ) : (
            <Alert type="info" showIcon message="未关联房屋时也可查询天星映射。" />
          )}
        </PaperCard>

        <PaperCard title="查询结果">
          {mapping ? (
            <Space direction="vertical" size={14} style={{ width: '100%' }}>
              <Descriptions bordered size="small" column={2}>
                <Descriptions.Item label="二十四山">{mapping.mountain_24}</Descriptions.Item>
                <Descriptions.Item label="天星">{mapping.tianxing}</Descriptions.Item>
                <Descriptions.Item label="别名" span={2}>{(mapping.aliases || []).join('、') || '-'}</Descriptions.Item>
                <Descriptions.Item label="分组">{mapping.group}</Descriptions.Item>
                <Descriptions.Item label="五行">{mapping.element || '-'}</Descriptions.Item>
                <Descriptions.Item label="卦宫">{mapping.trigram || '-'}</Descriptions.Item>
                <Descriptions.Item label="角度范围">
                  {mapping.degree_range?.start}° - {mapping.degree_range?.end}°，中心 {mapping.degree_range?.center}°
                </Descriptions.Item>
              </Descriptions>
              <Alert type="info" showIcon message={mapping.variant_note} />
              {record && <Tag color="green">已保存记录 #{record.id}</Tag>}
            </Space>
          ) : (
            <Empty description="查询后显示天星映射结果" image={Empty.PRESENTED_IMAGE_SIMPLE} />
          )}
        </PaperCard>
      </div>

      <PaperCard title="二十四山天星映射表" style={{ marginBottom: 18 }}>
        <Table
          rowKey="mountain_24"
          dataSource={mappings}
          columns={mappingColumns}
          pagination={false}
          size="small"
          locale={{ emptyText: <Empty description="暂无天星映射数据" image={Empty.PRESENTED_IMAGE_SIMPLE} /> }}
        />
      </PaperCard>

      <PaperCard title="天星查询记录" extra={`共 ${records.length} 条`}>
        <Table
          rowKey="id"
          dataSource={records}
          columns={columns}
          pagination={{ pageSize: 8 }}
          locale={{ emptyText: <Empty description="暂无天星查询记录" image={Empty.PRESENTED_IMAGE_SIMPLE} /> }}
        />
      </PaperCard>
    </div>
  );
}
