import React, { useEffect, useMemo, useState } from 'react';
import { App as AntdApp, Button, Empty, Form, Input, Modal, Select, Space, Table, Tabs, Tag } from 'antd';
import api from '../services/api';
import PageBanner from '../components/PageBanner';
import PaperCard from '../components/PaperCard';

const RELIABILITY_OPTIONS = [
  { value: 'A', label: 'A 高可信' },
  { value: 'B', label: 'B 中可信' },
  { value: 'C', label: 'C 参考' },
];

const RISK_OPTIONS = [
  { value: 'low', label: '低风险' },
  { value: 'medium', label: '中风险' },
  { value: 'high', label: '高风险' },
];

const MODULE_OPTIONS = [
  { value: 'knowledge', label: 'knowledge' },
  { value: 'bazi_report', label: 'bazi_report' },
  { value: 'fengshui_basic', label: 'fengshui_basic' },
  { value: 'fengshui_basic_report', label: 'fengshui_basic_report' },
  { value: 'fengshui_xuankong_report', label: 'fengshui_xuankong_report' },
  { value: 'fengshui_photo_report', label: 'fengshui_photo_report' },
  { value: 'date_selection_report', label: 'date_selection_report' },
  { value: 'naming_report', label: 'naming_report' },
  { value: 'word_divination_report', label: 'word_divination_report' },
  { value: 'yinzhai_study_report', label: 'yinzhai_study_report' },
];

