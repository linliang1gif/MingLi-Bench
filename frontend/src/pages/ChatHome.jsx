import React, { useEffect, useMemo, useRef, useState } from 'react';
import {
  Button, Tabs, Input, Empty, Spin, Alert, Modal, Tooltip, message,
} from 'antd';
import { PlusOutlined, SendOutlined, ReloadOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import dayjs from 'dayjs';
import utc from 'dayjs/plugin/utc';
import api from '../services/api';

import PaperCard from '../components/PaperCard';
import StatusTag from '../components/StatusTag';
import MarkdownView from '../components/MarkdownView';
import AnalysisModeSelector, { AnalysisModeTag } from '../components/AnalysisModeSelector';

dayjs.extend(utc);
const fmtLocal = (ts) => ts ? dayjs.utc(ts).local().format('YYYY-MM-DD HH:mm') : '';

const QUICK_QUESTIONS = [
  '今年财运怎么样？',
  '适合换工作吗？',
  '这段感情还值得继续吗？',
  '未来三年事业走势？',
  '两个人缘分深不深？',
  '生成综合报告',
];

export default function ChatHome() {
  const navigate = useNavigate();

  const [subjects, setSubjects] = useState([]);
  const [activeSubjectId, setActiveSubjectId] = useState(null);
  const [sessions, setSessions] = useState([]);
  const [activeSessionId, setActiveSessionId] = useState(null);
  const [reports, setReports] = useState([]);

  const [llmStatus, setLlmStatus] = useState(null);
  const [chart, setChart] = useState(null);
  const [chartLoading, setChartLoading] = useState(false);

  const [messages, setMessages] = useState([]);
  const [streaming, setStreaming] = useState(''); // 当前正在流式接收的助手文本
  const [input, setInput] = useState('');
  const [analysisMode, setAnalysisMode] = useState('safe');
  const [sending, setSending] = useState(false);
  const [chatError, setChatError] = useState(null);
  const messagesEndRef = useRef(null);
  const abortRef = useRef(null);

  // 初次加载
  useEffect(() => {
    api.llmStatus().then(setLlmStatus).catch(() => setLlmStatus({ available: false }));
    refreshSubjects();
  }, []);

  // 切命主：拉会话、报告、命盘
  useEffect(() => {
    if (!activeSubjectId) {
      setSessions([]); setReports([]); setChart(null); setMessages([]); setActiveSessionId(null);
      return;
    }
    api.listSessions(activeSubjectId).then(setSessions).catch(() => setSessions([]));
    api.listReports(activeSubjectId).then(setReports).catch(() => setReports([]));
    setChartLoading(true);
    api.getChart(activeSubjectId)
      .then(setChart)
      .catch(() => setChart(null))
      .finally(() => setChartLoading(false));
    setMessages([]); setActiveSessionId(null);
  }, [activeSubjectId]);

  // 切会话：加载历史消息
  useEffect(() => {
    if (!activeSessionId) return;
    api.getSession(activeSessionId)
      .then((s) => setMessages(s.messages || []))
      .catch(() => setMessages([]));
  }, [activeSessionId]);

  // 自动滚到底部
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages.length, streaming, sending]);

  // 卸载时中断流
  useEffect(() => () => abortRef.current?.(), []);

  function refreshSubjects() {
    api.listSubjects().then((rows) => {
      setSubjects(rows);
      setActiveSubjectId((cur) => cur ?? rows[0]?.id ?? null);
    }).catch(() => setSubjects([]));
  }

  async function send(text) {
    const content = (text ?? input).trim();
    if (!content) return;
    if (!activeSubjectId) {
      message.info('请先选择或创建命主');
      return;
    }

    // 综合报告快捷指令直接走报告生成
    if (content === '生成综合报告') {
      try {
        setSending(true);
        const r = await api.generateReport({ subjectId: activeSubjectId, reportType: 'general', analysisMode });
        setReports((prev) => [r, ...prev]);
        // 同时也写到对话窗中
        setMessages((prev) => [
          ...prev,
          { id: `local-u-${Date.now()}`, role: 'user', content },
          { id: `local-a-${Date.now() + 1}`, role: 'assistant', content: `已生成报告《${r.title}》，可在右侧「报告」标签或左侧「分析报告」中查看。\n\n${r.content}` },
        ]);
        setInput('');
        message.success('综合报告已生成');
      } catch (e) {
        message.error(e.message || '报告生成失败');
      } finally {
        setSending(false);
      }
      return;
    }

    setSending(true); setChatError(null); setInput(''); setStreaming('');
    const tmpId = `local-${Date.now()}`;
    setMessages((prev) => [...prev, { id: tmpId, role: 'user', content }]);

    let assembled = '';
    let metaSessionId = activeSessionId;

    abortRef.current?.();
    abortRef.current = api.chatStream({
      subjectId: activeSubjectId,
      sessionId: activeSessionId || undefined,
      message: content,
      analysisMode,
      onMeta: (m) => {
        if (m.session_id) {
          metaSessionId = m.session_id;
          setActiveSessionId(m.session_id);
        }
      },
      onDelta: (piece) => {
        assembled += piece;
        setStreaming(assembled);
      },
      onDone: (d) => {
        const finalContent = d?.content || assembled;
        setMessages((prev) => [
          ...prev,
          { id: `local-a-${Date.now()}`, role: 'assistant', content: finalContent },
        ]);
        setStreaming('');
        setSending(false);
        // 立即刷一次会话列表（拿到新会话/旧标题）
        api.listSessions(activeSubjectId).then(setSessions).catch(() => {});
      },
      onTitle: (newTitle) => {
        if (!newTitle) return;
        setSessions((prev) =>
          prev.map((s) => (s.id === metaSessionId ? { ...s, title: newTitle } : s))
        );
      },
      onError: (errMsg) => {
        setChatError(errMsg || '请求失败');
        setSending(false);
        setStreaming('');
      },
    });
  }

  const activeSubject = subjects.find((s) => s.id === activeSubjectId);

  return (
    <div
      style={{
        // 让 ChatHome 占满 ml-content，抵消 ml-content 的 padding
        margin: '-24px -28px -40px',
        height: 'calc(100% + 64px)',
        display: 'grid',
        gridTemplateColumns: '260px 1fr 360px',
        background: 'var(--ml-bg)',
      }}
    >
      {/* 左栏 */}
      <aside
        style={{
          borderRight: '1px solid var(--ml-divider)',
          display: 'flex',
          flexDirection: 'column',
          padding: 14,
          gap: 12,
          overflow: 'auto',
        }}
      >
        <Button
          type="primary"
          icon={<PlusOutlined />}
          onClick={() => navigate('/subjects/new')}
          block
        >
          新建命主
        </Button>

        <SectionTitle>命主列表</SectionTitle>
        {subjects.length ? (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
            {subjects.map((s) => (
              <SidebarItem
                key={s.id}
                active={s.id === activeSubjectId}
                title={s.nickname}
                subtitle={`${s.gender || '—'} · ${s.birth_date || '—'}`}
                onClick={() => setActiveSubjectId(s.id)}
              />
            ))}
          </div>
        ) : (
          <Empty description="尚无命主，先建一个吧" image={Empty.PRESENTED_IMAGE_SIMPLE} />
        )}

        <SectionTitle>历史对话</SectionTitle>
        {sessions.length ? (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
            {sessions.map((s) => (
              <SidebarItem
                key={s.id}
                active={s.id === activeSessionId}
                title={s.title || '未命名对话'}
                subtitle={fmtLocal(s.updated_at)}
                onClick={() => setActiveSessionId(s.id)}
              />
            ))}
          </div>
        ) : (
          <div style={{ color: 'var(--ml-text-faint)', fontSize: 12 }}>暂无对话</div>
        )}

        <SectionTitle>收藏报告</SectionTitle>
        {reports.length ? (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
            {reports.slice(0, 5).map((r) => (
              <SidebarItem
                key={r.id}
                title={r.title}
                subtitle={fmtLocal(r.created_at)}
                onClick={() => navigate(`/reports/${r.id}`)}
              />
            ))}
          </div>
        ) : (
          <div style={{ color: 'var(--ml-text-faint)', fontSize: 12 }}>暂无报告</div>
        )}
      </aside>

      {/* 中栏：聊天 */}
      <main style={{ display: 'flex', flexDirection: 'column', minWidth: 0 }}>
        {/* 顶 */}
        <div style={{ padding: '16px 24px 0' }}>
          <div style={{ display: 'flex', alignItems: 'flex-end', justifyContent: 'space-between' }}>
            <div>
              <div className="ml-title ml-title-lg">AI 问命</div>
              <div className="ml-subtitle" style={{ marginTop: 4 }}>
                以命盘为据，以 AI 为笔，生成你的个人命理分析。
              </div>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
              <AnalysisModeSelector value={analysisMode} onChange={setAnalysisMode} size="small" />
              <LLMBadge status={llmStatus} />
              {activeSubject && <SubjectBadge subject={activeSubject} />}
            </div>
          </div>
          {chatError && (
            <Alert type="error" showIcon message={chatError} style={{ marginTop: 10 }} />
          )}
        </div>

        {/* 对话区 */}
        <div
          style={{
            flex: 1,
            overflow: 'auto',
            padding: '16px 24px 0',
            display: 'flex',
            flexDirection: 'column',
            gap: 12,
          }}
        >
          {!activeSubject ? (
            <Empty
              style={{ marginTop: 80 }}
              description={<span style={{ color: 'var(--ml-text-sub)' }}>请先在左侧选择命主，或新建一个</span>}
            />
          ) : messages.length === 0 ? (
            <Empty
              style={{ marginTop: 80 }}
              description={
                <span style={{ color: 'var(--ml-text-sub)' }}>
                  当前命主：{activeSubject.nickname}。可输入问题，或选择下方快捷题。
                </span>
              }
            />
          ) : (
            <>
              {messages.map((m) => <Bubble key={m.id} role={m.role} content={m.content} />)}
              {sending && (streaming
                ? <Bubble role="assistant" content={streaming} streaming />
                : (
                  <div style={{ alignSelf: 'flex-start', color: 'var(--ml-text-sub)', fontSize: 13 }}>
                    <Spin size="small" /> 正在推演…
                  </div>
                )
              )}
            </>
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* 输入区 */}
        <div style={{ padding: 14, borderTop: '1px solid var(--ml-divider)', background: 'var(--ml-card-bg)' }}>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, marginBottom: 10 }}>
            {QUICK_QUESTIONS.map((q) => (
              <Button
                key={q}
                size="small"
                onClick={() => send(q)}
                disabled={sending || !activeSubjectId}
                style={{
                  borderColor: 'var(--ml-bronze)',
                  color: 'var(--ml-bronze)',
                  background: 'transparent',
                }}
              >
                {q}
              </Button>
            ))}
          </div>
          <Input.TextArea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="请输入你想了解的命理问题"
            autoSize={{ minRows: 2, maxRows: 5 }}
            disabled={!activeSubjectId}
            onPressEnter={(e) => {
              if (!e.shiftKey) {
                e.preventDefault();
                send();
              }
            }}
          />
          <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: 8 }}>
            <Button
              type="primary"
              icon={<SendOutlined />}
              onClick={() => send()}
              loading={sending}
              disabled={!activeSubjectId}
            >
              发送
            </Button>
          </div>
        </div>
      </main>

      {/* 右栏：Tabs */}
      <aside style={{ borderLeft: '1px solid var(--ml-divider)', overflow: 'auto', padding: 14 }}>
        <Tabs
          defaultActiveKey="chart"
          items={[
            { key: 'chart',        label: '命盘', children: <ChartTab subject={activeSubject} chart={chart} loading={chartLoading} onRecompute={() => activeSubjectId && api.generateChart(activeSubjectId).then(setChart)} /> },
            { key: 'wealth',       label: '财运', children: <FocusTab title="财运" subjectId={activeSubjectId} reportType="wealth" analysisMode={analysisMode} onCreated={(r)=>setReports(p=>[r,...p])} /> },
            { key: 'relationship', label: '感情', children: <FocusTab title="感情" subjectId={activeSubjectId} reportType="relationship" analysisMode={analysisMode} onCreated={(r)=>setReports(p=>[r,...p])} /> },
            { key: 'career',       label: '事业', children: <FocusTab title="事业" subjectId={activeSubjectId} reportType="career" analysisMode={analysisMode} onCreated={(r)=>setReports(p=>[r,...p])} /> },
            { key: 'reports',      label: '报告', children: <ReportsTab reports={reports} onClick={(id)=>navigate(`/reports/${id}`)} /> },
          ]}
        />
      </aside>
    </div>
  );
}

