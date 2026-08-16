import importlib.util
import sys
import tempfile
from pathlib import Path

GATE_PATH = Path("/home/ubuntu/apex-spiral/maintenance/experience_memory/cycle169/watermark_store.py")


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


WS = _load("experience_memory_watermark_store_cycle169", GATE_PATH)


def _make_watermark(seq):
    prev = "0" * 64 if seq == 1 else ("%064x" % (seq - 1))
    cur = "%064x" % seq
    return cur, prev


def test_in_memory_store_basic_monotonic():
    m = WS.InMemoryWatermarkStore()
    cur1, prev1 = _make_watermark(1)
    e1 = m.put_watermark(chain_id="a", seq=1, checkpoint_sha256=cur1, prev_checkpoint_sha256=prev1, written_at="t1")
    assert e1.chain_id == "a" and e1.seq == 1 and e1.checkpoint_sha256 == cur1
    v = m.get_watermark(chain_id="a")
    assert v.seq == 1 and v.checkpoint_sha256 == cur1 and v.entry_count == 1 and v.backend_append_only is False
    assert len(m.audit_trail(chain_id="a")) == 1
    assert m.is_append_only() is False


def test_file_append_only_store_persists_and_reconciles():
    with tempfile.TemporaryDirectory() as td:
        s = WS.FileAppendOnlyWatermarkStore(root_dir=td)
        assert s.is_append_only() is True
        for seq in (1, 2, 3):
            cur, prev = _make_watermark(seq)
            s.put_watermark(chain_id="b", seq=seq, checkpoint_sha256=cur, prev_checkpoint_sha256=prev, written_at=f"t{seq}")
        v = s.get_watermark(chain_id="b")
        cur3, _ = _make_watermark(3)
        assert v.seq == 3 and v.checkpoint_sha256 == cur3 and v.entry_count == 3 and v.backend_append_only is True
        audit = s.audit_trail(chain_id="b")
        assert [e.seq for e in audit] == [1, 2, 3]
        assert audit[-1].checkpoint_sha256 == cur3
        c1 = WS.canonical_entry(audit[-1])
        assert isinstance(c1, bytes) and c1 == WS.canonical_entry(audit[-1])
        s.close()


def test_chain_isolation_between_stores():
    m = WS.InMemoryWatermarkStore()
    cur1, prev1 = _make_watermark(1)
    m.put_watermark(chain_id="x", seq=1, checkpoint_sha256=cur1, prev_checkpoint_sha256=prev1, written_at="t1")
    v = m.get_watermark(chain_id="y")
    assert v.seq == 0 and v.entry_count == 0 and v.checkpoint_sha256 == ("0" * 64) and v.backend_append_only is False
    assert m.audit_trail(chain_id="y") == ()


def test_sequence_not_monotonic_rejected():
    m = WS.InMemoryWatermarkStore()
    cur1, prev1 = _make_watermark(1)
    cur2, prev2 = _make_watermark(2)
    m.put_watermark(chain_id="seq", seq=1, checkpoint_sha256=cur1, prev_checkpoint_sha256=prev1, written_at="t1")
    raised = False
    try:
        m.put_watermark(chain_id="seq", seq=5, checkpoint_sha256=cur2, prev_checkpoint_sha256=prev2, written_at="t5")
    except WS.SequenceNotMonotonic:
        raised = True
    assert raised, "SequenceNotMonotonic not raised"


def test_prev_checkpoint_sha256_mismatch_rejected():
    m = WS.InMemoryWatermarkStore()
    cur1, prev1 = _make_watermark(1)
    cur2, prev2 = _make_watermark(2)
    m.put_watermark(chain_id="m", seq=1, checkpoint_sha256=cur1, prev_checkpoint_sha256=prev1, written_at="t1")
    raised = False
    try:
        m.put_watermark(chain_id="m", seq=2, checkpoint_sha256=cur2, prev_checkpoint_sha256=cur2, written_at="t2")
    except WS.PayloadMismatch:
        raised = True
    assert raised, "PayloadMismatch not raised"