export default function KnowledgeBase() {
  const { message } = AntdApp.useApp();
  const [books, setBooks] = useState([]);
  const [categories, setCategories] = useState([]);
  const [loading, setLoading] = useState(true);
  const [bookModal, setBookModal] = useState(false);
  const [chunkModal, setChunkModal] = useState(false);
  const [initBusy, setInitBusy] = useState(false);
  const [activeBook, setActiveBook] = useState(null);
  const [chunks, setChunks] = useState([]);
  const [searchResult, setSearchResult] = useState(null);
  const [bookFilters, setBookFilters] = useState({});
  const [bookForm] = Form.useForm();
  const [chunkForm] = Form.useForm();
  const [searchForm] = Form.useForm();
  const [bookFilterForm] = Form.useForm();

  const categoryOptions = useMemo(
    () => categories.map((c) => ({ value: c.code, label: `${c.code} ${c.name}` })),
    [categories],
  );
  const bookOptions = useMemo(
    () => books.map((b) => ({ value: b.id, label: `${b.id} ${b.title}` })),
    [books],
  );

  function refreshBooks(nextFilters = bookFilters) {
    setLoading(true);
    api.listKnowledgeBooks(nextFilters)
      .then(setBooks)
      .catch((e) => {
        message.error(e.message || '读取书籍失败');
        setBooks([]);
      })
      .finally(() => setLoading(false));
  }

  useEffect(() => {
    refreshBooks();
    api.listCategories().then(setCategories).catch(() => setCategories([]));
  }, []);

  function onFilterBooks() {
    const values = bookFilterForm.getFieldsValue();
    setBookFilters(values);
    refreshBooks(values);
  }

  function onResetBookFilters() {
    bookFilterForm.resetFields();
    setBookFilters({});
    refreshBooks({});
  }

  async function saveBook() {
    const values = await bookForm.validateFields();
    try {
      await api.createKnowledgeBook(values);
      message.success('书籍已新增');
      setBookModal(false);
      refreshBooks();
    } catch (e) {
      message.error(e.message || '新增失败');
    }
  }

  async function onInitKnowledge() {
    setInitBusy(true);
    try {
      const res = await api.initKnowledge();
      message.success(`初始化完成，新增 ${res.inserted_books || 0} 本 / ${res.inserted_chunks || 0} 条片段`);
      refreshBooks();
    } catch (e) {
      message.error(e.message || '初始化古籍失败');
    } finally {
      setInitBusy(false);
    }
  }

  async function openChunks(book) {
    setActiveBook(book);
    setChunkModal(true);
    chunkForm.setFieldsValue({ book_id: book.id });
    try {
      setChunks(await api.listKnowledgeChunks(book.id));
    } catch {
      setChunks([]);
    }
  }

  async function saveChunk() {
    const values = await chunkForm.validateFields();
    try {
      await api.createKnowledgeChunk(values);
      message.success('片段已新增');
      setChunks(await api.listKnowledgeChunks(values.book_id));
      chunkForm.setFieldsValue({
        book_id: values.book_id,
        chapter: '',
        section: '',
        original_text: '',
        explanation: '',
        tags: '',
        applicable_modules: '',
        source_ref: '',
      });
    } catch (e) {
      message.error(e.message || '新增失败');
    }
  }

  async function onSearch() {
    const values = await searchForm.validateFields();
    try {
      setSearchResult(await api.searchKnowledge(values));
    } catch (e) {
      message.error(e.message || '搜索失败');
    }
  }

  function onResetSearch() {
    searchForm.resetFields();
    setSearchResult(null);
  }

  function renderTagList(values, color) {
    const items = Array.isArray(values)
      ? values
      : values
        ? String(values).split(/[,，、;；]/).map((item) => item.trim()).filter(Boolean)
        : [];
    if (!items.length) return '—';
    return (
      <Space size={[0, 4]} wrap>
        {items.slice(0, 4).map((item) => <Tag key={item} color={color}>{item}</Tag>)}
        {items.length > 4 ? <Tag>+{items.length - 4}</Tag> : null}
      </Space>
    );
  }

  async function copyReference(row) {
    const text = [
      `chunk_id: ${row.chunk_id || row.id}`,
      `book_title: ${row.book_title || '未知书名'}`,
      row.chapter ? `chapter: ${row.chapter}` : '',
      row.source_ref ? `source_ref: ${row.source_ref}` : '',
    ].filter(Boolean).join('\n');
    try {
      let copied = false;
      const textarea = document.createElement('textarea');
      textarea.value = text;
      textarea.setAttribute('readonly', '');
      textarea.style.position = 'fixed';
      textarea.style.left = '-9999px';
      document.body.appendChild(textarea);
      textarea.select();
      copied = document.execCommand('copy');
      document.body.removeChild(textarea);

      if (navigator.clipboard?.writeText) {
        try {
          await navigator.clipboard.writeText(text);
          copied = true;
        } catch {
          if (!copied) throw new Error('copy_failed');
        }
      }
      if (!copied) throw new Error('copy_failed');
      message.success('引用信息已复制');
    } catch {
      message.error('复制失败，请检查浏览器剪贴板权限');
    }
  }

  const bookColumns = [
    { title: '书名', dataIndex: 'title', render: (v) => <b>{v}</b> },
    { title: '类目', dataIndex: 'category_code', width: 100 },
    { title: '作者', dataIndex: 'author', width: 120, render: (v) => v || '—' },
    { title: '朝代', dataIndex: 'dynasty', width: 90, render: (v) => v || '—' },
    { title: '可信度', dataIndex: 'reliability_level', width: 90 },
    { title: '风险', dataIndex: 'risk_level', width: 90, render: (v) => <Tag>{v || '—'}</Tag> },
    { title: '说明', dataIndex: 'description', ellipsis: true, render: (v) => v || '—' },
    { title: '操作', width: 110, render: (_, r) => <Button size="small" onClick={() => openChunks(r)}>片段</Button> },
  ];

  const chunkColumns = [
    { title: '章节', dataIndex: 'chapter', width: 120, render: (v) => v || '—' },
    { title: '原文', dataIndex: 'original_text', ellipsis: true },
    { title: '解释', dataIndex: 'explanation', ellipsis: true, render: (v) => v || '—' },
    { title: '出处', dataIndex: 'source_ref', width: 160, render: (v) => v || '—' },
  ];

  const searchColumns = [
    { title: '片段', dataIndex: 'chunk_id', width: 80, render: (v, r) => v || r.id },
    { title: '书名', dataIndex: 'book_title', width: 130, render: (v) => v || '—' },
    { title: '章节', dataIndex: 'chapter', width: 120, render: (v) => v || '—' },
    { title: '小节', dataIndex: 'section', width: 100, render: (v) => v || '—' },
    { title: '原文', dataIndex: 'original_text', ellipsis: true },
    { title: '解释', dataIndex: 'explanation', ellipsis: true, render: (v) => v || '—' },
    { title: '标签', dataIndex: 'tags', width: 180, render: (v) => renderTagList(v, 'blue') },
    { title: '模块', dataIndex: 'applicable_modules', width: 190, render: (v) => renderTagList(v, 'geekblue') },
    { title: '可信度', dataIndex: 'reliability_level', width: 80, render: (v) => v || '—' },
    { title: '风险', dataIndex: 'risk_level', width: 80, render: (v) => <Tag>{v || '—'}</Tag> },
    { title: '出处', dataIndex: 'source_ref', width: 160, render: (v) => v || '—' },
    {
      title: '操作',
      width: 110,
      render: (_, r) => <Button size="small" onClick={() => copyReference(r)}>复制引用</Button>,
    },
  ];

  return (
    <div>
      <PageBanner
        title="古籍知识库"
        subtitle="书籍、内容分片与 SQLite LIKE 检索"
        quote="聚典成库，以文证象。"
        extra={
          <Space>
            <Button onClick={() => refreshBooks()}>刷新</Button>
            <Button loading={initBusy} onClick={onInitKnowledge}>初始化古籍样例</Button>
            <Button type="primary" onClick={() => { bookForm.resetFields(); setBookModal(true); }}>新增书籍</Button>
          </Space>
        }
      />

      <PaperCard title="知识检索" style={{ marginBottom: 18 }}>
        <Form form={searchForm} layout="inline">
          <Form.Item name="query" style={{ minWidth: 240 }}>
            <Input placeholder="阳宅 大门 床位" />
          </Form.Item>
          <Form.Item name="category_code" style={{ minWidth: 220 }}>
            <Select allowClear placeholder="选择类目" options={categoryOptions} />
          </Form.Item>
          <Form.Item name="book_id" style={{ minWidth: 220 }}>
            <Select allowClear showSearch optionFilterProp="label" placeholder="选择书籍" options={bookOptions} />
          </Form.Item>
          <Form.Item name="tags" style={{ minWidth: 180 }}>
            <Input placeholder="标签，如 阳宅,大门" />
          </Form.Item>
          <Form.Item name="applicable_module" style={{ minWidth: 220 }}>
            <Select allowClear showSearch optionFilterProp="label" placeholder="适用模块" options={MODULE_OPTIONS} />
          </Form.Item>
          <Form.Item name="reliability_level" style={{ minWidth: 140 }}>
            <Select allowClear placeholder="可信度" options={RELIABILITY_OPTIONS} />
          </Form.Item>
          <Form.Item name="risk_level" style={{ minWidth: 140 }}>
            <Select allowClear placeholder="风险级别" options={RISK_OPTIONS} />
          </Form.Item>
          <Form.Item name="limit" initialValue={50} style={{ minWidth: 120 }}>
            <Select
              placeholder="返回数量"
              options={[10, 20, 50, 100].map((value) => ({ value, label: `${value} 条` }))}
            />
          </Form.Item>
          <Space>
            <Button type="primary" onClick={onSearch}>搜索</Button>
            <Button onClick={onResetSearch}>重置</Button>
          </Space>
        </Form>
        {searchResult && (
          <Table
            style={{ marginTop: 16 }}
            rowKey="id"
            size="small"
            dataSource={searchResult.results || []}
            columns={searchColumns}
            locale={{ emptyText: <Empty description="无匹配内容" image={Empty.PRESENTED_IMAGE_SIMPLE} /> }}
            pagination={{ pageSize: 8 }}
          />
        )}
      </PaperCard>

      <PaperCard title="古籍书籍" extra={`共 ${books.length} 本`}>
        <Form form={bookFilterForm} layout="inline" style={{ marginBottom: 16 }}>
          <Form.Item name="query" style={{ minWidth: 220 }}>
            <Input placeholder="书名、别名、说明" />
          </Form.Item>
          <Form.Item name="category_code" style={{ minWidth: 220 }}>
            <Select allowClear placeholder="选择类目" options={categoryOptions} />
          </Form.Item>
          <Form.Item name="reliability_level" style={{ minWidth: 140 }}>
            <Select allowClear placeholder="可信度" options={RELIABILITY_OPTIONS} />
          </Form.Item>
          <Form.Item name="risk_level" style={{ minWidth: 140 }}>
            <Select allowClear placeholder="风险级别" options={RISK_OPTIONS} />
          </Form.Item>
          <Space>
            <Button type="primary" onClick={onFilterBooks}>筛选</Button>
            <Button onClick={onResetBookFilters}>重置</Button>
          </Space>
        </Form>
        {books.length === 0 && !loading ? (
          <Empty description="暂无匹配书籍" image={Empty.PRESENTED_IMAGE_SIMPLE} />
        ) : (
          <Table rowKey="id" loading={loading} dataSource={books} columns={bookColumns} pagination={{ pageSize: 10 }} />
        )}
      </PaperCard>

      <Modal title="新增书籍" open={bookModal} onCancel={() => setBookModal(false)} onOk={saveBook} width={760}>
        <Form form={bookForm} layout="vertical">
          <Space style={{ width: '100%' }} size={12}>
            <Form.Item name="title" label="书名" rules={[{ required: true }]} style={{ width: 240 }}><Input /></Form.Item>
            <Form.Item name="category_code" label="类目" rules={[{ required: true }]} style={{ width: 260 }}>
              <Select options={categoryOptions} />
            </Form.Item>
            <Form.Item name="reliability_level" label="可信度" initialValue="C" style={{ width: 100 }}><Input /></Form.Item>
          </Space>
          <Space style={{ width: '100%' }} size={12}>
            <Form.Item name="alias" label="别名" style={{ width: 180 }}><Input /></Form.Item>
            <Form.Item name="author" label="作者" style={{ width: 180 }}><Input /></Form.Item>
            <Form.Item name="dynasty" label="朝代" style={{ width: 140 }}><Input /></Form.Item>
            <Form.Item name="risk_level" label="风险级别" initialValue="medium" style={{ width: 140 }}><Input /></Form.Item>
          </Space>
          <Form.Item name="source" label="来源"><Input /></Form.Item>
          <Form.Item name="description" label="说明"><Input.TextArea rows={3} /></Form.Item>
        </Form>
      </Modal>

      <Modal
        title={activeBook ? `内容片段 · ${activeBook.title}` : '内容片段'}
        open={chunkModal}
        onCancel={() => setChunkModal(false)}
        footer={null}
        width={920}
      >
        <Tabs
          items={[
            {
              key: 'list',
              label: '片段列表',
              children: (
                <Table
                  rowKey="id"
                  size="small"
                  dataSource={chunks}
                  columns={chunkColumns}
                  pagination={{ pageSize: 6 }}
                  locale={{ emptyText: <Empty description="暂无片段" image={Empty.PRESENTED_IMAGE_SIMPLE} /> }}
                />
              ),
            },
            {
              key: 'new',
              label: '新增片段',
              children: (
                <Form form={chunkForm} layout="vertical">
                  <Form.Item name="book_id" hidden><Input /></Form.Item>
                  <Space style={{ width: '100%' }} size={12}>
                    <Form.Item name="chapter" label="章节" style={{ width: 180 }}><Input /></Form.Item>
                    <Form.Item name="section" label="小节" style={{ width: 180 }}><Input /></Form.Item>
                    <Form.Item name="source_ref" label="出处" style={{ width: 260 }}><Input /></Form.Item>
                  </Space>
                  <Form.Item name="original_text" label="原文" rules={[{ required: true }]}><Input.TextArea rows={5} /></Form.Item>
                  <Form.Item name="explanation" label="解释"><Input.TextArea rows={3} /></Form.Item>
                  <Form.Item name="tags" label="标签"><Input placeholder="阳宅,大门,床位" /></Form.Item>
                  <Form.Item name="applicable_modules" label="适用模块"><Input placeholder="fengshui_basic,compass_report" /></Form.Item>
                  <Button type="primary" onClick={saveChunk}>保存片段</Button>
                </Form>
              ),
            },
          ]}
        />
      </Modal>
    </div>
  );
}
