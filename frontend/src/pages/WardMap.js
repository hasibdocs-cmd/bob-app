import React, { useEffect, useState } from 'react';
import api from '../api';
import { MapContainer, TileLayer, CircleMarker, Popup } from 'react-leaflet';

export default function WardMap() {
  const [wards, setWards] = useState([]);
  const [heatmap, setHeatmap] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.get('/analytics/ward-heatmap')
      .then(r => setHeatmap(r.data))
      .finally(() => setLoading(false));
  }, []);

  // Approximate coordinates for Bengaluru wards
  const WARD_COORDS = {
    'Jayanagar': [12.9308, 77.5838],
    'Malleswaram': [13.0035, 77.5673],
    'Whitefield': [12.9698, 77.7500],
    'Koramangala': [12.9352, 77.6245],
    'Hebbal': [13.0450, 77.5942],
    'BTM Layout': [12.9166, 77.6101],
    'Yelahanka': [13.1005, 77.5963],
    'Marathahalli': [12.9591, 77.6974],
  };

  const getRiskColor = (score) => {
    if (score >= 7) return '#dc2626';
    if (score >= 4) return '#d97706';
    return '#16a34a';
  };

  if (loading) return <div className="spinner" />;

  return (
    <div>
      <div className="card mb-4">
        <div className="card-header">
          <span className="card-title">🗺️ Bengaluru Ward Risk Map</span>
          <div style={{ display: 'flex', gap: 16, fontSize: 12 }}>
            <span style={{ color: '#16a34a' }}>● Low Risk</span>
            <span style={{ color: '#d97706' }}>● Medium Risk</span>
            <span style={{ color: '#dc2626' }}>● High Risk</span>
          </div>
        </div>
        <div className="map-container">
          <MapContainer center={[12.9716, 77.5946]} zoom={11} style={{ height: '100%', width: '100%' }}>
            <TileLayer
              attribution='&copy; OpenStreetMap contributors'
              url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
            />
            {heatmap.map(ward => {
              const coords = WARD_COORDS[ward.ward_name];
              if (!coords) return null;
              return (
                <CircleMarker
                  key={ward.ward_id}
                  center={coords}
                  radius={Math.max(12, ward.open_complaints * 2)}
                  pathOptions={{ color: getRiskColor(ward.flood_risk_score), fillColor: getRiskColor(ward.flood_risk_score), fillOpacity: 0.5 }}
                >
                  <Popup>
                    <strong>{ward.ward_name}</strong><br />
                    Open Complaints: {ward.open_complaints}<br />
                    Flood Risk: {ward.flood_risk_score}/10<br />
                    Cleanliness: {ward.cleanliness_score}/100
                  </Popup>
                </CircleMarker>
              );
            })}
          </MapContainer>
        </div>
      </div>

      <div className="card">
        <div className="card-header"><span className="card-title">Ward Summary Table</span></div>
        <div className="table-wrap">
          <table>
            <thead>
              <tr><th>Ward</th><th>Zone</th><th>Open Issues</th><th>Flood Risk</th><th>Cleanliness Score</th></tr>
            </thead>
            <tbody>
              {heatmap.sort((a, b) => b.flood_risk_score - a.flood_risk_score).map(w => (
                <tr key={w.ward_id}>
                  <td><strong>{w.ward_name}</strong></td>
                  <td>{w.zone}</td>
                  <td><span className="badge badge-open">{w.open_complaints}</span></td>
                  <td>
                    <span className={w.flood_risk_score >= 7 ? 'risk-high' : w.flood_risk_score >= 4 ? 'risk-medium' : 'risk-low'} style={{ fontWeight: 600 }}>
                      {w.flood_risk_score}/10
                    </span>
                  </td>
                  <td>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                      <div style={{ flex: 1, background: 'var(--border)', borderRadius: 4, height: 8 }}>
                        <div style={{ width: `${w.cleanliness_score}%`, background: 'var(--success)', height: 8, borderRadius: 4 }} />
                      </div>
                      <span style={{ fontWeight: 600, fontSize: 13 }}>{w.cleanliness_score}</span>
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
