from app.pii import scrub_text, scrub_value


def test_scrub_email() -> None:
    out = scrub_text("Email me at student@vinuni.edu.vn")
    assert "student@" not in out
    assert "REDACTED_EMAIL" in out


def test_scrub_common_vietnamese_phone_formats() -> None:
    phone_numbers = (
        "0901234567",
        "090 123 4567",
        "090.123.4567",
        "090-123-4567",
        "+84 90 123 4567",
    )

    for phone_number in phone_numbers:
        out = scrub_text(f"Contact: {phone_number}")
        assert phone_number not in out
        assert "REDACTED_PHONE_VN" in out


def test_scrub_identity_and_payment_numbers() -> None:
    samples = {
        "079203001234": "REDACTED_CCCD",
        "4111-1111-1111-1111": "REDACTED_CREDIT_CARD",
        "B1234567": "REDACTED_PASSPORT",
        "AB1234567": "REDACTED_PASSPORT",
    }

    for raw_value, marker in samples.items():
        out = scrub_text(f"Sensitive value: {raw_value}")
        assert raw_value not in out
        assert marker in out


def test_scrub_labeled_address() -> None:
    raw_address = "Địa chỉ: 123 Nguyễn Trãi, Quận 1, TP.HCM"
    out = scrub_text(f"Customer profile | {raw_address}; verified=true")

    assert "123 Nguyễn Trãi" not in out
    assert "REDACTED_ADDRESS" in out
    assert "verified=true" in out


def test_scrub_value_recurses_through_nested_containers() -> None:
    payload = {
        "contacts": [
            "student@vinuni.edu.vn",
            {"phone": "090 123 4567"},
        ],
        "identity": ("B1234567", {"cccd": "079203001234"}),
        "attempts": 2,
        "verified": True,
        "missing": None,
    }

    scrubbed = scrub_value(payload)
    rendered = repr(scrubbed)

    assert "student@vinuni.edu.vn" not in rendered
    assert "090 123 4567" not in rendered
    assert "B1234567" not in rendered
    assert "079203001234" not in rendered
    assert scrubbed["attempts"] == 2
    assert scrubbed["verified"] is True
    assert scrubbed["missing"] is None
