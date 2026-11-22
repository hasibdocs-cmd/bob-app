import React from 'react';
import { NavLink, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

const NAV_ITEMS = {
  citizen: [
    { path: '/', label: 'Dashboard', icon: '📊' },
    { path: '/complaints', label: 'My Reports', icon: '📋' },
    { path: '/map', label: 'Ward Map', icon: '🗺️' },
  ],
  field_officer: [
    { path: '/', label: 'Dashboard', icon: '📊' },
    { path: '/complaints', label: 'My Tasks', icon: '🔧' },
    { path: '/map', label: 'Ward Map', icon: '🗺️' },
  ],
  ward_officer: [
    { path: '/', label: 'Dashboard', icon: '📊' },
    { path: '/complaints', label: 'Ward Issues', icon: '📋' },
    { path: '/map', label: 'Ward Map', icon: '🗺️' },
  ],
  commissioner: [
    { path: '/', label: 'City Dashboard', icon: '📊' },
    { path: '/complaints', label: 'All Issues', icon: '📋' },
    { path: '/map', label: 'City Map', icon: '🗺️' },
  ],
};

const ROLE_LABELS = {
  citizen: 'Citizen', field_officer: 'Field Officer',
  ward_officer: 'Ward Officer', commissioner: 'Commissioner',
};

export default function Sidebar() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const items = NAV_ITEMS[user?.role] || NAV_ITEMS.citizen;

  const handleLogout = () => { logout(); navigate('/login'); };

  return (
    <div className="sidebar">
      <div className="sidebar-logo">
        <h1>🏙️ NagaraAI</h1>
        <span>Bengaluru Civic Platform</span>
      </div>

      <nav className="sidebar-nav">
        {items.map(item => (
          <NavLink key={item.path} to={item.path} end={item.path === '/'}>
            {({ isActive }) => (
              <div className={`nav-item ${isActive ? 'active' : ''}`}>
                <span style={{ fontSize: 16 }}>{item.icon}</span>
                {item.label}
              </div>
            )}
          </NavLink>
        ))}
      </nav>

      <div className="sidebar-footer">
        <div className="user-chip">
          <div className="user-avatar">{user?.name?.[0]?.toUpperCase()}</div>
          <div className="user-info" style={{ flex: 1, minWidth: 0 }}>
            <div className="name" style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{user?.name}</div>
            <div className="role">{ROLE_LABELS[user?.role]}</div>
          </div>
          <button onClick={handleLogout} style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--muted)', fontSize: 16 }} title="Logout">↩</button>
        </div>
      </div>
    </div>
  );
}
