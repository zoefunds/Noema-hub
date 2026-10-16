"""Deterministic protocol helpers shared by contracts and direct tests."""

import hashlib
import json
import re
from urllib.parse import urlsplit, urlunsplit

MAX_BASELINE = 4
MAX_ACTIVE = 24
MAX_EVIDENCE = 18
MAX_LIFETIME_SUBMISSIONS = 72
MAX_DECISIVE_IDS = 12


def canonical_json(value) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def digest_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def normalize_url(value: str) -> str:
    if not isinstance(value, str) or len(value) > 900:
        raise ValueError("invalid URL")
    parts = urlsplit(value.strip())
    if parts.scheme != "https" or not parts.hostname or parts.username or parts.password:
        raise ValueError("only credential-free HTTPS URLs are accepted")
    host = parts.hostname.lower()
    port = parts.port
    netloc = host if port in (None, 443) else f"{host}:{port}"
    path = re.sub(r"/{2,}", "/", parts.path or "/")
    return urlunsplit(("https", netloc, path, parts.query, ""))


def evidence_key(dossier_id: str, url: str, claim: str) -> str:
    return digest_text(canonical_json({
        "dossier_id": dossier_id,
        "url": normalize_url(url),
        "claim_digest": digest_text(claim.strip()),
    }))


def commitment_for(chain_id: str, hub: str, dossier_id: str, researcher: str,
                   url: str, claim: str, salt: str) -> str:
    return digest_text(canonical_json({
        "domain": "NOEMA_DISCLOSURE_V1",
        "chain_id": chain_id,
        "hub": hub.lower(),
        "dossier_id": dossier_id,
        "researcher": researcher.lower(),
        "url": normalize_url(url),
        "claim": claim.strip(),
        "salt": salt,
    }))


def manifest_root(items: list[dict]) -> str:
    leaves = [digest_text(canonical_json({
        "id": item["id"],
        "claim_digest": item["claim_digest"],
        "content_digest": item["content_digest"],
        "source_host": item["source_host"],
    })) for item in items]
    return digest_text(canonical_json(leaves))


def validate_decision(result: dict, valid_ids: set[str]) -> dict:
    outcome = result.get("outcome")
    if outcome not in ("POSITION_A", "POSITION_B", "UNRESOLVED"):
        raise ValueError("unknown outcome")
    ids = result.get("decisive_ids")
    if not isinstance(ids, list) or len(ids) > MAX_DECISIVE_IDS:
        raise ValueError("invalid decisive ids")
    clean = []
    for item in ids:
        if not isinstance(item, str) or item not in valid_ids or item in clean:
            raise ValueError("decisive id is absent or duplicated")
        clean.append(item)
    if outcome == "UNRESOLVED" and clean:
        raise ValueError("an unresolved decision cannot name decisive evidence")
    if outcome != "UNRESOLVED" and not clean:
        raise ValueError("a resolved decision must name decisive evidence")
    basis = result.get("basis")
    if not isinstance(basis, str) or not basis.strip() or len(basis) > 1200:
        raise ValueError("invalid basis")
    return {"outcome": outcome, "decisive_ids": clean, "basis": basis.strip()}
