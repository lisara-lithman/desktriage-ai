import React from 'react';
import { Routes, Route, Link, useNavigate, useLocation } from 'react-router-dom';
import Login            from './pages/Login';
import Register         from './pages/Register';
import EmployeeDashboard from './pages/EmployeeDashboard';
import AdminDashboard   from './pages/AdminDashboard';
import './index.css';

function Navbar() {
  const navigate  = useNavigate();
  const location  = useLocation();
  const token     = localStorage.getItem('token');
  const role      = localStorage.getItem('role');
  const username  = localStorage.getItem('username');

  const isLoggedIn  = !!token;
  const isAuthPage  = location.pathname === '/login' || location.pathname === '/register' || location.pathname === '/';

  const handleLogout = () => {
    localStorage.clear();
    navigate('/login');
  };

  return (
    <nav className="navbar">
      <Link to={isLoggedIn ? (role === 'user' ? '/employee-dashboard' : '/admin-dashboard') : '/login'} className="navbar-brand">
        <div className="brand-icon">🏢</div>
        DeskTriage AI
      </Link>

      <div className="navbar-links">
        {isLoggedIn ? (
          <>
            <span className="nav-user-label">👤 {username}</span>
            <button className="nav-link nav-link-logout" onClick={handleLogout} id="nav-logout-btn">
              Sign Out
            </button>
          </>
        ) : (
          <>
            <Link to="/login"    className="nav-link">Login</Link>
            <Link to="/register" className="nav-link nav-link-primary">Register</Link>
          </>
        )}
      </div>
    </nav>
  );
}

function App() {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', minHeight: '100vh' }}>
      <Navbar />
      <Routes>
        <Route path="/"                   element={<Login />} />
        <Route path="/login"              element={<Login />} />
        <Route path="/register"           element={<Register />} />
        <Route path="/employee-dashboard" element={<EmployeeDashboard />} />
        <Route path="/admin-dashboard"    element={<AdminDashboard />} />
      </Routes>
    </div>
  );
}

export default App;