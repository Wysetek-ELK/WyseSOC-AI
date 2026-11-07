import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_system_servers_live_and_history(client: AsyncClient, admin_token: str):
    headers = {"Authorization": f"Bearer {admin_token}"}

    # 1. Test Live Metrics Endpoint
    live_res = await client.get("/api/system/servers/live", headers=headers)
    assert live_res.status_code == 200
    live_data = live_res.json()
    assert "server_1" in live_data
    assert "server_2" in live_data
    assert live_data["server_1"]["server_id"] == "server-1"
    assert live_data["server_1"]["status"] == "ONLINE"
    assert "cpu_percent" in live_data["server_1"]
    assert "memory_percent" in live_data["server_1"]

    # 2. Test Historical Metrics Endpoint
    hist_res = await client.get("/api/system/servers/history?window=24h", headers=headers)
    assert hist_res.status_code == 200
    hist_data = hist_res.json()
    assert "server_1_series" in hist_data
    assert "server_2_series" in hist_data
    assert "stats" in hist_data
    assert len(hist_data["server_1_series"]) > 0
    assert len(hist_data["server_2_series"]) > 0
