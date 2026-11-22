"""Noosphere v0 portable context source validator: not identity, memory hosting or authority.

Only explicit PUBLIC_SYNTHETIC project bundles can reach LOCAL_REVIEWABLE_SOURCE_ONLY.
Other classes HOLD without returning protected user content. This module never reads
ChatGPT memory, Brain/Palace/Play, connected accounts, or executes model prompts.
"""
from __future__ import annotations
from copy import deepcopy
from hashlib import sha256
import argparse
import json
import re
from pathlib import Path
from typing import Any

SCHEMA = "atlas.memory-bundle/v0"
HSN_DIGEST = "07533cf7a6b6f567259962bf73efee9b22b47cbacb429499787800e07864e5a6"
BUNDLE_FIELDS = frozenset({"schema_version", "bundle_id", "recorded_at", "subject", "context_summary", "ontology", "sources", "permissions", "provenance", "fork", "rehydration", "status"})
CONTRACT_FIELDS = frozenset({"schema_version", "contract_id", "bundle_schema", "allowed_reconstruction", "uncertainty_mandatory", "human_confirmation_required", "identity_claim", "source_rights_policy", "opt_out", "promotions", "disclosure"})


class ContinuityHold(ValueError):
    """Failed source/consent/correctness gate. No elevated host authority."""


def require(c: bool, code: str) -> None:
    if not c:
        raise ContinuityHold(code)


def string(s: Any) -> bool:
    return isinstance(s, str) and bool(s)


def exactsha(s: Any) -> bool:
    return isinstance(s, str) and re.fullmatch(r"[a-f0-9]{64}", s) is not None


def canonical_sha256(obj: Any) -> str:
    """Python-local canonical dump; explicitly NOT RFC 8785/JCS or a signature."""
    return sha256(json.dumps(obj,sort_keys=True,separators=(",",":"),ensure_ascii=False,allow_nan=False).encode("utf-8")).hexdigest()


def parse_text(s: str) -> Any:
    def unique_pairs(pairs):
        out = {}
        for k,v in pairs:
            if k in out: raise ContinuityHold("DUPLICATE_JSON_KEY")
            out[k]=v
        return out
    return json.loads(s, object_pairs_hook=unique_pairs, parse_constant=lambda _: (_ for _ in ()).throw(ContinuityHold("NONFINITE_JSON_NUMBER")))


