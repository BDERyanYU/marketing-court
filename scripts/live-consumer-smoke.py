"""Opt-in real-model check of the native factory and paired reactions."""
import argparse
import json
from pathlib import Path

import httpx


def main(url):
    def checked(response):
        response.raise_for_status()
        return response.json()

    with httpx.Client(base_url=url, timeout=600) as client:
        sample = checked(client.get('/api/jury/demo'))
        if sample['mode'] != 'live':
            raise RuntimeError('This exercise requires live consumer simulation.')
        report = checked(client.post('/api/jury/reports', files={
            'file': ('bottle-research.txt', sample['report_text'].encode('utf-8'), 'text/plain')}))
        print('Real report extraction completed.', flush=True)
        panel = checked(client.post('/api/jury/panels', json={
            'report_id': report['report_id'], 'member_count': 1}))
        assert len(panel['members']) == 1 and panel['members'][0]['specification']['type'] == 'TinyPerson'
        assert panel['theories'] and panel['tinytroupe_plan']
        print('Real TinyTroupe native persona and marketing knowledge integration completed.', flush=True)
        comparison = checked(client.post('/api/jury/comparisons', json={
            'panel_id': panel['panel_id'], 'original_text': sample['original_text'], 'revised_text': sample['revised_text']}))
        comparison = checked(client.post(f'/api/jury/comparisons/{comparison["comparison_id"]}/advance-members',
                                         json={'expected_index': comparison['next_index']}))
        assert comparison['next_index'] is None and len(comparison['exposures']) == 2 and len(comparison['pairs']) == 1
        assert checked(client.get(f'/api/jury/comparisons/{comparison["comparison_id"]}')) == comparison
        target = Path('test-results/live-consumer-integration.json')
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps({'report': report, 'panel': panel, 'comparison': comparison},
                                     ensure_ascii=False, indent=2), encoding='utf-8')
        print('Real isolated A/B reactions and saved comparison completed.', flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--url', default='http://127.0.0.1:8020')
    main(parser.parse_args().url)
