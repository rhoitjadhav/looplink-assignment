const OFFER_DEFS = {
  PRODUCT_PERCENT_DISCOUNT: {
    label: "Product % discount",
    fields: [
      { name: "percent", label: "Percent off", type: "number", min: 0.01, max: 100 },
      { name: "applies_to", label: "Applies to (SKUs / label)", type: "text" },
    ],
  },
  CART_FIXED_DISCOUNT: {
    label: "Cart fixed discount",
    fields: [
      { name: "amount_off", label: "Amount off", type: "number", min: 0.01 },
      { name: "min_basket", label: "Minimum basket", type: "number", min: 0 },
    ],
  },
  STICKER_EARN: {
    label: "Sticker earn",
    fields: [
      { name: "stickers", label: "Stickers earned", type: "number", min: 1, step: 1 },
      { name: "per_amount", label: "Per amount spent", type: "number", min: 0.01 },
    ],
  },
};

export default function OfferEditor({ offers, onChange, disabled }) {
  const addOffer = (type) => {
    const blank = { type };
    OFFER_DEFS[type].fields.forEach((f) => (blank[f.name] = ""));
    onChange([...offers, blank]);
  };
  const updateField = (i, name, value) =>
    onChange(offers.map((o, idx) => (idx === i ? { ...o, [name]: value } : o)));
  const removeOffer = (i) => onChange(offers.filter((_, idx) => idx !== i));

  return (
    <fieldset disabled={disabled} style={{ border: '1px solid #e5e7eb', borderRadius: 8, padding: '1rem', margin: '1rem 0' }}>
      <legend style={{ fontWeight: 600, padding: '0 6px' }}>Offers</legend>
      {offers.length === 0 && (
        <p style={{ color: '#6b7280', margin: '0 0 10px' }}>
          No offers attached yet — at least one is required to launch.
        </p>
      )}
      {offers.map((offer, i) => (
        <div key={i} className="offer-row">
          <strong>{OFFER_DEFS[offer.type].label}</strong>
          {OFFER_DEFS[offer.type].fields.map((f) => (
            <label key={f.name}>
              {f.label}
              <input
                type={f.type} min={f.min} max={f.max} step={f.step ?? "any"}
                value={offer[f.name]}
                onChange={(e) => updateField(i, f.name, e.target.value)}
                required
              />
            </label>
          ))}
          <button type="button" className="btn btn-secondary" style={{ alignSelf: 'flex-end' }}
            onClick={() => removeOffer(i)}>
            Remove
          </button>
        </div>
      ))}
      <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginTop: 8 }}>
        {Object.entries(OFFER_DEFS).map(([type, def]) => (
          <button key={type} type="button" className="btn btn-secondary"
            onClick={() => addOffer(type)}>
            + {def.label}
          </button>
        ))}
      </div>
    </fieldset>
  );
}
