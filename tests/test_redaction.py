from ragchatbot.orchestrator.redaction import redact_ticket


def test_redact_pan_and_phone() -> None:
    ticket = {"pan": "4111-1111-1111-1111", "contact_phone": "+1-555-010-4821"}
    redacted, flags = redact_ticket(ticket)
    assert redacted["pan"] == "[REDACTED_PAN]"
    assert "[REDACTED_PHONE]" in redacted["contact_phone"]
    assert flags