/* ====================== 子组件 ====================== */

function SectionTitle({ children }) {
  return (
    <div
      style={{
        marginTop: 6,
        marginBottom: 2,
        fontFamily: 'var(--ml-font-serif)',
        color: 'var(--ml-bronze)',
        fontSize: 12,
        letterSpacing: 2,
      }}
    >
      {children}
    </div>
  );
}

function SidebarItem({ active, title, subtitle, onClick }) {
  return (
    <div
      onClick={onClick}
      style={{
        cursor: 'pointer',
        padding: '8px 10px',
        borderRadius: 8,
        border: `1px solid ${active ? 'var(--ml-bronze)' : 'transparent'}`,
        background: active ? 'rgba(94, 139, 126, 0.14)' : 'transparent',
      }}
    >
      <div
        style={{
          fontFamily: 'var(--ml-font-serif)',
          fontSize: 14,
          color: 'var(--ml-text)',
          whiteSpace: 'nowrap',
          overflow: 'hidden',
          textOverflow: 'ellipsis',
        }}
      >
        {title}
      </div>
      {subtitle && (
        <div style={{ fontSize: 11, color: 'var(--ml-text-faint)', marginTop: 2 }}>
          {subtitle}
        </div>
      )}
    </div>
  );
}

function LLMBadge({ status }) {
  if (!status) return null;
  if (!status.available) return <StatusTag status="failed" text="AI 未配置" />;
  return (
    <Tooltip title={`Provider: ${status.provider} · Model: ${status.model}`}>
      <span><StatusTag status="completed" text={`AI 就绪 · ${status.provider}`} /></span>
    </Tooltip>
  );
}

