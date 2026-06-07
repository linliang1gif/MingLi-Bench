import React, { useEffect, useMemo, useState } from 'react';
import {
  Alert,
  Button,
  Descriptions,
  Empty,
  Form,
  InputNumber,
  message,
  Select,
  Space,
  Spin,
  Switch,
  Table,
  Tag,
} from 'antd';
import { useNavigate } from 'react-router-dom';
import api from '../services/api';
import AnalysisModeSelector from '../components/AnalysisModeSelector';
import PageBanner from '../components/PageBanner';
import PaperCard from '../components/PaperCard';

const palaceColors = {
  center: '#F4EBD6',
  qian: '#E9EEF1',
  dui: '#F2E7E2',
  gen: '#EAF1E7',
  li: '#F7E1D8',
  kan: '#E2EBF2',
  kun: '#EFE6D8',
  zhen: '#E5F0EA',
  xun: '#E7EFEA',
};

function yearFromDate(value) {
  const year = Number(String(value || '').slice(0, 4));
  return Number.isFinite(year) && year > 0 ? year : undefined;
}

function XuanKongGrid({ result }) {
  const cells = result?.grid || [];
  if (!cells.length) {
    return <Empty description="计算后展示九宫飞星基础盘" image={Empty.PRESENTED_IMAGE_SIMPLE} />;
  }
  return (
    <div
      style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(3, minmax(120px, 1fr))',
        gap: 10,
        maxWidth: 620,
      }}
    >
      {cells.map((cell) => (
        <div
          key={cell.key}
          style={{
            minHeight: 118,
            border: '1px solid var(--ml-border)',
            borderRadius: 8,
            background: palaceColors[cell.key] || 'var(--ml-card-bg)',
            padding: 12,
            display: 'flex',
            flexDirection: 'column',
            justifyContent: 'space-between',
          }}
        >
          <Space style={{ justifyContent: 'space-between', width: '100%' }}>
            <b style={{ fontFamily: 'var(--ml-font-serif)', color: 'var(--ml-text)' }}>{cell.name}</b>
            <Tag color="gold">{cell.direction}</Tag>
          </Space>
          <div style={{ display: 'flex', alignItems: 'baseline', gap: 12 }}>
            <span style={{ fontSize: 30, fontWeight: 700, color: 'var(--ml-text)' }}>
              {cell.base_star}
            </span>
            <span style={{ color: 'var(--ml-text-sub)' }}>运星</span>
          </div>
          <Space>
            <Tag color="blue">年星 {cell.annual_star}</Tag>
            <Tag>{cell.trigram}</Tag>
          </Space>
        </div>
      ))}
    </div>
  );
}

