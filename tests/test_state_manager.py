from state_manager import StateManager


def test_marks_and_reports_done(tmp_path):
    s = StateManager(tmp_path / "state.json")
    assert not s.is_done("Oleh")
    s.mark_done("Oleh", [{"link": "https://a.com"}])
    assert s.is_done("Oleh")
    assert s.get_results("Oleh") == [{"link": "https://a.com"}]


def test_persists_across_instances(tmp_path):
    path = tmp_path / "state.json"
    StateManager(path).mark_done("Maria", [{"link": "x"}])

    reloaded = StateManager(path)
    assert reloaded.is_done("Maria")
    assert reloaded.all_results() == {"Maria": [{"link": "x"}]}


def test_clear_removes_file(tmp_path):
    path = tmp_path / "state.json"
    s = StateManager(path)
    s.mark_done("Pavlo", [])
    s.clear()
    assert not path.exists()
    assert StateManager(path).all_results() == {}


def test_corrupt_file_starts_fresh(tmp_path):
    path = tmp_path / "state.json"
    path.write_text("{not valid json", encoding="utf-8")
    s = StateManager(path)
    assert s.all_results() == {}


def test_record_failure_counts_and_persists(tmp_path):
    path = tmp_path / "state.json"
    s = StateManager(path)
    assert s.record_failure("q") == 1
    assert s.record_failure("q") == 2
    # persists across instances
    assert StateManager(path).record_failure("q") == 3


def test_mark_done_clears_failures(tmp_path):
    path = tmp_path / "state.json"
    s = StateManager(path)
    s.record_failure("q")
    s.mark_done("q", [{"link": "x"}])
    # a fresh instance should see no lingering failure count for the query
    assert StateManager(path).record_failure("q") == 1