function SubjectBadge({ subject }) {
  return (
    <span
      style={{
        fontSize: 12,
        color: 'var(--ml-text-sub)',
        border: '1px solid var(--ml-border)',
        padding: '2px 10px',
        borderRadius: 999,
        background: 'rgba(94, 139, 126, 0.08)',
      }}
    >
      {subject.nickname} · {subject.gender || '—'} · {subject.birth_date || '—'}
    </span>
  );
}

function Bubble({ role, content, streaming }) {
  const isUser = role === 'user';
  return (
    <div style={{ display: 'flex', justifyContent: isUser ? 'flex-end' : 'flex-start' }}>
      <div
        style={{
          maxWidth: 760,
          padding: '12px 16px',
          borderRadius: 14,
          fontSize: 14,
          lineHeight: 1.85,
          color: 'var(--ml-text)',
          background: isUser ? 'rgba(94, 139, 126, 0.10)' : 'var(--ml-card-bg)',
          border: `1px solid ${isUser ? 'rgba(94, 139, 126, 0.30)' : 'var(--ml-border)'}`,
          boxShadow: 'var(--ml-shadow-soft)',
        }}
      >
        {isUser ? (
          <div style={{ whiteSpace: 'pre-wrap' }}>{content}</div>
        ) : (
          <MarkdownView content={content} compact />
        )}
        {streaming && <span className="ml-stream-caret">▍</span>}
      </div>
    </div>
  );
}

