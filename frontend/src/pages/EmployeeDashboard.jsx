import React from 'react';
import { useNavigate } from 'react-router-dom';

export default function EmployeeDashboard() {
  const navigate = useNavigate();
  const username = localStorage.getItem('username') || 'Employee';

  const handleLogout = () => {
    localStorage.clear();
    navigate('/login');
  };

  return (
    <div className="dashboard-shell">
      <div className="dashboard-card">
        <div style={{
          width: 60, height: 60, borderRadius: 14,
          background: 'linear-gradient(135deg, #06b6d4, #6366f1)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          fontSize: '1.8rem', margin: '0 auto 1.25rem',
          boxShadow: '0 0 40px rgba(6,182,212,0.4)'
        }}>🎫</div>
        <h2 style={{ marginBottom: '0.5rem' }}>IT Support Portal</h2>
        <p style={{ color: 'var(--clr-text-2)', marginBottom: '1.5rem' }}>
          Welcome, <strong style={{ color: 'var(--clr-heading)' }}>{username}</strong> — submit and track your tickets below.
        </p>
        <button
          onClick={handleLogout}
          className="btn-primary"
          style={{ maxWidth: 200 }}
          id="employee-logout-btn"
        >
          Sign Out
        </button>
      </div>
    </div>
  );
}