def test_view_to_trusted_watermark_shape_matches_cycle168():
    m = WS.InMemoryWatermarkStore()
    cur1, prev1 = _make_watermark(1)
    m.put_watermark(chain_id="v", seq=1, checkpoint_sha256=cur1, prev_checkpoint_sha256=prev1, written_at="t1")
    v = m.get_watermark(chain_id="v")
    tw = WS.view_to_trusted_watermark(v)
    assert set(tw.keys()) >= {"seq", "checkpoint_sha256", "entry_count", "backend_name", "backend_append_only"}
    assert tw["seq"] == 1 and tw["checkpoint_sha256"] == cur1 and tw["entry_count"] == 1
    assert tw["backend_append_only"] is False
    assert isinstance(tw["backend_name"], str) and tw["backend_name"]


def test_audit_trail_past_entries_immutable_via_canonical_bytes():
    m = WS.InMemoryWatermarkStore()
    cur1, prev1 = _make_watermark(1)
    cur2, prev2 = _make_watermark(2)
    m.put_watermark(chain_id="i", seq=1, checkpoint_sha256=cur1, prev_checkpoint_sha256=prev1, written_at="t1")
    audit_after_1 = list(m.audit_trail(chain_id="i"))
    m.put_watermark(chain_id="i", seq=2, checkpoint_sha256=cur2, prev_checkpoint_sha256=prev2, written_at="t2")
    audit_after_2 = m.audit_trail(chain_id="i")
    assert WS.canonical_entry(audit_after_1[0]) == WS.canonical_entry(audit_after_2[0])
    raised = False
    try:
        audit_after_2[0].seq = 999
    except Exception as exc:
        raised = "frozen" in str(exc).lower() or "assign" in str(exc).lower()
    assert raised, "frozen dataclass accepted mutation"


def test_file_append_only_store_rejects_mid_stream_truncation():
    with tempfile.TemporaryDirectory() as td:
        s = WS.FileAppendOnlyWatermarkStore(root_dir=td)
        cur1, prev1 = _make_watermark(1)
        s.put_watermark(chain_id="t", seq=1, checkpoint_sha256=cur1, prev_checkpoint_sha256=prev1, written_at="t1")
        s.close()
        files = list(Path(td).glob("t.log"))
        assert len(files) == 1
        p = files[0]
        good = p.read_bytes()
        p.write_bytes(good[: len(good) // 2])
        s2 = WS.FileAppendOnlyWatermarkStore(root_dir=td)
        raised = False
        try:
            s2.get_watermark(chain_id="t")
        except WS.PayloadMismatch as exc:
            raised = "truncat" in str(exc).lower() or "json" in str(exc).lower()
        assert raised, "truncated file was accepted silently"
        s2.close()


def test_promotion_allowed_always_false_in_cycle169():
    m = WS.InMemoryWatermarkStore()
    cur1, prev1 = _make_watermark(1)
    m.put_watermark(chain_id="c", seq=1, checkpoint_sha256=cur1, prev_checkpoint_sha256=prev1, written_at="t1")
    rep = WS.verify_promotion_allowed(m, chain_id="c")
    assert rep["decision"] == "candidate_hold"
    assert rep["promotion_allowed"] is False
    assert rep["writes_active_memory"] is False
    assert rep["writes_production_state"] is False
    assert rep["status"] == "candidate_hold"


def test_in_memory_and_file_stores_round_trip_consistently():
    with tempfile.TemporaryDirectory() as td:
        inmem = WS.InMemoryWatermarkStore()
        fstore = WS.FileAppendOnlyWatermarkStore(root_dir=td)
        for seq in (1, 2, 3):
            prev = "0" * 64 if seq == 1 else ("%064x" % (seq - 1))
            cur = "%064x" % seq
            for store in (inmem, fstore):
                store.put_watermark(chain_id="same", seq=seq, checkpoint_sha256=cur, prev_checkpoint_sha256=prev, written_at=f"t{seq}")
        v_m = inmem.get_watermark(chain_id="same")
        v_f = fstore.get_watermark(chain_id="same")
        cur3 = "%064x" % 3
        assert v_m.seq == v_f.seq == 3
        assert v_m.checkpoint_sha256 == v_f.checkpoint_sha256 == cur3
        assert v_m.entry_count == v_f.entry_count == 3
        assert v_m.backend_append_only is False and v_f.backend_append_only is True
        assert v_m.backend_name != v_f.backend_name
        fstore.close()
