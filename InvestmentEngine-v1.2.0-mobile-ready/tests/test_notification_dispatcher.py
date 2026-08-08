from app.notifications.dispatcher import NotificationDispatcher


def test_notification_template_render_replaces_known_placeholders() -> None:
    rendered = NotificationDispatcher._render(
        "{{system}} {{direction}} Edge {{edge}}",
        {"system": "ETH/BTC", "direction": "BTC→ETH", "edge": "82,4"},
    )
    assert rendered == "ETH/BTC BTC→ETH Edge 82,4"


def test_notification_number_format_uses_turkish_separators() -> None:
    assert NotificationDispatcher._format_number("123456.789", 2) == "123.456,79"