function ChartTab({ subject, chart, loading, onRecompute }) {
  if (!subject) return <Empty description="请先选择命主" />;
  if (loading) return <div style={{ display: 'flex', justifyContent: 'center', padding: 30 }}><Spin /></div>;
  const pillars = chart?.pillars || {};
  const wuxing = chart?.wuxing?.counts || {};
  const summary = chart?.summary;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
      <PaperCard title="四柱" extra={<a onClick={onRecompute}><ReloadOutlined /> 重新推算</a>}>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 8 }}>
          {['year','month','day','hour'].map((k) => {
            const c = pillars[k] || {};
            return (
              <div key={k} style={{
                border: '1px solid var(--ml-divider)',
                borderRadius: 10,
                padding: '10px 6px',
                textAlign: 'center',
                background: 'rgba(94, 139, 126, 0.06)',
              }}>
                <div style={{ fontSize: 11, color: 'var(--ml-text-faint)' }}>{c.label || k}</div>
                <div style={{ fontFamily: 'var(--ml-font-serif)', fontSize: 22, color: 'var(--ml-text)', marginTop: 4 }}>
                  {c.stem || '—'}{c.branch || ''}
                </div>
              </div>
            );
          })}
        </div>
      </PaperCard>

      <PaperCard title="五行简析">
        {Object.keys(wuxing).length ? (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: 6 }}>
            {Object.entries(wuxing).map(([w, c]) => (
              <div key={w} style={{ textAlign: 'center' }}>
                <div style={{ fontFamily: 'var(--ml-font-serif)', color: 'var(--ml-text)' }}>{w}</div>
                <div style={{ color: 'var(--ml-bronze)', fontSize: 18 }}>{c}</div>
              </div>
            ))}
          </div>
        ) : <Empty description="暂无五行数据" image={Empty.PRESENTED_IMAGE_SIMPLE} />}
        {summary && (
          <div style={{ marginTop: 10, fontSize: 13, color: 'var(--ml-text-sub)' }}>{summary}</div>
        )}
      </PaperCard>

      <PaperCard title="当前关注问题">
        <div style={{ color: 'var(--ml-text)', fontSize: 13 }}>
          {(subject.focus_topics && subject.focus_topics.length) ? subject.focus_topics.join(' · ') : '未选择关注方向'}
        </div>
      </PaperCard>
    </div>
  );
}

