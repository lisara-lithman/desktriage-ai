import React, { useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import { useNavigate } from 'react-router-dom';

const API = 'http://127.0.0.1:8000';

const DEPARTMENTS = ['IT_Support', 'HR_Operations', 'Corporate_Finance'];
const PRIORITIES  = ['Low', 'Medium', 'High', 'Critical'];

const STATUS_META = {
  Pending_Admin_Review: { label: 'Pending Review', color: '#f59e0b', bg: 'rgba(245,158,11,0.12)' },
  In_Progress:          { label: 'In Progress',    color: '#06b6d4', bg: 'rgba(6,182,212,0.12)'   },
  Resolved:             { label: 'Resolved',        color: '#34d399', bg: 'rgba(52,211,153,0.12)'  },
  Closed:               { label: 'Closed',          color: '#94a3b8', bg: 'rgba(148,163,184,0.12)' },
};

const PRIORITY_COLOR = {
  Low:      '#34d399',
  Medium:   '#f59e0b',
  High:     '#f87171',
  Critical: '#c084fc',
};

export default function EmployeeDashboard() {
  const navigate  = useNavigate();
  const username  = localStorage.getItem('username') || 'Employee';
  const token     = localStorage.getItem('token');

  const [activeTab, setActiveTab] = useState('submit');
  const [tickets,   setTickets]   = useState([]);
  const [loading,   setLoading]   = useState(false);
  const [ticketsLoading, setTicketsLoading] = useState(false);

  const [form, setForm] = useState({
    title: '', description: '', department: 'IT_Support', priority: 'Medium',
  });
  const [submitMsg, setSubmitMsg] = useState({ type: '', text: '' });

  // ── Auth guard ─────────────────────────────────────────────────────────────
  useEffect(() => {
    if (!token) navigate('/login');
  }, [token, navigate]);

  // ── Fetch tickets ──────────────────────────────────────────────────────────
  const fetchTickets = useCallback(async () => {
    setTicketsLoading(true);
    try {
      const res = await axios.get(`${API}/api/tickets/my`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      setTickets(res.data.tickets || []);
    } catch {
      // silently fail; token may have expired
    } finally {
      setTicketsLoading(false);
    }
  }, [token]);

  useEffect(() => {
    if (activeTab === 'tickets') fetchTickets();
  }, [activeTab, fetchTickets]);

  // ── Handlers ───────────────────────────────────────────────────────────────
  const handleChange = (e) =>
    setForm({ ...form, [e.target.name]: e.target.value });

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setSubmitMsg({ type: '', text: '' });

    try {
      await axios.post(`${API}/api/tickets/submit`, form, {
        headers: { Authorization: `Bearer ${token}` },
      });
      setSubmitMsg({ type: 'success', text: '✅ Ticket submitted! Your admin has been notified.' });
      setForm({ title: '', description: '', department: 'IT_Support', priority: 'Medium' });
    } catch (err) {
      setSubmitMsg({ type: 'error', text: err.response?.data?.detail || 'Submission failed. Try again.' });
    } finally {
      setLoading(false);
    }
  };

  const handleLogout = () => {
    localStorage.clear();
    navigate('/login');
  };

  // ── Render ─────────────────────────────────────────────────────────────────
  return (
    <div className="dash-shell">

      {/* ── Sidebar ─────────────────────────────────────────────── */}
      <aside className="dash-sidebar">
        <div className="dash-sidebar-logo">
          <div className="dash-sidebar-icon">🎫</div>
          <span>DeskTriage</span>
        </div>

        <nav className="dash-nav">
          <button
            className={`dash-nav-item ${activeTab === 'submit' ? 'active' : ''}`}
            onClick={() => setActiveTab('submit')}
            id="tab-submit"
          >
            <span className="dash-nav-icon">✏️</span>
            <span>Submit Ticket</span>
          </button>
          <button
            className={`dash-nav-item ${activeTab === 'tickets' ? 'active' : ''}`}
            onClick={() => setActiveTab('tickets')}
            id="tab-my-tickets"
          >
            <span className="dash-nav-icon">📋</span>
            <span>My Tickets</span>
          </button>
        </nav>

        <div className="dash-sidebar-footer">
          <div className="dash-user-chip">
            <div className="dash-avatar">{username[0]?.toUpperCase()}</div>
            <div>
              <div className="dash-user-name">{username}</div>
              <div className="dash-user-role">Employee</div>
            </div>
          </div>
          <button className="dash-logout-btn" onClick={handleLogout} id="employee-logout-btn">
            Sign Out
          </button>
        </div>
      </aside>

      {/* ── Main Content ─────────────────────────────────────────── */}
      <main className="dash-main">

        {/* Submit Ticket Tab */}
        {activeTab === 'submit' && (
          <div className="dash-section">
            <div className="dash-section-header">
              <h1 className="dash-section-title">Submit a Support Ticket</h1>
              <p className="dash-section-sub">Your request will be routed to the relevant department admin and reviewed promptly.</p>
            </div>

            <div className="ticket-form-card">
              {submitMsg.text && (
                <div className={`alert ${submitMsg.type === 'success' ? 'alert-success' : 'alert-error'}`}>
                  {submitMsg.text}
                </div>
              )}

              <form onSubmit={handleSubmit} className="form-stack">
                <div className="form-group">
                  <label className="form-label" htmlFor="ticket-title">Ticket Title</label>
                  <input
                    id="ticket-title"
                    name="title"
                    className="form-input"
                    placeholder="Brief summary of your issue…"
                    value={form.title}
                    onChange={handleChange}
                    required
                  />
                </div>

                <div className="form-group">
                  <label className="form-label" htmlFor="ticket-description">Description</label>
                  <textarea
                    id="ticket-description"
                    name="description"
                    className="form-input form-textarea"
                    placeholder="Describe your issue in detail — include any error messages, steps taken, etc."
                    value={form.description}
                    onChange={handleChange}
                    required
                    rows={5}
                  />
                </div>

                <div className="form-grid-2">
                  <div className="form-group">
                    <label className="form-label" htmlFor="ticket-department">Department</label>
                    <select
                      id="ticket-department"
                      name="department"
                      className="form-input"
                      value={form.department}
                      onChange={handleChange}
                    >
                      {DEPARTMENTS.map(d => (
                        <option key={d} value={d}>{d.replace(/_/g, ' ')}</option>
                      ))}
                    </select>
                  </div>

                  <div className="form-group">
                    <label className="form-label" htmlFor="ticket-priority">Priority</label>
                    <select
                      id="ticket-priority"
                      name="priority"
                      className="form-input"
                      value={form.priority}
                      onChange={handleChange}
                    >
                      {PRIORITIES.map(p => (
                        <option key={p} value={p}>{p}</option>
                      ))}
                    </select>
                  </div>
                </div>

                <button
                  type="submit"
                  className="btn-primary"
                  disabled={loading}
                  id="ticket-submit-btn"
                >
                  {loading ? 'Submitting…' : 'Submit Ticket →'}
                </button>
              </form>
            </div>
          </div>
        )}

        {/* My Tickets Tab */}
        {activeTab === 'tickets' && (
          <div className="dash-section">
            <div className="dash-section-header">
              <h1 className="dash-section-title">My Tickets</h1>
              <p className="dash-section-sub">Track the status of all your submitted support requests.</p>
            </div>

            {ticketsLoading && (
              <div className="dash-loading">
                <div className="dash-spinner" />
                <span>Loading your tickets…</span>
              </div>
            )}

            {!ticketsLoading && tickets.length === 0 && (
              <div className="dash-empty">
                <div className="dash-empty-icon">📭</div>
                <p>No tickets yet. Submit one to get started!</p>
              </div>
            )}

            <div className="ticket-list">
              {tickets.map(ticket => {
                const s = STATUS_META[ticket.status] || STATUS_META['Pending_Admin_Review'];
                const pc = PRIORITY_COLOR[ticket.priority] || '#94a3b8';
                return (
                  <div key={ticket._id} className="ticket-card" id={`ticket-${ticket._id}`}>
                    {/* Header row */}
                    <div className="ticket-card-header">
                      <div className="ticket-card-title-row">
                        <h3 className="ticket-card-title">{ticket.title}</h3>
                        <span
                          className="ticket-status-badge"
                          style={{ color: s.color, background: s.bg, border: `1px solid ${s.color}30` }}
                        >
                          {s.label}
                        </span>
                      </div>
                      <div className="ticket-meta-row">
                        <span className="ticket-meta-item">
                          🏢 {ticket.department?.replace(/_/g, ' ')}
                        </span>
                        <span className="ticket-meta-item" style={{ color: pc }}>
                          ⚡ {ticket.priority}
                        </span>
                        <span className="ticket-meta-item">
                          🕐 {new Date(ticket.created_at).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' })}
                        </span>
                      </div>
                    </div>

                    {/* Description */}
                    <p className="ticket-description">{ticket.description}</p>

                    {/* Admin Reply */}
                    {ticket.admin_reply ? (
                      <div className="ticket-reply-block">
                        <div className="ticket-reply-label">
                          <span>💬</span>
                          <span>Admin Reply</span>
                          {ticket.replied_by && (
                            <span className="ticket-replied-by">by @{ticket.replied_by}</span>
                          )}
                        </div>
                        <p className="ticket-reply-text">{ticket.admin_reply}</p>
                      </div>
                    ) : (
                      <div className="ticket-awaiting">
                        <span>⏳</span> Awaiting admin response…
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </main>
    </div>
  );
}