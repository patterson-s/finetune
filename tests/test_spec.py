"""Tests for the task-spec loader (finetune/spec.py)."""
import pytest

from finetune.spec import TaskSpec, load_tasks


def test_load_tasks_returns_dict():
    tasks = load_tasks()
    assert isinstance(tasks, dict)
    # All 5 tasks from configs/tasks.yaml present
    assert "education_extraction" in tasks
    assert "org_harmonization" in tasks
    assert "fec_hierarchical_classification" in tasks


def test_task_spec_has_required_fields():
    tasks = load_tasks()
    edu = tasks["education_extraction"]
    assert isinstance(edu, TaskSpec)
    assert edu.id == "education_extraction"
    assert edu.name
    assert edu.tier == 1
    # model_tiers with cloud + jetson
    assert edu.model_tiers["cloud"]
    assert edu.model_tiers["jetson"]
    # gold_source with path
    assert edu.gold_source["path"]


def test_all_tasks_are_valid_specs():
    tasks = load_tasks()
    for task in tasks.values():
        assert isinstance(task, TaskSpec)
        assert task.id
        assert task.name
        assert isinstance(task.tier, int)
        # Active/planned tiers (1,2) must specify model tiers; backburner (3) may not yet
        if task.tier <= 2:
            assert task.model_tiers.get("cloud")
            assert task.model_tiers.get("jetson")


def test_backburner_tasks_flagged():
    tasks = load_tasks()
    assert tasks["fec_hierarchical_classification"].tier == 3
    assert tasks["pydeal_type_classification"].tier == 3
