import asyncio
from unittest import mock

import aiohttp
import pytest

from bottery import Bottery


@pytest.fixture
def bot():
    bot = Bottery()
    yield bot
    bot.stop()


@pytest.fixture
def fake_engine():
    class FakeEngine:
        def __init__(self):
            self.tasks = []
            self.configure_calls = 0

        async def configure(self):
            self.configure_calls += 1
            self.tasks.append("fake_task")

    return FakeEngine()


@pytest.mark.parametrize(
    "attribute,instance_type",
    [
        ("loop", asyncio.AbstractEventLoop),
        ("session", aiohttp.ClientSession),
    ],
)
def test_default_properties(bot, attribute, instance_type):
    assert isinstance(getattr(bot, attribute), instance_type)


@pytest.mark.parametrize(
    "attribute,value",
    [
        ("loop", "custom_loop"),
        ("session", "custom_session"),
    ],
)
def test_already_defined_properties(attribute, value):
    bot = Bottery()

    try:
        setattr(bot, f"_{attribute}", value)

        assert getattr(bot, attribute) == value
    finally:
        bot.stop()


@pytest.mark.asyncio
async def test_configure_without_platforms(bot):
    with pytest.raises(Exception):
        await bot.configure()


@pytest.mark.parametrize(
    "platforms",
    [
        {},
        {"fake": {}},
        {"fake": {"ENGINE": None}},
        {"fake": {"ENGINE": ""}},
        {"fake": {"ENGINE": "module.does_not_exist"}},
    ],
)
@pytest.mark.asyncio
async def test_configure_invalid_platforms(bot, platforms):
    bot.settings.PLATFORMS = platforms

    with pytest.raises(Exception):
        await bot.configure()


@pytest.mark.asyncio
async def test_configure_platform_with_valid_engine(bot, fake_engine):
    bot.settings.PLATFORMS = {
        "fake": {
            "ENGINE": "module.fake_engine",
        }
    }

    with mock.patch(
        "bottery.bottery.importlib.import_module"
    ) as mock_import:
        module = mock.Mock()
        module.configure = fake_engine.configure
        mock_import.return_value = module

        await bot.configure()

        mock_import.assert_called_once_with("module.fake_engine")


@pytest.mark.asyncio
async def test_configure_engine_configures_tasks(bot, fake_engine):
    bot.settings.PLATFORMS = {
        "fake": {
            "ENGINE": "module.fake_engine",
        }
    }

    with mock.patch(
        "bottery.bottery.importlib.import_module"
    ) as mock_import:
        module = mock.Mock()
        module.configure = fake_engine.configure
        mock_import.return_value = module

        await bot.configure()

        assert fake_engine.configure_calls == 1
        assert fake_engine.tasks == ["fake_task"]


@pytest.mark.parametrize(
    "platforms",
    [
        {
            "first": {
                "ENGINE": "module.first",
            },
            "second": {
                "ENGINE": "module.second",
            },
        },
        {
            "telegram": {
                "ENGINE": "module.telegram",
            },
            "discord": {
                "ENGINE": "module.discord",
            },
            "slack": {
                "ENGINE": "module.slack",
            },
        },
    ],
)
@pytest.mark.asyncio
async def test_configure_multiple_platforms(bot, platforms):
    bot.settings.PLATFORMS = platforms

    with mock.patch(
        "bottery.bottery.importlib.import_module"
    ) as mock_import:
        mock_import.return_value = mock.Mock()

        await bot.configure()

        assert mock_import.call_count == len(platforms)


@pytest.mark.asyncio
async def test_configure_engine_failure_is_propagated(bot):
    bot.settings.PLATFORMS = {
        "fake": {
            "ENGINE": "module.fake_engine",
        }
    }

    error = RuntimeError("configuration failed")

    with mock.patch(
        "bottery.bottery.importlib.import_module",
        side_effect=error,
    ):
        with pytest.raises(RuntimeError, match="configuration failed"):
            await bot.configure()


@mock.patch("bottery.bottery.importlib.import_module")
def test_bottery_import_msghandlers(mock_import_module):
    from bottery.conf import settings

    settings.configure(ROOT_MSGCONF="another_handlers")

    expected_return = ["handlers"]
    mock_import_module.return_value.msghandlers = expected_return

    bottery = Bottery()

    assert bottery.import_msghandlers() == expected_return
    mock_import_module.assert_called_once_with("another_handlers")