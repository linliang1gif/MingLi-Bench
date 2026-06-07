/**
 * 明理 AI 助手 · 前端 API 封装
 *  - 默认走 /api，由 Vite 代理至 http://127.0.0.1:8000
 *  - 通过 VITE_API_BASE_URL / VITE_API_BASE 可指定独立后端地址
 */

const BASE = import.meta.env.VITE_API_BASE_URL || import.meta.env.VITE_API_BASE || '';

function withAnalysisMode(body = {}) {
  const next = { ...(body || {}) };
  const mode = next.analysis_mode || next.analysisMode;
  delete next.analysisMode;
  if (mode) next.analysis_mode = mode;
  return next;
}

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
    if (body instanceof FormData) {
      init.body = body;
    } else {
      init.headers = { 'Content-Type': 'application/json' };
      init.body = JSON.stringify(body);
    }
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
  systemCheck: () => request('/api/system/check'),
  backupDatabase: () => request('/api/system/backup-db', { method: 'POST' }),
  getSystemTestCases: () => request('/api/system/test-cases'),

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
  chat: ({ subjectId, sessionId, message, analysisMode = 'safe' }) =>
    request('/api/chat', {
      method: 'POST',
      body: { subject_id: subjectId, session_id: sessionId, message, analysis_mode: analysisMode },
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
  chatStream({ subjectId, sessionId, message, analysisMode = 'safe', onMeta, onDelta, onDone, onTitle, onError }) {
    const controller = new AbortController();
    const url = `${BASE}/api/chat/stream`;

    (async () => {
      let res;
      try {
        res = await fetch(url, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', Accept: 'text/event-stream' },
          body: JSON.stringify({ subject_id: subjectId, session_id: sessionId, message, analysis_mode: analysisMode }),
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
  generateReport: ({ subjectId, reportType = 'general', question, analysisMode = 'safe' }) =>
    request('/api/reports/generate', {
      method: 'POST',
      body: { subject_id: subjectId, report_type: reportType, question, analysis_mode: analysisMode },
      timeoutMs: 240000,
    }),
  listReports: (params) => {
    const query = params && typeof params === 'object' ? params : (params ? { subject_id: params } : undefined);
    return request('/api/reports', { params: query ? withAnalysisMode(query) : query });
  },
  getReport: (reportId) => request(`/api/reports/${reportId}`),
  listReportVersions: (reportId) => request(`/api/reports/${reportId}/versions`),
  getReportVersion: (reportId, versionId) =>
    request(`/api/reports/${reportId}/versions/${versionId}`),

  // —— 知识类目 / 古籍
  initCategories: () => request('/api/categories/init', { method: 'POST' }),
  listCategories: (params) => request('/api/categories', { params }),
  initKnowledge: () => request('/api/knowledge/init', { method: 'POST' }),
  listKnowledgeBooks: (params) => request('/api/knowledge/books', { params }),
  createKnowledgeBook: (body) => request('/api/knowledge/books', { method: 'POST', body }),
  getKnowledgeBook: (id) => request(`/api/knowledge/books/${id}`),
  createKnowledgeChunk: (body) => request('/api/knowledge/chunks', { method: 'POST', body }),
  listKnowledgeChunks: (bookId) => request(`/api/knowledge/books/${bookId}/chunks`),
  searchKnowledge: (body) => request('/api/knowledge/search', { method: 'POST', body }),
  importKnowledgeBookJson: (body) => request('/api/knowledge/import-book-json', { method: 'POST', body }),
  importKnowledgeFolder: (body) => request('/api/knowledge/import-folder', { method: 'POST', body }),
  getKnowledgeImportLogs: (params) => request('/api/knowledge/import-logs', { params }),
  getKnowledgeImportSampleFormat: () => request('/api/knowledge/import-sample-format'),
  getKnowledgeQualityCheck: () => request('/api/knowledge/quality-check'),

  // —— Prompt / 风控
  initPrompts: () => request('/api/prompts/init', { method: 'POST' }),
  listPrompts: (params) => request('/api/prompts', { params }),
  createPrompt: (body) => request('/api/prompts', { method: 'POST', body }),
  updatePrompt: (id, body) => request(`/api/prompts/${id}`, { method: 'PUT', body }),
  testPrompt: (id, body) => request(`/api/prompts/${id}/test`, {
    method: 'POST',
    body: withAnalysisMode(body),
    timeoutMs: 240000,
  }),
  initRiskTerms: () => request('/api/risk-terms/init', { method: 'POST' }),
  listRiskTerms: (params) => request('/api/risk-terms', { params }),
  checkRisk: (text, analysisMode = 'safe') => request('/api/risk/check', {
    method: 'POST',
    body: { text, analysis_mode: analysisMode },
  }),

  // —— 房屋 / 罗盘
  listHouses: () => request('/api/houses'),
  createHouse: (body) => request('/api/houses', { method: 'POST', body }),
  getHouse: (id) => request(`/api/houses/${id}`),
  listHouseCompassRecords: (id) => request(`/api/houses/${id}/compass-records`),
  setHouseMainDoorFromRecord: (houseId, recordId) =>
    request(`/api/houses/${houseId}/set-main-door-from-record/${recordId}`, { method: 'POST' }),
  convertCompass: (degree) => request('/api/compass/convert', { method: 'POST', body: { degree } }),
  createCompassRecord: (body) => request('/api/compass/records', { method: 'POST', body }),
  listCompassRecords: (params) => request('/api/compass/records', { params }),
  deleteCompassRecord: (id) => request(`/api/compass/records/${id}`, { method: 'DELETE' }),
  generateFengshuiBasicReport: (houseId, analysisMode = 'safe') => request('/api/fengshui/basic-report', {
    method: 'POST',
    body: { house_id: Number(houseId), analysis_mode: analysisMode },
    timeoutMs: 240000,
  }),
  getXuanKongPeriod: (year) => request('/api/xuankong/period', { params: { year } }),
  calculateXuanKong: (body) => request('/api/xuankong/calculate', {
    method: 'POST',
    body,
    timeoutMs: 240000,
  }),
  generateXuanKongReport: (body) => request('/api/xuankong/report', {
    method: 'POST',
    body: withAnalysisMode(body),
    timeoutMs: 240000,
  }),
  listXuanKongRecords: (params) => request('/api/xuankong/records', { params }),
  uploadFengshuiPhoto: ({ houseId, roomType, file }) => {
    const form = new FormData();
    if (houseId !== undefined && houseId !== null && houseId !== '') form.append('house_id', houseId);
    form.append('room_type', roomType || 'bedroom');
    form.append('file', file);
    return request('/api/fengshui-photo/upload', {
      method: 'POST',
      body: form,
      timeoutMs: 120000,
    });
  },
  analyzeFengshuiPhoto: (recordId) => request('/api/fengshui-photo/analyze', {
    method: 'POST',
    body: { record_id: Number(recordId) },
    timeoutMs: 240000,
  }),
  generateFengshuiPhotoReport: ({ recordId, userCorrection, analysisMode = 'safe' }) => request('/api/fengshui-photo/report', {
    method: 'POST',
    body: { record_id: Number(recordId), user_correction: userCorrection || {}, analysis_mode: analysisMode },
    timeoutMs: 240000,
  }),
  getFengshuiPhotoRecords: (params) => request('/api/fengshui-photo/records', { params }),
  deleteFengshuiPhotoRecord: (id) => request(`/api/fengshui-photo/records/${id}`, { method: 'DELETE' }),
  uploadLandscapePhoto: ({
    houseId,
    sceneType,
    targetLabel,
    degree,
    latitude,
    longitude,
    locationNote,
    file,
  }) => {
    const form = new FormData();
    if (houseId !== undefined && houseId !== null && houseId !== '') form.append('house_id', houseId);
    form.append('scene_type', sceneType || 'house_landscape');
    if (targetLabel) form.append('target_label', targetLabel);
    if (degree !== undefined && degree !== null && degree !== '') form.append('degree', degree);
    if (latitude !== undefined && latitude !== null && latitude !== '') form.append('latitude', latitude);
    if (longitude !== undefined && longitude !== null && longitude !== '') form.append('longitude', longitude);
    if (locationNote) form.append('location_note', locationNote);
    form.append('file', file);
    return request('/api/landscape-photo/upload', {
      method: 'POST',
      body: form,
      timeoutMs: 120000,
    });
  },
  analyzeLandscapePhoto: (recordId) => request('/api/landscape-photo/analyze', {
    method: 'POST',
    body: { record_id: Number(recordId) },
    timeoutMs: 240000,
  }),
  generateLandscapePhotoReport: ({ recordId, userCorrection, analysisMode = 'safe' }) => request('/api/landscape-photo/report', {
    method: 'POST',
    body: { record_id: Number(recordId), user_correction: userCorrection || {}, analysis_mode: analysisMode },
    timeoutMs: 240000,
  }),
  getLandscapePhotoRecord: (id) => request(`/api/landscape-photo/records/${id}`),
  getLandscapePhotoRecords: (params) => request('/api/landscape-photo/records', { params }),
  deleteLandscapePhotoRecord: (id) => request(`/api/landscape-photo/records/${id}`, { method: 'DELETE' }),
  createYinzhaiRecord: (body) => request('/api/yinzhai/records', {
    method: 'POST',
    body,
    timeoutMs: 120000,
  }),
  getYinzhaiRecord: (id) => request(`/api/yinzhai/records/${id}`),
  listYinzhaiRecords: (params) => request('/api/yinzhai/records', { params }),
  deleteYinzhaiRecord: (id) => request(`/api/yinzhai/records/${id}`, { method: 'DELETE' }),
  generateYinzhaiReport: (recordId, analysisMode = 'safe') => request('/api/yinzhai/report', {
    method: 'POST',
    body: { record_id: Number(recordId), analysis_mode: analysisMode },
    timeoutMs: 240000,
  }),
  getTianxingMappings: () => request('/api/tianxing/mappings'),
  lookupTianxing: (params) => request('/api/tianxing/lookup', { params }),
  queryTianxing: (body) => request('/api/tianxing/query', {
    method: 'POST',
    body,
    timeoutMs: 120000,
  }),
  listTianxingRecords: (params) => request('/api/tianxing/records', { params }),
  deleteTianxingRecord: (id) => request(`/api/tianxing/records/${id}`, { method: 'DELETE' }),
  generateTianxingReport: (body) => request('/api/tianxing/report', {
    method: 'POST',
    body: withAnalysisMode(body),
    timeoutMs: 240000,
  }),

  // —— 择日 / 起名 / 测字
  dateSelection: (type, body) => request(`/api/date-selection/${type}`, {
    method: 'POST',
    body: withAnalysisMode(body),
    timeoutMs: 240000,
  }),
  naming: (type, body) => request(`/api/naming/${type}`, {
    method: 'POST',
    body: withAnalysisMode(body),
    timeoutMs: 240000,
  }),
  wordDivination: (body) => request('/api/divination/word', {
    method: 'POST',
    body: withAnalysisMode(body),
    timeoutMs: 240000,
  }),
  lotteryDivination: (body) => request('/api/divination/lottery', {
    method: 'POST',
    body: withAnalysisMode(body),
    timeoutMs: 240000,
  }),

  // —— 历史
  history: (subjectId) =>
    request('/api/history', { params: subjectId ? { subject_id: subjectId } : undefined }),

  // —— 案例反馈
  listCases: (params) => request('/api/cases', { params }),
  getCaseDetail: (caseId) => request(`/api/cases/${caseId}`),
  submitFeedback: (caseId, body) =>
    request(`/api/cases/${caseId}/feedback`, { method: 'POST', body }),
  listFeedbacks: (params) => request('/api/feedbacks', { params }),
  feedbackSummary: () => request('/api/feedbacks/summary'),
};

export default api;
