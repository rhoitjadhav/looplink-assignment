import { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { api } from '../api';
import StatusBadge from '../components/StatusBadge';

function fmtDate(dt) {
  if (!dt) return '—';
  return new Date(dt).toISOString().replace('T', ' ').slice(0, 16) + ' UTC';
}

export default function CampaignList() {
  const [campaigns, setCampaigns] = useState(null);
  const [error, setError] = useState(null);
  const navigate = useNavigate();

  const load = () => {
    setError(null);
    setCampaigns(null);
    api.listCampaigns()
      .then(setCampaigns)
      .catch(e => setError(e.message));
  };

  useEffect(load, []);

  return (
    <div className="container">
      <div className="page-header">
        <h1>Campaigns</h1>
        <Link to="/admin/new" className="btn">New campaign</Link>
      </div>

      {campaigns === null && !error && <p>Loading campaigns…</p>}

      {error && (
        <div className="error-banner">
          {error}
          <button className="btn btn-secondary" onClick={load}>Retry</button>
        </div>
      )}

      {campaigns && campaigns.length === 0 && (
        <div style={{ textAlign: 'center', padding: '3rem 0' }}>
          <p style={{ color: '#6b7280', marginBottom: '1.25rem' }}>
            No campaigns yet. Create your first campaign to get started.
          </p>
          <Link to="/admin/new" className="btn">New campaign</Link>
        </div>
      )}

      {campaigns && campaigns.length > 0 && (
        <table>
          <thead>
            <tr>
              <th>Name</th>
              <th>Status</th>
              <th>Window</th>
              <th>Offers</th>
              <th>Enrolled</th>
            </tr>
          </thead>
          <tbody>
            {campaigns.map(c => (
              <tr key={c.id} onClick={() => navigate(`/admin/${c.id}`)}>
                <td>
                  <Link to={`/admin/${c.id}`} onClick={e => e.stopPropagation()}>
                    {c.name}
                  </Link>
                </td>
                <td><StatusBadge status={c.status} /></td>
                <td style={{ fontSize: '0.85rem', color: '#374151' }}>
                  {fmtDate(c.starts_at)} – {fmtDate(c.ends_at)}
                </td>
                <td>{c.offers.length}</td>
                <td>{c.enrollment_count}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
