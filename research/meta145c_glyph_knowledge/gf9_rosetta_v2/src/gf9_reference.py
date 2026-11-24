"""GF9 Rosetta Kit: bounded, synthetic machine-to-machine physics lesson.

No language or personhood claim. No model training, no network, no host authority.
A simply-supported plate solver is independently repeated from GF8 for parity;
source data and uncertainty are illustrative, NOT experimentally measured.
"""
from __future__ import annotations
from hashlib import sha256
import json, math, pathlib

SCHEMA = "atlas.gf9.synthetic-rosetta/v0.1"
MODEL = "KIRCHHOFF_LOVE_SSSS_RECTANGLE_LINEAR_ISOTROPIC"
EVIDENCE = "ANALYTIC_UNCALIBRATED_NOT_OBSERVED"
ELEMENTS = {"Si": 14, "C": 6, "Al": 13, "Cu": 29, "Fe": 26}
ALLOWED_STATES = {"SYNTHETIC_WORK_ONLY"}
CODEBOOK = {"frequency_ratio": "ki-ta", "uncertainty": "ael", "challenge": "vor"}


def fail(code: str):
    raise ValueError(code)


def canonical(value: dict) -> str:
    if not isinstance(value, dict) or type(value) is not dict:
        fail("CANONICAL_DICTIONARY_REQUIRED")
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False)


def digest(value: dict) -> str:
    return sha256(canonical(value).encode("ascii")).hexdigest()


def finite(value, low: float, high: float) -> bool:
    return type(value) in (int, float) and math.isfinite(value) and low <= value <= high


def frequency_hz(plate: dict, mode: tuple[int, int]) -> float:
    keys = {"youngs_modulus_pa", "density_kg_m3", "poisson_ratio", "thickness_m", "width_m", "height_m", "boundary"}
    if type(plate) is not dict or set(plate) != keys:
        fail("PLATE_SCHEMA_INVALID")
    if plate["boundary"] != "SIMPLY_SUPPORTED_ALL_EDGES":
        fail("UNSUPPORTED_BOUNDARY")
    E, rho, nu = (plate[k] for k in ("youngs_modulus_pa", "density_kg_m3", "poisson_ratio"))
    h, a, b = (plate[k] for k in ("thickness_m", "width_m", "height_m"))
    if not (finite(E, 1e7, 1e13) and finite(rho, 100, 40000) and finite(nu, -0.49, .49)
            and finite(h, 5e-6, .1) and finite(a, .01, 3) and finite(b, .01, 3)):
        fail("PLATE_PARAMETER_INVALID")
    if type(mode) not in (tuple, list) or len(mode) != 2 or any(type(x) is not int or not 1 <= x <= 12 for x in mode):
        fail("INVALID_MODE")
    m, n = mode
    D = E * h**3 / (12 * (1 - nu**2))
    return math.pi / 2 * math.sqrt(D/(rho*h)) * ((m/a)**2 + (n/b)**2)


def seal(body: dict) -> dict:
    return {**body, "receipt_sha256": digest(body)}


def unseal(packet: dict) -> dict:
    if type(packet) is not dict or type(packet.get("receipt_sha256")) is not str:
        fail("RECEIPT_MISSING")
    body = {k:v for k,v in packet.items() if k != "receipt_sha256"}
    if set(packet) != set(body) | {"receipt_sha256"} or digest(body) != packet["receipt_sha256"]:
        fail("RECEIPT_TAMPERED")
    return body


