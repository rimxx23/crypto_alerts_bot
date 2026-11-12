from decimal import Decimal

import httpx

BINANCE_PRICE_URL = "https://api.binance.com/api/v3/ticker/price"


async def get_price(symbol: str) -> Decimal:
    async with httpx.AsyncClient() as client:
        response = await client.get(BINANCE_PRICE_URL, params={"symbol": symbol})
        response.raise_for_status()
        data = response.json()
        return Decimal(data["price"])