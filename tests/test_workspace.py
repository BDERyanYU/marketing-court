from concurrent.futures import ThreadPoolExecutor
from threading import Event

from fastapi.testclient import TestClient

from backend.app.core.llm import ModelError
from backend.app.core.store import Store
from backend.app.services.review_demo import DemoProvider
from backend.app.main import create_app
from backend.app.models.workspace import Meeting
from backend.app.services.workspace import upsert
from tests.test_review_api import OCR, Provider, reviewed


def demo_meeting(client, **updates):
    review = client.post('/api/demo').json()
    payload = dict(review_id=review['review_id'], title='环保承诺修改方向',
                   issue_ids=[review['risks'][0]['risk_id']], roles=['consumer', 'legal'],
                   trigger='disputed', goal='direction')
    payload.update(updates)
    return client.post(f'/api/workspace/projects/{review["project_id"]}/meetings', json=payload)


def persona(client):
    return client.post('/api/workspace/personas', json=dict(name='谨慎的环保消费者',
        summary='希望清楚理解环保范围，尚未经真实受众验证。', needs=['可核查的说明'], concerns=['绝对化表述'])).json()


def test_persona_versions_project_context_meeting_writeback_and_restart(tmp_path):
    database = tmp_path / 'app.db'
    with TestClient(create_app(database_path=database, provider=DemoProvider())) as client:
        review = client.post('/api/demo').json()
        project_id = review['project_id']
        audience = persona(client)
        version = client.post(f'/api/workspace/personas/{audience["persona_id"]}/versions', json=dict(
            name='谨慎的环保消费者 v2', summary='人工更新的假设', market='GB', needs=['证明材料'], concerns=[])).json()
        assert version['version'] == 2 and version['family_id'] == audience['family_id']
        assert len(client.get('/api/workspace/personas').json()) == 2
        context = dict(persona_ids=[audience['persona_id']], brand_notes='只能使用有依据的产品事实',
                       market_notes='需核查当地语言理解', language='英语', archived=False)
        assert client.put(f'/api/workspace/projects/{project_id}/context', json=context).status_code == 200
        response = demo_meeting(client)
        assert response.status_code == 201, response.text
        meeting = response.json()
        assert meeting['personas'][0]['persona_id'] == audience['persona_id']
        context['persona_ids'] = [version['persona_id']]
        client.put(f'/api/workspace/projects/{project_id}/context', json=context)
        assert client.get(f'/api/workspace/meetings/{meeting["meeting_id"]}').json()['personas'][0] == audience
        advance = f'/api/workspace/meetings/{meeting["meeting_id"]}/advance'
        assert client.post(advance, json={'expected_index': 1}).status_code == 409
        assert client.post(f'/api/workspace/meetings/{meeting["meeting_id"]}/writeback').status_code == 409
        first = client.post(advance, json={'expected_index': 0, 'instruction': '优先讨论证据范围'}).json()
        assert len(first['turns']) == 1
        assert client.post(advance, json={'expected_index': 0}).json() == first
    with TestClient(create_app(database_path=database, provider=DemoProvider())) as client:
        for index in range(1, 5):
            response = client.post(advance, json={'expected_index': index})
            assert response.status_code == 200, response.text
        finished = response.json()
        assert finished['status'] == 'completed' and len(finished['turns']) == 4 and finished['conclusion']
        assert client.post(advance, json={'expected_index': 4}).json() == finished
        endpoint = f'/api/workspace/meetings/{meeting["meeting_id"]}/writeback'
        addendum = client.post(endpoint).json()
        assert client.post(endpoint).json() == addendum
        report = client.get(f'/api/reviews/{review["review_id"]}/report').json()
        assert report['review'] == review  # Original assessment is immutable.
        assert report['roundtable_addenda'] == [addendum]
        assert client.post(f'/api/workspace/meetings/{meeting["meeting_id"]}/recheck', json={'text': 'Product details.'}).status_code == 409
        detail = client.get(f'/api/workspace/projects/{project_id}').json()
        assert detail['status'] == 'concluded'
        assert detail['addenda'] == [addendum]


