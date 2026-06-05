import React, { useState } from 'react';
import axios from 'axios';
import { useNavigate, Link } from 'react-router-dom';

export default function Register() {
  const navigate = useNavigate();
  const [formData, setFormData] = useState({
    first_name: '', last_name: '', username: '',
    email: '', password: '', confirm_password: '', phone_number: '',
  });
  const [error,   setError]   = useState('');
  const [success, setSuccess] = useState('');
  const [loading, setLoading] = useState(false);

  const handleChange = (e) =>
    setFormData({ ...formData, [e.target.name]: e.target.value });

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setSuccess('');

    if (formData.password !== formData.confirm_password) {
      setError('Passwords do not match.');
      return;
    }

    setLoading(true);
    try {
      const payload = {
        first_name:       formData.first_name,
        last_name:        formData.last_name,
        username:         formData.username,
        email:            formData.email,
        password:         formData.password,
        confirm_password: formData.confirm_password,
        phone_number:     formData.phone_number || null,
      };

      const response = await axios.post('http://127.0.0.1:8000/api/auth/register', payload);
      setSuccess(response.data.message + ' — Redirecting to login…');
      setTimeout(() => navigate('/login'), 2000);
    } catch (err) {
      setError(err.response?.data?.detail || 'Registration failed. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="page-container">
      <div className="auth-card auth-card-wide" id="register-card">

        {/* Logo + Heading */}
        <div className="auth-logo-block">
          <div className="auth-logo-icon">✨</div>
          <h2 className="auth-title">Create your account</h2>
          <p className="auth-subtitle">Join the DeskTriage AI platform</p>
        </div>

        {/* Alerts */}
        {error   && <div className="alert alert-error"   role="alert" id="register-error"><span>⚠️</span><span>{error}</span></div>}
        {success && <div className="alert alert-success" role="status" id="register-success"><span>✅</span><span>{success}</span></div>}

        {/* Form */}
        <form
          onSubmit={handleSubmit}
          className="form-stack"
          style={{ marginTop: (error || success) ? '1rem' : 0 }}
          id="register-form"
        >
          {/* Row 1 — Names */}
          <div className="form-grid-2">
            <div className="form-group">
              <label className="form-label" htmlFor="reg-first-name">First Name</label>
              <input
                id="reg-first-name"
                type="text"
                name="first_name"
                required
                placeholder="Jane"
                className="form-input"
                onChange={handleChange}
              />
            </div>
            <div className="form-group">
              <label className="form-label" htmlFor="reg-last-name">Last Name</label>
              <input
                id="reg-last-name"
                type="text"
                name="last_name"
                required
                placeholder="Doe"
                className="form-input"
                onChange={handleChange}
              />
            </div>
          </div>

          {/* Username */}
          <div className="form-group">
            <label className="form-label" htmlFor="reg-username">Username</label>
            <input
              id="reg-username"
              type="text"
              name="username"
              required
              placeholder="janedoe_ops"
              className="form-input"
              onChange={handleChange}
            />
          </div>

          {/* Email */}
          <div className="form-group">
            <label className="form-label" htmlFor="reg-email">Corporate Email</label>
            <input
              id="reg-email"
              type="email"
              name="email"
              required
              placeholder="jane@company.com"
              autoComplete="email"
              className="form-input"
              onChange={handleChange}
            />
          </div>

          {/* Phone */}
          <div className="form-group">
            <label className="form-label" htmlFor="reg-phone">
              Phone Number <span style={{ color: 'var(--clr-muted)', fontWeight: 400 }}>(optional)</span>
            </label>
            <input
              id="reg-phone"
              type="tel"
              name="phone_number"
              placeholder="+1 555 000 0000"
              className="form-input"
              onChange={handleChange}
            />
          </div>

          {/* Passwords */}
          <div className="form-grid-2">
            <div className="form-group">
              <label className="form-label" htmlFor="reg-password">Password</label>
              <input
                id="reg-password"
                type="password"
                name="password"
                required
                placeholder="Min 8 characters"
                autoComplete="new-password"
                className="form-input"
                onChange={handleChange}
              />
            </div>
            <div className="form-group">
              <label className="form-label" htmlFor="reg-confirm">Confirm Password</label>
              <input
                id="reg-confirm"
                type="password"
                name="confirm_password"
                required
                placeholder="••••••••"
                autoComplete="new-password"
                className="form-input"
                onChange={handleChange}
              />
            </div>
          </div>

          <button
            id="register-submit"
            type="submit"
            className="btn-primary"
            disabled={loading}
            style={{ marginTop: '8px' }}
          >
            {loading ? 'Creating Account…' : 'Create Account →'}
          </button>
        </form>

        {/* Footer */}
        <p className="auth-footer">
          Already have an account?{' '}
          <Link to="/login">Sign in</Link>
        </p>

      </div>
    </div>
  );
}