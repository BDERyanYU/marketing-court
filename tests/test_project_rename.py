from fastapi.testclient import TestClient
from backend.app.main import create_app


def test_rename_project_preserves_data_and_survives_restart(tmp_path):
    database = tmp_path / 'rename.db'
    with TestClient(create_app(database_path=database)) as client:
        review = client.post('/api/demo').json()
        pid = review['project_id']
        original = client.get('/api/projects').json()[0]
        renamed = client.patch('/api/projects/' + pid, json={'name': '  新项目名称  '})
        assert renamed.status_code == 200
        assert renamed.json() == {**original, 'name': '新项目名称'}
        for name in ['', '   ', 'x' * 101]:
            assert client.patch('/api/projects/' + pid, json={'name': name}).status_code == 422
        assert client.patch('/api/projects/missing', json={'name': '名称'}).status_code == 404
        assert client.get('/api/projects/' + pid + '/reviews').json()[0]['review_id'] == review['review_id']
    with TestClient(create_app(database_path=database)) as client:
        assert client.get('/api/projects').json()[0]['name'] == '新项目名称'
