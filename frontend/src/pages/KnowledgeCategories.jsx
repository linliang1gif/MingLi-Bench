import React, { useEffect, useState } from 'react';
import { Button, Empty, message, Space, Table, Tag } from 'antd';
import api from '../services/api';
import PageBanner from '../components/PageBanner';
import PaperCard from '../components/PaperCard';

const priorityColor = {
  P0: 'green',
  P1: 'blue',
  P2: 'gold',
  P3: 'orange',
  P4: 'red',
};

export default function KnowledgeCategories() {
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(true);
  const [initBusy, setInitBusy] = useState(false);

  function refresh() {
    setLoading(true);
    api.listCategories()
      .then(setRows)
      .catch((e) => {
        message.error(e.message || '读取知识类目失败');
        setRows([]);
      })
      .finally(() => setLoading(false));
  }

  useEffect(refresh, []);

  async function onInit() {
    setInitBusy(true);
    try {
      const res = await api.initCategories();
      message.success(`初始化完成，新增 ${res.inserted || 0} 条`);
      refresh();
    } catch (e) {
      message.error(e.message || '初始化失败');
    } finally {
      setInitBusy(false);
    }
  }

  const columns = [
    { title: '编号', dataIndex: 'code', width: 80 },
    { title: '类目', dataIndex: 'name', render: (v) => <b>{v}</b> },
    {
      title: '优先级',
      dataIndex: 'priority',
      width: 100,
      render: (v) => <Tag color={priorityColor[v] || 'default'}>{v || 'P2'}</Tag>,
    },
    {
      title: '状态',
      dataIndex: 'enabled',
      width: 90,
      render: (v) => <Tag color={v ? 'green' : 'default'}>{v ? '启用' : '停用'}</Tag>,
    },
    { title: '说明', dataIndex: 'description', render: (v) => v || '—' },
  ];

  return (
    <div>
      <PageBanner
        title="知识类目"
        subtitle="AI 易学传统文化私人工具平台的 60 大知识目录"
        quote="先立纲目，再收群书。"
        extra={
          <Space>
            <Button onClick={refresh}>刷新</Button>
            <Button type="primary" loading={initBusy} onClick={onInit}>初始化 60 类</Button>
          </Space>
        }
      />
      <PaperCard title="60 大知识类目" extra={`共 ${rows.length} 类`}>
        {rows.length === 0 && !loading ? (
          <Empty description="暂无类目，点击初始化 60 类" image={Empty.PRESENTED_IMAGE_SIMPLE} />
        ) : (
          <Table
            rowKey="code"
            loading={loading}
            dataSource={rows}
            columns={columns}
            pagination={{ pageSize: 20 }}
          />
        )}
      </PaperCard>
    </div>
  );
}
