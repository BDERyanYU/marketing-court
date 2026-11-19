"""Explicit real-model rehearsal for project context, roundtable and report writeback."""
import argparse
import json
import time
from pathlib import Path

import httpx


def checked(response):
    response.raise_for_status()
    return response.json()


def wait_review(client, task):
    deadline = time.monotonic() + 300
    retried = False
    while time.monotonic() < deadline:
        task = checked(client.get(f'/api/tasks/{task["task_id"]}'))
        if task['status'] == 'completed':
            return checked(client.get(f'/api/reviews/{task["result_id"]}'))
        if task['status'] in ('failed', 'interrupted'):
            if not retried and 'Could not contact DeepSeek' in (task['error'] or ''):
                retried = True
                checked(client.post(f'/api/tasks/{task["task_id"]}/retry'))
                continue
            raise RuntimeError(task['error'])
        time.sleep(1)
    raise TimeoutError('Review did not finish.')


def main(url, resume=False):
    with httpx.Client(base_url=url, timeout=120) as client:
        assert checked(client.get('/health'))['mode'] == 'live'
        if resume:
            projects = checked(client.get('/api/workspace/projects'))
            project = next(p['project'] for p in projects if p['project']['name'] == 'v3 真实圆桌闭环演练')
            detail = checked(client.get(f'/api/workspace/projects/{project["project_id"]}'))
            review = detail['reviews'][0]
        else:
            project = checked(client.post('/api/projects', json=dict(name='v3 真实圆桌闭环演练', channel='website')))
            asset = checked(client.post(f'/api/projects/{project["project_id"]}/assets', data={'text': '100% Eco-Friendly. Meet the Everyday Bottle.'}))
            review = wait_review(client, checked(client.post(f'/api/assets/{asset["asset_version_id"]}/reviews')))
        endpoint = f'/api/projects/{project["project_id"]}/assets'
        assert review['risks']
        print('Real text review completed.', flush=True)
        persona = checked(client.post('/api/workspace/personas/derive/from-review', json={'project_id': project['project_id'], 'review_id': review['review_id']}))
        assert persona['provenance'] == 'inferred_from_material'
        checked(client.put(f'/api/workspace/projects/{project["project_id"]}/context', json={
            'persona_ids': [persona['persona_id']], 'brand_notes': '演练只使用原文与现有证据，不能增加产品事实。', 'market_notes': '英国，独立站广告文字。'}))
        asset2 = checked(client.post(endpoint, data={'text': '100% Eco-Friendly. Meet the Everyday Bottle.'}))
        review2 = wait_review(client, checked(client.post(f'/api/assets/{asset2["asset_version_id"]}/reviews')))
        assert review2['audience_context']['personas'] and review2['audience_fit']
        print('Real persona derivation and contextual review completed.', flush=True)
        meeting = checked(client.post(f'/api/workspace/projects/{project["project_id"]}/meetings', json={
            'review_id': review2['review_id'], 'title': '收窄环保承诺并确定复审方向',
            'issue_ids': [review2['risks'][0]['risk_id']], 'roles': ['consumer', 'legal'], 'trigger': 'disputed', 'goal': 'copy'}))
        for index in range(5):
            meeting = checked(client.post(f'/api/workspace/meetings/{meeting["meeting_id"]}/advance', json={
                'expected_index': index, 'instruction': '请只根据已有产品事实与引用提出建议。' if index == 0 else ''}))
            print(f'Roundtable step {index + 1}/5 saved.', flush=True)
        assert meeting['status'] == 'completed' and len(meeting['turns']) == 4 and meeting['conclusion']
        checked(client.post(f'/api/workspace/meetings/{meeting["meeting_id"]}/writeback'))
        report = checked(client.get(f'/api/reviews/{review2["review_id"]}/report'))
        assert report['roundtable_addenda'] and report['review'] == review2
        # Submit an explicit fact-preserving deletion rather than accept unverified generated facts.
        rechecked = wait_review(client, checked(client.post(f'/api/workspace/meetings/{meeting["meeting_id"]}/recheck',
            json={'text': 'Meet the Everyday Bottle.'})))
        assert rechecked['project_id'] == project['project_id']
        target = Path(__file__).resolve().parents[1] / 'test-results' / 'v3-live-report.json'
        target.write_text(json.dumps({'report': report, 'meeting': meeting, 'recheck': rechecked}, ensure_ascii=False, indent=2), encoding='utf-8')
        print(f'Real project/persona/review/roundtable/writeback/recheck completed: {target}', flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--url', default='http://127.0.0.1:8000')
    parser.add_argument('--resume', action='store_true')
    args = parser.parse_args()
    main(args.url, args.resume)