function FocusTab({ title, subjectId, reportType, analysisMode, onCreated }) {
  const [busy, setBusy] = useState(false);
  const [tip, setTip] = useState(null);
  if (!subjectId) return <Empty description="请先选择命主" />;
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
      <PaperCard title={`${title} · 专项分析`}>
        <div style={{ color: 'var(--ml-text-sub)', fontSize: 13, lineHeight: 1.8 }}>
          一键生成「{title}」专项分析报告，结果会落库并出现在右侧「报告」标签与左侧「分析报告」中。
        </div>
        <div style={{ marginTop: 10 }}>
          <Button
            type="primary"
            loading={busy}
            onClick={async () => {
              setBusy(true); setTip(null);
              try {
                const r = await api.generateReport({ subjectId, reportType, analysisMode });
                onCreated?.(r);
                setTip(`已生成《${r.title}》`);
              } catch (e) { setTip(e.message || '生成失败'); }
              finally { setBusy(false); }
            }}
          >
            生成 {title} 专项报告
          </Button>
          {tip && <span style={{ marginLeft: 10, color: 'var(--ml-text-sub)', fontSize: 12 }}>{tip}</span>}
          <div style={{ marginTop: 10 }}>
            <AnalysisModeTag mode={analysisMode} />
          </div>
        </div>
      </PaperCard>
    </div>
  );
}

function ReportsTab({ reports, onClick }) {
  if (!reports?.length) return <Empty description="尚无报告" image={Empty.PRESENTED_IMAGE_SIMPLE} />;
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
      {reports.map((r) => (
        <div
          key={r.id}
          onClick={() => onClick(r.id)}
          style={{
            cursor: 'pointer',
            padding: 10,
            border: '1px solid var(--ml-divider)',
            borderRadius: 10,
            background: 'rgba(94, 139, 126, 0.06)',
          }}
        >
          <div style={{ fontFamily: 'var(--ml-font-serif)', color: 'var(--ml-text)' }}>{r.title}</div>
          <div style={{ fontSize: 11, color: 'var(--ml-text-faint)', marginTop: 2 }}>
            {fmtLocal(r.created_at)}
          </div>
        </div>
      ))}
    </div>
  );
}
