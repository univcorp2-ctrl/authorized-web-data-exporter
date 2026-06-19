# CODEX

## Project intent

Build a stable, generic, authorized web data exporter for login-based websites. Kenbiya is included as the first site profile, but the architecture must remain reusable for other sites.

## Safety and compliance boundaries

Do not add CAPTCHA bypass, authentication bypass, proxy rotation, stealth evasion, IP rotation, or bot-detection circumvention. Stability should come from conservative rate limiting, robots.txt inspection, checkpointing, retries, and clear error reporting.

## Quality gates

Run:

```bash
ruff check .
pytest
```

## Key files

- `profiles/kenbiya.yml`
- `src/authorized_web_exporter/crawler.py`
- `src/authorized_web_exporter/robots.py`
- `src/authorized_web_exporter/parser.py`
- `.github/workflows/export.yml`
