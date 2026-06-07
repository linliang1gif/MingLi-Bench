import React, { useEffect, useState } from 'react';
import { Alert, Button, Descriptions, Empty, List, message, Space, Spin, Tag } from 'antd';
import { useParams } from 'react-router-dom';
import dayjs from 'dayjs';
import utc from 'dayjs/plugin/utc';
import api from '../services/api';
import PageBanner from '../components/PageBanner';
import PaperCard from '../components/PaperCard';
import MarkdownView from '../components/MarkdownView';
import { AnalysisModeTag } from '../components/AnalysisModeSelector';

dayjs.extend(utc);
const fmtLocal = (ts) => ts ? dayjs.utc(ts).local().format('YYYY-MM-DD HH:mm') : '—';

const REPORT_TYPE_LABELS = {
  general: '综合命理分析',
  wealth: '财运专项分析',
  career: '事业专项分析',
  relationship: '感情专项分析',
  yearly: '流年走势分析',
  fengshui_basic: '阳宅基础报告',
  fengshui_xuankong_report: '玄空飞星报告',
  fengshui_photo_report: '拍照风水报告',
  landscape_photo_report: '外局拍照研究报告',
  heritage_risk_record_report: '文保风险记录报告',
  yinzhai_study_report: '阴宅研究报告',
  tianxing_fengshui_report: '天星风水报告',
};

const typeLabel = (value) => REPORT_TYPE_LABELS[value] || value || '未知类型';

