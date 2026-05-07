import React, { useEffect, useState } from 'react';
import { Button, Table, Space, Popconfirm, Empty, message } from 'antd';
import { PlusOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import api from '../services/api';
import PageBanner from '../components/PageBanner';
import PaperCard from '../components/PaperCard';

export default function Subjects() {
  const navigate = useNavigate();
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(true);

  function refresh() {
    setLoading(true);
    api.listSubjects()
      .then(setRows)
      .catch(() => setRows([]))
      .finally(() => setLoading(false));
  }
  useEffect(refresh, []);

  const columns = [
    { title: '称呼', dataIndex: 'nickname', render: (v) => <span style={{ fontFamily: 'var(--ml-font-serif)' }}>{v}</span> },
    { title: '性别', dataIndex: 'gender', width: 80 },
    { title: '出生', render: (_, r) => `${r.birth_date || '—'} ${r.birth_time || ''}` },
    { title: '出生地', dataIndex: 'birth_place', ellipsis: true },
    {
      title: '关注方向',
      dataIndex: 'focus_topics',
      render: (v) => Array.isArray(v) && v.length ? v.join(' · ') : '—',
    },
    {
      title: '操作',
      width: 160,
      render: (_, r) => (
        <Space>
          <Button size="small" onClick={() => navigate(`/chart/${r.id}`)}>命盘</Button>
          <Popconfirm
            title="删除该命主？"
            description="删除后会同步移除其命盘 / 对话 / 报告。"
            onConfirm={async () => {
              try {
                await api.deleteSubject(r.id);
                message.success('已删除');
                refresh();
              } catch (e) { message.error(e.message || '删除失败'); }
            }}
          >
            <Button size="small" danger>删除</Button>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <div>
      <PageBanner
        title="命主档案"
        subtitle="管理你创建的命主基础信息"
        quote="盘为据，主为本。"
        extra={
          <Button type="primary" icon={<PlusOutlined />} onClick={() => navigate('/subjects/new')}>
            新建命主
          </Button>
        }
      />
      <PaperCard title="命主列表" extra={`共 ${rows.length} 位`}>
        {rows.length === 0 && !loading ? (
          <Empty description="尚未创建命主" image={Empty.PRESENTED_IMAGE_SIMPLE} />
        ) : (
          <Table rowKey="id" loading={loading} dataSource={rows} columns={columns} pagination={false} />
        )}
      </PaperCard>
    </div>
  );
}
