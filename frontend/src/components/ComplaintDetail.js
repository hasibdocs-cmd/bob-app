import React, { useState } from 'react';
import { useAuth } from '../context/AuthContext';
import api from '../api';
import toast from 'react-hot-toast';

const NOTIFY_CHANNELS = [
  { value: 'whatsapp', label: '💬 WhatsApp' },
  { value: 'sms', label: '📱 SMS' },
  { value: 'telegram', label: '✈️ Telegram' },
  { value: 'email', label: '📧 Email' },
];

const STATUSES = ['open', 'assigned', 'in_progress', 'resolved', 'escalated', 'closed'];
const STATUS_COLORS = {
  open: 'badge-open', assigned: 'badge-assigned', in_progress: 'badge-in_progress',
  resolved: 'badge-resolved', escalated: 'badge-escalated', closed: 'badge-closed',
};

export default function ComplaintDetail({ complaint: initial, onClose, onUpdated }) {
  const { user } = useAuth();
  const [complaint, setComplaint] = useState(initial);
  const [updating, setUpdating] = useState(false);
  const [rating, setRating] = useState(complaint.citizen_rating || 0);
  const [notifyPanel, setNotifyPanel] = useState(false);
  const [notifyForm, setNotifyForm] = useState({ channel: 'whatsapp', recipient: '' });
  const [notifying, setNotifying] = useState(false);

  const updateStatus = async (status, note = '') => {
    setUpdating(true);
    try {
      const res = await api.patch(`/complaints/${complaint.id}`, { status, note });
      setComplaint(res.data);
      toast.success(`Status updated to "${status}"`);
      onUpdated();
    } catch { toast.error('Update failed'); }
    finally { setUpdating(false); }
  };

  const submitRating = async (r) => {
    try {
      await api.post(`/complaints/${complaint.id}/rate`, { rating: r });
      setRating(r);
      toast.success('Rating submitted!');
    } catch { toast.error('Rating failed'); }
  };

  const sendNotification = async () => {
    if (!notifyForm.recipient) { toast.error('Enter a recipient'); return; }
    setNotifying(true);
    try {
      await api.post('/channels/dispatch', {
        complaint_id: complaint.id,
        channel: notifyForm.channel,
        recipient: notifyForm.recipient,
      });
      toast.success(`Notification sent via ${notifyForm.channel}`);
      setNotifyPanel(false);
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Send failed');
    } finally { setNotifying(false); }
  };

  const canUpdateStatus = ['field_officer', 'ward_officer', 'commissioner'].includes(user.role);

  return (
    <div className="modal-overlay" onClick={e => e.target === e.currentTarget && onClose()}>
      <div className="modal" style={{ maxWidth: 640 }}>
        <div className="modal-header">
          <div>
            <span className="modal-title">{complaint.title}</span>
            <div style={{ fontSize: 12, color: 'var(--muted)', marginTop: 2 }}>{complaint.ticket_id}</div>
          </div>
          <button className="modal-close" onClick={onClose}>✕</button>
        </div>

        {/* AI Summary */}
        {complaint.ai_summary && (
          <div style={{ background: 'var(--accent-light)', borderRadius: 8, padding: 12, marginBottom: 16, fontSize: 13 }}>
            <span className="ai-tag" style={{ marginBottom: 4, display: 'inline-block' }}>🤖 IBM watsonx.ai Analysis</span>
            <p style={{ marginTop: 6, color: 'var(--text)' }}>{complaint.ai_summary}</p>
            <p style={{ marginTop: 4, color: 'var(--muted)' }}>
              Confidence: {Math.round((complaint.ai_confidence || 0) * 100)}% •
              Category: {complaint.ai_classification?.replace(/_/g, ' ')}
            </p>
          </div>
        )}

        <div className="grid-2 mb-4">
          <div>
            <div className="form-label">Status</div>
            <span className={`badge ${STATUS_COLORS[complaint.status]}`}>{complaint.status.replace('_', ' ')}</span>
          </div>
          <div>
            <div className="form-label">Priority</div>
            <span className={`badge badge-${complaint.priority}`}>{complaint.priority}</span>
          </div>
          <div>
            <div className="form-label">Category</div>
            <span>{complaint.category?.replace(/_/g, ' ')}</span>
          </div>
          <div>
            <div className="form-label">Filed</div>
            <span>{new Date(complaint.created_at).toLocaleString()}</span>
          </div>
          {complaint.address && (
            <div style={{ gridColumn: '1/-1' }}>
              <div className="form-label">Location</div>
              <span>📍 {complaint.address}</span>
            </div>
          )}
          {complaint.sla_deadline && (
            <div>
              <div className="form-label">SLA Deadline</div>
              <span style={{ color: new Date(complaint.sla_deadline) < new Date() ? 'var(--danger)' : 'var(--text)' }}>
                ⏰ {new Date(complaint.sla_deadline).toLocaleString()}
              </span>
            </div>
          )}
          {complaint.resolved_at && (
            <div>
              <div className="form-label">Resolved At</div>
              <span style={{ color: 'var(--success)' }}>✅ {new Date(complaint.resolved_at).toLocaleString()}</span>
            </div>
          )}
        </div>

        {complaint.image_url && (
          <div className="mb-4">
            <img src={complaint.image_url} alt="Issue" style={{ width: '100%', borderRadius: 8, border: '1px solid var(--border)', maxHeight: 200, objectFit: 'cover' }} />
          </div>
        )}

        {complaint.description && (
          <div className="mb-4">
            <div className="form-label">Description</div>
            <p style={{ fontSize: 14 }}>{complaint.description}</p>
          </div>
        )}

        {/* Timeline */}
        {complaint.updates?.length > 0 && (
          <div className="mb-4">
            <div className="form-label" style={{ marginBottom: 8 }}>Activity Timeline</div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              {complaint.updates.map(u => (
                <div key={u.id} style={{ display: 'flex', gap: 10, fontSize: 13 }}>
                  <div style={{ width: 8, height: 8, borderRadius: '50%', background: 'var(--accent)', marginTop: 5, flexShrink: 0 }} />
                  <div>
                    <span className={`badge ${STATUS_COLORS[u.status]}`}>{u.status.replace('_', ' ')}</span>
                    {u.note && <span style={{ marginLeft: 8, color: 'var(--muted)' }}>{u.note}</span>}
                    <div style={{ color: 'var(--muted)', fontSize: 11, marginTop: 2 }}>{new Date(u.created_at).toLocaleString()}</div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Actions for officers */}
        {canUpdateStatus && complaint.status !== 'resolved' && complaint.status !== 'closed' && (
          <div className="mb-4">
            <div className="form-label" style={{ marginBottom: 8 }}>Update Status</div>
            <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
              {complaint.status === 'open' && (
                <button className="btn btn-primary btn-sm" disabled={updating} onClick={() => updateStatus('in_progress', 'Field team dispatched')}>
                  🔧 Mark In Progress
                </button>
              )}
              {['assigned', 'in_progress'].includes(complaint.status) && (
                <button className="btn btn-success btn-sm" disabled={updating} onClick={() => updateStatus('resolved', 'Issue resolved by field team')}>
                  ✅ Mark Resolved
                </button>
              )}
              <button className="btn btn-danger btn-sm" disabled={updating} onClick={() => updateStatus('escalated', 'Escalated due to SLA breach')}>
                ⚡ Escalate
              </button>
            </div>
          </div>
        )}

        {/* Share / Notify panel */}
        {canUpdateStatus && (
          <div className="mb-4">
            <button className="btn btn-secondary btn-sm" onClick={() => setNotifyPanel(v => !v)}>
              📣 {notifyPanel ? 'Cancel' : 'Send Notification'}
            </button>
            {notifyPanel && (
              <div style={{ marginTop: 10, padding: 12, border: '1px solid var(--border)', borderRadius: 8, background: 'var(--surface)' }}>
                <div className="form-label" style={{ marginBottom: 6 }}>Notify citizen via:</div>
                <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 8 }}>
                  {NOTIFY_CHANNELS.map(c => (
                    <button
                      key={c.value}
                      className={`btn btn-sm ${notifyForm.channel === c.value ? 'btn-primary' : 'btn-secondary'}`}
                      onClick={() => setNotifyForm(f => ({ ...f, channel: c.value }))}
                    >{c.label}</button>
                  ))}
                </div>
                <input
                  className="form-control"
                  placeholder={
                    notifyForm.channel === 'email' ? 'citizen@example.com' :
                    notifyForm.channel === 'telegram' ? 'Telegram chat_id' :
                    '+91XXXXXXXXXX'
                  }
                  value={notifyForm.recipient}
                  onChange={e => setNotifyForm(f => ({ ...f, recipient: e.target.value }))}
                  style={{ marginBottom: 8 }}
                />
                <button className="btn btn-primary btn-sm" disabled={notifying} onClick={sendNotification}>
                  {notifying ? 'Sending…' : `Send via ${notifyForm.channel}`}
                </button>
              </div>
            )}
          </div>
        )}

        {/* Citizen rating */}
        {user.role === 'citizen' && complaint.status === 'resolved' && (
          <div>
            <div className="form-label" style={{ marginBottom: 8 }}>Rate Resolution</div>
            <div style={{ display: 'flex', gap: 6 }}>
              {[1, 2, 3, 4, 5].map(r => (
                <button key={r} style={{
                  fontSize: 24, background: 'none', border: 'none', cursor: 'pointer',
                  opacity: r <= (rating || 0) ? 1 : 0.3
                }} onClick={() => submitRating(r)}>⭐</button>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
