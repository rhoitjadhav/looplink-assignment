import re


class InvalidIdentity(ValueError):
    pass


_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def normalize_identity(raw: str) -> tuple[str, str]:
    """Return (identity_type, normalized). Pragmatic by spec:
    email -> trim + lowercase; phone -> strip everything but digits
    (keep a single leading +). Not E.164 — deliberately."""
    value = (raw or "").strip()
    if not value:
        raise InvalidIdentity("Identity is required")

    if "@" in value:
        value = value.lower()
        if not _EMAIL_RE.match(value):
            raise InvalidIdentity("That doesn't look like a valid email")
        return "email", value

    plus = "+" if value.lstrip().startswith("+") else ""
    digits = re.sub(r"\D", "", value)
    if not (7 <= len(digits) <= 15):
        raise InvalidIdentity("That doesn't look like a valid phone number")
    return "phone", plus + digits
