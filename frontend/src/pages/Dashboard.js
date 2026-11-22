import React, { useEffect, useState } from 'react';
import api from '../api';
import { useAuth } from '../context/AuthContext';
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell, Legend
} from 'recharts';

const COLORS = ['#2563eb', '#16a34a', '#d97706', '#dc2626', '#7c3aed', '#0891b2'];

function StatCard({ label, value, sub, color }) {
  return (
    <div className="stat-card">
      <div className="label">{label}</div>
      <div className="value" style={color ? { color } : {}}>{value}</div>
      {sub && <div className="sub">{sub}</div>}
    </div>
  );
}

export default function Dashboard() {
  const { user } = useAuth();
  const [stats, setStats] = useState(null);
  const [heatmap, setHeatmap] = useState([]);
  const [contractors, setContractors] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      api.get('/analytics/city'),
      api.get('/analytics/ward-heatmap'),
      api.get('/analytics/contractors'),
    ]).then(([s, h, c]) => {
      setStats(s.data);
      setHeatmap(h.data);
      setContractors(c.data);
    }).finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="spinner" />;

  const riskData = heatmap.map(w => ({ name: w.ward_name, risk: w.flood_risk_score, complaints: w.open_complaints }));
  const categoryData = [
    { name: 'Garbage', value: 40 },
    { name: 'C&D Waste', value: 25 },
    { name: 'Waterlogging', value: 20 },
    { name: 'Drain Blockage', value: 10 },
    { name: 'Groundwater', value: 5 },
  ];

  return (
    <div>
      <div className="stat-grid">
        <StatCard label="Total Complaints" value={stats.total_complaints} sub="All time" />
        <StatCard label="Open Issues" value={stats.open_complaints} sub="Needs attention" color="#dc2626" />
        <StatCard label="Resolved Today" value={stats.resolved_today} sub="Last 24 hrs" color="#16a34a" />
        <StatCard label="Avg Resolution" value={`${stats.avg_resolution_hours}h`} sub="Mean time to close" />
        <StatCard label="High Risk Wards" value={stats.high_risk_wards} sub="Flood risk ≥ 7.0" color="#d97706" />
        <StatCard label="Top Issue" value={stats.top_category.replace(/_/g, ' ')} sub="Most reported" />
      </div>

      <div className="grid-2 mb-4">
        <div className="card">
          <div className="card-header"><span className="card-title">Ward Risk & Open Complaints</span></div>
          <ResponsiveContainer width="100%" height={240}>
            <BarChart data={riskData} margin={{ top: 0, right: 10, left: -20, bottom: 0 }}>
              <XAxis dataKey="name" tick={{ fontSize: 11 }} />
              <YAxis tick={{ fontSize: 11 }} />
              <Tooltip />
              <Bar dataKey="complaints" name="Open" fill="#2563eb" radius={[4,4,0,0]} />
              <Bar dataKey="risk" name="Flood Risk" fill="#dc2626" radius={[4,4,0,0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>

        <div className="card">
          <div className="card-header"><span className="card-title">Issue Category Breakdown</span></div>
          <ResponsiveContainer width="100%" height={240}>
            <PieChart>
              <Pie data={categoryData} cx="50%" cy="50%" outerRadius={80} dataKey="value" label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`} labelLine={false}>
                {categoryData.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
              </Pie>
              <Tooltip />
            </PieChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div className="card">
        <div className="card-header"><span className="card-title">Contractor Compliance Leaderboard</span></div>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>#</th><th>Contractor</th><th>Assigned</th><th>Resolved</th>
                <th>Resolution Rate</th><th>Compliance Score</th>
              </tr>
            </thead>
            <tbody>
              {contractors.map((c, i) => (
                <tr key={c.id}>
                  <td>{i + 1}</td>
                  <td><strong>{c.name}</strong></td>
                  <td>{c.total_assigned}</td>
                  <td>{c.total_resolved}</td>
                  <td>{c.resolution_rate}%</td>
                  <td>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                      <div style={{ flex: 1, background: 'var(--border)', borderRadius: 4, height: 8 }}>
                        <div style={{ width: `${c.compliance_score}%`, background: c.compliance_score >= 80 ? 'var(--success)' : c.compliance_score >= 60 ? 'var(--warning)' : 'var(--danger)', height: 8, borderRadius: 4 }} />
                      </div>
                      <span style={{ fontWeight: 600, fontSize: 13 }}>{c.compliance_score}</span>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
