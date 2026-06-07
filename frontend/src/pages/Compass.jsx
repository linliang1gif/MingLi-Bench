import React, { useEffect, useRef, useState } from 'react';
import {
  Alert,
  Button,
  Form,
  Input,
  InputNumber,
  message,
  Popconfirm,
  Select,
  Segmented,
  Space,
  Statistic,
  Table,
  Tag,
} from 'antd';
import api from '../services/api';
import PageBanner from '../components/PageBanner';
import PaperCard from '../components/PaperCard';

const direction24 = ['子', '癸', '丑', '艮', '寅', '甲', '卯', '乙', '辰', '巽', '巳', '丙', '午', '丁', '未', '坤', '申', '庚', '酉', '辛', '戌', '乾', '亥', '壬'];
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

function normalizeDegree(value) {
  const num = Number(value);
  if (!Number.isFinite(num)) return null;
  return ((num % 360) + 360) % 360;
}

function convertLocal(value) {
  const degree = normalizeDegree(value);
  if (degree == null) return null;
  const dirs = ['北', '东北', '东', '东南', '南', '西南', '西', '西北'];
  const direction8 = dirs[Math.floor(((degree + 22.5) % 360) / 45)];
  const mountain = direction24[Math.floor(((degree + 7.5) % 360) / 15)];
  return {
    degree: Number(degree.toFixed(1)),
    direction_8: direction8,
    direction_24: mountain,
  };
}

function angularDistance(a, b) {
  const diff = Math.abs(a - b) % 360;
  return diff > 180 ? 360 - diff : diff;
}

function stabilityFromSamples(samples) {
  if (samples.length < 4) return null;
  const latest = samples[samples.length - 1];
  const maxDiff = Math.max(...samples.map((v) => angularDistance(v, latest)));
  return Math.max(0, Math.min(100, Math.round(100 - maxDiff * 5)));
}

