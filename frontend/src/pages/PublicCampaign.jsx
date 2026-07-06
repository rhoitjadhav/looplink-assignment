import { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { api } from '../api';

function describeOffer(offer) {
  const p = offer.params;
  switch (offer.type) {
    case 'PRODUCT_PERCENT_DISCOUNT':
      return <><strong>{p.percent}% off</strong> {p.applies_to}</>;
    case 'CART_FIXED_DISCOUNT':
      return <><strong>{p.amount_off} off</strong> when you spend {p.min_basket} or more</>;
    case 'STICKER_EARN':
      return <><strong>{p.stickers} sticker(s)</strong> for every {p.per_amount} you spend</>;
    default:
      return offer.type;
  }
}

export default function PublicCampaign() {
  const { token } = useParams();
  const [pageState, setPageState] = useState('loading');
  const [campaign, setCampaign] = useState(null);
  const [identity, setIdentity] = useState('');
  const [enrollResult, setEnrollResult] = useState(null);
  const [identityError, setIdentityError] = useState(null);
  const [enrolling, setEnrolling] = useState(false);

  const load = () => {
    setPageState('loading');
    api.publicView(token)
      .then(data => {
        setPageState(data.state);
        setCampaign(data.campaign);
      })
      .catch(err => {
        if (err.status === 404) setPageState('invalid');
        else setPageState('network_error');
      });
  };

  useEffect(load, [token]);

  const handleEnroll = async e => {
    e.preventDefault();
    setIdentityError(null);
    setEnrolling(true);
    try {
      const result = await api.enroll(token, identity);
      setEnrollResult(result);
      setCampaign(result.campaign);
    } catch (err) {
      if (err.status === 422) {
        setIdentityError(err.detail?.message || err.message);
      } else if (err.code === 'not_live') {
        setPageState('ended');
        setCampaign(null);
      } else {
        setIdentityError(err.message || 'Something went wrong.');
      }
    } finally {
      setEnrolling(false);
    }
  };

  if (pageState === 'loading') {
    return <div className="public-page"><p>Loading…</p></div>;
  }
  if (pageState === 'invalid') {
    return (
      <div className="public-page">
        <p>This link isn't valid. Check with the store that shared it.</p>
      </div>
    );
  }
  if (pageState === 'network_error') {
    return (
      <div className="public-page">
        <p>Can't reach the server.</p>
        <button className="btn" onClick={load}>Retry</button>
      </div>
    );
  }
  if (pageState === 'not_open') {
    return (
      <div className="public-page">
        <p>This campaign isn't open yet. Come back soon!</p>
      </div>
    );
  }
  if (pageState === 'ended') {
    return (
      <div className="public-page">
        <p>This campaign has ended.</p>
      </div>
    );
  }

  // live
  return (
    <div className="public-page">
      <h1>{campaign.name}</h1>
      {campaign.description && <p style={{ color: '#4b5563' }}>{campaign.description}</p>}

      <div style={{ marginBottom: '1.5rem' }}>
        {campaign.offers.map((o, i) => (
          <div key={i} className="offer-card">{describeOffer(o)}</div>
        ))}
      </div>

      {enrollResult ? (
        <div>
          <div className="success-msg">
            {enrollResult.already_enrolled
              ? "Welcome back — you're already enrolled."
              : "You're in! Show this at the till."}
          </div>
          {enrollResult.campaign.offers.map((o, i) => (
            <div key={i} className="offer-card">{describeOffer(o)}</div>
          ))}
        </div>
      ) : (
        <form onSubmit={handleEnroll}>
          <label htmlFor="identity" style={{ display: 'block', marginBottom: 6, fontWeight: 500 }}>
            Your phone or email
          </label>
          <input
            id="identity"
            type="text"
            inputMode="email"
            value={identity}
            onChange={e => setIdentity(e.target.value)}
            aria-describedby={identityError ? 'identity-err' : undefined}
            required
          />
          {identityError && (
            <p id="identity-err" className="error" role="alert">{identityError}</p>
          )}
          <button type="submit" className="btn btn-full" disabled={enrolling}>
            {enrolling ? 'Enrolling…' : 'Get my offers'}
          </button>
        </form>
      )}
    </div>
  );
}
