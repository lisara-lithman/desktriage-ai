import React from 'react';
import { Routes, Route, Link } from 'react-router-dom';
import Login from './pages/Login';
import Register from './pages/Register';
import EmployeeDashboard from './pages/EmployeeDashboard';
import AdminDashboard from './pages/AdminDashboard';
import './index.css';

function App() {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', minHeight: '100vh' }}>
      {/* ── Global Navigation Bar ── */}
      <nav className="navbar">
        <Link to="/" className="navbar-brand">
          <div className="brand-icon">🏢</div>
          DeskTriage AI
        </Link>

        <div className="navbar-links">
          <Link to="/login"    className="nav-link">Login</Link>
          <Link to="/register" className="nav-link nav-link-primary">Register</Link>
        </div>
      </nav>

      {/* ── Route Viewport ── */}
      <Routes>
        <Route path="/"                  element={<Login />} />
        <Route path="/login"             element={<Login />} />
        <Route path="/register"          element={<Register />} />
        <Route path="/employee-dashboard" element={<EmployeeDashboard />} />
        <Route path="/admin-dashboard"   element={<AdminDashboard />} />
      </Routes>
    </div>
  );
}

export default App;