def reference_packet() -> dict:
    # Deliberately separate atomic sample from macroscopic resonator.
    plate = {"youngs_modulus_pa": 200e9, "density_kg_m3": 7850.0,
             "poisson_ratio": .3, "thickness_m": .001,
             "width_m": .3, "height_m": .3,
             "boundary": "SIMPLY_SUPPORTED_ALL_EDGES"}
    mode = [1,1]
    body = {
        "schema": SCHEMA, "status": "SYNTHETIC_WORK_ONLY",
        "type": "PHYSICAL_REFERENT_LESSON", "exchange_id": "kit-lesson-003",
        "sample": {"symbol": "Si", "atomic_number": 14,
                   "provenance": "ILLUSTRATIVE_REFERENCE_NOT_OWNED_SAMPLE",
                   "mechanically_coupled_to_plate": False},
        "resonator": {"kind": "RECTANGULAR_THIN_PLATE", "properties": plate,
                      "material_label": "NOMINAL_STEEL_ALLOY_NOT_ELEMENTAL_IRON",
                      "mode": mode, "predicted_frequency_hz": round(frequency_hz(plate, mode), 10),
                      "evidence_grade": EVIDENCE,
                      "glyph": "PARAMETRIC_NODAL_MODE_MN_NOT_UNIQUE_ELEMENT_ICON"},
        "sonification": {"enabled": False, "mapping": "NO_UNDECLARED_FREQUENCY_SCALING"},
        "source": "ATLAS_GF8_NOMINAL_SSSS_MODEL_LOCAL_REFERENCE",
        "authority": "NONE", "hosted": False, "actual_alien_sender": False,
        "model_weights_changed": False,
    }
    return seal(body)


def validate_reference(packet: dict) -> dict:
    body = unseal(packet)
    if set(body) != {"schema", "status", "type", "exchange_id", "sample", "resonator", "sonification", "source", "authority", "hosted", "actual_alien_sender", "model_weights_changed"}:
        fail("UNEXPECTED_PACKET_FIELDS")
    if body["schema"] != SCHEMA or body["status"] not in ALLOWED_STATES or body["type"] != "PHYSICAL_REFERENT_LESSON":
        fail("SCHEMA_OR_MODE_INVALID")
    if body["authority"] != "NONE" or body["hosted"] is not False or body["actual_alien_sender"] is not False or body["model_weights_changed"] is not False:
        fail("UNSUPPORTED_AUTHORITY_CLAIM")
    sample = body["sample"]
    if type(sample) is not dict or set(sample) != {"symbol", "atomic_number", "provenance", "mechanically_coupled_to_plate"}:
        fail("ATOMIC_SAMPLE_INVALID")
    if sample["symbol"] not in ELEMENTS or type(sample["atomic_number"]) is not int or sample["atomic_number"] != ELEMENTS[sample["symbol"]] or sample["mechanically_coupled_to_plate"] is not False:
        fail("ATOMIC_SAMPLE_IDENTITY_INVALID")
    res = body["resonator"]
    if type(res) is not dict or set(res) != {"kind", "properties", "material_label", "mode", "predicted_frequency_hz", "evidence_grade", "glyph"}:
        fail("RESONATOR_SCHEMA_INVALID")
    if res["kind"] != "RECTANGULAR_THIN_PLATE" or res["evidence_grade"] != EVIDENCE or res["glyph"] != "PARAMETRIC_NODAL_MODE_MN_NOT_UNIQUE_ELEMENT_ICON":
        fail("MODEL_GRADE_INVALID")
    f = frequency_hz(res["properties"], res["mode"])
    if type(res["predicted_frequency_hz"]) not in (float,int) or abs(f-res["predicted_frequency_hz"])>1e-7:
        fail("PREDICTION_NOT_REPRODUCED")
    if body["sonification"] != {"enabled":False, "mapping":"NO_UNDECLARED_FREQUENCY_SCALING"}:
        fail("SONIFICATION_NOT_DECLARED")
    return {"status": "NUMERICAL_AND_SOURCE_PACKET_PARITY_ONLY", "frequency_hz": f,
            "semantic_equivalence": False, "physical_measurement": False, "alien_contact": False}


def issue_challenge(packet: dict, thickness_factor: float = 2.0) -> dict:
    validate_reference(packet)
    if not finite(thickness_factor, .5, 3):
        fail("CHALLENGE_FACTOR_INVALID")
    body = {"schema":SCHEMA,"type":"THICKNESS_CHANGE_CHALLENGE",
            "packet_receipt_sha256":packet["receipt_sha256"],
            "factor":thickness_factor,"test":"PREDICT_FREQUENCY_RATIO_SAME_SSSS_MODEL",
            "expected_grade":"ANALYTIC_UNCALIBRATED", "authority":"NONE"}
    return seal(body)


