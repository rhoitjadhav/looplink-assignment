import { useState, useEffect } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { api } from '../api';
import OfferEditor from '../components/OfferEditor';

function toDatetimeLocal(isoStr) {
  if (!isoStr) return '';
  return isoStr.replace('Z', '').slice(0, 16);
}

function toISO(dtLocal) {
  if (!dtLocal) return null;
  return dtLocal + ':00Z';
}

const NUMERIC_FIELDS = {
  PRODUCT_PERCENT_DISCOUNT: ['percent'],
  CART_FIXED_DISCOUNT: ['amount_off', 'min_basket'],
  STICKER_EARN: ['stickers', 'per_amount'],
};

function coerceOffers(offers) {
  return offers.map(o => {
    const out = { type: o.type };
    (NUMERIC_FIELDS[o.type] || []).forEach(f => { out[f] = Number(o[f]); });
    Object.keys(o).forEach(k => {
      if (k !== 'type' && !(k in out)) out[k] = o[k];
    });
    return out;
  });
}

export default function CampaignForm() {
  const { id } = useParams();
  const navigate = useNavigate();
  const isEdit = Boolean(id);

  const [loading, setLoading] = useState(isEdit);
  const [loadError, setLoadError] = useState(null);
  const [campaign, setCampaign] = useState(null);

  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [startsAt, setStartsAt] = useState('');
  const [endsAt, setEndsAt] = useState('');
  const [offers, setOffers] = useState([]);
  const [version, setVersion] = useState(null);

  const [fieldErrors, setFieldErrors] = useState({});
  const [banner, setBanner] = useState(null);
  const [submitting, setSubmitting] = useState(false);

  const prefill = (c) => {
    setCampaign(c);
    setName(c.name);
    setDescription(c.description);
    setStartsAt(toDatetimeLocal(c.starts_at));
    setEndsAt(toDatetimeLocal(c.ends_at));
    setOffers(c.offers.map(o => ({ type: o.type, ...o.params })));
    setVersion(c.version);
  };

  const loadCampaign = () => {
    setLoading(true);
    setLoadError(null);
    api.getCampaign(id)
      .then(c => { prefill(c); setLoading(false); })
      .catch(e => { setLoadError(e.message); setLoading(false); });
  };

  useEffect(() => { if (isEdit) loadCampaign(); }, [id]);

  if (isEdit && loading) return <div className="container"><p>Loading…</p></div>;
  if (isEdit && loadError) return <div className="container"><div className="error-banner">{loadError}</div></div>;
  if (isEdit && campaign && campaign.status !== 'draft') {
    return (
      <div className="container">
        <p>
          This campaign is <strong>{campaign.status}</strong> and can no longer be edited.
        </p>
        <Link to={`/admin/${id}`} className="btn btn-secondary">Back to campaign</Link>
      </div>
    );
  }

  const validate = () => {
    const errs = {};
    if (!name.trim()) errs.name = 'Name is required.';
    if (startsAt && endsAt && new Date(endsAt) <= new Date(startsAt)) {
      errs.endsAt = 'End must be after start.';
    }
    return errs;
  };

  const handleSubmit = async e => {
    e.preventDefault();
    setBanner(null);
    const errs = validate();
    if (Object.keys(errs).length) { setFieldErrors(errs); return; }
    setFieldErrors({});
    setSubmitting(true);

    const payload = {
      name: name.trim(),
      description,
      starts_at: toISO(startsAt),
      ends_at: toISO(endsAt),
      offers: coerceOffers(offers),
    };

    try {
      const saved = isEdit
        ? await api.updateCampaign(id, { ...payload, version })
        : await api.createCampaign(payload);
      navigate(`/admin/${saved.id}`);
    } catch (err) {
      setSubmitting(false);
      if (err.code === 'version_conflict') {
        setBanner({ type: 'conflict', message: err.message });
      } else if (err.code === 'status_conflict') {
        setBanner({ type: 'status', message: err.message });
      } else if (err.status === 422) {
        const detail = err.detail;
        if (Array.isArray(detail)) {
          const ferrs = {};
          const msgs = [];
          detail.forEach(d => {
            const field = d.loc?.[d.loc.length - 1];
            if (field && typeof field === 'string') ferrs[field] = d.msg;
            else msgs.push(d.msg);
          });
          setFieldErrors(ferrs);
          if (msgs.length) setBanner({ type: 'error', message: msgs.join('; ') });
        } else {
          setBanner({ type: 'error', message: err.message });
        }
      } else {
        setBanner({ type: 'error', message: err.message || 'Something went wrong.' });
      }
    }
  };

  return (
    <div className="container">
      <h1>{isEdit ? 'Edit campaign' : 'New campaign'}</h1>

      {banner?.type === 'conflict' && (
        <div className="error-banner">
          {banner.message}
          <button className="btn btn-secondary"
            onClick={() => { setBanner(null); loadCampaign(); }}>
            Reload
          </button>
        </div>
      )}
      {banner?.type === 'status' && (
        <div className="error-banner">
          {banner.message}
          <Link to={`/admin/${id}`} className="btn btn-secondary">Back to campaign</Link>
        </div>
      )}
      {banner?.type === 'error' && (
        <div className="error-banner">{banner.message}</div>
      )}

      <form onSubmit={handleSubmit}>
        <div className="field">
          <label htmlFor="name">Name</label>
          <input id="name" type="text" value={name} onChange={e => setName(e.target.value)}
            aria-describedby={fieldErrors.name ? 'name-err' : undefined} />
          {fieldErrors.name && <p id="name-err" className="error">{fieldErrors.name}</p>}
        </div>

        <div className="field">
          <label htmlFor="description">Description</label>
          <textarea id="description" rows={3} value={description}
            onChange={e => setDescription(e.target.value)} />
        </div>

        <div className="field">
          <label htmlFor="starts_at">Starts at (UTC)</label>
          <input id="starts_at" type="datetime-local" value={startsAt}
            onChange={e => setStartsAt(e.target.value)} />
        </div>

        <div className="field">
          <label htmlFor="ends_at">Ends at (UTC)</label>
          <input id="ends_at" type="datetime-local" value={endsAt}
            onChange={e => setEndsAt(e.target.value)}
            aria-describedby={fieldErrors.endsAt ? 'ends-err' : undefined} />
          {fieldErrors.endsAt && <p id="ends-err" className="error">{fieldErrors.endsAt}</p>}
        </div>

        <OfferEditor offers={offers} onChange={setOffers} disabled={submitting} />

        <div style={{ marginTop: '1.5rem', display: 'flex', gap: 8 }}>
          <button type="submit" className="btn" disabled={submitting}>
            {submitting ? 'Saving…' : isEdit ? 'Save changes' : 'Create campaign'}
          </button>
          <Link to={isEdit ? `/admin/${id}` : '/admin'} className="btn btn-secondary">
            Cancel
          </Link>
        </div>
      </form>
    </div>
  );
}