export default function ReportDetail() {
  const { id } = useParams();
  const [report, setReport] = useState(null);
  const [versions, setVersions] = useState([]);
  const [activeVersion, setActiveVersion] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    Promise.all([api.getReport(id), api.listReportVersions(id)])
      .then(([r, v]) => {
        setReport(r);
        setVersions(v);
        setActiveVersion(v?.[0] || r.latest_version || null);
      })
      .catch((e) => message.error(e.message || '读取报告详情失败'))
      .finally(() => setLoading(false));
  }, [id]);

  if (loading) return <Spin />;
  if (!report) return <Empty description="报告不存在" image={Empty.PRESENTED_IMAGE_SIMPLE} />;

  const risk = activeVersion?.risk_check_result;
  const markdown = activeVersion?.markdown || report.content || '';
  const analysisMode =
    activeVersion?.analysis_mode ||
    activeVersion?.input_json?.analysis_mode ||
    report.analysis_mode ||
    'safe';
  const isResearchMode = analysisMode === 'research';
  const references = Array.isArray(activeVersion?.references_json)
    ? activeVersion.references_json
    : activeVersion?.references_json
      ? [activeVersion.references_json]
      : [];

  async function copyMarkdown() {
    try {
      await navigator.clipboard.writeText(markdown);
      message.success('Markdown 已复制');
    } catch {
      message.error('复制失败，请检查浏览器剪贴板权限');
    }
  }

  function downloadMarkdown() {
    const safeTitle = (report.title || `report-${report.id}`).replace(/[\\/:*?"<>|]/g, '_');
    const blob = new Blob([markdown], { type: 'text/markdown;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${safeTitle}.md`;
    a.click();
    URL.revokeObjectURL(url);
  }

  return (
    <div>
      <PageBanner
        title={report.title}
        subtitle="报告正文、Prompt 版本、风控结果与历史版本"
        quote="一文一版，生成可追。"
        extra={
          <Space>
            <Button onClick={copyMarkdown}>复制 Markdown</Button>
            <Button type="primary" onClick={downloadMarkdown}>下载 Markdown</Button>
          </Space>
        }
      />
      <PaperCard title="报告元信息" style={{ marginBottom: 18 }}>
        <Descriptions bordered size="small" column={2}>
          <Descriptions.Item label="报告类型">{typeLabel(report.report_type)}</Descriptions.Item>
          <Descriptions.Item label="生成时间">{fmtLocal(report.created_at)}</Descriptions.Item>
          <Descriptions.Item label="分析模式"><AnalysisModeTag mode={analysisMode} /></Descriptions.Item>
          <Descriptions.Item label="Prompt 版本">{activeVersion?.prompt_version || '—'}</Descriptions.Item>
          <Descriptions.Item label="模型">{activeVersion?.model_used || '—'}</Descriptions.Item>
          <Descriptions.Item label="风控结果" span={2}>
            {risk ? (
              <Space wrap>
                <Tag color={risk.passed ? 'green' : 'red'}>{risk.passed ? '通过' : '命中风险'}</Tag>
                {(risk.hits || []).map((h) => (
                  <Tag color={h.allowed_by_research_mode ? 'orange' : 'red'} key={h.term}>
                    {h.term}{h.allowed_by_research_mode ? ' · 研究展示' : ''}
                  </Tag>
                ))}
              </Space>
            ) : '—'}
          </Descriptions.Item>
          <Descriptions.Item label="古籍引用" span={2}>
            {references.length ? (
              <Space direction="vertical" size={4}>
                {references.map((r, idx) => (
                  <div key={`${r.chunk_id || idx}-${r.source_ref || idx}`}>
                    <div>
                      {r.chunk_id ? <Tag>chunk #{r.chunk_id}</Tag> : null}
                      <b>{r.book_title || r.title || '未命名来源'}</b>
                      {r.chapter ? ` · ${r.chapter}` : ''}
                      {r.section ? ` · ${r.section}` : ''}
                      {r.source_ref ? ` · ${r.source_ref}` : ''}
                    </div>
                    {r.original_text ? (
                      <div style={{ color: 'var(--ml-text-faint)', fontSize: 12 }}>
                        原文：{r.original_text}
                      </div>
                    ) : null}
                    {r.explanation ? (
                      <div style={{ color: 'var(--ml-text-faint)', fontSize: 12 }}>
                        解释：{r.explanation}
                      </div>
                    ) : null}
                  </div>
                ))}
              </Space>
            ) : '暂无古籍引用来源'}
          </Descriptions.Item>
        </Descriptions>
      </PaperCard>

      {isResearchMode && (
        <Alert
          type="warning"
          showIcon
          message="自用研究模式"
          description="该报告包含传统断语、民俗资料或流派观点，仅供个人研究，不作为现实决策依据。"
          style={{ marginBottom: 18 }}
        />
      )}

      {risk && (risk.hits || []).length > 0 && (
        <Alert
          type={isResearchMode ? 'info' : 'warning'}
          showIcon
          message={isResearchMode ? '研究模式风险词记录' : '报告命中风险词'}
          description={(risk.hits || []).map((h) => (
            `${h.term}：${h.allowed_by_research_mode ? (h.safety_note || '自用研究模式允许作为传统术语展示') : (h.replacement_suggestion || h.category)}`
          )).join('；')}
          style={{ marginBottom: 18 }}
        />
      )}

      <PaperCard title="报告正文" style={{ marginBottom: 18 }}>
        <MarkdownView content={markdown} />
      </PaperCard>

      <PaperCard title="历史版本" extra={`共 ${versions.length} 个`}>
        <List
          dataSource={versions}
          locale={{ emptyText: <Empty description="暂无版本记录" image={Empty.PRESENTED_IMAGE_SIMPLE} /> }}
          renderItem={(v) => (
            <List.Item style={{ cursor: 'pointer' }} onClick={() => setActiveVersion(v)}>
              <List.Item.Meta
                title={<Space><b>版本 {v.version}</b>{activeVersion?.id === v.id && <Tag color="green">当前查看</Tag>}</Space>}
                description={`${fmtLocal(v.created_at)} · ${typeLabel(v.report_type)} · ${v.analysis_mode === 'research' ? '自用研究模式' : '普通模式'} · ${v.prompt_version || '无 Prompt 版本'}`}
              />
            </List.Item>
          )}
        />
      </PaperCard>
    </div>
  );
}
