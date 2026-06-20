from unittest.mock import MagicMock
from unittest.mock import patch

from cartography.intel.aws.route53 import _link_record_ips


def test_link_record_ips_calls_helper_per_record_with_ip_list():
    # Arrange: two A records; one AAAA-shaped record (we only test that
    # _link_ip_to_A_record gets called with the right args).
    records = [
        {
            "id": "z1.example.com|A|app",
            "name": "app.example.com",
            "type": "A",
            "zoneid": "z1",
            "ip_addresses": ["10.0.0.1", "10.0.0.2"],
            "value": "10.0.0.1,10.0.0.2",
        },
        {
            "id": "z1.example.com|AAAA|api",
            "name": "api.example.com",
            "type": "AAAA",
            "zoneid": "z1",
            "ip_addresses": ["2001:db8::1"],
            "value": "2001:db8::1",
        },
    ]
    update_tag = 123456789
    session = MagicMock()

    # Act
    with patch("cartography.intel.aws.route53._link_ip_to_A_record") as mock_link:
        _link_record_ips(session, records, update_tag)

    # Assert: helper called once per record, with the right args, in order.
    assert mock_link.call_count == 2
    calls = mock_link.call_args_list
    assert calls[0].args == (
        session,
        update_tag,
        ["10.0.0.1", "10.0.0.2"],
        "z1.example.com|A|app",
    )
    assert calls[1].args == (
        session,
        update_tag,
        ["2001:db8::1"],
        "z1.example.com|AAAA|api",
    )


def test_link_record_ips_skips_records_without_ip_addresses():
    # Arrange: one ALIAS (type=ALIAS) record has no ip_addresses key by design.
    records = [
        {
            "id": "z1.example.com|ALIAS|cdn",
            "name": "cdn.example.com",
            "type": "ALIAS",
            "zoneid": "z1",
            "ip_addresses": [],
            "value": "d111111.cloudfront.net",
        },
        {
            "id": "z1.example.com|A|app",
            "name": "app.example.com",
            "type": "A",
            "zoneid": "z1",
            "ip_addresses": ["10.0.0.1"],
            "value": "10.0.0.1",
        },
    ]
    session = MagicMock()
    update_tag = 1

    # Act
    with patch("cartography.intel.aws.route53._link_ip_to_A_record") as mock_link:
        _link_record_ips(session, records, update_tag)

    # Assert: ALIAS record is skipped; only the A record triggers the helper.
    assert mock_link.call_count == 1
    assert mock_link.call_args.args == (
        session,
        update_tag,
        ["10.0.0.1"],
        "z1.example.com|A|app",
    )


def test_link_record_ips_handles_empty_record_list():
    # Arrange: empty records list.
    session = MagicMock()
    update_tag = 1

    # Act
    with patch("cartography.intel.aws.route53._link_ip_to_A_record") as mock_link:
        _link_record_ips(session, [], update_tag)

    # Assert: helper not called.
    mock_link.assert_not_called()


def test_link_record_ips_skips_records_without_id(caplog):
    # Arrange: a record that has ip_addresses but no id.
    # Schema requires id, but defensive code should warn-and-skip anyway.
    records = [
        {
            "name": "broken.example.com",
            "type": "A",
            "zoneid": "z1",
            "ip_addresses": ["10.0.0.1"],
            "value": "10.0.0.1",
            # "id" intentionally missing
        },
    ]
    session = MagicMock()
    update_tag = 7

    # Act
    with patch("cartography.intel.aws.route53._link_ip_to_A_record") as mock_link:
        with caplog.at_level("WARNING"):
            _link_record_ips(session, records, update_tag)

    # Assert: helper not called when id missing; warning was logged.
    mock_link.assert_not_called()
    assert any("Skipping IP link" in record.message for record in caplog.records)
