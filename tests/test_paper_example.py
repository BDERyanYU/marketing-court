from fastapi.testclient import TestClient

from backend.app.jury.demo import DemoProvider
from backend.app.jury.examples import PAPER_REPORT, PAPER_ORIGINAL, PAPER_REVISED
from backend.app.jury.main import create_app


def test_paper_example_full_flow_is_grounded_and_separate_from_bottle(tmp_path):
    path = tmp_path / 'jury.db'
    with TestClient(create_app(database_path=path, provider=DemoProvider())) as client:
        sample = client.get('/api/jury/examples/copier-paper').json()
        assert sample['report_text'] == PAPER_REPORT
        assert sample['original_text'] == PAPER_ORIGINAL
        assert '(5 Rivers)' in sample['original_text']
        assert sample['revised_text'] == PAPER_REVISED
        assert 'Blue Angel' in sample['revised_text']
        assert client.get('/api/jury/examples/unknown').status_code == 404
        report = client.post('/api/jury/reports', files={'file': (sample['filename'], sample['report_text'].encode())})
        assert report.status_code == 201, report.text
        report = report.json()
        assert len(report['personas']) == 4
        assert all(t['source_quote'] in PAPER_REPORT for p in report['personas'] for t in p['traits'])
        panel = client.post('/api/jury/panels', json={'report_id': report['report_id'], 'member_count': 2})
        assert panel.status_code == 201, panel.text
        panel = panel.json()
        assert len(panel['members']) == 2
        assert '复印纸' in str(panel['members'])
        assert '通勤' not in str(panel['members'])
        bottle = client.get('/api/jury/demo').json()
        base = {'panel_id': panel['panel_id']}
        assert client.post('/api/jury/comparisons', json={**base, 'original_text': bottle['original_text'], 'revised_text': bottle['revised_text']}).status_code == 409
        result = client.post('/api/jury/comparisons', json={**base, 'original_text': PAPER_ORIGINAL, 'revised_text': PAPER_REVISED})
        assert result.status_code == 201, result.text
        result = result.json()
        url = '/api/jury/comparisons/' + result['comparison_id']
        while result['next_index'] is not None:
            advanced = client.post(url + '/advance-members', json={'expected_index': result['next_index']})
            assert advanced.status_code == 200, advanced.text
            result = advanced.json()
        assert len(result['pairs']) == 2
        assert '纸' in str(result['pairs'])
        assert '水杯' not in str(result['pairs'])
    with TestClient(create_app(database_path=path, provider=DemoProvider())) as client:
        assert client.get(url).json() == result
