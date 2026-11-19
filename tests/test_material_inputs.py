import pytest
from fastapi.testclient import TestClient

from backend.app.main import create_app
from tests.test_review_api import OCR, Provider, png


def finished_review(client, asset):
    response = client.post(f'/api/assets/{asset["asset_version_id"]}/reviews')
    assert response.status_code == 202, response.text
    task = client.get(f'/api/tasks/{response.json()["task_id"]}').json()
    assert task["status"] == "completed", task
    return client.get(f'/api/reviews/{task["result_id"]}').json()


def test_one_project_accepts_image_text_and_combined_and_restores(tmp_path):
    database = tmp_path / "app.db"
    ocr = OCR()
    provider = Provider()
    with TestClient(create_app(database_path=database, provider=provider, ocr=ocr)) as client:
        project = client.post('/api/projects', json={"name": "Mixed campaign", "product_category": "electronics"}).json()
        endpoint = f'/api/projects/{project["project_id"]}/assets'
        image = client.post(endpoint, files={"file": ("ad.png", png(), "image/png")}).json()
        text = client.post(endpoint, data={"text": "100% Eco-Friendly. Text only."}).json()
        both = client.post(endpoint, files={"file": ("ad.png", png(), "image/png")},
                           data={"text": "100% Eco-Friendly. Extra product description."}).json()
        assert [a['kind'] for a in [image, text, both]] == ['image', 'text', 'image']
        reviews = [finished_review(client, a) for a in [image, text, both]]
        assert ocr.calls == 2  # Text-only never initializes or invokes OCR.
        assert [r['risks'][0]['input_origin'] for r in reviews] == ['image', 'text', 'both']
        assert reviews[1]['anchors'] == [] and reviews[1]['risks'][0]['anchor_ids'] == []
        assert reviews[2]['image_text'] == '100% Eco-Friendly.\nMeet the Everyday Bottle.'
        assert reviews[2]['supplied_text'] == both['text']
        assert both['text'] in reviews[2]['original_text']
        assert all(r['product_category'] == 'electronics' for r in reviews)
        for review in reviews[1:]:
            risk_id = review['risks'][0]['risk_id']
            task = client.post(f'/api/reviews/{review["review_id"]}/risks/{risk_id}/rewrite').json()
            done = client.get(f'/api/tasks/{task["task_id"]}').json()
            assert done['status'] == 'completed', done
            rewrite = client.get(f'/api/rewrites/{done["result_id"]}').json()
            assert rewrite['revised_text'].count('Eco-Friendly') == review['original_text'].count('Eco-Friendly') - 1
            recheck = client.get(f'/api/reviews/{rewrite["review_id"]}').json()
            assert len(recheck['risks']) == (1 if review['supplied_text'] and review['image_text'] else 0)
            assert client.get(f'/api/reviews/{review["review_id"]}').json() == review
            assert client.post(f'/api/risks/{risk_id}/appeals').status_code == 201
    with TestClient(create_app(database_path=database, provider=Provider(), ocr=OCR())) as client:
        saved = client.get(f'/api/projects/{project["project_id"]}/reviews').json()
        assert len(saved) == 5  # Three originals plus two separate rechecks.
        report = client.get(f'/api/reviews/{reviews[2]["review_id"]}/report').json()
        assert report['asset']['text'] == both['text']
        assert report['review']['supplied_text'] == both['text']
        assert report['review']['image_text'] == reviews[2]['image_text']
        assert report['project']['product_category'] == 'electronics'
        assert report['rewrites'] and report['court_cases']


@pytest.mark.parametrize('market', ['EU', 'US', 'CA', 'AU', 'CN', 'JP', 'KR', 'SG'])
def test_uncovered_market_preserves_context_without_a_risk_verdict(tmp_path, market):
    class ContextProvider(Provider):
        def complete(self, **kwargs):
            assert kwargs['context']['market'] == market
            assert kwargs['context']['product_category'] == 'beauty'
            return super().complete(**kwargs)

    provider = ContextProvider()
    with TestClient(create_app(database_path=tmp_path / 'app.db', provider=provider)) as client:
        project = client.post('/api/projects', json={'name': market, 'market': market, 'product_category': 'beauty'}).json()
        asset = client.post(f'/api/projects/{project["project_id"]}/assets', data={'text': '100% Eco-Friendly.'}).json()
        review = finished_review(client, asset)
        assert review['coverage_status'] == 'unsupported' and review['rule_pack_version'] == 'none'
        assert review['sources'] == [] and review['risks'] == [] and review['claims']
        assert review['market'] == market and review['product_category'] == 'beauty'
        assert provider.calls == ['claim_extraction']
        report = client.get(f'/api/reviews/{review["review_id"]}/report').json()
        assert report['project']['market'] == market
        assert report['review']['coverage_status'] == 'unsupported'


def test_material_validation_and_text_claim_cannot_get_image_coordinates(tmp_path):
    provider = Provider()
    provider.claim = '100% Eco-Friendly. Supplied text only.'
    with TestClient(create_app(database_path=tmp_path / 'app.db', provider=provider, ocr=OCR())) as client:
        project = client.post('/api/projects', json={'name': 'Validation'}).json()
        endpoint = f'/api/projects/{project["project_id"]}/assets'
        assert client.post(endpoint).status_code == 422
        assert client.post(endpoint, data={'text': '   '}).status_code == 422
        assert client.post(endpoint, data={'text': 'x' * 8001}).status_code == 422
        assert client.post(endpoint, files={'file': ('bad.png', b'invalid', 'image/png')}, data={'text': 'valid'}).status_code == 415
        assert client.post('/api/projects', json={'name': 'Unknown', 'market': 'XX'}).status_code == 422
        asset = client.post(endpoint, files={'file': ('ad.png', png(), 'image/png')},
                            data={'text': provider.claim}).json()
        review = finished_review(client, asset)
        assert review['risks'][0]['input_origin'] == 'text'
        assert review['risks'][0]['anchor_ids'] == []
        assert review['risks'][0]['location_status'] == 'needs_confirmation'
