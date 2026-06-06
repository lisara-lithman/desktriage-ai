import React, { useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import { useNavigate } from 'react-router-dom';

const API = 'http://127.0.0.1:8000';

const STATUS_OPTIONS = ['Pending_Admin_Review', 'In_Progress', 'Resolved', 'Closed'];

const STATUS_META = {
  Pending_Admin_Review: { label: 'Pending Review', color: '#f59e0b', bg: 'rgba(245,158,11,0.12)' },
  In_Progress:          { label: 'In Progress',    color: '#06b6d4', bg: 'rgba(6,182,212,0.12)'  },
  Resolved:             { label: 'Resolved',        color: '#34d399', bg: 'rgba(52,211,153,0.12)' },
  Closed:               { label: 'Closed',          color: '#94a3b8', bg: 'rgba(148,163,184,0.12)'},
};

const PRIORITY_COLOR = {
  Low:      '#34d399',
  Medium:   '#f59e0b',
  High:     '#f87171',
  Critical: '#c084fc',
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
  const [replyForms,     setReplyForms]     = useState({});  // { ticketId: { reply, status } }
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

  // ── Reply handlers ─────────────────────────────────────────────────────────
  const handleReplyChange = (ticketId, field, value) => {
    setReplyForms(prev => ({
      ...prev,
      [ticketId]: { ...prev[ticketId], [field]: value },
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
    total:    tickets.length,
    pending:  tickets.filter(t => t.status === 'Pending_Admin_Review').length,
    active:   tickets.filter(t => t.status === 'In_Progress').length,
    resolved: tickets.filter(t => t.status === 'Resolved' || t.status === 'Closed').length,
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
          <div className="dash-stat-item">
            <span className="dash-stat-label">Pending</span>
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
                {isGlobal ? '🌐 Global Admin' : `🏢 ${department?.replace(/_/g, ' ')}`}
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
                {isGlobal ? 'All Tickets — Global View' : `${department?.replace(/_/g, ' ')} Tickets`}
              </h1>
              <p className="dash-section-sub">
                {isGlobal
                  ? 'Viewing all tickets across every department.'
                  : `Viewing tickets assigned to your department.`}
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
              const isExpanded = expandedId === ticket._id;
              const rf = replyForms[ticket._id] || { reply: ticket.admin_reply || '', status: ticket.status };
              const rloading = replyLoading[ticket._id] || false;
              const rmsg     = replyMsg[ticket._id]     || '';

              return (
                <div key={ticket._id} className={`ticket-card ${isExpanded ? 'ticket-card-expanded' : ''}`} id={`admin-ticket-${ticket._id}`}>
                  {/* Header */}
                  <div
                    className="ticket-card-header"
                    style={{ cursor: 'pointer' }}
                    onClick={() => setExpandedId(isExpanded ? null : ticket._id)}
                  >
                    <div className="ticket-card-title-row">
                      <h3 className="ticket-card-title">{ticket.title}</h3>
                      <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexShrink: 0 }}>
                        <span
                          className="ticket-status-badge"
                          style={{ color: s.color, background: s.bg, border: `1px solid ${s.color}30` }}
                        >
                          {s.label}
                        </span>
                        <span className="ticket-expand-arrow">{isExpanded ? '▲' : '▼'}</span>
                      </div>
                    </div>
                    <div className="ticket-meta-row">
                      <span className="ticket-meta-item">👤 {ticket.employee_username}</span>
                      <span className="ticket-meta-item">📧 {ticket.employee_email}</span>
                      {isGlobal && (
                        <span className="ticket-meta-item">🏢 {ticket.department?.replace(/_/g, ' ')}</span>
                      )}
                      <span className="ticket-meta-item" style={{ color: pc }}>⚡ {ticket.priority}</span>
                      <span className="ticket-meta-item">
                        🕐 {new Date(ticket.created_at).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' })}
                      </span>
                    </div>
                  </div>

                  {/* Expandable detail + reply panel */}
                  {isExpanded && (
                    <div className="ticket-expand-body">
                      <div className="form-divider" style={{ margin: '0.75rem 0' }} />

                      {/* Description */}
                      <div className="form-group" style={{ marginBottom: '1rem' }}>
                        <span className="form-label">Issue Description</span>
                        <p className="ticket-description">{ticket.description}</p>
                      </div>

                      {/* Existing reply */}
                      {ticket.admin_reply && (
                        <div className="ticket-reply-block" style={{ marginBottom: '1rem' }}>
                          <div className="ticket-reply-label">
                            <span>💬</span>
                            <span>Previous Reply</span>
                            {ticket.replied_by && (
                              <span className="ticket-replied-by">by @{ticket.replied_by}</span>
                            )}
                          </div>
                          <p className="ticket-reply-text">{ticket.admin_reply}</p>
                        </div>
                      )}

                      {/* Reply form */}
                      <div className="admin-reply-form">
                        <div className="form-group">
                          <label className="form-label" htmlFor={`reply-text-${ticket._id}`}>
                            Your Reply to Employee
                          </label>
                          <textarea
                            id={`reply-text-${ticket._id}`}
                            className="form-input form-textarea"
                            rows={4}
                            placeholder="Type your response here…"
                            value={rf.reply}
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
                            disabled={rloading}
                            onClick={() => handleReplySubmit(ticket._id)}
                            id={`reply-submit-${ticket._id}`}
                          >
                            {rloading ? 'Sending…' : 'Send Reply →'}
                          </button>
                        </div>

                        {rmsg === 'success' && (
                          <div className="alert alert-success" style={{ marginTop: '0.75rem' }}>
                            ✅ Reply sent successfully!
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