"""MN2 RPC transient error detection."""

from backend.services.mn2_rpc_client import is_transient_rpc_error


def test_is_transient_rpc_error_queue_depth():
    assert is_transient_rpc_error("HTTP 500: Work queue depth exceeded")


def test_is_transient_rpc_error_permanent():
    assert not is_transient_rpc_error("Wallet RPC authentication failed")