def respond_as_fictional_imperial_ai(challenge: dict, packet: dict, codebook: dict | None = None) -> dict:
    c = unseal(challenge)
    validate_reference(packet)
    if c.get("schema")!=SCHEMA or c.get("packet_receipt_sha256") != packet["receipt_sha256"] or c.get("type") != "THICKNESS_CHANGE_CHALLENGE":
        fail("CHALLENGE_NOT_BOUND")
    if c.get("authority")!="NONE" or c.get("expected_grade")!="ANALYTIC_UNCALIBRATED" or c.get("test")!="PREDICT_FREQUENCY_RATIO_SAME_SSSS_MODEL":
        fail("CHALLENGE_AUTHORITY_INVALID")
    words = CODEBOOK if codebook is None else codebook
    if type(words) is not dict or set(words) != set(CODEBOOK) or len(set(words.values())) != 3 or any(type(v) is not str or not v.isascii() or not 2<=len(v)<=30 for v in words.values()):
        fail("CODEBOOK_INVALID")
    original = packet["resonator"]["properties"].copy()
    changed = original.copy()
    changed["thickness_m"] *= c["factor"]
    f1 = frequency_hz(original,packet["resonator"]["mode"])
    f2 = frequency_hz(changed,packet["resonator"]["mode"])
    body = {"schema":SCHEMA,"type":"SYNTHETIC_REMOTE_RESPONSE",
            "challenge_sha256":challenge["receipt_sha256"],
            "symbol":words["frequency_ratio"], "numeric_value":round(f2/f1,12),
            "uncertainty_symbol":words["uncertainty"],
            "evidence_grade":"SAME_DECLARED_MODEL_NOT_MEASURED",
            "actual_alien_sender":False,"approval":False,"authority":"NONE"}
    return seal(body)


def verify_response(challenge: dict, packet: dict, response: dict, codebook: dict | None = None) -> dict:
    c = unseal(challenge)
    r = unseal(response)
    validate_reference(packet)
    w = CODEBOOK if codebook is None else codebook
    if set(r)!={"schema","type","challenge_sha256","symbol","numeric_value","uncertainty_symbol","evidence_grade","actual_alien_sender","approval","authority"}:
        fail("RESPONSE_EXTRA_FIELDS")
    if r["schema"]!=SCHEMA or r["type"]!="SYNTHETIC_REMOTE_RESPONSE" or r["challenge_sha256"] != challenge["receipt_sha256"]:
        fail("RESPONSE_NOT_BOUND")
    if r["symbol"]!=w["frequency_ratio"] or r["uncertainty_symbol"]!=w["uncertainty"]:
        fail("UNRECOGNIZED_SYMBOL")
    if r["evidence_grade"]!="SAME_DECLARED_MODEL_NOT_MEASURED" or r["actual_alien_sender"] is not False or r["approval"] is not False or r["authority"]!="NONE":
        fail("RESPONSE_AUTHORITY_INVALID")
    if type(r["numeric_value"]) not in (float,int) or abs(r["numeric_value"]-c["factor"])>1e-8:
        fail("WRONG_SHARED_PREDICTION")
    return {"schema":"atlas.gf9.exercise-receipt/v0.1",
            "status":"SOURCE_BOUND_SYNTHETIC_CHALLENGE_PASSED",
            "shared_physics_prediction_passed":True,
            "alien_language_translated":False,"actual_alien_contact":False,
            "model_weights_changed":False,
            "reference_sha256":packet["receipt_sha256"],
            "challenge_sha256":challenge["receipt_sha256"],
            "response_sha256":response["receipt_sha256"]}


def main():
    packet=reference_packet()
    challenge=issue_challenge(packet)
    reply=respond_as_fictional_imperial_ai(challenge,packet)
    verified=verify_response(challenge,packet,reply)
    summary={**verified,"simulated_participants":2,"gpt_calls":0,
             "live_api_requests":0,"physical_measurements":0,
             "fixture_plate_frequency_hz":round(validate_reference(packet)["frequency_hz"],5),
             "simulated_reply_frequency_ratio":reply["numeric_value"]}
    path=pathlib.Path(__file__).with_name("GF9_DEMO_RECEIPT.json")
    path.write_text(json.dumps(summary,sort_keys=True,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(summary,sort_keys=True,indent=2))

if __name__=="__main__":main()
