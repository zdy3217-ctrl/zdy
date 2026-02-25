#!/usr/bin/env python3
"""Consistency audit layer for NarratorAI Omega outputs.

This script does NOT modify cmd.exe. It provides quality constraints for:
- Voice consistency
- Anime character consistency
- Scene consistency
- Object consistency
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
REPORT_DIR = ROOT / "reports"
DEFAULT_PROFILE = ROOT / "tools" / "consistency_profile.example.json"
DEFAULT_REPORT = REPORT_DIR / "consistency_audit.json"


@dataclass
class RuleResult:
    name: str
    status: str
    details: str


def _load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"JSON root must be object: {path}")
    return data


def _ok(name: str, details: str) -> RuleResult:
    return RuleResult(name=name, status="pass", details=details)


def _fail(name: str, details: str) -> RuleResult:
    return RuleResult(name=name, status="fail", details=details)


def _valid_range(value: Any) -> bool:
    return isinstance(value, list) and len(value) == 2 and all(isinstance(i, (int, float)) for i in value) and value[0] <= value[1]


def validate_profile(profile: dict[str, Any]) -> list[RuleResult]:
    results: list[RuleResult] = []

    required_sections = ["voice", "character", "scene", "object"]
    missing = [s for s in required_sections if s not in profile]
    if missing:
        results.append(_fail("profile_sections", f"missing sections: {missing}"))
    else:
        results.append(_ok("profile_sections", "all required sections exist"))

    voice = profile.get("voice", {})
    has_voice_keys = all(k in voice for k in ["speaker_id", "pitch_range", "speed_range"])
    if has_voice_keys and isinstance(voice.get("speaker_id"), str) and _valid_range(voice.get("pitch_range")) and _valid_range(voice.get("speed_range")):
        results.append(_ok("voice_constraints", "voice constraints are structurally valid"))
    else:
        results.append(_fail("voice_constraints", "voice constraints missing keys or invalid ranges"))

    character = profile.get("character", {})
    has_char_keys = all(k in character for k in ["id", "core_traits", "forbidden_drifts"])
    if has_char_keys and isinstance(character.get("id"), str) and isinstance(character.get("core_traits"), list) and isinstance(character.get("forbidden_drifts"), list):
        results.append(_ok("character_constraints", "character constraints are structurally valid"))
    else:
        results.append(_fail("character_constraints", "character constraints missing keys or invalid types"))

    scene = profile.get("scene", {})
    has_scene_keys = all(k in scene for k in ["style_anchor", "lighting", "palette"])
    if has_scene_keys and all(isinstance(scene.get(k), str) for k in ["style_anchor", "lighting", "palette"]):
        results.append(_ok("scene_constraints", "scene constraints are structurally valid"))
    else:
        results.append(_fail("scene_constraints", "scene constraints missing keys or invalid types"))

    obj = profile.get("object", {})
    has_obj_keys = all(k in obj for k in ["identity_tags", "material", "size_band"])
    if has_obj_keys and isinstance(obj.get("identity_tags"), list) and isinstance(obj.get("material"), str) and isinstance(obj.get("size_band"), list):
        results.append(_ok("object_constraints", "object constraints are structurally valid"))
    else:
        results.append(_fail("object_constraints", "object constraints missing keys or invalid types"))

    return results


def validate_dataset(dataset: dict[str, Any], profile: dict[str, Any]) -> list[RuleResult]:
    """Validate generated timeline/script data against consistency profile."""
    results: list[RuleResult] = []
    frames = dataset.get("frames", [])
    if not isinstance(frames, list) or not frames:
        return [_fail("dataset_frames", "dataset.frames is missing or empty")]

    # Voice consistency
    p_voice = profile["voice"]
    pitch_min, pitch_max = p_voice["pitch_range"]
    speed_min, speed_max = p_voice["speed_range"]
    for i, frame in enumerate(frames, start=1):
        voice = frame.get("voice", {})
        if voice.get("speaker_id") != p_voice.get("speaker_id"):
            results.append(_fail("voice_speaker_consistency", f"frame {i}: speaker_id drift"))
            break
        pitch = voice.get("pitch")
        speed = voice.get("speed")
        if not isinstance(pitch, (int, float)) or not (pitch_min <= pitch <= pitch_max):
            results.append(_fail("voice_pitch_consistency", f"frame {i}: pitch out of range"))
            break
        if not isinstance(speed, (int, float)) or not (speed_min <= speed <= speed_max):
            results.append(_fail("voice_speed_consistency", f"frame {i}: speed out of range"))
            break
    else:
        results.append(_ok("voice_speaker_consistency", "all frames keep same speaker_id"))
        results.append(_ok("voice_pitch_consistency", "all frames pitch stays in configured range"))
        results.append(_ok("voice_speed_consistency", "all frames speed stays in configured range"))

    # Character consistency
    p_char = profile["character"]
    required_traits = set(p_char.get("core_traits", []))
    forbidden = set(p_char.get("forbidden_drifts", []))
    for i, frame in enumerate(frames, start=1):
        ch = frame.get("character", {})
        if ch.get("id") != p_char.get("id"):
            results.append(_fail("character_id_consistency", f"frame {i}: character id drift"))
            break
        traits_raw = ch.get("traits", [])
        if not isinstance(traits_raw, list):
            results.append(_fail("character_trait_consistency", f"frame {i}: traits must be list"))
            break
        traits = set(traits_raw)
        if not required_traits.issubset(traits):
            results.append(_fail("character_trait_consistency", f"frame {i}: missing core traits"))
            break
        if forbidden.intersection(traits):
            results.append(_fail("character_trait_consistency", f"frame {i}: forbidden drift detected"))
            break
    else:
        results.append(_ok("character_id_consistency", "all frames keep same character id"))
        results.append(_ok("character_trait_consistency", "core traits remain stable"))

    # Scene consistency
    p_scene = profile["scene"]
    for i, frame in enumerate(frames, start=1):
        sc = frame.get("scene", {})
        if sc.get("style_anchor") != p_scene.get("style_anchor"):
            results.append(_fail("scene_style_consistency", f"frame {i}: style anchor drift"))
            break
        if sc.get("lighting") != p_scene.get("lighting"):
            results.append(_fail("scene_lighting_consistency", f"frame {i}: lighting drift"))
            break
        if sc.get("palette") != p_scene.get("palette"):
            results.append(_fail("scene_palette_consistency", f"frame {i}: palette drift"))
            break
    else:
        results.append(_ok("scene_style_consistency", "scene style anchor stable"))
        results.append(_ok("scene_lighting_consistency", "scene lighting stable"))
        results.append(_ok("scene_palette_consistency", "scene palette stable"))

    # Object consistency
    p_obj = profile["object"]
    required_tags = set(p_obj.get("identity_tags", []))
    for i, frame in enumerate(frames, start=1):
        items = frame.get("object", [])
        if not isinstance(items, list) or not items:
            results.append(_fail("object_presence_consistency", f"frame {i}: object missing"))
            break
        first = items[0]
        if not isinstance(first, dict):
            results.append(_fail("object_schema_consistency", f"frame {i}: object item must be dict"))
            break
        tags_raw = first.get("identity_tags", [])
        if not isinstance(tags_raw, list):
            results.append(_fail("object_schema_consistency", f"frame {i}: identity_tags must be list"))
            break
        tags = set(tags_raw)
        if not required_tags.issubset(tags):
            results.append(_fail("object_identity_consistency", f"frame {i}: identity tag drift"))
            break
        if first.get("material") != p_obj.get("material"):
            results.append(_fail("object_material_consistency", f"frame {i}: material drift"))
            break
        if first.get("size") not in p_obj.get("size_band", []):
            results.append(_fail("object_size_consistency", f"frame {i}: out-of-band size"))
            break
    else:
        results.append(_ok("object_presence_consistency", "object exists in all frames"))
        results.append(_ok("object_schema_consistency", "object schema is valid in all frames"))
        results.append(_ok("object_identity_consistency", "object identity tags stable"))
        results.append(_ok("object_material_consistency", "object material stable"))
        results.append(_ok("object_size_consistency", "object size is in configured band"))

    return results


def main() -> int:
    parser = argparse.ArgumentParser(description="NarratorAI Omega consistency audit")
    parser.add_argument("--profile", type=Path, default=DEFAULT_PROFILE, help="Consistency profile JSON")
    parser.add_argument("--input", type=Path, default=None, help="Generated timeline/script JSON to validate")
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT, help="Output report path")
    args = parser.parse_args()

    profile = _load_json(args.profile)
    results = validate_profile(profile)

    if any(r.status == "fail" for r in results):
        mode = "profile_invalid"
    else:
        mode = "profile_only"
        if args.input is not None:
            dataset = _load_json(args.input)
            results.extend(validate_dataset(dataset, profile))
            mode = "profile_and_dataset"

    passed = sum(1 for r in results if r.status == "pass")
    failed = sum(1 for r in results if r.status == "fail")

    report = {
        "project": "NarratorAI Omega",
        "mode": mode,
        "profile": str(args.profile),
        "input": str(args.input) if args.input else None,
        "summary": {"total": len(results), "passed": passed, "failed": failed},
        "results": [r.__dict__ for r in results],
    }

    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print(f"Consistency audit report: {args.report}")
    for r in results:
        print(f"[{r.status.upper()}] {r.name}: {r.details}")

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
