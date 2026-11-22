import asyncio
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from pydantic import ValidationError

from app.models.alert import Direction
from app.services.ai_alert import AlertDraft, ParsedAlert, normalize_price


@pytest.mark.parametrize("price", ["0", "-1", "NaN", "0.000000001", "1000000000000"])
def test_rejects_price_that_cannot_be_saved(price):
    with pytest.raises(ValidationError):
        AlertDraft(symbol="ETHUSDT", direction="above", target_price=price)


@pytest.mark.parametrize(("decision", "saved"), [("yes", True), ("no", False)])
def test_draft_waits_for_price_and_button(monkeypatch, decision, saved):
    from app.bot import main

    async def run():
        class DraftState:
            status = None
            data = {}

            async def get_state(self):
                return self.status

            async def set_state(self, state):
                self.status = state.state

            async def get_data(self):
                return self.data

            async def set_data(self, data):
                self.data = data

            async def clear(self):
                self.status, self.data = None, {}

        state = DraftState()
        message = MagicMock(spec=main.Message)
        message.answer = AsyncMock()
        message.edit_reply_markup = AsyncMock()
        message.text = "Notify me if ETH goes up"

        extract = AsyncMock(return_value=ParsedAlert(
            supported=True,
            draft=AlertDraft(symbol="ETHUSDT", direction="above", target_price=None),
        ))
        save = AsyncMock()
        monkeypatch.setattr(main.settings, "OLLAMA_MODEL", "test-model")
        monkeypatch.setattr(main, "extract_alert", extract)
        monkeypatch.setattr(main, "save_alert", save)

        await main.build_ai_alert(message, state)
        assert "target price" in message.answer.await_args.args[0]
        assert state.status == main.AIAlert.collecting.state

        message.text = "3500"
        await main.build_ai_alert(message, state)
        assert "ETHUSDT > 3500" in message.answer.await_args.args[0]
        extract.assert_awaited_once()
        save.assert_not_awaited()

        key = state.data["key"]
        callback = SimpleNamespace(
            data=f"ai-alert:{decision}:{key}",
            message=message,
            from_user=SimpleNamespace(id=123),
            answer=AsyncMock(),
        )
        await main.confirm_ai_alert(callback, state)
        await main.confirm_ai_alert(callback, state)
        assert save.await_count == int(saved)
        if saved:
            assert save.await_args.args[1:] == (123, "ETHUSDT", Direction.ABOVE, Decimal("3500"))

    asyncio.run(run())


def test_accepts_decimal_comma_in_clarification():
    assert normalize_price("3,25") == "3.25"