def test_roundtable_rejects_cross_project_issues_duplicates_and_missing_review(tmp_path):
    with TestClient(create_app(database_path=tmp_path / 'app.db', provider=DemoProvider())) as client:
        assert demo_meeting(client, issue_ids=['unknown']).status_code == 422
        assert demo_meeting(client, roles=['legal', 'legal']).status_code == 422
        assert demo_meeting(client, roles=['unknown', 'legal']).status_code == 422
        assert demo_meeting(client, issue_ids=['demo-eco-bottle', 'demo-eco-bottle']).status_code == 422
        assert demo_meeting(client, review_id='unknown').status_code == 404
        other = client.post('/api/projects', json={'name': 'Other'}).json()
        result = client.post(f'/api/workspace/projects/{other["project_id"]}/meetings', json=dict(
            review_id='demo-review-1', title='No cross-project', issue_ids=['demo-eco-bottle'], roles=['legal', 'brand'], trigger='disputed'))
        assert result.status_code == 422
        assert client.put(f'/api/workspace/projects/{other["project_id"]}/context', json={'persona_ids': ['missing']}).status_code == 404
        assert client.post('/api/workspace/meetings/missing/advance', json={'expected_index': 0}).status_code == 404


class WorkspaceProvider(Provider):
    def __init__(self):
        super().__init__()
        self.bad_citation = False
        self.contexts = []

    def complete(self, **kwargs):
        step, context = kwargs['step'], kwargs['context']
        self.contexts.append((step, context))
        if step == 'roundtable_turn':
            return kwargs['output'](viewpoint='该表述需要与范围匹配的证明。', proposal='补证或删除该句。',
                                    vote='need_evidence', source_ids=['UNKNOWN' if self.bad_citation else 'G1'])
        if step == 'roundtable_conclusion':
            return kwargs['output'](consensus=['先补证'], disagreements=['暂无真实受众验证'], recommendations=['删除绝对化承诺'],
                                    todos=['复审'], risk_notes=['未批准投放'], revised_copy='Meet the Everyday Bottle.', source_ids=['G1'])
        if step == 'audience_fit':
            assert context['audience']['personas']
            return kwargs['output'](status='mixed', reason='表达方向契合，但证据不足。', suggestions=['收窄范围'])
        if step == 'persona_derivation':
            return kwargs['output'](name='派生消费者假设', summary='仅从文案推断的偏好，人口统计未知。', market='GB', needs=['证据'], concerns=[])
        return super().complete(**kwargs)


def test_live_context_snapshot_citations_failure_retry_and_roundtable_recheck(tmp_path):
    database = tmp_path / 'app.db'
    provider = WorkspaceProvider()
    with TestClient(create_app(database_path=database, provider=provider, ocr=OCR())) as client:
        review, task = reviewed(client)
        audience = persona(client)
        context = dict(persona_ids=[audience['persona_id']], brand_notes='实际品牌备注', market_notes='实际市场备注')
        client.put(f'/api/workspace/projects/{review["project_id"]}/context', json=context)
        meeting = client.post(f'/api/workspace/projects/{review["project_id"]}/meetings', json=dict(
            review_id=review['review_id'], title='Live meeting', issue_ids=[review['risks'][0]['risk_id']],
            roles=['consumer', 'legal'], trigger='high_risk', include_personas=False, include_market=False)).json()
        advance = f'/api/workspace/meetings/{meeting["meeting_id"]}/advance'
        provider.bad_citation = True
        assert client.post(advance, json={'expected_index': 0}).status_code == 502
        failed = client.get(f'/api/workspace/meetings/{meeting["meeting_id"]}').json()
        assert failed['turns'] == [] and failed['status'] == 'interrupted'
        provider.bad_citation = False
        for index in range(5):
            assert client.post(advance, json={'expected_index': index}).status_code == 200
        turn_context = next(c for s, c in provider.contexts if s == 'roundtable_turn')
        assert turn_context['personas'] == [] and turn_context['market'] is None and turn_context['project_context'] is None
        assert 'audience_context' not in turn_context['review']
        recheck = f'/api/workspace/meetings/{meeting["meeting_id"]}/recheck'
        task = client.post(recheck, json={'text': 'Meet the Everyday Bottle.'}).json()
        assert client.post(recheck, json={'text': 'Meet the Everyday Bottle.'}).json()['task_id'] == task['task_id']
        done = client.get(f'/api/tasks/{task["task_id"]}').json()
        assert done['status'] == 'completed', done
        report = client.get(f'/api/reviews/{done["result_id"]}').json()
        assert report['audience_context']['personas'][0]['persona_id'] == audience['persona_id']
        assert report['audience_fit']['status'] == 'mixed'
        new_asset = client.get(f'/api/assets/{report["asset_version_id"]}').json()
        assert new_asset['origin_meeting_id'] == meeting['meeting_id']
        assert client.get(f'/api/reviews/{review["review_id"]}').json() == review
        derived = client.post('/api/workspace/personas/derive/from-review', json={'project_id': review['project_id'], 'review_id': review['review_id']}).json()
        assert derived['provenance'] == 'inferred_from_material' and derived['source_review_id'] == review['review_id']


