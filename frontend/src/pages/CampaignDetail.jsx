import { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { QRCodeSVG } from 'qrcode.react';
import { api } from '../api';
import StatusBadge from '../components/StatusBadge';

function fmtDate(dt) {
  if (!dt) return '—';
  return new Date(dt).toISOString().replace('T', ' ').slice(0, 16) + ' UTC';
}

function describeOffer(o) {
  const p = o.params;
  switch (o.type) {
    case 'PRODUCT_PERCENT_DISCOUNT': return `${p.percent}% off — ${p.applies_to}`;
    case 'CART_FIXED_DISCOUNT':      return `${p.amount_off} off, min basket ${p.min_basket}`;
    case 'STICKER_EARN':             return `${p.stickers} sticker(s) per ${p.per_amount} spent`;
    default: return o.type;
  }
}

const ACTION_LABELS = { schedule: 'Schedule', launch: 'Launch now', end: 'End campaign' };

export default function CampaignDetail() {
  const { id } = useParams();
  const [campaign, setCampaign] = useState(null);
  const [error, setError] = useState(null);
  const [transitioning, setTransitioning] = useState(false);
  const [actionBanner, setActionBanner] = useState(null);
  const [copied, setCopied] = useState(false);

  const load = () => {
    setError(null);
    api.getCampaign(id).then(setCampaign).catch(e => setError(e.message));
  };

  useEffect(load, [id]);

  const handleAction = async (action) => {
    if (action === 'end' && !window.confirm('End this campaign? This cannot be undone.')) return;
    setTransitioning(true);
    setActionBanner(null);
    try {
      const updated = await api.transition(id, action, campaign.version);
      setCampaign(updated);
    } catch (err) {
      if (err.code === 'version_conflict') {
        setActionBanner('This campaign changed elsewhere — reloading…');
      } else {
        setActionBanner(err.message || 'Transition failed.');
      }
      load();
    } finally {
      setTransitioning(false);
    }
  };

  const publicUrl = campaign
    ? `${window.location.origin}/c/${campaign.public_token}`
    : '';

  const handleCopy = () => {
    navigator.clipboard.writeText(publicUrl).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  };

  if (!campaign && !error) return <div className="container"><p>Loading…</p></div>;
  if (error) return (
    <div className="container">
      <div className="error-banner">{error}</div>
      <button className="btn btn-secondary" onClick={load}>Retry</button>
    </div>
  );

  const showActions = campaign.allowed_actions.length > 0 || campaign.launch_problems.length > 0;

  return (
    <div className="container">
      <div className="page-header">
        <div>
          <h1 style={{ marginBottom: 6 }}>{campaign.name}</h1>
          <StatusBadge status={campaign.status} />
        </div>
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          {campaign.status === 'draft' && (
            <Link to={`/admin/${id}/edit`} className="btn btn-secondary">Edit</Link>
          )}
          <Link to="/admin" className="btn btn-secondary">← Back</Link>
        </div>
      </div>

      {actionBanner && <div className="error-banner">{actionBanner}</div>}

      {campaign.description && <p>{campaign.description}</p>}

      <dl style={{ display: 'grid', gridTemplateColumns: 'max-content 1fr', gap: '6px 16px', margin: '1rem 0' }}>
        <dt style={{ fontWeight: 600 }}>Window</dt>
        <dd style={{ margin: 0 }}>{fmtDate(campaign.starts_at)} – {fmtDate(campaign.ends_at)}</dd>
        <dt style={{ fontWeight: 600 }}>Enrollments</dt>
        <dd style={{ margin: 0 }}>{campaign.enrollment_count}</dd>
      </dl>

      <h3>Offers</h3>
      {campaign.offers.length === 0
        ? <p style={{ color: '#6b7280' }}>No offers attached.</p>
        : (
          <ul style={{ paddingLeft: '1.25rem' }}>
            {campaign.offers.map(o => <li key={o.id}>{describeOffer(o)}</li>)}
          </ul>
        )
      }

      {showActions && (
        <div style={{ marginTop: '1.5rem' }}>
          <h3 style={{ marginBottom: 6 }}>Actions</h3>
          {campaign.launch_problems.length > 0 && (
            <ul className="hint-list">
              {campaign.launch_problems.map((p, i) => <li key={i}>{p}</li>)}
            </ul>
          )}
          <div className="actions">
            {campaign.allowed_actions.map(action => (
              <button
                key={action}
                className={`btn${action === 'end' ? ' btn-danger' : ''}`}
                disabled={transitioning}
                onClick={() => handleAction(action)}
              >
                {ACTION_LABELS[action]}
              </button>
            ))}
          </div>
        </div>
      )}

      {campaign.status === 'live' && (
        <div className="qr-block">
          <h3>Distribution</h3>
          <div className="qr-url">{publicUrl}</div>
          <button className="btn btn-secondary" onClick={handleCopy} style={{ marginBottom: 14 }}>
            {copied ? '✓ Copied!' : 'Copy link'}
          </button>
          <div>
            <QRCodeSVG value={publicUrl} size={200} includeMargin />
          </div>
        </div>
      )}

      {campaign.status === 'ended' && (
        <p style={{ color: '#6b7280', marginTop: '1rem' }}>This campaign has ended.</p>
      )}
    </div>
  );
}
