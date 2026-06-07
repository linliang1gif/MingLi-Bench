import React, { useEffect, useMemo, useRef, useState } from 'react';
import {
  Alert,
  Button,
  Checkbox,
  Descriptions,
  Empty,
  Form,
  Input,
  InputNumber,
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
import LocationPicker from '../components/LocationPicker';
import PageBanner from '../components/PageBanner';
import PaperCard from '../components/PaperCard';

const sceneOptions = [
  { value: 'yinzhai_environment', label: '阴宅环境' },
  { value: 'tianxing_site', label: '天星现场方向' },
  { value: 'house_landscape', label: '房屋外局' },
  { value: 'heritage_risk', label: '文保风险巡查' },
  { value: 'manual_target', label: '手动目标' },
];

const heritageRiskOptions = [
  { value: 'low', label: '低：仅作地貌记录' },
  { value: 'medium', label: '中：存在需核实线索' },
  { value: 'high', label: '高：建议保持现场并上报' },
  { value: 'unknown', label: '未评估' },
];

const patrolPriorityOptions = [
  { value: 'routine', label: '常规巡查' },
  { value: 'follow_up', label: '复核巡查' },
  { value: 'urgent', label: '优先核验' },
  { value: 'unknown', label: '未标注' },
];

const verificationStatusOptions = [
  { value: 'pending', label: '待核验' },
  { value: 'in_review', label: '核验中' },
  { value: 'verified_non_heritage', label: '已核验：普通地貌/扰动' },
  { value: 'reported', label: '已整理上报' },
];

const terrainAnomalyOptions = [
  { value: 'none', label: '未见明显异常' },
  { value: 'mound_like', label: '堆土/隆起样地貌' },
  { value: 'cut_slope', label: '削坡/断面样地貌' },
  { value: 'stone_like', label: '石构件样对象' },
  { value: 'inscription_like', label: '文字刻痕样痕迹' },
  { value: 'surface_object', label: '地表遗物样对象' },
  { value: 'unknown', label: '待核验' },
];

const disturbanceTypeOptions = [
  { value: 'none', label: '未见明显扰动' },
  { value: 'construction', label: '施工扰动' },
  { value: 'earthwork', label: '土方扰动' },
  { value: 'erosion', label: '水土流失/塌陷' },
  { value: 'recent_digging_like', label: '近期翻动样痕迹' },
  { value: 'unknown', label: '待核验' },
];

const directionOptions = [
  '北', '东北', '东', '东南', '南', '西南', '西', '西北',
  '子', '癸', '丑', '艮', '寅', '甲', '卯', '乙', '辰', '巽', '巳', '丙',
  '午', '丁', '未', '坤', '申', '庚', '酉', '辛', '戌', '乾', '亥', '壬',
].map((value) => ({ value, label: value }));

function sceneLabel(value) {
  return sceneOptions.find((item) => item.value === value)?.label || value || '未标注';
}

function boolInitial(analysis, name) {
  return (analysis?.objects || []).some((obj) => obj.name === name);
}

function isHeritageScene(value) {
  return value === 'heritage_risk';
}

function buildSurveyGridCode(latitude, longitude) {
  if (latitude == null || longitude == null || latitude === '' || longitude === '') return undefined;
  const lat = Number(latitude);
  const lng = Number(longitude);
  if (!Number.isFinite(lat) || !Number.isFinite(lng)) return undefined;
  return `GRID-${Math.round(lat * 100)}-${Math.round(lng * 100)}`;
}

export default function LandscapePhoto() {
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
  const sceneType = Form.useWatch('scene_type', form);
  const selectedHouse = useMemo(
    () => houses.find((h) => h.id === houseId),
    [houses, houseId],
  );

  function refreshRecords(nextHouseId = houseId) {
    api.getLandscapePhotoRecords(nextHouseId ? { house_id: nextHouseId } : undefined)
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
          scene_type: 'house_landscape',
          degree: rows[0]?.main_door_degree,
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
      const upload = await api.uploadLandscapePhoto({
        houseId: values.house_id,
        sceneType: values.scene_type,
        targetLabel: values.target_label,
        degree: values.degree,
        latitude: values.latitude,
        longitude: values.longitude,
        locationNote: values.location_note,
        file: selectedFile,
      });
      setRecord(upload.record);
      setUploading(false);
      setAnalyzing(true);
      const analyzed = await api.analyzeLandscapePhoto(upload.record_id);
      setRecord(analyzed.record);
      setAnalysis(analyzed.analysis);
      correctionForm.setFieldsValue({
        has_mountain: boolInitial(analyzed.analysis, 'mountain'),
        has_water: boolInitial(analyzed.analysis, 'water'),
        has_road: boolInitial(analyzed.analysis, 'road') || boolInitial(analyzed.analysis, 'path'),
        has_building: boolInitial(analyzed.analysis, 'building'),
        has_tree: boolInitial(analyzed.analysis, 'tree'),
        has_pole: boolInitial(analyzed.analysis, 'pole'),
        is_open_bright: boolInitial(analyzed.analysis, 'open_space'),
        has_pressure_object: false,
        has_artificial_mound: boolInitial(analyzed.analysis, 'artificial_mound'),
        has_stone_object: boolInitial(analyzed.analysis, 'stone_object'),
        has_inscription: boolInitial(analyzed.analysis, 'inscription'),
        has_surface_artifact: boolInitial(analyzed.analysis, 'surface_artifact'),
        has_recent_disturbance: boolInitial(analyzed.analysis, 'recent_disturbance'),
        heritage_risk_level: values.scene_type === 'heritage_risk' ? 'unknown' : undefined,
        survey_grid_code: values.scene_type === 'heritage_risk'
          ? buildSurveyGridCode(values.latitude, values.longitude)
          : undefined,
        patrol_priority: values.scene_type === 'heritage_risk' ? 'unknown' : undefined,
        verification_status: values.scene_type === 'heritage_risk' ? 'pending' : undefined,
        terrain_anomaly_type: values.scene_type === 'heritage_risk' ? 'unknown' : undefined,
        disturbance_type: values.scene_type === 'heritage_risk' ? 'unknown' : undefined,
        evidence_note: '',
        protection_note: '',
        target_direction: analyzed.record?.direction_24,
        water_direction: undefined,
        road_direction: undefined,
        tianxing_mountain: analyzed.record?.direction_24,
        note: '',
      });
      refreshRecords(values.house_id);
      message.success('外局图片识别完成，请核对并校正');
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
      const report = await api.generateLandscapePhotoReport({
        recordId: record.id,
        userCorrection: values,
        analysisMode,
      });
      message.success(isHeritageScene(record.scene_type) ? '文保风险记录报告已生成' : '外局拍照研究报告已生成');
      navigate(`/reports/${report.report_id || report.id}`);
    } catch (e) {
      message.error(e.message || '生成报告失败');
    } finally {
      setReporting(false);
    }
  }

  async function onDeleteRecord(recordId) {
    try {
      await api.deleteLandscapePhotoRecord(recordId);
      message.success('外局拍照记录已删除');
      refreshRecords();
    } catch (e) {
      message.error(e.message || '删除失败');
    }
  }

  const columns = [
    { title: '时间', dataIndex: 'created_at', width: 160, render: (v) => v ? String(v).replace('T', ' ').slice(0, 16) : '—' },
    { title: '场景', dataIndex: 'scene_type', width: 130, render: (v) => <Tag color={isHeritageScene(v) ? 'orange' : 'blue'}>{sceneLabel(v)}</Tag> },
    { title: '目标', dataIndex: 'target_label', width: 140, render: (v) => v || '—' },
    { title: '方位', width: 120, render: (_, r) => r.degree == null ? (r.direction_24 || '—') : `${r.degree}° / ${r.direction_24 || '—'}` },
    {
      title: '位置',
      width: 150,
      render: (_, r) => (
        r.latitude != null && r.longitude != null
          ? `${Number(r.latitude).toFixed(5)}, ${Number(r.longitude).toFixed(5)}`
          : '—'
      ),
    },
    { title: '图片', dataIndex: 'image_path', ellipsis: true, render: (v) => v || '—' },
    { title: '报告', dataIndex: 'report_id', width: 90, render: (v) => v ? <Button size="small" onClick={() => navigate(`/reports/${v}`)}>查看</Button> : '—' },
    {
      title: '操作',
      width: 90,
      render: (_, r) => (
        <Popconfirm title="删除这条外局拍照记录？" onConfirm={() => onDeleteRecord(r.id)}>
          <Button size="small" danger>删除</Button>
        </Popconfirm>
      ),
    },
  ];

  if (loading) return <Spin />;

  return (
    <div>
      <PageBanner
        title="外局拍照识别"
        subtitle="上传现场外局图片，识别环境对象，结合罗盘与天星资料生成研究报告"
        quote="取象于外，留证于图。"
        extra={
          <Space>
            <Button loading={uploading || analyzing} onClick={onUploadAndAnalyze}>
              {analyzing ? '识别中' : '提交 AI 识别'}
            </Button>
            <AnalysisModeSelector value={analysisMode} onChange={setAnalysisMode} />
            <Button type="primary" loading={reporting} onClick={onGenerateReport}>
              {isHeritageScene(sceneType) ? '生成文保风险报告' : '生成外局报告'}
            </Button>
          </Space>
        }
      />

      {isHeritageScene(sceneType) && (
        <Alert
          type="error"
          showIcon
          style={{ marginBottom: 18 }}
          message="文保风险记录边界"
          description="本功能仅用于文物保护风险记录，不用于寻找、定位、挖掘古墓葬。不得输出古墓概率、墓道/墓室/入口推测、寻找路线、挖掘建议或探测建议。发现疑似文物或古墓葬痕迹时，请保持现场，不要扰动，并联系当地文物主管部门。"
        />
      )}

      <div className="ml-grid cols-2" style={{ marginBottom: 18 }}>
        <PaperCard title="拍照与上传">
          <Space direction="vertical" size={16} style={{ width: '100%' }}>
            <Form form={form} layout="vertical">
              <Form.Item name="house_id" label="关联房屋档案">
                <Select
                  allowClear
                  placeholder="可选"
                  options={houses.map((h) => ({ value: h.id, label: h.name }))}
                  onChange={(value) => {
                    const house = houses.find((item) => item.id === value);
                    form.setFieldsValue({ degree: house?.main_door_degree });
                    setRecord(null);
                    setAnalysis(null);
                    refreshRecords(value);
                  }}
                />
              </Form.Item>
              <Space wrap size={14} align="start">
                <Form.Item name="scene_type" label="场景类型" rules={[{ required: true }]} style={{ width: 180 }}>
                  <Select
                    options={sceneOptions}
                    onChange={(value) => {
                      setRecord(null);
                      setAnalysis(null);
                      correctionForm.resetFields();
                      if (isHeritageScene(value)) {
                        correctionForm.setFieldsValue({ heritage_risk_level: 'unknown' });
                      }
                    }}
                  />
                </Form.Item>
                <Form.Item name="target_label" label="目标名称" style={{ width: 200 }}>
                  <Input placeholder="如案山、水口、门前道路" />
                </Form.Item>
                <Form.Item name="degree" label="目标角度" style={{ width: 150 }}>
                  <InputNumber min={0} max={360} precision={2} style={{ width: '100%' }} />
                </Form.Item>
              </Space>
              <LocationPicker
                form={form}
                title="现场位置记录"
                description="可在地图上标记拍照位置，用于外局照片和报告版本追溯。"
                notePlaceholder="可记录公开可描述的拍照点、周边参照物或资料来源"
              />
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
              <Alert type="info" showIcon message={`当前关联：${selectedHouse.name}`} />
            ) : (
              <Alert type="info" showIcon message="未关联房屋时也可识别外局图片，但报告无法自动带入房屋档案和罗盘测点。" />
            )}

            {previewUrl ? (
              <img
                src={previewUrl}
                alt="外局预览"
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
              <Empty description="请选择或拍摄一张外局现场图片" image={Empty.PRESENTED_IMAGE_SIMPLE} />
            )}
          </Space>
        </PaperCard>

        <PaperCard title="识别结果">
          {analysis ? (
            <Space direction="vertical" size={14} style={{ width: '100%' }}>
              <Descriptions bordered size="small" column={1}>
                <Descriptions.Item label="场景类型">{sceneLabel(analysis.scene_type || sceneType)}</Descriptions.Item>
                <Descriptions.Item label="识别来源">{analysis.source || 'llm'}</Descriptions.Item>
                {analysis.vision_model && (
                  <Descriptions.Item label="视觉模型">{analysis.vision_model}</Descriptions.Item>
                )}
                <Descriptions.Item label="需人工确认">{analysis.need_user_confirm ? '是' : '否'}</Descriptions.Item>
                {record?.direction_24 && (
                  <Descriptions.Item label="目标山向">
                    {record.degree != null ? `${record.degree}° / ` : ''}{record.direction_8 || '—'} / {record.direction_24}
                  </Descriptions.Item>
                )}
              </Descriptions>
              {analysis.note && <Alert type="info" showIcon message={analysis.note} />}
              {analysis.vision_empty_objects && (
                <Alert
                  type="warning"
                  showIcon
                  message="未取得模型对象列表"
                  description="视觉模型已响应，但没有返回可直接展示的 objects，系统已补充基础校正项。请按照片实际情况核对。"
                />
              )}
              {!!analysis.possible_issues?.length && (
                <Alert
                  type="warning"
                  showIcon
                  message="需核对事项"
                  description={(
                    <ul style={{ margin: 0, paddingLeft: 18 }}>
                      {analysis.possible_issues.map((item, index) => (
                        <li key={`${index}-${String(item).slice(0, 12)}`}>{typeof item === 'string' ? item : item?.text || JSON.stringify(item)}</li>
                      ))}
                    </ul>
                  )}
                />
              )}
              {isHeritageScene(analysis.scene_type || sceneType) && (
                <Alert
                  type="warning"
                  showIcon
                  message="仅做文保风险巡查"
                  description="识别结果只用于记录巡查网格、可见地貌、人工痕迹和扰动线索；不判断古墓位置或概率，不提供入口、挖掘、探测或寻找路线。疑似信息需要专业人员现场核实。"
                />
              )}
              {analysis.tianxing?.mapping && (
                <Alert
                  type="success"
                  showIcon
                  message={`天星映射：${analysis.tianxing.mapping.mountain_24} · ${analysis.tianxing.mapping.tianxing}`}
                  description={analysis.tianxing.mapping.variant_note}
                />
              )}
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
            <Empty description="提交识别后展示外局对象结果" image={Empty.PRESENTED_IMAGE_SIMPLE} />
          )}
        </PaperCard>
      </div>

      <PaperCard title="用户校正" style={{ marginBottom: 18 }}>
        <Form form={correctionForm} layout="vertical">
          <Space wrap size={18} align="start">
            <Form.Item name="has_mountain" valuePropName="checked"><Checkbox>可见山体/高处</Checkbox></Form.Item>
            <Form.Item name="has_water" valuePropName="checked"><Checkbox>可见水体</Checkbox></Form.Item>
            <Form.Item name="has_road" valuePropName="checked"><Checkbox>可见道路</Checkbox></Form.Item>
            <Form.Item name="has_building" valuePropName="checked"><Checkbox>可见建筑</Checkbox></Form.Item>
            <Form.Item name="has_tree" valuePropName="checked"><Checkbox>可见树木</Checkbox></Form.Item>
            <Form.Item name="has_pole" valuePropName="checked"><Checkbox>可见杆塔/立柱</Checkbox></Form.Item>
            <Form.Item name="is_open_bright" valuePropName="checked"><Checkbox>前方较开阔明亮</Checkbox></Form.Item>
            <Form.Item name="has_pressure_object" valuePropName="checked"><Checkbox>存在压迫性遮挡物</Checkbox></Form.Item>
          </Space>
          {isHeritageScene(sceneType) && (
            <>
              <Alert
                type="warning"
                showIcon
                style={{ margin: '4px 0 16px' }}
                message="文保巡查网格与线索核验"
                description="以下字段用于巡查网格、地貌异常、扰动和上报材料整理，不用于判断古墓位置、概率、入口或可挖掘点。"
              />
              <Space wrap size={18} align="start">
                <Form.Item name="has_artificial_mound" valuePropName="checked"><Checkbox>人工堆土/封土样地貌</Checkbox></Form.Item>
                <Form.Item name="has_stone_object" valuePropName="checked"><Checkbox>石构件/石刻样对象</Checkbox></Form.Item>
                <Form.Item name="has_inscription" valuePropName="checked"><Checkbox>文字刻痕/铭文样痕迹</Checkbox></Form.Item>
                <Form.Item name="has_surface_artifact" valuePropName="checked"><Checkbox>地表遗物样对象</Checkbox></Form.Item>
                <Form.Item name="has_recent_disturbance" valuePropName="checked"><Checkbox>近期扰动痕迹</Checkbox></Form.Item>
              </Space>
              <Space wrap size={14} align="start">
                <Form.Item name="survey_grid_code" label="巡查网格编号" style={{ width: 220 }}>
                  <Input placeholder="例如：GRID-3123-12147" />
                </Form.Item>
                <Form.Item name="patrol_priority" label="巡查优先级" style={{ width: 180 }}>
                  <Select options={patrolPriorityOptions} />
                </Form.Item>
                <Form.Item name="verification_status" label="核验状态" style={{ width: 220 }}>
                  <Select options={verificationStatusOptions} />
                </Form.Item>
                <Form.Item name="heritage_risk_level" label="文保风险等级" style={{ width: 220 }}>
                  <Select options={heritageRiskOptions} />
                </Form.Item>
                <Form.Item name="terrain_anomaly_type" label="地貌异常类型" style={{ width: 220 }}>
                  <Select options={terrainAnomalyOptions} />
                </Form.Item>
                <Form.Item name="disturbance_type" label="扰动类型" style={{ width: 220 }}>
                  <Select options={disturbanceTypeOptions} />
                </Form.Item>
                <Form.Item name="evidence_note" label="线索证据备注" style={{ width: 520 }}>
                  <Input.TextArea rows={2} placeholder="例如：仅记录照片可见现象；需专业人员现场核实，未触碰疑似对象。" />
                </Form.Item>
                <Form.Item name="protection_note" label="现场保护/上报备注" style={{ width: 520 }}>
                  <Input placeholder="例如：已保持现场，未触碰疑似对象；拟联系当地文物主管部门核实。" />
                </Form.Item>
              </Space>
            </>
          )}
          <Space wrap size={14} align="start">
            <Form.Item name="target_direction" label="目标方向" style={{ width: 180 }}>
              <Select allowClear options={directionOptions} />
            </Form.Item>
            <Form.Item name="water_direction" label="水体方向" style={{ width: 180 }}>
              <Select allowClear options={directionOptions} />
            </Form.Item>
            <Form.Item name="road_direction" label="道路方向" style={{ width: 180 }}>
              <Select allowClear options={directionOptions} />
            </Form.Item>
            <Form.Item name="tianxing_mountain" label="天星/二十四山校正" style={{ width: 180 }}>
              <Select allowClear options={directionOptions.slice(8)} />
            </Form.Item>
          </Space>
          <Form.Item name="note" label="补充说明">
            <Input.TextArea rows={3} placeholder="例如：前方为道路，左侧有水体，远处有高楼遮挡；照片视角仅朝向大门外。" />
          </Form.Item>
        </Form>
      </PaperCard>

      <PaperCard title="外局拍照记录" extra={`共 ${records.length} 条`}>
        <Table
          rowKey="id"
          dataSource={records}
          columns={columns}
          pagination={{ pageSize: 8 }}
          locale={{ emptyText: <Empty description="暂无外局拍照记录" image={Empty.PRESENTED_IMAGE_SIMPLE} /> }}
        />
      </PaperCard>
    </div>
  );
}
