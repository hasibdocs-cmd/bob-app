import React, { useEffect, useState, useCallback } from 'react';
import api from '../api';
import { useAuth } from '../context/AuthContext';
import toast from 'react-hot-toast';
import ReportModal from '../components/ReportModal';
import ComplaintDetail from '../components/ComplaintDetail';

const STATUS_COLORS = {
  open: 'badge-open', assigned: 'badge-assigned', in_progress: 'badge-in_progress',
  resolved: 'badge-resolved', escalated: 'badge-escalated', closed: 'badge-closed',
};
const PRIORITY_COLORS = {
  critical: 'badge-critical', high: 'badge-high', medium: 'badge-medium', low: 'badge-low',
};

function SLABar({ deadline }) {
  if (!deadline) return null;
  const now = Date.now();
  const end = new Date(deadline).getTime();
  const start = end - 72 * 3600 * 1000;
  const pct = Math.max(0, Math.min(100, ((now - start) / (end - start)) * 100));
  const color = pct > 80 ? 'var(--danger)' : pct > 50 ? 'var(--warning)' : 'var(--success)';
  return (
    <div className="sla-bar">
      <div className="sla-fill" style={{ width: `${pct}%`, background: color }} />
    </div>
  );
}

export default function Complaints() {
  const { user } = useAuth();
  const [complaints, setComplaints] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showReport, setShowReport] = useState(false);
  const [selected, setSelected] = useState(null);
  const [filters, setFilters] = useState({ status: '', category: '' });

  const fetchComplaints = useCallback(() => {
    setLoading(true);
    const params = {};
    if (filters.status) params.status = filters.status;
    if (filters.category) params.category = filters.category;
    api.get('/complaints/', { params })
      .then(r => setComplaints(r.data))
      .finally(() => setLoading(false));
  }, [filters]);

  useEffect(() => { fetchComplaints(); }, [fetchComplaints]);

  const handleCreated = () => { setShowReport(false); fetchComplaints(); };
  const handleUpdated = () => { setSelected(null); fetchComplaints(); };

  return (
    <div>
      <div className="flex-between mb-4">
        <div style={{ display: 'flex', gap: 10 }}>
          <select className="form-control" style={{ width: 160 }} value={filters.status}
            onChange={e => setFilters(f => ({ ...f, status: e.target.value }))}>
            <option value="">All Statuses</option>
            {['open','assigned','in_progress','resolved','escalated','closed'].map(s =>
              <option key={s} value={s}>{s.replace('_', ' ')}</option>
            )}
          </select>
          <select className="form-control" style={{ width: 180 }} value={filters.category}
            onChange={e => setFilters(f => ({ ...f, category: e.target.value }))}>
            <option value="">All Categories</option>
            {['garbage_black_spot','cd_waste','waterlogging','drain_blockage','groundwater','other'].map(c =>
              <option key={c} value={c}>{c.replace(/_/g, ' ')}</option>
            )}
          </select>
        </div>
        {user.role === 'citizen' && (
          <button className="btn btn-primary" onClick={() => setShowReport(true)}>
            + Report Issue
          </button>
        )}
      </div>

      {loading ? <div className="spinner" /> : complaints.length === 0 ? (
        <div className="empty-state">
          <div style={{ fontSize: 40 }}>📋</div>
          <p style={{ marginTop: 8 }}>No complaints found</p>
          {user.role === 'citizen' && <button className="btn btn-primary mt-2" onClick={() => setShowReport(true)}>Report your first issue</button>}
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          {complaints.map(c => (
            <div key={c.id} className="complaint-card" onClick={() => setSelected(c)}>
              <div className="complaint-card-header">
                <span className="ticket-id">{c.ticket_id}</span>
                <div style={{ display: 'flex', gap: 6 }}>
                  <span className={`badge ${PRIORITY_COLORS[c.priority]}`}>{c.priority}</span>
                  <span className={`badge ${STATUS_COLORS[c.status]}`}>{c.status.replace('_', ' ')}</span>
                </div>
              </div>
              <div className="complaint-title">{c.title}</div>
              <div className="complaint-meta">
                <span>📂 {c.category.replace(/_/g, ' ')}</span>
                {c.address && <span>📍 {c.address}</span>}
                <span>🕐 {new Date(c.created_at).toLocaleDateString()}</span>
                {c.ai_classification && (
                  <span className="ai-tag">🤖 AI: {c.ai_classification.replace(/_/g, ' ')} ({Math.round((c.ai_confidence || 0) * 100)}%)</span>
                )}
              </div>
              <SLABar deadline={c.sla_deadline} />
            </div>
          ))}
        </div>
      )}

      {showReport && <ReportModal onClose={() => setShowReport(false)} onCreated={handleCreated} />}
      {selected && <ComplaintDetail complaint={selected} onClose={() => setSelected(null)} onUpdated={handleUpdated} />}
    </div>
  );
}
