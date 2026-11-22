import React from 'react';
import { Routes, Route, Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import Sidebar from './Sidebar';
import Dashboard from '../pages/Dashboard';
import Complaints from '../pages/Complaints';
import WardMap from '../pages/WardMap';

const PAGE_TITLES = {
  '/': 'Dashboard',
  '/complaints': 'Issues & Complaints',
  '/map': 'Ward Map',
};

export default function AppShell() {
  const { user } = useAuth();
  const location = useLocation();
  const title = PAGE_TITLES[location.pathname] || 'NagaraAI';

  if (!user) return <Navigate to="/login" replace />;

  return (
    <div className="app-shell">
      <Sidebar />
      <div className="main-content">
        <div className="topbar">
          <span className="topbar-title">{title}</span>
          <div style={{ fontSize: 12, color: 'var(--muted)' }}>
            🤖 Powered by IBM watsonx.ai
          </div>
        </div>
        <div className="page-body">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/complaints" element={<Complaints />} />
            <Route path="/map" element={<WardMap />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </div>
      </div>
    </div>
  );
}
