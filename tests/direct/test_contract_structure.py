import ast
from pathlib import Path


ROOT = Path(__file__).parents[2]
HUB = ROOT / "contracts" / "noema_hub.py"
WITNESS = ROOT / "contracts" / "source_witness.py"
ENGINE = ROOT / "contracts" / "verdict_engine.py"


def contract_methods(path: Path, class_name: str) -> set[str]:
    tree = ast.parse(path.read_text())
    contract = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == class_name)
    return {node.name for node in contract.body if isinstance(node, ast.FunctionDef)}


def test_hub_exposes_complete_recovery_and_economic_lifecycle():
    methods = contract_methods(HUB, "NoemaHub")
    assert {"open_dossier", "seal_disclosure", "disclose", "record_attestation", "record_verdict",
            "expire_disclosure", "expire_stage", "expire_dossier", "withdraw", "get_stats"} <= methods


def test_workers_are_bound_and_callbacks_are_authenticated():
    hub = HUB.read_text()
    witness = WITNESS.read_text()
    engine = ENGINE.read_text()
    assert "witness callback only" in hub and "engine callback only" in hub
    assert "only the bound hub" in witness and "only the bound hub" in engine
    assert "self.bootstrapper = \"\"" in hub


def test_provenance_and_closure_consensus_fields_are_code_level_invariants():
    witness = WITNESS.read_text()
    engine = ENGINE.read_text()
    for field in ("content_digest", "http_status", "publisher", "canonical_url", "published_at"):
        assert field in witness
    for field in ("manifest_root", "decisive_ids", "basis_digest", "outcome", "sufficient"):
        assert field in engine


def test_bounds_and_timeout_rollback_are_explicit():
    hub = HUB.read_text()
    assert "MAX_LIFETIME_SUBMISSIONS = 72" in hub
    assert "MAX_EVIDENCE = 18" in hub
    assert 'item["id"] != submission["id"]' in hub
    assert '"INCONCLUSIVE_TIMEOUT"' in hub
