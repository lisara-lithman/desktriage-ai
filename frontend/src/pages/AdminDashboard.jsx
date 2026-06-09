import React, { useState, useEffect, useCallback, useRef } from 'react';
import axios from 'axios';
import { useNavigate } from 'react-router-dom';

const API = 'http://127.0.0.1:8000';

const STATUS_OPTIONS = ['Pending_Admin_Review', 'In_Progress', 'Resolved', 'Closed'];

const STATUS_META = {
  AI_Processing:        { label: 'AI Analyzing…',  color: '#818cf8', bg: 'rgba(129,140,248,0.12)' },
  Pending_Admin_Review: { label: 'Pending Review',  color: '#f59e0b', bg: 'rgba(245,158,11,0.12)'  },
  In_Progress:          { label: 'In Progress',     color: '#06b6d4', bg: 'rgba(6,182,212,0.12)'   },
  Resolved:             { label: 'Resolved',         color: '#34d399', bg: 'rgba(52,211,153,0.12)'  },
  Closed:               { label: 'Closed',           color: '#94a3b8', bg: 'rgba(148,163,184,0.12)' },
};

const PRIORITY_COLOR = {
  Low:      '#34d399',
  Medium:   '#f59e0b',
  High:     '#f87171',
  Critical: '#c084fc',
  Pending:  '#64748b',
};

const DEPT_LABELS = {
  IT_Support: 'IT Support',
  Finance:    'Finance',
  HR:         'Human Resources',
  Pending:    'Classifying…',
};

