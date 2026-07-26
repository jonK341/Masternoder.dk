def test_no_obs_playbook():
    from backend.services.youtube_stream_ingest_service import ingest_status, no_obs_playbook

    pb = no_obs_playbook()
    assert pb["success"] is True
    assert pb["obs_required"] is False
    assert pb["recommended"] == "browser_tab_capture"
    st = ingest_status()
    assert st["success"] is True
