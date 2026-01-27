# PROJECT KNOWLEDGE BASE

**Generated:** Tue Jan 27 2026
**Scope:** Root

## OVERVIEW
Modern Python library for Upbit Open API. Features async-first design, Pydantic V2 models, strict typing, and financial precision using Decimal.

## API VERSION
- **REST API**: v1 (e.g., `https://api.upbit.com/v1/...`)
- **WebSocket**: v1 (e.g., `wss://api.upbit.com/websocket/v1`)


## STRUCTURE
```
upbit_connect/
├── auth.py           # JWT authentication logic (no external deps)
├── client.py         # Main entry points (UpbitClient, AsyncUpbitClient)
├── models/           # Pydantic V2 data models
├── services/         # API domains (Exchange, Quotation)
└── websocket/        # Real-time WebSocket client
tests/                # Pytest suite (mirrors source structure)
```

## WHERE TO LOOK
| Task | Location | Notes |
|------|----------|-------|
| **Add API Endpoint** | `upbit_connect/services/` | Add to `ExchangeService` or `QuotationService` |
| **Update Models** | `upbit_connect/models/` | Use Pydantic V2; strict types |
| **Auth Logic** | `upbit_connect/auth.py` | JWT generation; handles headers |
| **Real-time Data** | `upbit_connect/websocket/` | `UpbitWebSocket` implementation |
| **Tests** | `tests/` | Run `pytest` to verify |

## CODE MAP
| Symbol | Type | Location | Role |
|--------|------|----------|------|
| `AsyncUpbitClient` | Class | `client.py` | Main async entry point |
| `UpbitClient` | Class | `client.py` | Synchronous wrapper |
| `ExchangeService` | Class | `services/exchange.py` | Trading, Account APIs (Auth req) |
| `QuotationService` | Class | `services/quotation.py` | Market data APIs (Public) |
| `UpbitWebSocket` | Class | `websocket/client.py` | WebSocket connection manager |

## CONVENTIONS
- **Financial Precision**: **CRITICAL**. ALWAYS use `Decimal` for price/volume/fee. NEVER use `float`.
  - Use validator: `@field_validator("price", mode="before")` to coerce inputs.
- **Async First**: Implement logic in `AsyncUpbitClient` first; `UpbitClient` wraps it.
- **Type Hinting**: Use Python 3.10+ syntax (`str | None`, `list[str]`).
- **Imports**: 3 blocks (Std, 3rd-party, Local), alphabetical, 1 newline separator.
- **Docstrings**: Google Style required for all public members.

## ANTI-PATTERNS (THIS PROJECT)
- **NO Floats**: `float(price)` is strictly forbidden. Use `Decimal(str(price))`.
- **NO Optional**: Use `Type | None` instead of `Optional[Type]`.
- **NO External JWT**: Do not add `pyjwt`. Use `upbit_connect.auth` (std lib based).
- **NO Loose Typing**: `Any` is discouraged. MyPy is strict.

## COMMANDS
```bash
# Test
pytest
pytest tests/test_auth.py

# Lint & Format
ruff check
ruff format

# Type Check (Strict)
mypy .
```

## NOTES
- **Rate Limiting**: Handled automatically (Exchange: 8/sec, Quotation: 30/sec).
- **Context Managers**: Always use `async with` or `with` to ensure session cleanup.