export default function XuanKong() {
  const navigate = useNavigate();
  const [form] = Form.useForm();
  const [houses, setHouses] = useState([]);
  const [records, setRecords] = useState([]);
  const [loading, setLoading] = useState(true);
  const [calcBusy, setCalcBusy] = useState(false);
  const [reportBusy, setReportBusy] = useState(false);
  const [result, setResult] = useState(null);
  const [record, setRecord] = useState(null);
  const [useHouseDoor, setUseHouseDoor] = useState(true);
  const [analysisMode, setAnalysisMode] = useState('safe');

  const selectedHouseId = Form.useWatch('house_id', form);
  const selectedHouse = useMemo(
    () => houses.find((h) => h.id === selectedHouseId),
    [houses, selectedHouseId],
  );

  function refreshRecords(houseId = selectedHouseId) {
    api.listXuanKongRecords(houseId ? { house_id: houseId } : undefined)
      .then(setRecords)
      .catch(() => setRecords([]));
  }

  useEffect(() => {
    setLoading(true);
    api.listHouses()
      .then((rows) => {
        setHouses(rows);
        if (rows[0]) {
          const house = rows[0];
          form.setFieldsValue({
            house_id: house.id,
            build_year: house.build_year || new Date().getFullYear(),
            move_in_year: yearFromDate(house.move_in_date),
            annual_year: new Date().getFullYear(),
            facing_degree: house.main_door_degree ?? 180,
          });
          refreshRecords(house.id);
        } else {
          form.setFieldsValue({
            build_year: new Date().getFullYear(),
            annual_year: new Date().getFullYear(),
            facing_degree: 180,
          });
        }
      })
      .catch((e) => message.error(e.message || '读取房屋档案失败'))
      .finally(() => setLoading(false));
  }, []);

  function onHouseChange(houseId) {
    const house = houses.find((h) => h.id === houseId);
    setResult(null);
    setRecord(null);
    if (house) {
      form.setFieldsValue({
        build_year: house.build_year || form.getFieldValue('build_year'),
        move_in_year: yearFromDate(house.move_in_date),
        facing_degree: house.main_door_degree ?? form.getFieldValue('facing_degree'),
      });
    }
    refreshRecords(houseId);
  }

  async function onCalculate() {
    const values = await form.validateFields();
    if (useHouseDoor && !values.house_id) {
      message.warning('使用主门朝向时，请先选择房屋档案');
      return;
    }
    if (useHouseDoor && selectedHouse?.main_door_degree == null) {
      message.warning('该房屋暂无主门角度，请先在房屋档案中设置，或改用手动角度');
      return;
    }
    setCalcBusy(true);
    try {
      const payload = {
        house_id: values.house_id,
        build_year: values.build_year,
        move_in_year: values.move_in_year,
        annual_year: values.annual_year,
        facing_degree: useHouseDoor ? undefined : values.facing_degree,
        use_house_main_door: useHouseDoor,
      };
      const res = await api.calculateXuanKong(payload);
      setResult(res.result);
      setRecord(res.record || null);
      if (values.house_id) refreshRecords(values.house_id);
      message.success(res.record ? '玄空盘已计算并保存' : '玄空盘已计算');
    } catch (e) {
      message.error(e.message || '计算失败');
    } finally {
      setCalcBusy(false);
    }
  }

  async function onGenerateReport() {
    const values = await form.validateFields();
    if (!values.house_id) {
      message.warning('生成玄空报告需要先选择房屋档案');
      return;
    }
    if (useHouseDoor && selectedHouse?.main_door_degree == null) {
      message.warning('该房屋暂无主门角度，请先设置主门朝向，或改用手动角度');
      return;
    }
    setReportBusy(true);
    try {
      const report = await api.generateXuanKongReport({
        house_id: values.house_id,
        build_year: values.build_year,
        move_in_year: values.move_in_year,
        annual_year: values.annual_year,
        facing_degree: useHouseDoor ? undefined : values.facing_degree,
        use_house_main_door: useHouseDoor,
        analysisMode,
      });
      message.success('玄空飞星报告已生成');
      navigate(`/reports/${report.id}`);
    } catch (e) {
      message.error(e.message || '生成报告失败');
    } finally {
      setReportBusy(false);
    }
  }

  const historyColumns = [
    { title: '时间', dataIndex: 'created_at', width: 170, render: (v) => v ? String(v).replace('T', ' ').slice(0, 16) : '—' },
    { title: '建成年份', dataIndex: 'build_year', width: 100 },
    { title: '入住年份', dataIndex: 'move_in_year', width: 100, render: (v) => v || '—' },
    { title: '运', dataIndex: 'period', width: 90, render: (v) => <Tag color="blue">{v}</Tag> },
    { title: '朝向', dataIndex: 'facing_degree', width: 90, render: (v) => `${v}°` },
    { title: '坐向', width: 130, render: (_, r) => <Tag color="gold">坐{r.sitting_direction_24}向{r.facing_direction_24}</Tag> },
  ];

  if (loading) return <Spin />;

  return (
    <div>
      <PageBanner
        title="玄空飞星"
        subtitle="三元九运、二十四山坐向与简化九宫飞星基础盘"
        quote="一运入中，九宫成局。"
        extra={
          <Space>
            <Button onClick={onCalculate} loading={calcBusy}>计算玄空盘</Button>
            <AnalysisModeSelector value={analysisMode} onChange={setAnalysisMode} />
            <Button type="primary" onClick={onGenerateReport} loading={reportBusy}>生成玄空报告</Button>
          </Space>
        }
      />

      <PaperCard title="计算条件" style={{ marginBottom: 18 }}>
        <Form form={form} layout="vertical">
          <Space size={14} wrap align="start">
            <Form.Item name="house_id" label="房屋档案" style={{ width: 240 }}>
              <Select
                allowClear
                placeholder="选择房屋"
                onChange={onHouseChange}
                options={houses.map((h) => ({ value: h.id, label: h.name }))}
              />
            </Form.Item>
            <Form.Item name="build_year" label="建成年份" rules={[{ required: true }]}>
              <InputNumber min={1800} max={2200} style={{ width: 140 }} />
            </Form.Item>
            <Form.Item name="move_in_year" label="入住年份">
              <InputNumber min={1800} max={2200} style={{ width: 140 }} />
            </Form.Item>
            <Form.Item name="annual_year" label="年星年份">
              <InputNumber min={1800} max={2200} style={{ width: 140 }} />
            </Form.Item>
            <Form.Item label="使用主门朝向">
              <Switch checked={useHouseDoor} onChange={setUseHouseDoor} />
            </Form.Item>
            {!useHouseDoor && (
              <Form.Item name="facing_degree" label="手动朝向角度" rules={[{ required: true }]}>
                <InputNumber min={0} max={360} style={{ width: 150 }} />
              </Form.Item>
            )}
          </Space>
        </Form>
        {useHouseDoor && selectedHouse?.main_door_degree == null && (
          <Alert
            type="warning"
            showIcon
            message="当前房屋暂无主门角度"
            description="可在房屋详情中从大门测点同步主门朝向，或关闭开关后手动输入朝向角度。"
          />
        )}
      </PaperCard>

      <PaperCard title="玄空基础盘" style={{ marginBottom: 18 }}>
        {result ? (
          <Space direction="vertical" size={16} style={{ width: '100%' }}>
            <Descriptions bordered size="small" column={3}>
              <Descriptions.Item label="三元九运">
                <Tag color="blue">{result.period.period}</Tag>
                {result.period.cycle_start}-{result.period.cycle_end}
              </Descriptions.Item>
              <Descriptions.Item label="朝向">
                {result.facing.degree}° · {result.facing.facing_direction_24}
              </Descriptions.Item>
              <Descriptions.Item label="坐山">
                {result.facing.sitting_direction_24}
              </Descriptions.Item>
              <Descriptions.Item label="坐向">
                坐{result.facing.sitting_direction_24}向{result.facing.facing_direction_24}
              </Descriptions.Item>
              <Descriptions.Item label="中宫运星">{result.base_star.center_star}</Descriptions.Item>
              <Descriptions.Item label="中宫年星">{result.annual_star.center_star}</Descriptions.Item>
            </Descriptions>
            <Alert type="info" showIcon message={result.method_note} />
            {record && <Tag color="green">已保存记录 #{record.id}</Tag>}
            <XuanKongGrid result={result} />
          </Space>
        ) : (
          <XuanKongGrid result={null} />
        )}
      </PaperCard>

      <PaperCard title="玄空计算记录" extra={`共 ${records.length} 条`}>
        <Table
          rowKey="id"
          dataSource={records}
          columns={historyColumns}
          pagination={{ pageSize: 8 }}
          locale={{ emptyText: <Empty description="暂无玄空记录" image={Empty.PRESENTED_IMAGE_SIMPLE} /> }}
        />
      </PaperCard>
    </div>
  );
}