def validate_bundle(raw: Any) -> dict[str, Any]:
    """Fail closed on wrong scope or claims; never return private source bodies."""
    require(type(raw) is dict and set(raw) == BUNDLE_FIELDS, "BUNDLE_FIELDS_INVALID")
    require(raw["schema_version"] == SCHEMA and raw["status"] == "CANDIDATE_NOT_CANON", "BUNDLE_SCHEMA_OR_STATUS_MISMATCH")
    require(string(raw["bundle_id"]) and re.fullmatch(r"[a-z][a-z0-9_-]{2,80}",raw["bundle_id"]) is not None, "BUNDLE_ID_INVALID")
    require(isinstance(raw["recorded_at"],str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}",raw["recorded_at"]) is not None, "DATE_INVALID")
    require(string(raw["context_summary"]) and len(raw["context_summary"]) <= 10000, "SUMMARY_INVALID")
    subject=raw["subject"]
    require(type(subject) is dict and set(subject)=={"kind","opaque_subject_id"}, "SUBJECT_FIELDS_INVALID")
    require(subject["kind"]=="PROJECT_SYNTHETIC" and string(subject["opaque_subject_id"]), "PRIVATE_OR_PERSONA_SUBJECT_HOLD")
    ontology=raw["ontology"]
    require(type(ontology) is dict and set(ontology)=={"registry","edition","digest_sha256","addresses"}, "ONTOLOGY_FIELDS_INVALID")
    require(ontology["registry"]=="ariadne-reader" and ontology["edition"]=="v0.7" and ontology["digest_sha256"]==HSN_DIGEST, "ONTOLOGY_EDITION_HOLD")
    require(type(ontology["addresses"]) is list and len(ontology["addresses"])<=12 and len(set(map(str,ontology["addresses"])))==len(ontology["addresses"]), "ONTOLOGY_ADDRESSES_INVALID")
    for a in ontology["addresses"]: require(isinstance(a,str) and re.fullmatch(r"H(?:0[1-9]|1[0-2])\.S(?:0[1-9]|1[0-2])\.N(?:0[1-9]|1[0-2])",a) is not None, "ONTOLOGY_ADDRESS_INVALID")
    sources=raw["sources"]
    require(type(sources) is list and 1<=len(sources)<=20, "SOURCES_MISSING")
    ref_ids=set()
    for source in sources:
        require(type(source) is dict and set(source)=={"ref","sha256","scope","source_status","authorship"}, "SOURCE_FIELDS_INVALID")
        require(string(source["ref"]) and source["ref"].startswith("synthetic://") and len(source["ref"])<=200, "NONPUBLIC_OR_UNVERIFIED_REF_HOLD")
        require(source["ref"] not in ref_ids and exactsha(source["sha256"]), "DUPLICATE_OR_UNHASHED_SOURCE")
        ref_ids.add(source["ref"])
        require(source["scope"]=="PUBLIC_SYNTHETIC" and source["source_status"]=="SOURCE_POINTER_ONLY" and source["authorship"]=="SELF_DECLARED", "SOURCE_AUTHORITY_OR_SCOPE_HOLD")
    perms=raw["permissions"]
    require(type(perms) is dict and set(perms)=={"data_class","allowed_purposes","read_grant","return_grant","revocation_epoch","public_release_authorized"}, "PERMISSIONS_FIELDS_INVALID")
    require(perms["data_class"]=="PUBLIC_SYNTHETIC" and perms["allowed_purposes"]==["LOCAL_REPLAY_DEMO"], "PRIVATE_OR_EXTERNAL_PURPOSE_HOLD")
    require(perms["read_grant"]=="HOST_NOT_ATTESTED" and perms["return_grant"]=="HOST_NOT_ATTESTED" and type(perms["revocation_epoch"]) is int and perms["revocation_epoch"]>=0 and perms["public_release_authorized"] is False, "UNATTESTED_PERMISSION_HOLD")
    prov=raw["provenance"]
    require(type(prov) is dict and set(prov)=={"author_claim","source_edition","raw_export_status","observed_revision"}, "PROVENANCE_FIELDS_INVALID")
    require(prov["author_claim"]=="SELF_DECLARED" and prov["raw_export_status"]=="SOURCE_POINTER_ONLY" and string(prov["source_edition"]) and string(prov["observed_revision"]), "OVERCLAIMED_SOURCE_PROVENANCE")
    fork=raw["fork"]
    require(type(fork) is dict and set(fork)=={"parent_sha256","fork_status","parent_authority_inherited"}, "FORK_FIELDS_INVALID")
    require(fork["parent_sha256"] is None or exactsha(fork["parent_sha256"]), "FORK_PARENT_INVALID")
    require(fork["fork_status"] in {"ORIGINAL","FORK_PREPARED"} and fork["parent_authority_inherited"] is False, "FORK_AUTHORITY_HOLD")
    r=raw["rehydration"]
    require(type(r) is dict and set(r)=={"contract_id","identity_claim","uncertainties","human_confirmation_required","private_mode_import"}, "REHYDRATION_FIELDS_INVALID")
    require(r["contract_id"]=="atlas.rehydration-contract/v0-demo" and r["identity_claim"]=="ARCHIVAL_CONTEXT_ONLY" and r["human_confirmation_required"] is True and r["private_mode_import"] is False, "IDENTITY_OR_PRIVACY_HOLD")
    require(type(r["uncertainties"]) is list and len(r["uncertainties"])>=1 and all(string(x) for x in r["uncertainties"]), "UNCERTAINTY_MISSING")
    return {"status":"LOCAL_REVIEWABLE_SOURCE_ONLY","bundle_id":raw["bundle_id"],"source_count":len(sources),"addresses_count":len(ontology["addresses"]),"bundle_sha256_python_only":canonical_sha256(raw),"host_verified":False,"canon":False,"source_bodies_returned":False,"identity_attested":False,"rights_at_return":"NOT_CHECKED"}


def validate_contract(raw: Any) -> dict[str, Any]:
    require(type(raw) is dict and set(raw)==CONTRACT_FIELDS, "CONTRACT_FIELDS_INVALID")
    require(raw["schema_version"]=="atlas.rehydration-contract/v0" and raw["contract_id"]=="atlas.rehydration-contract/v0-demo" and raw["bundle_schema"]==SCHEMA, "CONTRACT_SCHEMA_MISMATCH")
    require(raw["identity_claim"]=="ARCHIVAL_CONTEXT_ONLY" and raw["source_rights_policy"]=="HOST_CHECK_READ_AND_RETURN" and raw["opt_out"]=="SUPPORTED_NOT_OBSERVED", "CONTRACT_RIGHTS_OR_IDENTITY_HOLD")
    require(raw["human_confirmation_required"] is True and raw["promotions"]=="NONE" and raw["disclosure"]=="NOT_PERSON_OR_CONSCIOUSNESS", "CONTRACT_AUTHORITY_HOLD")
    require(raw["allowed_reconstruction"]==["ATTRIBUTE_VERBATIM_SOURCE_POINTERS","DRAFT_HUMAN_REVIEW_SUMMARY"] and type(raw["uncertainty_mandatory"]) is list and len(raw["uncertainty_mandatory"])>=1, "CONTRACT_RECONSTRUCTION_HOLD")
    return {"status":"LOCAL_CONTRACT_VALID_NOT_HOSTED","can_rehydrate_real_identity":False,"consent_granted":False}


def prepare_fork(raw: dict[str,Any]) -> dict[str,Any]:
    validate_bundle(raw)
    fork=deepcopy(raw)
    fork["fork"]["parent_sha256"]=canonical_sha256(raw)
    fork["fork"]["fork_status"]="FORK_PREPARED"
    fork["fork"]["parent_authority_inherited"]=False
    return fork


def prepare_rehydration(raw: Any, contract: Any) -> dict[str,Any]:
    b=validate_bundle(raw)
    validate_contract(contract)
    return {"status":"PREPARED_NOT_EXECUTED","source_bundle_sha256":b["bundle_sha256_python_only"],"source_count":b["source_count"],"identity_continuity":"NOT_PROVEN","model_calls":0,"host_authorization":"NOT_ESTABLISHED","human_review_required":True,"source_bodies_returned":False}


def main(argv=None):
    parser=argparse.ArgumentParser(description="Offline redacted continuity validator, not a live rehydration service")
    parser.add_argument("--bundle",type=Path,default=Path(__file__).resolve().parents[1]/"examples/example-memory-bundle.redacted.json")
    parser.add_argument("--contract",type=Path,default=Path(__file__).resolve().parents[1]/"examples/example-rehydration-contract.redacted.json")
    a=parser.parse_args(argv)
    try:
        b=parse_text(a.bundle.read_text(encoding="utf-8"))
        c=parse_text(a.contract.read_text(encoding="utf-8"))
        print(json.dumps(prepare_rehydration(b,c),sort_keys=True,indent=2))
        return 0
    except (ContinuityHold,ValueError,KeyError,TypeError,OverflowError,OSError,UnicodeError) as e:
        print(json.dumps({"status":"HOLD","reason":type(e).__name__+": "+str(e)}))
        return 2

if __name__=="__main__":raise SystemExit(main())