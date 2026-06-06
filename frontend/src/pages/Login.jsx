import React, { useState } from 'react';
import axios from 'axios';
import { useNavigate, Link } from 'react-router-dom';

export default function Login() {
  const navigate = useNavigate();
  const [credentials, setCredentials] = useState({ email: '', password: '' });
  const [error,   setError]   = useState('');
  const [loading, setLoading] = useState(false);

  const handleChange = (e) =>
    setCredentials({ ...credentials, [e.target.name]: e.target.value });

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      const response = await axios.post('http://127.0.0.1:8000/api/auth/login', credentials);
      const { access_token, role, username, email, department } = response.data;

      // Persist session data
      localStorage.setItem('token',      access_token);
      localStorage.setItem('role',       role);
      localStorage.setItem('username',   username);
      localStorage.setItem('email',      email);
      localStorage.setItem('department', department || '');

      // Route based on role
      if (role === 'admin_global' || role === 'admin_dept') {
        navigate('/admin-dashboard');
      } else {
        navigate('/employee-dashboard');
      }
    } catch (err) {
      setError(err.response?.data?.detail || 'Invalid credentials. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="page-container">
      <div className="auth-card" id="login-card">

        {/* Logo + Heading */}
        <div className="auth-logo-block">
          <div className="auth-logo-icon">🔐</div>
          <h2 className="auth-title">Welcome back</h2>
          <p className="auth-subtitle">Sign in to your DeskTriage workspace</p>
        </div>

        {/* Error alert */}
        {error && (
          <div className="alert alert-error" role="alert" id="login-error">
            <span>⚠️</span>
            <span>{error}</span>
          </div>
        )}

        {/* Form */}
        <form onSubmit={handleSubmit} className="form-stack" style={{ marginTop: error ? '1rem' : 0 }}>
          <div className="form-group">
            <label className="form-label" htmlFor="login-email">Corporate Email</label>
            <input
              id="login-email"
              type="email"
              name="email"
              required
              autoComplete="email"
              placeholder="you@company.com"
              className="form-input"
              onChange={handleChange}
            />
          </div>

          <div className="form-group">
            <label className="form-label" htmlFor="login-password">Password</label>
            <input
              id="login-password"
              type="password"
              name="password"
              required
              autoComplete="current-password"
              placeholder="••••••••"
              className="form-input"
              onChange={handleChange}
            />
          </div>

          <button
            id="login-submit"
            type="submit"
            className="btn-primary"
            disabled={loading}
            style={{ marginTop: '8px' }}
          >
            {loading ? 'Authenticating…' : 'Sign In →'}
          </button>
        </form>

        {/* Footer */}
        <p className="auth-footer">
          Don't have an account?{' '}
          <Link to="/register">Create one</Link>
        </p>

      </div>
    </div>
  );
}