export default function Compass() {
  const [form] = Form.useForm();
  const [recordForm] = Form.useForm();
  const [houses, setHouses] = useState([]);
  const [records, setRecords] = useState([]);
  const [result, setResult] = useState(null);
  const [mode, setMode] = useState('manual');
  const [measuring, setMeasuring] = useState(false);
  const [sensorError, setSensorError] = useState('');
  const [samples, setSamples] = useState([]);
  const [busy, setBusy] = useState(false);
  const [saving, setSaving] = useState(false);
  const listenerRef = useRef(null);

  const stabilityScore = stabilityFromSamples(samples);
  const unstable = stabilityScore != null && stabilityScore < 65;

  function refreshRecords() {
    api.listCompassRecords().then(setRecords).catch(() => setRecords([]));
  }

  useEffect(() => {
    api.listHouses().then(setHouses).catch(() => setHouses([]));
    refreshRecords();
    return () => {
      if (listenerRef.current) {
        window.removeEventListener('deviceorientationabsolute', listenerRef.current);
        window.removeEventListener('deviceorientation', listenerRef.current);
      }
    };
  }, []);

  function applyMeasuredDegree(degree) {
    const converted = convertLocal(degree);
    if (!converted) return;
    setResult(converted);
    setSamples((prev) => {
      const next = [...prev.slice(-11), converted.degree];
      recordForm.setFieldsValue({
        degree: converted.degree,
        stability_score: stabilityFromSamples(next),
      });
      return next;
    });
  }

  async function onConvert() {
    const values = await form.validateFields();
    setBusy(true);
    try {
      const converted = await api.convertCompass(values.degree);
      setResult(converted);
      setSamples([]);
      recordForm.setFieldsValue({ degree: converted.degree, stability_score: null });
    } catch (e) {
      message.error(e.message || '换算失败');
    } finally {
      setBusy(false);
    }
  }

  async function startMeasure() {
    if (!('DeviceOrientationEvent' in window)) {
      setSensorError('当前浏览器不支持方向传感器，请使用手动输入角度。');
      return;
    }
    try {
      if (typeof window.DeviceOrientationEvent.requestPermission === 'function') {
        const state = await window.DeviceOrientationEvent.requestPermission();
        if (state !== 'granted') {
          setSensorError('方向传感器权限未开启，请授权后再测量。');
          return;
        }
      }
    } catch {
      setSensorError('方向传感器权限请求失败，请改用手动输入。');
      return;
    }

    setSensorError('');
    setSamples([]);
    const listener = (event) => {
      const raw = typeof event.webkitCompassHeading === 'number'
        ? event.webkitCompassHeading
        : typeof event.alpha === 'number'
          ? 360 - event.alpha
          : null;
      if (raw == null) return;
      applyMeasuredDegree(raw);
    };
    listenerRef.current = listener;
    window.addEventListener('deviceorientationabsolute', listener);
    window.addEventListener('deviceorientation', listener);
    setMeasuring(true);
  }

  function stopMeasure() {
    if (listenerRef.current) {
      window.removeEventListener('deviceorientationabsolute', listenerRef.current);
      window.removeEventListener('deviceorientation', listenerRef.current);
      listenerRef.current = null;
    }
    setMeasuring(false);
  }

  async function onSaveRecord() {
    const values = await recordForm.validateFields();
    setSaving(true);
    try {
      await api.createCompassRecord(values);
      message.success('罗盘记录已保存');
      refreshRecords();
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
      refreshRecords();
    } catch (e) {
      message.error(e.message || '删除失败');
    }
  }

  const columns = [
    { title: '房屋', dataIndex: 'house_id', width: 120, render: (v) => houses.find((h) => h.id === v)?.name || '—' },
    { title: '场景', dataIndex: 'scene_type', width: 100 },
    { title: '对象', dataIndex: 'object_type', width: 110 },
    { title: '角度', dataIndex: 'degree', width: 90, render: (v) => `${v}°` },
    { title: '八方', dataIndex: 'direction_8', width: 90, render: (v) => <Tag color="blue">{v}</Tag> },
    { title: '二十四山', dataIndex: 'direction_24', width: 110, render: (v) => <Tag color="gold">{v}</Tag> },
    { title: '稳定性', dataIndex: 'stability_score', width: 90, render: (v) => (v == null ? '—' : `${v}`) },
    { title: '备注', dataIndex: 'note', render: (v) => v || '—' },
    {
      title: '操作',
      width: 90,
      render: (_, r) => (
        <Popconfirm title="删除这个测点？" onConfirm={() => onDeleteRecord(r.id)}>
          <Button size="small" danger>删除</Button>
        </Popconfirm>
      ),
    },
  ];

  return (
    <div>
      <PageBanner title="罗盘测向" subtitle="H5 真实测向与手动角度换算，并保存房屋测点" quote="一度一山，分金有位。" />

      <PaperCard title="测向模式" style={{ marginBottom: 18 }}>
        <Space direction="vertical" style={{ width: '100%' }} size={16}>
          <Segmented
            value={mode}
            onChange={(v) => setMode(v)}
            options={[
              { value: 'manual', label: '手动输入' },
              { value: 'sensor', label: '真实测向' },
            ]}
          />

          {mode === 'manual' ? (
            <Form form={form} layout="inline" initialValues={{ degree: 90 }}>
              <Form.Item name="degree" label="角度" rules={[{ required: true }]}>
                <InputNumber min={0} max={360} style={{ width: 180 }} />
              </Form.Item>
              <Button type="primary" loading={busy} onClick={onConvert}>换算</Button>
            </Form>
          ) : (
            <Space direction="vertical" style={{ width: '100%' }} size={12}>
              <Space>
                <Button type="primary" disabled={measuring} onClick={startMeasure}>开始测量</Button>
                <Button disabled={!measuring} onClick={stopMeasure}>停止测量</Button>
              </Space>
              {sensorError && <Alert type="warning" showIcon message={sensorError} />}
              {unstable && <Alert type="warning" showIcon message="角度波动较大，请远离金属或重新校准" />}
            </Space>
          )}

          {result && (
            <Space wrap>
              <Statistic title="当前角度" value={result.degree} suffix="°" precision={1} />
              <Tag color="blue">八方：{result.direction_8}</Tag>
              <Tag color="gold">二十四山：{result.direction_24}</Tag>
              {stabilityScore != null && <Tag color={unstable ? 'orange' : 'green'}>稳定性：{stabilityScore}</Tag>}
            </Space>
          )}
        </Space>
      </PaperCard>

      <PaperCard title="保存测点" style={{ marginBottom: 18 }}>
        <Form
          form={recordForm}
          layout="inline"
          initialValues={{ scene_type: 'indoor', object_type: 'main_door' }}
        >
          <Form.Item name="house_id" label="房屋" style={{ width: 220 }}>
            <Select allowClear options={houses.map((h) => ({ value: h.id, label: h.name }))} />
          </Form.Item>
          <Form.Item name="scene_type" label="场景" rules={[{ required: true }]} style={{ width: 150 }}>
            <Select options={sceneOptions} />
          </Form.Item>
          <Form.Item name="object_type" label="对象" rules={[{ required: true }]} style={{ width: 160 }}>
            <Select options={objectOptions} />
          </Form.Item>
          <Form.Item name="degree" label="角度" rules={[{ required: true }]}>
            <InputNumber min={0} max={360} style={{ width: 150 }} />
          </Form.Item>
          <Form.Item name="stability_score" hidden><InputNumber /></Form.Item>
          <Form.Item name="note" label="备注"><Input style={{ width: 220 }} /></Form.Item>
          <Button loading={saving} onClick={onSaveRecord}>保存测点</Button>
        </Form>
      </PaperCard>

      <PaperCard title="测点记录" extra={`共 ${records.length} 条`}>
        <Table rowKey="id" dataSource={records} columns={columns} pagination={{ pageSize: 10 }} />
      </PaperCard>
    </div>
  );
}
