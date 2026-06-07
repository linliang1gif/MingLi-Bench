import React, { useEffect, useState } from 'react';
import { Button, Empty, Form, Input, InputNumber, message, Modal, Space, Table, Tag } from 'antd';
import { useNavigate } from 'react-router-dom';
import api from '../services/api';
import PageBanner from '../components/PageBanner';
import PaperCard from '../components/PaperCard';

export default function HouseProfiles() {
  const navigate = useNavigate();
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(true);
  const [modalOpen, setModalOpen] = useState(false);
  const [saving, setSaving] = useState(false);
  const [form] = Form.useForm();

  function refresh() {
    setLoading(true);
    api.listHouses()
      .then(setRows)
      .catch((e) => {
        message.error(e.message || '读取房屋档案失败');
        setRows([]);
      })
      .finally(() => setLoading(false));
  }

  useEffect(refresh, []);

  async function onSave() {
    const values = await form.validateFields();
    setSaving(true);
    try {
      await api.createHouse(values);
      message.success('房屋档案已新增');
      setModalOpen(false);
      refresh();
    } catch (e) {
      message.error(e.message || '保存失败');
    } finally {
      setSaving(false);
    }
  }

  const columns = [
    { title: '名称', dataIndex: 'name', render: (v) => <b>{v}</b> },
    { title: '类型', dataIndex: 'house_type', width: 120, render: (v) => v || '—' },
    { title: '入住日期', dataIndex: 'move_in_date', width: 120, render: (v) => v || '—' },
    {
      title: '大门坐向',
      width: 180,
      render: (_, r) => r.main_door_degree == null ? '—' : (
        <Space>
          <Tag>{r.main_door_degree}°</Tag>
          <Tag color="blue">{r.main_door_direction_8}</Tag>
          <Tag color="gold">{r.main_door_direction_24}</Tag>
        </Space>
      ),
    },
    { title: '地址备注', dataIndex: 'address_note', ellipsis: true, render: (v) => v || '—' },
    { title: '操作', width: 90, render: (_, r) => <Button size="small" onClick={() => navigate(`/houses/${r.id}`)}>查看</Button> },
  ];

  return (
    <div>
      <PageBanner
        title="房屋档案"
        subtitle="记录住宅、办公室、店铺与罗盘测点"
        quote="宅有其形，向有其度。"
        extra={
          <Space>
            <Button onClick={refresh}>刷新</Button>
            <Button type="primary" onClick={() => { form.resetFields(); setModalOpen(true); }}>新增房屋</Button>
          </Space>
        }
      />
      <PaperCard title="房屋列表" extra={`共 ${rows.length} 处`}>
        {rows.length === 0 && !loading ? (
          <Empty description="暂无房屋档案" image={Empty.PRESENTED_IMAGE_SIMPLE} />
        ) : (
          <Table rowKey="id" loading={loading} dataSource={rows} columns={columns} pagination={{ pageSize: 10 }} />
        )}
      </PaperCard>

      <Modal title="新增房屋档案" open={modalOpen} onCancel={() => setModalOpen(false)} onOk={onSave} confirmLoading={saving} width={760}>
        <Form form={form} layout="vertical">
          <Space style={{ width: '100%' }} size={12}>
            <Form.Item name="name" label="名称" rules={[{ required: true }]} style={{ width: 220 }}><Input /></Form.Item>
            <Form.Item name="house_type" label="类型" style={{ width: 160 }}><Input placeholder="住宅/店铺/办公室" /></Form.Item>
            <Form.Item name="build_year" label="建成年份" style={{ width: 130 }}><InputNumber style={{ width: '100%' }} /></Form.Item>
            <Form.Item name="move_in_date" label="入住日期" style={{ width: 150 }}><Input placeholder="YYYY-MM-DD" /></Form.Item>
          </Space>
          <Form.Item name="address_note" label="地址备注"><Input /></Form.Item>
          <Form.Item name="main_door_degree" label="大门角度"><InputNumber min={0} max={360} style={{ width: 180 }} /></Form.Item>
          <Form.Item name="floorplan_note" label="户型备注"><Input.TextArea rows={4} /></Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