export default function AdminDashboard() {
  const navigate    = useNavigate();
  const username    = localStorage.getItem('username') || 'Admin';
  const role        = localStorage.getItem('role')     || '';
  const department  = localStorage.getItem('department') || '';
  const token       = localStorage.getItem('token');

  const isGlobal = role === 'admin_global';

  const [tickets,        setTickets]        = useState([]);
  const [loading,        setLoading]        = useState(false);
  const [expandedId,     setExpandedId]     = useState(null);
  const [filterStatus,   setFilterStatus]   = useState('all');
  const [filterPriority, setFilterPriority] = useState('all');
  const [replyForms,     setReplyForms]     = useState({});
  const [replyLoading,   setReplyLoading]   = useState({});
  const [replyMsg,       setReplyMsg]       = useState({});

  // ── Auth guard ─────────────────────────────────────────────────────────────
  useEffect(() => {
    if (!token || (role !== 'admin_global' && role !== 'admin_dept')) {
      navigate('/login');
    }
  }, [token, role, navigate]);

  // ── Fetch tickets ──────────────────────────────────────────────────────────
  const fetchTickets = useCallback(async () => {
    setLoading(true);
    try {
      const endpoint = isGlobal
        ? `${API}/api/tickets/admin/all`
        : `${API}/api/tickets/admin/dept`;
      const res = await axios.get(endpoint, {
        headers: { Authorization: `Bearer ${token}` },
      });
      setTickets(res.data.tickets || []);
    } catch {
      // session expired or forbidden
    } finally {
      setLoading(false);
    }
  }, [token, isGlobal]);

  useEffect(() => { fetchTickets(); }, [fetchTickets]);

  // ── Auto-refresh while any ticket is still AI_Processing ─────────────────
  useEffect(() => {
    const hasProcessing = tickets.some(t => t.status === 'AI_Processing');
    if (!hasProcessing) return;
    const interval = setInterval(() => fetchTickets(), 5000);
    return () => clearInterval(interval);
  }, [tickets, fetchTickets]);

  // ── When a ticket gets expanded, initialise the reply form with AI draft ──
  const handleExpand = (ticket) => {
    const id = ticket._id;
    const isExpanded = expandedId === id;
    setExpandedId(isExpanded ? null : id);

    // Pre-populate with AI draft on first expand (if not already edited)
    if (!isExpanded && !replyForms[id]) {
      setReplyForms(prev => ({
        ...prev,
        [id]: {
          reply:       ticket.ai_draft_reply || '',
          status:      ticket.status === 'AI_Processing' ? 'In_Progress' : ticket.status,
          isDirty:     false,
        },
      }));
    }
  };

  // ── Reply handlers ─────────────────────────────────────────────────────────
  const handleReplyChange = (ticketId, field, value) => {
    setReplyForms(prev => ({
      ...prev,
      [ticketId]: {
        ...prev[ticketId],
        [field]:  value,
        isDirty: field === 'reply' ? value !== (tickets.find(t => t._id === ticketId)?.ai_draft_reply || '') : prev[ticketId]?.isDirty,
      },
    }));
  };

  const handleResetToAiDraft = (ticketId) => {
    const ticket = tickets.find(t => t._id === ticketId);
    setReplyForms(prev => ({
      ...prev,
      [ticketId]: {
        ...prev[ticketId],
        reply:   ticket?.ai_draft_reply || '',
        isDirty: false,
      },
    }));
  };

  const handleReplySubmit = async (ticketId) => {
    const form = replyForms[ticketId] || {};
    if (!form.reply?.trim()) return;

    setReplyLoading(prev => ({ ...prev, [ticketId]: true }));
    setReplyMsg(prev => ({ ...prev, [ticketId]: '' }));

    try {
      await axios.post(
        `${API}/api/tickets/${ticketId}/reply`,
        { admin_reply: form.reply, status: form.status || 'In_Progress' },
        { headers: { Authorization: `Bearer ${token}` } }
      );
      setReplyMsg(prev => ({ ...prev, [ticketId]: 'success' }));
      await fetchTickets();
      setExpandedId(null);
    } catch (err) {
      setReplyMsg(prev => ({ ...prev, [ticketId]: err.response?.data?.detail || 'Failed to send reply.' }));
    } finally {
      setReplyLoading(prev => ({ ...prev, [ticketId]: false }));
    }
  };

  const handleLogout = () => {
    localStorage.clear();
    navigate('/login');
  };

  // ── Filter logic ──────────────────────────────────────────────────────────
  const filtered = tickets.filter(t => {
    const statusOk   = filterStatus   === 'all' || t.status   === filterStatus;
    const priorityOk = filterPriority === 'all' || t.priority === filterPriority;
    return statusOk && priorityOk;
  });

  const stats = {
    total:      tickets.length,
    processing: tickets.filter(t => t.status === 'AI_Processing').length,
    pending:    tickets.filter(t => t.status === 'Pending_Admin_Review').length,
    active:     tickets.filter(t => t.status === 'In_Progress').length,
    resolved:   tickets.filter(t => t.status === 'Resolved' || t.status === 'Closed').length,
  };

  // ── Render ─────────────────────────────────────────────────────────────────
  return (
    <div className="dash-shell">

      {/* ── Sidebar ─────────────────────────────────────────────── */}
      <aside className="dash-sidebar">
        <div className="dash-sidebar-logo">
          <div className="dash-sidebar-icon">🛡️</div>
          <span>DeskTriage</span>
        </div>

        <div className="dash-sidebar-section-label">Overview</div>
        <div className="dash-stats-list">
          <div className="dash-stat-item">
            <span className="dash-stat-label">Total Tickets</span>
            <span className="dash-stat-value">{stats.total}</span>
          </div>
          {stats.processing > 0 && (
            <div className="dash-stat-item">
              <span className="dash-stat-label">AI Analyzing</span>
              <span className="dash-stat-value" style={{ color: '#818cf8' }}>
                <span className="sidebar-pulse-dot" /> {stats.processing}
              </span>
            </div>
          )}
          <div className="dash-stat-item">
            <span className="dash-stat-label">Pending Review</span>
            <span className="dash-stat-value" style={{ color: '#f59e0b' }}>{stats.pending}</span>
          </div>
          <div className="dash-stat-item">
            <span className="dash-stat-label">In Progress</span>
            <span className="dash-stat-value" style={{ color: '#06b6d4' }}>{stats.active}</span>
          </div>
          <div className="dash-stat-item">
            <span className="dash-stat-label">Resolved</span>
            <span className="dash-stat-value" style={{ color: '#34d399' }}>{stats.resolved}</span>
          </div>
        </div>

        <div className="dash-sidebar-footer">
          <div className="dash-user-chip">
            <div className="dash-avatar" style={{ background: 'linear-gradient(135deg,#6366f1,#8b5cf6)' }}>
              {username[0]?.toUpperCase()}
            </div>
            <div>
              <div className="dash-user-name">{username}</div>
              <div className="dash-user-role">
                {isGlobal ? '🌐 Global Admin' : `🏢 ${DEPT_LABELS[department] || department}`}
              </div>
            </div>
          </div>
          <button className="dash-logout-btn" onClick={handleLogout} id="admin-logout-btn">
            Sign Out
          </button>
        </div>
      </aside>

      {/* ── Main Content ─────────────────────────────────────────── */}
      <main className="dash-main">
        <div className="dash-section">
          <div className="dash-section-header">
            <div>
              <h1 className="dash-section-title">
                {isGlobal ? 'All Tickets — Global View' : `${DEPT_LABELS[department] || department} Tickets`}
              </h1>
              <p className="dash-section-sub">
                {isGlobal
                  ? 'Viewing all tickets across every department.'
                  : 'Viewing tickets assigned to your department.'}
                {stats.processing > 0 && (
                  <span className="ai-processing-note"> AI is currently processing {stats.processing} ticket(s) — auto-refreshing.</span>
                )}
              </p>
            </div>

            {/* Filters */}
            <div className="admin-filters">
              <select
                className="form-input admin-filter-select"
                value={filterStatus}
                onChange={e => setFilterStatus(e.target.value)}
                id="filter-status"
              >
                <option value="all">All Statuses</option>
                <option value="AI_Processing">AI Analyzing</option>
                {STATUS_OPTIONS.map(s => (
                  <option key={s} value={s}>{STATUS_META[s]?.label}</option>
                ))}
              </select>
              <select
                className="form-input admin-filter-select"
                value={filterPriority}
                onChange={e => setFilterPriority(e.target.value)}
                id="filter-priority"
              >
                <option value="all">All Priorities</option>
                {['Low','Medium','High','Critical'].map(p => (
                  <option key={p} value={p}>{p}</option>
                ))}
              </select>
              <button className="btn-refresh" onClick={fetchTickets} title="Refresh tickets" id="refresh-tickets">
                🔄
              </button>
            </div>
          </div>

          {loading && (
            <div className="dash-loading">
              <div className="dash-spinner" />
              <span>Loading tickets…</span>
            </div>
          )}

          {!loading && filtered.length === 0 && (
            <div className="dash-empty">
              <div className="dash-empty-icon">📭</div>
              <p>No tickets match the current filters.</p>
            </div>
          )}

          {/* Ticket list */}
          <div className="ticket-list">
            {filtered.map(ticket => {
              const s  = STATUS_META[ticket.status] || STATUS_META['Pending_Admin_Review'];
              const pc = PRIORITY_COLOR[ticket.priority] || '#94a3b8';
              const isExpanded   = expandedId === ticket._id;
              const isProcessing = ticket.status === 'AI_Processing';
              const rf           = replyForms[ticket._id] || {};
              const rloading     = replyLoading[ticket._id] || false;
              const rmsg         = replyMsg[ticket._id]     || '';
              const hasDraft     = !!ticket.ai_draft_reply;

              return (
                <div
                  key={ticket._id}
                  className={`ticket-card ${isExpanded ? 'ticket-card-expanded' : ''} ${isProcessing ? 'ticket-card-processing' : ''}`}
                  id={`admin-ticket-${ticket._id}`}
                >
                  {/* Header */}
                  <div
                    className="ticket-card-header"
                    style={{ cursor: isProcessing ? 'default' : 'pointer' }}
                    onClick={() => !isProcessing && handleExpand(ticket)}
                  >
                    <div className="ticket-card-title-row">
                      <h3 className="ticket-card-title">{ticket.title}</h3>
                      <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexShrink: 0 }}>
                        <span
                          className={`ticket-status-badge ${isProcessing ? 'ticket-status-badge-pulse' : ''}`}
                          style={{ color: s.color, background: s.bg, border: `1px solid ${s.color}30` }}
                        >
                          {isProcessing && <span className="status-spinner" />}
                          {s.label}
                        </span>
                        {!isProcessing && (
                          <span className="ticket-expand-arrow">{isExpanded ? '▲' : '▼'}</span>
                        )}
                      </div>
                    </div>

                    <div className="ticket-meta-row">
                      <span className="ticket-meta-item">👤 {ticket.employee_username}</span>
                      <span className="ticket-meta-item">📧 {ticket.employee_email}</span>
                      {isGlobal && (
                        <span className="ticket-meta-item">
                          🏢 {DEPT_LABELS[ticket.department] || ticket.department}
                          {ticket.ai_department && <span className="ai-tag">🤖</span>}
                        </span>
                      )}
                      <span className="ticket-meta-item" style={{ color: pc }}>
                        ⚡ {ticket.priority === 'Pending' ? 'Classifying…' : ticket.priority}
                        {ticket.ai_priority && <span className="ai-tag">🤖</span>}
                      </span>
                      <span className="ticket-meta-item">
                        🕐 {new Date(ticket.created_at).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' })}
                      </span>
                    </div>

                    {/* AI Processing indicator inside card */}
                    {isProcessing && (
                      <div className="ticket-ai-processing">
                        <div className="ai-processing-dots"><span /><span /><span /></div>
                        <span>AI is analyzing this ticket — auto-refreshing every 5s…</span>
                      </div>
                    )}
                  </div>

                  {/* Expandable detail + reply panel */}
                  {isExpanded && !isProcessing && (
                    <div className="ticket-expand-body">
                      <div className="form-divider" style={{ margin: '0.75rem 0' }} />

                      {/* Description */}
                      <div className="form-group" style={{ marginBottom: '1rem' }}>
                        <span className="form-label">Issue Description</span>
                        <p className="ticket-description">{ticket.description}</p>
                      </div>

                      {/* AI Triage info row */}
                      {(ticket.ai_department || ticket.ai_priority) && (
                        <div className="ai-triage-info-row">
                          <span className="ai-triage-badge">🤖 AI Classification</span>
                          {ticket.ai_department && (
                            <span className="ai-triage-chip">
                              🏢 {DEPT_LABELS[ticket.ai_department] || ticket.ai_department}
                            </span>
                          )}
                          {ticket.ai_priority && (
                            <span className="ai-triage-chip" style={{ color: PRIORITY_COLOR[ticket.ai_priority] }}>
                              ⚡ {ticket.ai_priority}
                            </span>
                          )}
                          {ticket.ai_failed && (
                            <span className="ai-triage-chip ai-failed-chip">⚠️ AI routing used fallback</span>
                          )}
                        </div>
                      )}

                      {/* Existing confirmed reply (if already sent) */}
                      {ticket.admin_reply && (
                        <div className="ticket-reply-block" style={{ marginBottom: '1rem' }}>
                          <div className="ticket-reply-label">
                            <span>💬</span>
                            <span>Sent Reply</span>
                            {ticket.replied_by && (
                              <span className="ticket-replied-by">by @{ticket.replied_by}</span>
                            )}
                          </div>
                          <p className="ticket-reply-text">{ticket.admin_reply}</p>
                        </div>
                      )}

                      {/* Reply / Confirm form */}
                      <div className="admin-reply-form">

                        {/* AI Draft label + Reset button */}
                        <div className="reply-label-row">
                          <label className="form-label" htmlFor={`reply-text-${ticket._id}`}>
                            {hasDraft ? '🤖 AI Draft Reply' : 'Your Reply to Employee'}
                          </label>
                          {hasDraft && rf.isDirty && (
                            <button
                              className="btn-reset-draft"
                              onClick={() => handleResetToAiDraft(ticket._id)}
                              id={`reset-draft-${ticket._id}`}
                              type="button"
                            >
                              ↩ Reset to AI Draft
                            </button>
                          )}
                        </div>

                        {hasDraft && !rf.isDirty && (
                          <div className="ai-draft-hint">
                            ✨ Pre-filled with AI draft — review and edit before confirming.
                          </div>
                        )}
                        {hasDraft && rf.isDirty && (
                          <div className="ai-draft-hint ai-draft-modified">
                            ✏️ You have modified the AI draft.
                          </div>
                        )}

                        <div className="form-group">
                          <textarea
                            id={`reply-text-${ticket._id}`}
                            className="form-input form-textarea"
                            rows={5}
                            placeholder={hasDraft ? '' : 'Type your response here…'}
                            value={rf.reply || ''}
                            onChange={e => handleReplyChange(ticket._id, 'reply', e.target.value)}
                          />
                        </div>

                        <div className="admin-reply-actions">
                          <div className="form-group" style={{ flex: 1 }}>
                            <label className="form-label" htmlFor={`reply-status-${ticket._id}`}>
                              Update Status
                            </label>
                            <select
                              id={`reply-status-${ticket._id}`}
                              className="form-input"
                              value={rf.status || ticket.status}
                              onChange={e => handleReplyChange(ticket._id, 'status', e.target.value)}
                            >
                              {STATUS_OPTIONS.map(s => (
                                <option key={s} value={s}>{STATUS_META[s]?.label}</option>
                              ))}
                            </select>
                          </div>

                          <button
                            className="btn-primary admin-reply-btn"
                            disabled={rloading || !rf.reply?.trim()}
                            onClick={() => handleReplySubmit(ticket._id)}
                            id={`reply-submit-${ticket._id}`}
                          >
                            {rloading ? 'Sending…' : '✅ Confirm & Send Reply'}
                          </button>
                        </div>

                        {rmsg === 'success' && (
                          <div className="alert alert-success" style={{ marginTop: '0.75rem' }}>
                            ✅ Reply confirmed and sent to employee!
                          </div>
                        )}
                        {rmsg && rmsg !== 'success' && (
                          <div className="alert alert-error" style={{ marginTop: '0.75rem' }}>
                            ⚠️ {rmsg}
                          </div>
                        )}
                      </div>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      </main>
    </div>
  );
}