import React, { useEffect, useMemo, useState } from 'react';
import {
  Alert,
  App as AntdApp,
  Button,
  Collapse,
  Descriptions,
  Empty,
  List,
  Space,
  Spin,
  Statistic,
  Table,
  Tag,
  Typography,
} from 'antd';
import dayjs from 'dayjs';
import api from '../services/api';
import PageBanner from '../components/PageBanner';
import PaperCard from '../components/PaperCard';

const { Text } = Typography;

const MODULE_LABELS = {
  reports: '报告中心',
  knowledge: '古籍知识库',
  system: '系统自检',
};

function okTag(ok, yes = '正常', no = '异常') {
  return <Tag color={ok ? 'green' : 'red'}>{ok ? yes : no}</Tag>;
}

function fmtTime(ts) {
  return ts ? dayjs(ts).format('YYYY-MM-DD HH:mm') : '暂无';
}

export default function SystemCheck() {
  const { message } = AntdApp.useApp();
  const [check, setCheck] = useState(null);
  const [testCases, setTestCases] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [backupBusy, setBackupBusy] = useState(false);
  const [backupPath, setBackupPath] = useState('');

  async function load() {
    setLoading(true);
    setError('');
    try {
      const [checkRes, casesRes] = await Promise.all([
        api.systemCheck(),
        api.getSystemTestCases(),
      ]);
      setCheck(checkRes);
      setTestCases(casesRes);
    } catch (e) {
      setError(e.message || '系统自检读取失败');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  async function onBackup() {
    setBackupBusy(true);
    setBackupPath('');
    try {
      const res = await api.backupDatabase();
      setBackupPath(res.backup_path || '');
      message.success('数据库备份完成');
    } catch (e) {
      message.error(e.message || '数据库备份失败');
    } finally {
      setBackupBusy(false);
    }
  }

  const counts = check?.counts || {};
  const tableRows = useMemo(
    () => Object.entries(check?.tables || {}).map(([name, exists]) => ({ name, exists })),
    [check],
  );
  const cases = testCases?.cases || [];
  const backups = check?.backups || {};
  const groupedCases = useMemo(() => {
    return cases.reduce((acc, item) => {
      const key = item.module || 'other';
      if (!acc[key]) acc[key] = [];
      acc[key].push(item);
      return acc;
    }, {});
  }, [cases]);

  const caseColumns = [
    { title: '编号', dataIndex: 'id', width: 170 },
    { title: '模块', dataIndex: 'module', width: 110 },
    { title: '样例', dataIndex: 'title', width: 180 },
    {
      title: '输入',
      dataIndex: 'input',
      render: (value) => (
        <Text style={{ whiteSpace: 'pre-wrap' }}>
          {JSON.stringify(value || {}, null, 2)}
        </Text>
      ),
    },
    {
      title: '验收点',
      dataIndex: 'expected_checks',
      render: (items) => (
        <List
          size="small"
          dataSource={items || []}
          renderItem={(item) => <List.Item style={{ padding: '2px 0' }}>{item}</List.Item>}
        />
      ),
    },
  ];

  return (
    <div>
      <PageBanner
        title="系统自检"
        subtitle="后端、LLM、数据库、核心表、样例数据与备份能力"
        quote="可查，方可久用。"
        extra={
          <Space>
            <Button onClick={load}>刷新</Button>
            <Button type="primary" loading={backupBusy} onClick={onBackup}>
              立即备份数据库
            </Button>
          </Space>
        }
      />

      {loading ? (
        <PaperCard>
          <div style={{ display: 'flex', justifyContent: 'center', padding: 36 }}><Spin /></div>
        </PaperCard>
      ) : error ? (
        <Alert type="error" showIcon message="系统自检失败" description={error} />
      ) : !check ? (
        <PaperCard>
          <Empty description="暂无自检数据" image={Empty.PRESENTED_IMAGE_SIMPLE} />
        </PaperCard>
      ) : (
        <Space direction="vertical" size={16} style={{ width: '100%' }}>
          <PaperCard title="运行状态">
            <Space size={16} wrap>
              <Statistic title="系统版本" value={check.version || 'unknown'} />
              <Statistic title="知识类目" value={counts.categories_count || 0} />
              <Statistic title="风险词" value={counts.risk_terms_count || 0} />
              <Statistic title="Prompt 模板" value={counts.prompt_templates_count || 0} />
              <Statistic title="报告" value={counts.reports_count || 0} />
            </Space>
            <Descriptions
              style={{ marginTop: 18 }}
              size="small"
              column={1}
              bordered
              items={[
                {
                  key: 'version',
                  label: '版本',
                  children: <Tag color="blue">{check.version || 'unknown'}</Tag>,
                },
                {
                  key: 'backend',
                  label: '后端',
                  children: okTag(check.backend?.ok),
                },
                {
                  key: 'llm',
                  label: 'LLM',
                  children: check.llm?.available
                    ? <Tag color="green">{check.llm.provider} · {check.llm.model}</Tag>
                    : <Tag color="orange">未配置可用 Provider</Tag>,
                },
                {
                  key: 'database',
                  label: '数据库',
                  children: (
                    <Space direction="vertical" size={4}>
                      {okTag(check.database?.exists, '文件存在', '文件缺失')}
                      <Text code copyable>{check.database?.path || 'unknown'}</Text>
                    </Space>
                  ),
                },
                {
                  key: 'backups',
                  label: '备份文件',
                  children: `${backups.count || 0} 个`,
                },
                {
                  key: 'latest',
                  label: '最新报告时间',
                  children: fmtTime(check.latest_report_time),
                },
              ]}
            />
            {backupPath && (
              <Alert
                style={{ marginTop: 14 }}
                type="success"
                showIcon
                message="数据库备份已生成"
                description={<Text code copyable>{backupPath}</Text>}
              />
            )}
          </PaperCard>

          <PaperCard title="数据库备份" extra={`共 ${backups.count || 0} 个`}>
            {backups.latest?.length ? (
              <List
                size="small"
                dataSource={backups.latest}
                renderItem={(name) => (
                  <List.Item>
                    <Text code copyable>{name}</Text>
                  </List.Item>
                )}
              />
            ) : (
              <Empty description="暂无备份文件" image={Empty.PRESENTED_IMAGE_SIMPLE} />
            )}
          </PaperCard>

          <PaperCard title="核心表状态">
            <Table
              rowKey="name"
              size="small"
              pagination={false}
              dataSource={tableRows}
              columns={[
                { title: '表名', dataIndex: 'name' },
                { title: '状态', dataIndex: 'exists', render: (value) => okTag(value, '存在', '缺失') },
              ]}
              locale={{ emptyText: <Empty description="暂无表状态" image={Empty.PRESENTED_IMAGE_SIMPLE} /> }}
            />
          </PaperCard>

          <PaperCard title="异常提示" extra={`${check.issues?.length || 0} 条`}>
            {check.issues?.length ? (
              <Alert
                type="warning"
                showIcon
                message="发现需要处理的事项"
                description={
                  <List
                    size="small"
                    dataSource={check.issues}
                    renderItem={(item) => <List.Item>{item}</List.Item>}
                  />
                }
              />
            ) : (
              <Empty description="暂无异常" image={Empty.PRESENTED_IMAGE_SIMPLE} />
            )}
          </PaperCard>

          <PaperCard
            title="测试样例数据"
            extra={testCases?.version ? `版本 ${testCases.version}` : `${cases.length} 条`}
          >
            {testCases?.description && (
              <Alert style={{ marginBottom: 14 }} type="info" showIcon message={testCases.description} />
            )}
            {cases.length ? (
              <Collapse
                defaultActiveKey={Object.keys(groupedCases)}
                items={Object.entries(groupedCases).map(([module, rows]) => ({
                  key: module,
                  label: `${MODULE_LABELS[module] || module} · ${rows.length} 条`,
                  children: (
                    <Table
                      rowKey="id"
                      size="small"
                      dataSource={rows}
                      columns={caseColumns}
                      pagination={false}
                    />
                  ),
                }))}
              />
            ) : (
              <Empty description="暂无测试样例" image={Empty.PRESENTED_IMAGE_SIMPLE} />
            )}
          </PaperCard>
        </Space>
      )}
    </div>
  );
}
