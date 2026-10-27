"""Preview audio must support seeking and return normal missing-file responses."""
import pytest

pytest.importorskip('fastapi')


def test_gallery_range_download_and_missing_file(tmp_path):
    from fastapi.testclient import TestClient
    from tools.serve_music import create_app
    payload=bytes(range(256))*1000
    (tmp_path/'source.wav').write_bytes(payload)
    with TestClient(create_app(tmp_path)) as client:
        response=client.get('/source.wav',headers={'Range':'bytes=100-199'})
        assert response.status_code==206
        assert response.content==payload[100:200]
        assert response.headers['content-range']==f'bytes 100-199/{len(payload)}'
        assert client.get('/source.wav').content==payload
        assert client.get('/missing.wav').status_code==404