def test_restart_recovers_generating_meeting(tmp_path):
    database = tmp_path / 'app.db'
    with TestClient(create_app(database_path=database, provider=DemoProvider())) as client:
        meeting = Meeting.model_validate(demo_meeting(client).json())
    meeting.status = 'generating'
    upsert(Store(database), 'meeting', meeting.meeting_id, meeting.project_id, meeting)
    with TestClient(create_app(database_path=database, provider=DemoProvider())) as client:
        saved = client.get(f'/api/workspace/meetings/{meeting.meeting_id}').json()
        assert saved['status'] == 'interrupted'
        assert client.post(f'/api/workspace/meetings/{meeting.meeting_id}/advance', json={'expected_index': 0}).status_code == 200


def test_draft_feedback_archive_language_and_positive_report_topic(tmp_path):
    with TestClient(create_app(database_path=tmp_path / 'app.db', provider=DemoProvider())) as client:
        project = client.post('/api/projects', json={'name': 'Draft', 'channel': 'website'}).json()
        pid = project['project_id']
        assert client.get(f'/api/workspace/projects/{pid}').json()['status'] == 'draft'
        context = {'language': '英语 / English', 'archived': False}
        client.put(f'/api/workspace/projects/{pid}/context', json=context)
        asset = client.post(f'/api/projects/{pid}/assets', data={'text': 'Plain description.'}).json()
        assert asset['language'] == '英语 / English'
        review = client.post('/api/demo-cases/copier-paper').json()
        assert not review['risks'] and review['claims']
        decision = f'/api/workspace/reviews/{review["review_id"]}/decision'
        assert client.post(decision, json={'trigger': 'unsatisfied'}).status_code == 200
        detail = client.get(f'/api/workspace/projects/{review["project_id"]}').json()
        assert detail['decisions'][review['review_id']] == 'unsatisfied'
        response = client.post(f'/api/workspace/projects/{review["project_id"]}/meetings', json={
            'review_id': review['review_id'], 'title': '复核正面案例的覆盖边界',
            'issue_ids': [f'report:{review["review_id"]}'], 'roles': ['consumer', 'legal'], 'trigger': 'disputed'})
        assert response.status_code == 201, response.text


def test_concurrent_advance_spends_only_one_role_call(tmp_path):
    started, release = Event(), Event()

    class Slow(WorkspaceProvider):
        def complete(self, **kwargs):
            if kwargs['step'] == 'roundtable_turn':
                started.set()
                assert release.wait(5)
            return super().complete(**kwargs)

    provider = Slow()
    with TestClient(create_app(database_path=tmp_path / 'app.db', provider=provider)) as client:
        meeting = demo_meeting(client).json()
        endpoint = f'/api/workspace/meetings/{meeting["meeting_id"]}/advance'
        with ThreadPoolExecutor() as executor:
            first = executor.submit(client.post, endpoint, json={'expected_index': 0})
            assert started.wait(3)
            assert client.post(endpoint, json={'expected_index': 0}).status_code == 409
            release.set()
            assert len(first.result().json()['turns']) == 1
