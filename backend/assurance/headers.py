"""Defensive response headers. CSP is deliberately omitted from JSON API responses.
Serve a separately tested CSP at the Angular hosting layer, never by guessing directives.
"""
def apply_security_headers(headers, scheme: str):
    headers["X-Content-Type-Options"] = "nosniff"
    headers["X-Frame-Options"] = "DENY"
    headers["Referrer-Policy"] = "no-referrer"
    headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    headers["Cache-Control"] = "no-store"
    if scheme == "https":
        headers["Strict-Transport-Security"] = "max-age=31536000"
    return headers
