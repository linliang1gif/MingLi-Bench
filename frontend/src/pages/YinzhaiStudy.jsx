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
import LocationPicker from '../components/LocationPicker';
import PageBanner from '../components/PageBanner';
import PaperCard from '../components/PaperCard';

const siteTypes = [
  { value: 'study_case', label: '研究案例' },
  { value: 'ancestral_grave', label: '祖坟资料' },
  { value: 'cemetery', label: '墓园环境' },
  { value: 'memorial_site', label: '纪念空间' },
  { value: 'other', label: '其他' },
];

function siteTypeLabel(value) {
  return siteTypes.find((item) => item.value === value)?.label || value || '未标注';
}

function toObservation(values, key) {
  return {
    summary: values[`${key}_summary`] || '',
    note: values[`${key}_note`] || '',
  };
}

export default function YinzhaiStudy() {
  const navigate = useNavigate();
  const [form] = Form.useForm();
  const [houses, setHouses] = useState([]);
  const [records, setRecords] = useState([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [reportingId, setReportingId] = useState(null);
  const [currentRecord, setCurrentRecord] = useState(null);
  const [analysisMode, setAnalysisMode] = useState('safe');

  const houseId = Form.useWatch('house_id', form);
  const selectedHouse = useMemo(
    () => houses.find((house) => house.id === houseId),
    [houses, houseId],
  );

  function refreshRecords(nextHouseId = houseId) {
    return api.listYinzhaiRecords(nextHouseId ? { house_id: nextHouseId } : undefined)
      .then(setRecords)
      .catch((e) => {
        message.error(e.message || '读取阴宅研究记录失败');
        setRecords([]);
      });
  }

  useEffect(() => {
    setLoading(true);
    api.listHouses()
      .then((rows) => {
        setHouses(rows);
        form.setFieldsValue({
          house_id: rows[0]?.id,
          title: '阴宅研究记录',
          site_type: 'study_case',
        });
        return refreshRecords(rows[0]?.id);
      })
      .catch((e) => message.error(e.message || '读取房屋档案失败'))
      .finally(() => setLoading(false));
  }, []);

  async function onSave() {
    const values = await form.validateFields();
    setSaving(true);
    try {
      const payload = {
        house_id: values.house_id,
        title: values.title,
        site_type: values.site_type,
        location_note: values.location_note,
        latitude: values.latitude,
        longitude: values.longitude,
        mountain_degree: values.mountain_degree,
        facing_degree: values.facing_degree,
        dragon: toObservation(values, 'dragon'),
        cave: toObservation(values, 'cave'),
        sand: toObservation(values, 'sand'),
        water: toObservation(values, 'water'),
        direction: toObservation(values, 'direction'),
        environment: toObservation(values, 'environment'),
        research_note: values.research_note,
      };
      const record = await api.createYinzhaiRecord(payload);
      setCurrentRecord(record);
      await refreshRecords(values.house_id);
      message.success('阴宅研究记录已保存');
    } catch (e) {
      message.error(e.message || '保存失败');
    } finally {
      setSaving(false);
    }
  }

  async function onGenerateReport(recordId) {
    if (!recordId) {
      message.warning('请先保存研究记录');
      return;
    }
    setReportingId(recordId);
    try {
      const report = await api.generateYinzhaiReport(recordId, analysisMode);
      message.success('阴宅研究报告已生成');
      navigate(`/reports/${report.report_id || report.id}`);
    } catch (e) {
      message.error(e.message || '生成报告失败');
    } finally {
      setReportingId(null);
    }
  }

  async function onDelete(recordId) {
    try {
      await api.deleteYinzhaiRecord(recordId);
      if (currentRecord?.id === recordId) setCurrentRecord(null);
      await refreshRecords();
      message.success('研究记录已删除');
    } catch (e) {
      message.error(e.message || '删除失败');
    }
  }

  const columns = [
    { title: '时间', dataIndex: 'created_at', width: 160, render: (v) => v ? String(v).replace('T', ' ').slice(0, 16) : '-' },
    { title: '标题', dataIndex: 'title', ellipsis: true },
    { title: '类型', dataIndex: 'site_type', width: 120, render: (v) => <Tag color="blue">{siteTypeLabel(v)}</Tag> },
    {
      title: '位置',
      width: 150,
      render: (_, r) => (
        r.latitude != null && r.longitude != null
          ? `${Number(r.latitude).toFixed(5)}, ${Number(r.longitude).toFixed(5)}`
          : '-'
      ),
    },
    { title: '坐山', dataIndex: 'mountain_direction_24', width: 90, render: (v, r) => v ? `${v} ${r.mountain_degree ?? ''}°` : '-' },
    { title: '向首', dataIndex: 'facing_direction_24', width: 90, render: (v, r) => v ? `${v} ${r.facing_degree ?? ''}°` : '-' },
    {
      title: '报告',
      dataIndex: 'report_id',
      width: 90,
      render: (v) => v ? <Button size="small" onClick={() => navigate(`/reports/${v}`)}>查看</Button> : '-',
    },
    {
      title: '操作',
      width: 170,
      render: (_, record) => (
        <Space>
          <Button size="small" loading={reportingId === record.id} onClick={() => onGenerateReport(record.id)}>
            生成报告
          </Button>
          <Popconfirm title="删除这条研究记录？" onConfirm={() => onDelete(record.id)}>
            <Button size="small" danger>删除</Button>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  if (loading) return <Spin />;

  return (
    <div>
      <PageBanner
        title="阴宅研究"
        subtitle="龙穴砂水向资料记录、罗盘坐向整理与阴宅研究报告"
        quote="以资料为据，以边界为先。"
        extra={
          <Space>
            <Button onClick={onSave} loading={saving}>保存研究记录</Button>
            <AnalysisModeSelector value={analysisMode} onChange={setAnalysisMode} />
            <Button
              type="primary"
              disabled={!currentRecord?.id}
              loading={reportingId === currentRecord?.id}
              onClick={() => onGenerateReport(currentRecord?.id)}
            >
              生成阴宅研究报告
            </Button>
          </Space>
        }
      />

      <Alert
        type="warning"
        showIcon
        style={{ marginBottom: 18 }}
        message="安全边界"
        description="本功能仅做传统文化研究、堪舆资料整理和环境记录，不做墓地吉凶强断，不提供改葬、迁坟、法事化解或诱导消费建议。"
      />

      <div className="ml-grid cols-2" style={{ marginBottom: 18 }}>
        <PaperCard title="研究对象">
          <Form form={form} layout="vertical">
            <Form.Item name="house_id" label="关联房屋档案">
              <Select
                allowClear
                placeholder="可选"
                options={houses.map((house) => ({ value: house.id, label: house.name }))}
                onChange={(value) => {
                  setCurrentRecord(null);
                  refreshRecords(value);
                }}
              />
            </Form.Item>
            <Form.Item name="title" label="记录标题" rules={[{ required: true, message: '请填写标题' }]}>
              <Input placeholder="例如：某墓园环境研究记录" />
            </Form.Item>
            <Form.Item name="site_type" label="研究类型" rules={[{ required: true }]}>
              <Select options={siteTypes} />
            </Form.Item>
            <Space wrap size={14}>
              <Form.Item name="mountain_degree" label="坐山角度">
                <InputNumber min={0} max={360} precision={2} style={{ width: 140 }} />
              </Form.Item>
              <Form.Item name="facing_degree" label="向首角度">
                <InputNumber min={0} max={360} precision={2} style={{ width: 140 }} />
              </Form.Item>
            </Space>
            <LocationPicker
              form={form}
              title="现场位置记录"
              description="可在地图上记录研究对象的现场位置，用于资料归档和报告版本追溯。"
              notePlaceholder="记录公开可描述的区域、周边环境或资料来源，不填写敏感隐私地址也可以。"
            />
          </Form>
          {selectedHouse ? (
            <Alert type="info" showIcon message={`当前关联：${selectedHouse.name}`} />
          ) : (
            <Alert type="info" showIcon message="未关联房屋时也可保存研究记录，但报告不会带入房屋罗盘测点。" />
          )}
        </PaperCard>

        <PaperCard title="龙穴砂水向">
          <Form form={form} layout="vertical">
            {[
              ['dragon', '龙'],
              ['cave', '穴'],
              ['sand', '砂'],
              ['water', '水'],
              ['direction', '向'],
              ['environment', '形势环境'],
            ].map(([key, label]) => (
              <div key={key} style={{ marginBottom: 8 }}>
                <Form.Item name={`${key}_summary`} label={`${label}：概要`}>
                  <Input placeholder={`记录${label}的观察概要`} />
                </Form.Item>
                <Form.Item name={`${key}_note`} label={`${label}：备注`}>
                  <Input.TextArea rows={2} placeholder="可记录现场观察、资料出处或待核验点。" />
                </Form.Item>
              </div>
            ))}
            <Form.Item name="research_note" label="补充研究说明">
              <Input.TextArea rows={3} placeholder="补充资料来源、疑点、后续需校勘事项。" />
            </Form.Item>
          </Form>
        </PaperCard>
      </div>

      <PaperCard title="当前保存结果" style={{ marginBottom: 18 }}>
        {currentRecord ? (
          <Descriptions bordered size="small" column={2}>
            <Descriptions.Item label="记录 ID">#{currentRecord.id}</Descriptions.Item>
            <Descriptions.Item label="类型">{currentRecord.site_type_label}</Descriptions.Item>
            <Descriptions.Item label="现场坐标">
              {currentRecord.latitude != null && currentRecord.longitude != null
                ? `${Number(currentRecord.latitude).toFixed(6)}, ${Number(currentRecord.longitude).toFixed(6)}`
                : '-'}
            </Descriptions.Item>
            <Descriptions.Item label="坐山">{currentRecord.mountain_direction_24 || '-'} {currentRecord.mountain_degree ?? ''}</Descriptions.Item>
            <Descriptions.Item label="向首">{currentRecord.facing_direction_24 || '-'} {currentRecord.facing_degree ?? ''}</Descriptions.Item>
            <Descriptions.Item label="边界说明" span={2}>
              {currentRecord.result_json?.method_note || '仅用于传统文化研究和环境记录。'}
            </Descriptions.Item>
          </Descriptions>
        ) : (
          <Empty description="保存后在这里显示本次研究记录" image={Empty.PRESENTED_IMAGE_SIMPLE} />
        )}
      </PaperCard>

      <PaperCard title="研究记录" extra={`共 ${records.length} 条`}>
        <Table
          rowKey="id"
          dataSource={records}
          columns={columns}
          pagination={{ pageSize: 8 }}
          locale={{ emptyText: <Empty description="暂无阴宅研究记录" image={Empty.PRESENTED_IMAGE_SIMPLE} /> }}
        />
      </PaperCard>
    </div>
  );
}
