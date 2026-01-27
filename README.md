# Upbit Connect

**생산성, 타입 안정성, 비동기를 최우선으로 고려한 Modern Python Upbit API 라이브러리입니다.**

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

---

## 📌 주요 특징

- **완벽한 비동기(Async) 지원**: `asyncio` 기반의 고성능 논블로킹 I/O (동기 모드도 지원)
- **철저한 타입 시스템**: Pydantic V2 모델을 사용하여 모든 요청/응답을 완벽하게 검증
- **금융급 정밀도**: 부동소수점 오차 없는 `Decimal` 타입 사용
- **스마트한 속도 제한**: 업비트 API 제한(Rate Limit) 자동 감지 및 대기
- **간편한 WebSocket**: 자동 재연결 및 실시간 데이터 스트리밍 지원

## 🚀 설치 방법

```bash
pip install upbit-connect
```

## 🔑 인증 및 시작

[업비트 Open API](https://upbit.com/service_center/open_api_guide)에서 발급받은 키를 사용하여 클라이언트를 초기화합니다.

```python
import upbit_connect as upbit

# 비동기 클라이언트 (권장)
client = upbit.AsyncUpbitClient(
    access_key="MY_ACCESS_KEY",
    secret_key="MY_SECRET_KEY"
)

# 동기 클라이언트
# client = upbit.UpbitClient(access_key="...", secret_key="...")
```

---

## 📊 1. QUOTATION API (시세 조회)
*인증 불필요 (Public API)*

### 마켓 코드 조회
```python
# 모든 마켓 코드 조회
markets = await client.quotation.get_markets()
print(f"거래 가능 마켓: {len(markets)}개")
```

### 캔들(Candle) 조회
```python
# 비트코인 일봉(Day) 10개 조회
candles = await client.quotation.get_candles_days("KRW-BTC", count=10)
for c in candles:
    print(f"{c.candle_date_time_kst}: {c.trade_price:,}원")
```

### 현재가(Ticker) 조회
```python
# 여러 종목 현재가 동시 조회
tickers = await client.quotation.get_ticker(["KRW-BTC", "KRW-ETH"])
print(f"BTC: {tickers[0].trade_price:,}원")
```

### 호가(Orderbook) 조회
```python
orderbooks = await client.quotation.get_orderbook(["KRW-BTC"])
print(f"매도 1호가: {orderbooks[0].orderbook_units[0].ask_price}")
```

---

## 💸 2. EXCHANGE API (주문 및 자산)
*인증 필요 (Private API)*

### 자산(Asset) 조회
```python
# 내 계좌 잔고 조회
accounts = await client.exchange.get_accounts()
for acc in accounts:
    print(f"{acc.currency}: {acc.balance}")
```

### 주문(Order)하기
```python
from decimal import Decimal

# 지정가 매수 (비트코인 5천만원에 0.001개 매수)
buy_order = await client.exchange.buy_limit(
    market="KRW-BTC",
    price=Decimal("50000000"),
    volume=Decimal("0.001")
)

# 시장가 매도 (비트코인 0.001개 즉시 매도)
sell_order = await client.exchange.sell_market(
    market="KRW-BTC",
    volume=Decimal("0.001")
)
```

### 주문 취소
```python
# 주문 UUID로 취소
await client.exchange.cancel_order(uuid=buy_order.uuid)
```

---

## 📡 3. WEBSOCKET (실시간 데이터)
*실시간 시세 및 체결 수신*

```python
import asyncio
import upbit_connect as upbit

async def main():
    ws = upbit.UpbitWebSocket(
        access_key="MY_ACCESS_KEY",
        secret_key="MY_SECRET_KEY"
    )

    # 데이터 수신 콜백
    async def on_message(data):
        print(f"실시간 데이터: {data}")

    await ws.connect()

    # 원하는 채널 구독 (현재가, 체결, 호가, 내 주문)
    await ws.subscribe("unique-ticket-id", [
        {"type": "ticker", "codes": ["KRW-BTC", "KRW-ETH"]},
        {"type": "trade", "codes": ["KRW-BTC"]},
        {"type": "myOrder"}  # 내 주문 체결 알림 (Private)
    ])

    # 수신 루프 실행
    await ws.run(on_message)

if __name__ == "__main__":
    asyncio.run(main())
```

---

## ⚠️ 에러 처리

모든 에러는 `UpbitError`를 상속받아 명확하게 구분됩니다.

```python
try:
    await client.exchange.buy_limit(...)
except upbit.UpbitRateLimitError as e:
    print(f"너무 많은 요청입니다. {e.retry_after}초 대기하세요.")
except upbit.UpbitAPIError as e:
    print(f"API 오류 발생: {e.message}")
```

---

### 라이선스

MIT License. 이 라이브러리는 업비트(Dunamu Inc.)와 공식적인 관계가 없습니다.
