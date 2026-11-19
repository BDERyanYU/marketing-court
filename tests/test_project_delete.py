from fastapi import HTTPException
from fastapi.testclient import TestClient
from pydantic import BaseModel
import pytest

from backend.app.core.store import Store, now
from backend.app.main import create_app
from backend.app.models.review import Project, AssetVersion


class Record(BaseModel):
    status: str = "completed"
    marker: str = "test"


def test_delete_cascades_owned_records_and_files_but_preserves_other_projects(tmp_path):
    database, uploads = tmp_path / "app.db", tmp_path / "uploads"
    app = create_app(database_path=database, storage_path=uploads)
    with TestClient(app) as client:
        target = client.post('/api/demo').json()
        pid, aid, rid = target['project_id'], target['asset_version_id'], target['review_id']
        other = client.post('/api/projects', json={'name': 'Keep me'}).json()['project_id']
        store = Store(database)
        asset = client.get(f'/api/assets/{aid}').json()
        assert (uploads / asset['storage_name']).exists()
        store.add('rewrite', 'rewrite-test', rid, Record())
        store.add('report_addendum', 'addendum-test', pid, Record())
        store.add('persona', 'persona-test', 'persona-test', Record())
        task, _ = store.start_task('rewrite', rid + '/risk-test', 'demo', 'fixture')
        task.status = 'completed'
        store.save_task(task)
        response = client.delete(f'/api/projects/{pid}')
        assert response.status_code == 200, response.text
        assert not response.json()['file_cleanup_pending']
        assert not (uploads / asset['storage_name']).exists()
        for path in [f'/api/assets/{aid}', f'/api/reviews/{rid}', f'/api/tasks/{task.task_id}', f'/api/projects/{pid}/reviews']:
            assert client.get(path).status_code == 404
        with store.connection() as db:
            assert not db.execute('SELECT 1 FROM records WHERE parent IN (?,?)', (pid, rid)).fetchall()
            assert db.execute("SELECT 1 FROM records WHERE kind='persona' AND id='persona-test'").fetchone()
        assert client.delete(f'/api/projects/{pid}').status_code == 404
        with pytest.raises(HTTPException) as error:
            store.start_task('review', aid, 'live', 'test')
        assert error.value.status_code == 404
    with TestClient(create_app(database_path=database, storage_path=uploads)) as client:
        assert [p['project_id'] for p in client.get('/api/projects').json()] == [other]


@pytest.mark.parametrize('busy_kind', ['review', 'rewrite', 'meeting'])
def test_delete_rejects_busy_project_without_losing_data(tmp_path, busy_kind):
    database = tmp_path / 'app.db'
    with TestClient(create_app(database_path=database)) as client:
        review = client.post('/api/demo').json()
        store = Store(database)
        pid = review['project_id']
        if busy_kind == 'meeting':
            store.add('meeting', 'meeting-busy', pid, Record(status='generating'))
        else:
            resource = review['asset_version_id'] if busy_kind == 'review' else review['review_id'] + '/risk'
            store.start_task(busy_kind, resource, 'demo', 'test')
        assert client.delete(f'/api/projects/{pid}').status_code == 409
        assert client.get(f"/api/assets/{review['asset_version_id']}/image").status_code == 200
        assert len(client.get('/api/projects').json()) == 1


def test_cleanup_never_deletes_files_outside_upload_directory(tmp_path):
    database, storage = tmp_path / 'app.db', tmp_path / 'uploads'
    protected = tmp_path / 'keep.txt'
    protected.write_text('keep')
    store = Store(database)
    project = Project(project_id='p', name='p', created_at=now())
    store.add('project', 'p', 'p', project)
    asset = AssetVersion(asset_version_id='a', project_id='p', original_filename='a',
                         storage_name='../keep.txt', image_url='', sha256='x', width=1, height=1, created_at=now())
    store.add('asset', 'a', 'p', asset)
    with TestClient(create_app(database_path=database, storage_path=storage)) as client:
        assert client.delete('/api/projects/p').json()['file_cleanup_pending']
        assert protected.read_text() == 'keep'
