/**
 * 明理 AI 助手 · 前端 API 封装
 *  - 默认走 /api，由 Vite 代理至 http://127.0.0.1:8000
 *  - 通过 VITE_API_BASE 可指定独立后端地址
 */

const BASE = import.meta.env.VITE_API_BASE || '';

async function request(path, { method = 'GET', params, body, signal, timeoutMs } = {}) {
  let url = `${BASE}${path}`;
  if (params && typeof params === 'object') {
    const usp = new URLSearchParams();
    Object.entries(params).forEach(([k, v]) => {
      if (v !== undefined && v !== null && v !== '') usp.append(k, v);
    });
    const qs = usp.toString();
    if (qs) url += (url.includes('?') ? '&' : '?') + qs;
  }

  // 简单超时支持
  let controller;
  let timer;
  if (timeoutMs && !signal) {
    controller = new AbortController();
    signal = controller.signal;
    timer = setTimeout(() => controller.abort(), timeoutMs);
  }

  const init = { method, signal };
  if (body !== undefined) {
    init.headers = { 'Content-Type': 'application/json' };
    init.body = JSON.stringify(body);
  }

  let res;
  try {
    res = await fetch(url, init);
  } finally {
    if (timer) clearTimeout(timer);
  }

  let parsed = null;
  const text = await res.text();
  if (text) {
    try { parsed = JSON.parse(text); } catch { /* keep null */ }
  }
  if (!res.ok) {
    const message = (parsed && (parsed.detail || parsed.message)) || `HTTP ${res.status}`;
    const err = new Error(message);
    err.status = res.status;
    err.body = parsed;
    throw err;
  }
  return parsed;
}

export const api = {
  // —— 系统
  health: () => request('/api/health'),
  llmStatus: () => request('/api/llm/status'),

  // —— 命主
  listSubjects: () => request('/api/subjects'),
  getSubject: (id) => request(`/api/subjects/${id}`),
  createSubject: (payload) => request('/api/subjects', { method: 'POST', body: payload }),
  deleteSubject: (id) => request(`/api/subjects/${id}`, { method: 'DELETE' }),

  // —— 命盘
  generateChart: (subjectId) =>
    request(`/api/subjects/${subjectId}/chart`, { method: 'POST' }),
  getChart: (subjectId) => request(`/api/subjects/${subjectId}/chart`),
  previewChart: ({ birthDate, birthTime = '12:00' }) =>
    request('/api/chart/preview', { params: { birth_date: birthDate, birth_time: birthTime } }),

  // —— 对话
  chat: ({ subjectId, sessionId, message }) =>
    request('/api/chat', {
      method: 'POST',
      body: { subject_id: subjectId, session_id: sessionId, message },
      timeoutMs: 240000, // LLM 调用最长 4 分钟
    }),

  /**
   * 流式对话（SSE）。
   * 回调：
   *   onMeta({ session_id, provider, model, title })
   *   onDelta(text)
   *   onDone({ message_id, title, ok, provider, model })
   *   onTitle(newTitle)
   *   onError(message)
   * 返回：abort 函数
   */
  chatStream({ subjectId, sessionId, message, onMeta, onDelta, onDone, onTitle, onError }) {
    const controller = new AbortController();
    const url = `${BASE}/api/chat/stream`;

    (async () => {
      let res;
      try {
        res = await fetch(url, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', Accept: 'text/event-stream' },
          body: JSON.stringify({ subject_id: subjectId, session_id: sessionId, message }),
          signal: controller.signal,
        });
      } catch (e) {
        onError?.(e?.message || '网络错误');
        return;
      }
      if (!res.ok) {
        let detail = `HTTP ${res.status}`;
        try { const j = await res.json(); detail = j.detail || detail; } catch {}
        onError?.(detail);
        return;
      }

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';
      try {
        while (true) {
          const { value, done } = await reader.read();
          if (done) break;
          buffer += decoder.decode(value, { stream: true });
          let idx;
          while ((idx = buffer.indexOf('\n\n')) !== -1) {
            const evt = buffer.slice(0, idx);
            buffer = buffer.slice(idx + 2);
            let event = 'message';
            const dataParts = [];
            for (const line of evt.split('\n')) {
              if (line.startsWith('event:')) event = line.slice(6).trim();
              else if (line.startsWith('data:')) dataParts.push(line.slice(5).trim());
            }
            let data = null;
            try { data = dataParts.length ? JSON.parse(dataParts.join('')) : null; } catch {}
            if (event === 'meta') onMeta?.(data || {});
            else if (event === 'delta') onDelta?.((data && data.content) || '');
            else if (event === 'done') onDone?.(data || {});
            else if (event === 'title') onTitle?.((data && data.title) || '');
            else if (event === 'error') onError?.((data && data.error) || 'unknown');
          }
        }
      } catch (e) {
        if (e?.name !== 'AbortError') onError?.(e?.message || '流式中断');
      }
    })();

    return () => controller.abort();
  },

  listSessions: (subjectId) =>
    request('/api/chat/sessions', { params: subjectId ? { subject_id: subjectId } : undefined }),
  getSession: (sessionId) => request(`/api/chat/sessions/${sessionId}`),

  // —— 报告
  generateReport: ({ subjectId, reportType = 'general', question }) =>
    request('/api/reports/generate', {
      method: 'POST',
      body: { subject_id: subjectId, report_type: reportType, question },
      timeoutMs: 240000,
    }),
  listReports: (subjectId) =>
    request('/api/reports', { params: subjectId ? { subject_id: subjectId } : undefined }),
  getReport: (reportId) => request(`/api/reports/${reportId}`),

  // —— 历史
  history: (subjectId) =>
    request('/api/history', { params: subjectId ? { subject_id: subjectId } : undefined }),
};

export default api;
