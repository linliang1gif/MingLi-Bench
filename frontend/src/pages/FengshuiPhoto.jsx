import React, { useEffect, useMemo, useRef, useState } from 'react';
import {
  Alert,
  Button,
  Checkbox,
  Descriptions,
  Empty,
  Form,
  Input,
  List,
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

const roomOptions = [
  { value: 'bedroom', label: '卧室' },
  { value: 'living_room', label: '客厅' },
  { value: 'kitchen', label: '厨房' },
  { value: 'entrance', label: '大门/玄关' },
];

const directionOptions = [
  '北', '东北', '东', '东南', '南', '西南', '西', '西北',
  '子', '癸', '丑', '艮', '寅', '甲', '卯', '乙', '辰', '巽', '巳', '丙',
  '午', '丁', '未', '坤', '申', '庚', '酉', '辛', '戌', '乾', '亥', '壬',
].map((value) => ({ value, label: value }));

function roomLabel(value) {
  return roomOptions.find((r) => r.value === value)?.label || value || '未标注';
}

function boolInitial(analysis, name) {
  return (analysis?.objects || []).some((obj) => obj.name === name);
}

export default function FengshuiPhoto() {
  const navigate = useNavigate();
  const [form] = Form.useForm();
  const [correctionForm] = Form.useForm();
  const cameraInputRef = useRef(null);
  const uploadInputRef = useRef(null);

  const [houses, setHouses] = useState([]);
  const [records, setRecords] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedFile, setSelectedFile] = useState(null);
  const [previewUrl, setPreviewUrl] = useState('');
  const [record, setRecord] = useState(null);
  const [analysis, setAnalysis] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  const [reporting, setReporting] = useState(false);
  const [analysisMode, setAnalysisMode] = useState('safe');

  const houseId = Form.useWatch('house_id', form);
  const roomType = Form.useWatch('room_type', form);
  const selectedHouse = useMemo(
    () => houses.find((h) => h.id === houseId),
    [houses, houseId],
  );

  function refreshRecords(nextHouseId = houseId) {
    api.getFengshuiPhotoRecords(nextHouseId ? { house_id: nextHouseId } : undefined)
      .then(setRecords)
      .catch(() => setRecords([]));
  }

  useEffect(() => {
    setLoading(true);
    api.listHouses()
      .then((rows) => {
        setHouses(rows);
        form.setFieldsValue({
          house_id: rows[0]?.id,
          room_type: 'bedroom',
        });
        refreshRecords(rows[0]?.id);
      })
      .catch((e) => message.error(e.message || '读取房屋档案失败'))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    return () => {
      if (previewUrl) URL.revokeObjectURL(previewUrl);
    };
  }, [previewUrl]);

  function onPickFile(file) {
    if (!file) return;
    const okType = ['image/jpeg', 'image/png', 'image/webp'].includes(file.type);
    if (!okType) {
      message.warning('仅支持 jpg、jpeg、png、webp 图片');
      return;
    }
    if (file.size > 10 * 1024 * 1024) {
      message.warning('单张图片不能超过 10MB');
      return;
    }
    if (previewUrl) URL.revokeObjectURL(previewUrl);
    setSelectedFile(file);
    setPreviewUrl(URL.createObjectURL(file));
    setRecord(null);
    setAnalysis(null);
  }

  async function onUploadAndAnalyze() {
    const values = await form.validateFields();
    if (!selectedFile) {
      message.warning('请先拍照或选择图片');
      return;
    }
    setUploading(true);
    setAnalyzing(false);
    try {
      const upload = await api.uploadFengshuiPhoto({
        houseId: values.house_id,
        roomType: values.room_type,
        file: selectedFile,
      });
      setRecord(upload.record);
      setUploading(false);
      setAnalyzing(true);
      const analyzed = await api.analyzeFengshuiPhoto(upload.record_id);
      setRecord(analyzed.record);
      setAnalysis(analyzed.analysis);
      correctionForm.setFieldsValue({
        has_bed: boolInitial(analyzed.analysis, 'bed'),
        has_door: boolInitial(analyzed.analysis, 'door'),
        has_window: boolInitial(analyzed.analysis, 'window'),
        has_mirror: boolInitial(analyzed.analysis, 'mirror'),
        has_beam: boolInitial(analyzed.analysis, 'beam'),
        bed_head_direction: undefined,
        note: '',
      });
      refreshRecords(values.house_id);
      message.success('图片识别完成，请核对并校正');
    } catch (e) {
      message.error(e.message || '上传或识别失败');
    } finally {
      setUploading(false);
      setAnalyzing(false);
    }
  }

  async function onGenerateReport() {
    if (!record?.id) {
      message.warning('请先上传并识别图片');
      return;
    }
    const values = await correctionForm.validateFields();
    setReporting(true);
    try {
      const report = await api.generateFengshuiPhotoReport({
        recordId: record.id,
        userCorrection: values,
        analysisMode,
      });
      message.success('拍照风水报告已生成');
      navigate(`/reports/${report.report_id || report.id}`);
    } catch (e) {
      message.error(e.message || '生成报告失败');
    } finally {
      setReporting(false);
    }
  }

  async function onDeleteRecord(recordId) {
    try {
      await api.deleteFengshuiPhotoRecord(recordId);
      message.success('拍照记录已删除');
      refreshRecords();
    } catch (e) {
      message.error(e.message || '删除失败');
    }
  }

  const columns = [
    { title: '时间', dataIndex: 'created_at', width: 170, render: (v) => v ? String(v).replace('T', ' ').slice(0, 16) : '—' },
    { title: '房间', dataIndex: 'room_type', width: 110, render: (v) => <Tag color="blue">{roomLabel(v)}</Tag> },
    { title: '图片', dataIndex: 'image_path', ellipsis: true, render: (v) => v || '—' },
    { title: '报告', dataIndex: 'report_id', width: 90, render: (v) => v ? <Button size="small" onClick={() => navigate(`/reports/${v}`)}>查看</Button> : '—' },
    {
      title: '操作',
      width: 90,
      render: (_, r) => (
        <Popconfirm title="删除这条拍照记录？" onConfirm={() => onDeleteRecord(r.id)}>
          <Button size="small" danger>删除</Button>
        </Popconfirm>
      ),
    },
  ];

  if (loading) return <Spin />;

  return (
    <div>
      <PageBanner
        title="拍照识别"
        subtitle="手机拍照或上传图片，识别房间对象后校正并生成风水报告"
        quote="以图入案，以人为准。"
        extra={
          <Space>
            <Button loading={uploading || analyzing} onClick={onUploadAndAnalyze}>
              {analyzing ? '识别中' : '提交 AI 识别'}
            </Button>
            <AnalysisModeSelector value={analysisMode} onChange={setAnalysisMode} />
            <Button type="primary" loading={reporting} onClick={onGenerateReport}>
              生成拍照风水报告
            </Button>
          </Space>
        }
      />

      <div className="ml-grid cols-2" style={{ marginBottom: 18 }}>
        <PaperCard title="拍照与上传">
          <Space direction="vertical" size={16} style={{ width: '100%' }}>
            <Form form={form} layout="vertical">
              <Space wrap size={14} align="start">
                <Form.Item name="house_id" label="房屋档案" style={{ width: 240 }}>
                  <Select
                    allowClear
                    placeholder="选择房屋"
                    options={houses.map((h) => ({ value: h.id, label: h.name }))}
                    onChange={(value) => {
                      setRecord(null);
                      setAnalysis(null);
                      refreshRecords(value);
                    }}
                  />
                </Form.Item>
                <Form.Item name="room_type" label="房间类型" rules={[{ required: true }]} style={{ width: 180 }}>
                  <Select options={roomOptions} />
                </Form.Item>
              </Space>
            </Form>

            <Space wrap>
              <Button onClick={() => cameraInputRef.current?.click()}>手机拍照</Button>
              <Button onClick={() => uploadInputRef.current?.click()}>选择图片</Button>
            </Space>
            <input
              ref={cameraInputRef}
              type="file"
              accept="image/jpeg,image/png,image/webp"
              capture="environment"
              style={{ display: 'none' }}
              onChange={(e) => onPickFile(e.target.files?.[0])}
            />
            <input
              ref={uploadInputRef}
              type="file"
              accept="image/jpeg,image/png,image/webp"
              style={{ display: 'none' }}
              onChange={(e) => onPickFile(e.target.files?.[0])}
            />

            {selectedHouse ? (
              <Alert type="info" showIcon message={`当前房屋：${selectedHouse.name}`} />
            ) : (
              <Alert type="warning" showIcon message="未选择房屋时也可识别图片，但生成报告将无法结合房屋档案和罗盘测点。" />
            )}

            {previewUrl ? (
              <img
                src={previewUrl}
                alt="房间预览"
                style={{
                  width: '100%',
                  maxHeight: 420,
                  objectFit: 'contain',
                  border: '1px solid var(--ml-border)',
                  borderRadius: 8,
                  background: '#fff',
                }}
              />
            ) : (
              <Empty description="请选择或拍摄一张房间图片" image={Empty.PRESENTED_IMAGE_SIMPLE} />
            )}
          </Space>
        </PaperCard>

        <PaperCard title="识别结果">
          {analysis ? (
            <Space direction="vertical" size={14} style={{ width: '100%' }}>
              <Descriptions bordered size="small" column={1}>
                <Descriptions.Item label="房间类型">{roomLabel(analysis.room_type || roomType)}</Descriptions.Item>
                <Descriptions.Item label="识别来源">{analysis.source || 'llm'}</Descriptions.Item>
                <Descriptions.Item label="需人工确认">{analysis.need_user_confirm ? '是' : '否'}</Descriptions.Item>
              </Descriptions>
              {analysis.note && <Alert type="info" showIcon message={analysis.note} />}
              <List
                dataSource={analysis.objects || []}
                locale={{ emptyText: <Empty description="暂无识别对象" image={Empty.PRESENTED_IMAGE_SIMPLE} /> }}
                renderItem={(obj) => (
                  <List.Item>
                    <List.Item.Meta
                      title={<Space><b>{obj.label || obj.name}</b><Tag>{obj.position || '未知位置'}</Tag></Space>}
                      description={`置信度：${typeof obj.confidence === 'number' ? obj.confidence.toFixed(2) : '—'}`}
                    />
                  </List.Item>
                )}
              />
            </Space>
          ) : (
            <Empty description="提交识别后展示对象结果" image={Empty.PRESENTED_IMAGE_SIMPLE} />
          )}
        </PaperCard>
      </div>

      <PaperCard title="用户校正" style={{ marginBottom: 18 }}>
        <Form form={correctionForm} layout="vertical">
          <Space wrap size={18} align="start">
            <Form.Item name="has_bed" valuePropName="checked"><Checkbox>有床</Checkbox></Form.Item>
            <Form.Item name="has_door" valuePropName="checked"><Checkbox>有门</Checkbox></Form.Item>
            <Form.Item name="has_window" valuePropName="checked"><Checkbox>有窗</Checkbox></Form.Item>
            <Form.Item name="has_mirror" valuePropName="checked"><Checkbox>有镜子</Checkbox></Form.Item>
            <Form.Item name="has_beam" valuePropName="checked"><Checkbox>有横梁</Checkbox></Form.Item>
            <Form.Item name="bed_head_direction" label="床头方向" style={{ width: 180 }}>
              <Select allowClear options={directionOptions} />
            </Form.Item>
          </Space>
          <Form.Item name="note" label="补充说明">
            <Input.TextArea rows={3} placeholder="例如：门在右前方，窗在床尾方向，镜子不直对床。" />
          </Form.Item>
        </Form>
      </PaperCard>

      <PaperCard title="拍照识别记录" extra={`共 ${records.length} 条`}>
        <Table
          rowKey="id"
          dataSource={records}
          columns={columns}
          pagination={{ pageSize: 8 }}
          locale={{ emptyText: <Empty description="暂无拍照识别记录" image={Empty.PRESENTED_IMAGE_SIMPLE} /> }}
        />
      </PaperCard>
    </div>
  );
}
