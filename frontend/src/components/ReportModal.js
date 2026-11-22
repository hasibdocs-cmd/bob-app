import React, { useState } from 'react';
import api from '../api';
import toast from 'react-hot-toast';

const CHANNELS = [
  { value: 'web', label: '🌐 Web (this form)' },
  { value: 'whatsapp', label: '💬 WhatsApp' },
  { value: 'telegram', label: '✈️ Telegram' },
  { value: 'sms', label: '📱 SMS' },
  { value: 'email', label: '📧 Email' },
];

const CATEGORIES = [
  { value: 'garbage_black_spot', label: '🗑️ Garbage / Black Spot' },
  { value: 'cd_waste', label: '🧱 Construction & Demolition Waste' },
  { value: 'waterlogging', label: '🌊 Waterlogging / Flooding' },
  { value: 'drain_blockage', label: '🚰 Drain Blockage' },
  { value: 'groundwater', label: '💧 Groundwater / Water Shortage' },
  { value: 'other', label: '📋 Other' },
];

export default function ReportModal({ onClose, onCreated }) {
  const [form, setForm] = useState({
    title: '', description: '', category: 'garbage_black_spot',
    address: '', latitude: '', longitude: '', image_url: '',
    channel: 'web',
  });
  const [loading, setLoading] = useState(false);

  const set = k => e => setForm(f => ({ ...f, [k]: e.target.value }));

  const getLocation = () => {
    navigator.geolocation?.getCurrentPosition(pos => {
      setForm(f => ({ ...f, latitude: pos.coords.latitude, longitude: pos.coords.longitude }));
      toast.success('Location captured');
    }, () => toast.error('Location unavailable'));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      const payload = {
        ...form,
        latitude: form.latitude ? parseFloat(form.latitude) : null,
        longitude: form.longitude ? parseFloat(form.longitude) : null,
      };
      const res = await api.post('/complaints/', payload);
      toast.success(`🎉 Ticket ${res.data.ticket_id} filed! AI Priority: ${res.data.priority}`);
      onCreated(res.data);
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Submission failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="modal-overlay" onClick={e => e.target === e.currentTarget && onClose()}>
      <div className="modal">
        <div className="modal-header">
          <span className="modal-title">📢 Report a Civic Issue</span>
          <button className="modal-close" onClick={onClose}>✕</button>
        </div>

        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label className="form-label">Issue Title *</label>
            <input className="form-control" placeholder="e.g. Garbage dump near bus stop on 100ft road"
              value={form.title} onChange={set('title')} required />
          </div>

          <div className="form-group">
            <label className="form-label">Category</label>
            <select className="form-control" value={form.category} onChange={set('category')}>
              {CATEGORIES.map(c => <option key={c.value} value={c.value}>{c.label}</option>)}
            </select>
          </div>

          <div className="form-group">
            <label className="form-label">Description</label>
            <textarea className="form-control" placeholder="Describe the issue in detail…"
              value={form.description} onChange={set('description')} />
          </div>

          <div className="form-group">
            <label className="form-label">Address / Landmark</label>
            <input className="form-control" placeholder="e.g. Near Jayanagar 4th Block Park"
              value={form.address} onChange={set('address')} />
          </div>

          <div className="grid-2">
            <div className="form-group">
              <label className="form-label">Latitude</label>
              <input className="form-control" placeholder="12.9716" value={form.latitude} onChange={set('latitude')} />
            </div>
            <div className="form-group">
              <label className="form-label">Longitude</label>
              <input className="form-control" placeholder="77.5946" value={form.longitude} onChange={set('longitude')} />
            </div>
          </div>

          <button type="button" className="btn btn-secondary btn-sm mb-4" onClick={getLocation}>
            📍 Use My Location
          </button>

          <div className="form-group">
            <label className="form-label">Image URL (optional)</label>
            <input className="form-control" placeholder="https://…" value={form.image_url} onChange={set('image_url')} />
          </div>

          <div className="form-group">
            <label className="form-label">📡 Reporting Channel</label>
            <select className="form-control" value={form.channel} onChange={set('channel')}>
              {CHANNELS.map(c => <option key={c.value} value={c.value}>{c.label}</option>)}
            </select>
            {form.channel !== 'web' && (
              <p style={{ fontSize: 12, color: 'var(--muted)', marginTop: 4 }}>
                You can also report directly via {form.channel === 'whatsapp' ? 'WhatsApp' : form.channel === 'telegram' ? 'Telegram Bot' : form.channel === 'sms' ? 'SMS' : 'Email'} — NagaraAI will auto-classify your message.
              </p>
            )}
          </div>

          <div style={{ background: 'var(--accent-light)', borderRadius: 8, padding: 12, marginBottom: 16, fontSize: 13, color: 'var(--accent)' }}>
            🤖 <strong>IBM watsonx.ai</strong> will automatically classify this issue, assign priority, and set SLA.
          </div>

          <div style={{ display: 'flex', gap: 10, justifyContent: 'flex-end' }}>
            <button type="button" className="btn btn-secondary" onClick={onClose}>Cancel</button>
            <button type="submit" className="btn btn-primary" disabled={loading}>
              {loading ? 'Submitting…' : 'Submit & Let AI Classify'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
