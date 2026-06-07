import React, { useEffect, useState } from 'react';
import {
  Button,
  Descriptions,
  Empty,
  Form,
  Input,
  InputNumber,
  message,
  Modal,
  Popconfirm,
  Select,
  Space,
  Spin,
  Table,
  Tag,
} from 'antd';
import { useNavigate, useParams } from 'react-router-dom';
import api from '../services/api';
import AnalysisModeSelector from '../components/AnalysisModeSelector';
import PageBanner from '../components/PageBanner';
import PaperCard from '../components/PaperCard';

const objectOptions = [
  { value: 'main_door', label: '大门' },
  { value: 'bed', label: '床位' },
  { value: 'desk', label: '书桌' },
  { value: 'stove', label: '灶位' },
  { value: 'window', label: '窗户' },
  { value: 'sofa', label: '沙发' },
  { value: 'other', label: '其他' },
];

const sceneOptions = [
  { value: 'indoor', label: '室内' },
  { value: 'outdoor', label: '室外' },
  { value: 'balcony', label: '阳台' },
  { value: 'entrance', label: '入户' },
];

function isDoorRecord(row) {
  return ['main_door', '大门', '门', '入户门', 'front_door'].includes(String(row.object_type || '').trim());
}

export default function HouseDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [house, setHouse] = useState(null);
  const [records, setRecords] = useState([]);
  const [loading, setLoading] = useState(true);
  const [recordModalOpen, setRecordModalOpen] = useState(false);
  const [saving, setSaving] = useState(false);
  const [reportBusy, setReportBusy] = useState(false);
  const [analysisMode, setAnalysisMode] = useState('safe');
  const [form] = Form.useForm();

  function refresh() {
    setLoading(true);
    Promise.all([
      api.getHouse(id),
      api.listHouseCompassRecords(id),
    ])
      .then(([h, r]) => {
        setHouse(h);
        setRecords(r);
      })
      .catch((e) => message.error(e.message || '读取房屋详情失败'))
      .finally(() => setLoading(false));
  }

  useEffect(refresh, [id]);

  function openRecordModal() {
    form.setFieldsValue({
      house_id: Number(id),
      scene_type: 'indoor',
      object_type: 'main_door',
      degree: undefined,
      note: '',
    });
    setRecordModalOpen(true);
  }

  async function onSaveRecord() {
    const values = await form.validateFields();
    setSaving(true);
    try {
      await api.createCompassRecord({ ...values, house_id: Number(id) });
      message.success('测点已保存');
      setRecordModalOpen(false);
      refresh();
    } catch (e) {
      message.error(e.message || '保存失败');
    } finally {
      setSaving(false);
    }
  }

  async function onDeleteRecord(recordId) {
    try {
      await api.deleteCompassRecord(recordId);
      message.success('测点已删除');
      refresh();
    } catch (e) {
      message.error(e.message || '删除失败');
    }
  }

  async function onSetMainDoor(recordId) {
    try {
      const next = await api.setHouseMainDoorFromRecord(id, recordId);
      setHouse(next);
      message.success('已同步为主门朝向');
    } catch (e) {
      message.error(e.message || '同步失败');
    }
  }

  async function onGenerateReport() {
    setReportBusy(true);
    try {
      const report = await api.generateFengshuiBasicReport(id, analysisMode);
      message.success('阳宅基础报告已生成');
      navigate(`/reports/${report.id}`);
    } catch (e) {
      message.error(e.message || '生成失败');
    } finally {
      setReportBusy(false);
    }
  }

  const columns = [
    { title: '场景', dataIndex: 'scene_type', width: 110 },
    { title: '对象', dataIndex: 'object_type', width: 110 },
    { title: '角度', dataIndex: 'degree', width: 90, render: (v) => `${v}°` },
    { title: '八方', dataIndex: 'direction_8', width: 90, render: (v) => <Tag color="blue">{v}</Tag> },
    { title: '二十四山', dataIndex: 'direction_24', width: 110, render: (v) => <Tag color="gold">{v}</Tag> },
    { title: '稳定性', dataIndex: 'stability_score', width: 90, render: (v) => (v == null ? '—' : v) },
    { title: '备注', dataIndex: 'note', render: (v) => v || '—' },
    {
      title: '操作',
      width: 210,
      render: (_, r) => (
        <Space>
          {isDoorRecord(r) && (
            <Button
              size="small"
              disabled={house?.main_door_degree != null}
              onClick={() => onSetMainDoor(r.id)}
            >
              设为主门
            </Button>
          )}
          <Popconfirm title="删除这个测点？" onConfirm={() => onDeleteRecord(r.id)}>
            <Button size="small" danger>删除</Button>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  if (loading) return <Spin />;
  if (!house) return <Empty description="房屋不存在" image={Empty.PRESENTED_IMAGE_SIMPLE} />;

  return (
    <div>
      <PageBanner
        title={house.name}
        subtitle="房屋档案详情、罗盘测点与阳宅基础报告"
        quote="一宅一案，一向一记。"
        extra={
          <Space>
            <Button onClick={openRecordModal}>新增测点</Button>
            <AnalysisModeSelector value={analysisMode} onChange={setAnalysisMode} />
            <Button type="primary" loading={reportBusy} onClick={onGenerateReport}>
              生成阳宅报告
            </Button>
          </Space>
        }
      />
      <PaperCard title="基础信息" style={{ marginBottom: 18 }}>
        <Descriptions column={2} bordered size="small">
          <Descriptions.Item label="类型">{house.house_type || '—'}</Descriptions.Item>
          <Descriptions.Item label="建成年份">{house.build_year || '—'}</Descriptions.Item>
          <Descriptions.Item label="入住日期">{house.move_in_date || '—'}</Descriptions.Item>
          <Descriptions.Item label="主门朝向">
            {house.main_door_degree == null ? '暂无主门朝向，可从大门测点一键设置' : (
              <Space>
                <Tag>{house.main_door_degree}°</Tag>
                <Tag color="blue">{house.main_door_direction_8}</Tag>
                <Tag color="gold">{house.main_door_direction_24}</Tag>
              </Space>
            )}
          </Descriptions.Item>
          <Descriptions.Item label="地址备注" span={2}>{house.address_note || '—'}</Descriptions.Item>
          <Descriptions.Item label="户型备注" span={2}>{house.floorplan_note || '—'}</Descriptions.Item>
        </Descriptions>
      </PaperCard>

      <PaperCard title="罗盘测点" extra={`共 ${records.length} 条`}>
        <Table
          rowKey="id"
          dataSource={records}
          columns={columns}
          pagination={{ pageSize: 10 }}
          locale={{ emptyText: <Empty description="暂无测点" image={Empty.PRESENTED_IMAGE_SIMPLE} /> }}
        />
      </PaperCard>

      <Modal
        title="新增罗盘测点"
        open={recordModalOpen}
        onCancel={() => setRecordModalOpen(false)}
        onOk={onSaveRecord}
        confirmLoading={saving}
        width={720}
      >
        <Form form={form} layout="vertical">
          <Form.Item name="house_id" hidden><Input /></Form.Item>
          <Space style={{ width: '100%' }} size={12}>
            <Form.Item name="scene_type" label="场景" rules={[{ required: true }]} style={{ width: 160 }}>
              <Select options={sceneOptions} />
            </Form.Item>
            <Form.Item name="object_type" label="对象" rules={[{ required: true }]} style={{ width: 180 }}>
              <Select options={objectOptions} />
            </Form.Item>
            <Form.Item name="degree" label="角度" rules={[{ required: true }]} style={{ width: 160 }}>
              <InputNumber min={0} max={360} style={{ width: '100%' }} />
            </Form.Item>
          </Space>
          <Form.Item name="note" label="备注"><Input.TextArea rows={3} /></Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
