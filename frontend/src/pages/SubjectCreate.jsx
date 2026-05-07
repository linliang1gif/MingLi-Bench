import React, { useState } from 'react';
import { Form, Input, Select, DatePicker, TimePicker, Button, Checkbox, message, Space } from 'antd';
import { useNavigate } from 'react-router-dom';
import dayjs from 'dayjs';
import api from '../services/api';
import PageBanner from '../components/PageBanner';
import PaperCard from '../components/PaperCard';

const FOCUS = ['财运', '事业', '感情', '健康', '学业', '家庭', '流年'];

export default function SubjectCreate() {
  const nav = useNavigate();
  const [form] = Form.useForm();
  const [submitting, setSubmitting] = useState(false);

  async function onSubmit(values) {
    setSubmitting(true);
    try {
      const payload = {
        nickname: values.nickname,
        gender: values.gender,
        birth_date: values.birth_date ? dayjs(values.birth_date).format('YYYY-MM-DD') : undefined,
        birth_time: values.birth_time ? dayjs(values.birth_time).format('HH:mm') : undefined,
        birth_place: values.birth_place,
        calendar_type: values.calendar_type || 'solar',
        focus_topics: values.focus_topics || [],
        notes: values.notes,
      };
      const created = await api.createSubject(payload);
      // 自动生成命盘
      try { await api.generateChart(created.id); } catch { /* ignore */ }
      message.success('命主已创建');
      nav('/subjects');
    } catch (e) {
      message.error(e.message || '创建失败');
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div>
      <PageBanner
        title="新建命主"
        subtitle="填写基础信息，平台将自动推算简化版命盘"
        quote="名以载主，盘以载命。"
      />
      <PaperCard title="基础信息" extra="出生时间越准确，命盘越可靠">
        <Form
          form={form}
          layout="vertical"
          initialValues={{ calendar_type: 'solar', gender: '男' }}
          onFinish={onSubmit}
          style={{ maxWidth: 720 }}
        >
          <Form.Item name="nickname" label="称呼" rules={[{ required: true, message: '请输入称呼' }]}>
            <Input maxLength={32} placeholder="例如：自己 / 阿明" />
          </Form.Item>

          <Space size={20} wrap>
            <Form.Item name="gender" label="性别" style={{ width: 160 }}>
              <Select options={[
                { value: '男', label: '男' },
                { value: '女', label: '女' },
                { value: '其他', label: '其他' },
              ]} />
            </Form.Item>
            <Form.Item name="calendar_type" label="历法" style={{ width: 160 }}>
              <Select options={[
                { value: 'solar', label: '公历' },
                { value: 'lunar', label: '农历' },
              ]} />
            </Form.Item>
            <Form.Item name="birth_date" label="出生日期" rules={[{ required: true, message: '请选择出生日期' }]} style={{ width: 200 }}>
              <DatePicker style={{ width: '100%' }} />
            </Form.Item>
            <Form.Item name="birth_time" label="出生时辰" style={{ width: 200 }}>
              <TimePicker format="HH:mm" minuteStep={5} style={{ width: '100%' }} />
            </Form.Item>
          </Space>

          <Form.Item name="birth_place" label="出生地">
            <Input maxLength={64} placeholder="省 / 市 / 区，可留空" />
          </Form.Item>

          <Form.Item name="focus_topics" label="重点关注方向">
            <Checkbox.Group>
              <Space wrap>
                {FOCUS.map((t) => <Checkbox key={t} value={t}>{t}</Checkbox>)}
              </Space>
            </Checkbox.Group>
          </Form.Item>

          <Form.Item name="notes" label="备注">
            <Input.TextArea rows={3} placeholder="可选：补充背景信息" />
          </Form.Item>

          <Space>
            <Button type="primary" htmlType="submit" loading={submitting}>创建命主</Button>
            <Button onClick={() => nav(-1)}>取消</Button>
          </Space>
        </Form>
      </PaperCard>
    </div>
  );
}
