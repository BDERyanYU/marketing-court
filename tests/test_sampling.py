from collections import Counter
from itertools import product

import pytest
from fastapi.testclient import TestClient

from backend.app.jury.demo import DemoProvider
from backend.app.jury.main import create_app


def sample_report(client):
    example = client.get("/api/jury/demo").raise_for_status().json()
    report = client.post("/api/jury/reports", files={
        "file": ("research.txt", example["report_text"].encode()),
    }).raise_for_status().json()
    return example, {
        "report_id": report["report_id"],
        "persona_id": report["personas"][0]["persona_id"],
    }


def panel_for(client, base, **sampling):
    response = client.post("/api/jury/panels", json={
        **base, "member_count": 4, "sampling": sampling,
    })
    assert response.status_code == 201, response.text
    return response.json()


def test_default_panel_applies_tinytroupe_joint_quotas_and_saves_the_plan(tmp_path, monkeypatch):
    monkeypatch.setenv("JURY_MODE", "demo")
    database = tmp_path / "sampling.db"
    with TestClient(create_app(database_path=database)) as client:
        _, base = sample_report(client)
        response = client.post("/api/jury/panels", json={"report_id": base["report_id"], "member_count": 3})
        panel = response.raise_for_status().json()
        derivation = panel["tinytroupe_plan"]
        assert derivation["source_commit"].startswith("7ce8be3")
        assert len(derivation["sampling_space"]["dimensions"]) == 2
        counts = Counter(tuple(sorted(member["sampled_values"].items())) for member in panel["members"])
        assert counts == {
            tuple(sorted(group["sampled_values"].items())): group["quantity"]
            for group in derivation["sample_plan"]
        }
        assert sorted(counts.values()) == [1, 2]
        assert len({member["member_id"] for member in panel["members"]}) == 3
        assert panel["base_persona"] is None
        assert panel["theories"] == []
        for member in panel["members"]:
            specification = member["specification"]
            assert specification["type"] == "TinyPerson"
            assert specification["persona"]["personality"]["big_five"]
            assert specification["persona"]["behaviors"]["routines"]
            assert "persona_prompt" not in member

    with TestClient(create_app(database_path=database)) as client:
        assert client.get("/api/jury/panels/" + panel["panel_id"]).raise_for_status().json() == panel


def test_full_sampling_keeps_all_crossed_choices_and_feeds_blind_voting(tmp_path, monkeypatch):
    class RecordingDemo(DemoProvider):
        def __init__(self):
            self.reactions = []

        def complete(self, *, step, instruction, context, output):
            if step == "jury_reaction":
                self.reactions.append(context["member"])
            return super().complete(step=step, instruction=instruction, context=context, output=output)

    monkeypatch.setenv("JURY_MODE", "demo")
    provider = RecordingDemo()
    app = create_app(database_path=tmp_path / "sampling.db", provider=provider)
    with TestClient(app) as client:
        sample, base = sample_report(client)
        panel = panel_for(client, base, mode="full", seed=19)
        expected = set(product(("地铁灯箱", "商品详情页", "手机信息流"), ("低", "中", "高")))
        combinations = {
            (member["sampled_values"]["接触渠道"], member["sampled_values"]["证据关注度"])
            for member in panel["members"]
        }
        assert len(panel["members"]) == len(expected) == 9
        assert combinations == expected
        assert panel["sampling"]["seed"] == 19
        assert client.get("/api/jury/panels/" + panel["panel_id"]).raise_for_status().json() == panel

        comparison = client.post("/api/jury/comparisons", json={
            "panel_id": panel["panel_id"], "original_text": sample["original_text"],
            "revised_text": sample["revised_text"],
        }).raise_for_status().json()
        path = f"/api/jury/comparisons/{comparison['comparison_id']}/advance"
        for index in range(18):
            comparison = client.post(path, json={"expected_index": index}).raise_for_status().json()
        assert comparison["next_index"] is None
        assert [pair["member_id"] for pair in comparison["pairs"]] == [m["member_id"] for m in panel["members"]]
        assert sum(comparison["vote_counts"]["A"].values()) == sum(comparison["vote_counts"]["B"].values()) == 9
        for index, member in enumerate(panel["members"]):
            left, right = provider.reactions[2 * index:2 * index + 2]
            assert left == right
            assert left["sampled_conditions"] == [
                {"name": "接触渠道", "kind": "exposure", "value": member["sampled_values"]["接触渠道"]},
                {"name": "证据关注度", "kind": "trait", "value": member["sampled_values"]["证据关注度"]},
            ]


def test_random_sampling_repeats_fixed_choices_with_a_seed(tmp_path, monkeypatch):
    monkeypatch.setenv("JURY_MODE", "demo")
    app = create_app(database_path=tmp_path / "sampling.db")
    with TestClient(app) as client:
        _, base = sample_report(client)
        first = panel_for(client, base, mode="random", seed=27)
        second = panel_for(client, base, mode="random", seed=27)
        assert first["sampling"] == second["sampling"]
        selections = [m["sampled_values"] for m in first["members"]]
        assert selections == [m["sampled_values"] for m in second["members"]]
        assert len({tuple(sorted(values.items())) for values in selections}) == 4


@pytest.mark.parametrize("member_count", [1, 6])
def test_user_controls_the_native_panel_size(tmp_path, member_count):
    app = create_app(database_path=tmp_path / "sampling.db", provider=DemoProvider())
    with TestClient(app) as client:
        _, base = sample_report(client)
        panel = client.post("/api/jury/panels", json={
            "report_id": base["report_id"], "member_count": member_count,
        }).raise_for_status().json()
    assert len(panel["members"]) == member_count
    assert sum(group["quantity"] for group in panel["tinytroupe_plan"]["sample_plan"]) == member_count
