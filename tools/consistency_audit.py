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
    return json.loads(path.read_text(encoding="utf-8"))


def _ok(name: str, details: str) -> RuleResult:
    return RuleResult(name=name, status="pass", details=details)


def _fail(name: str, details: str) -> RuleResult:
    return RuleResult(name=name, status="fail", details=details)


def validate_profile(profile: dict[str, Any]) -> list[RuleResult]:
    results: list[RuleResult] = []

    required_sections = ["voice", "character", "scene", "object"]
    missing = [s for s in required_sections if s not in profile]
    if missing:
        results.append(_fail("profile_sections", f"missing sections: {missing}"))
    else:
        results.append(_ok("profile_sections", "all required sections exist"))

    voice = profile.get("voice", {})
    if all(k in voice for k in ["speaker_id", "pitch_range", "speed_range"]):
        results.append(_ok("voice_constraints", "voice constraints are defined"))
    else:
        results.append(_fail("voice_constraints", "voice constraints missing keys"))

    character = profile.get("character", {})
    if all(k in character for k in ["id", "core_traits", "forbidden_drifts"]):
        results.append(_ok("character_constraints", "character constraints are defined"))
    else:
        results.append(_fail("character_constraints", "character constraints missing keys"))

    scene = profile.get("scene", {})
    if all(k in scene for k in ["style_anchor", "lighting", "palette"]):
        results.append(_ok("scene_constraints", "scene constraints are defined"))
    else:
        results.append(_fail("scene_constraints", "scene constraints missing keys"))

    obj = profile.get("object", {})
    if all(k in obj for k in ["identity_tags", "material", "size_band"]):
        results.append(_ok("object_constraints", "object constraints are defined"))
    else:
        results.append(_fail("object_constraints", "object constraints missing keys"))

    return results


def validate_dataset(dataset: dict[str, Any], profile: dict[str, Any]) -> list[RuleResult]:
    """Validate generated timeline/script data against consistency profile.

    Expected dataset schema:
    {
      "frames": [
        {
          "voice": {"speaker_id": "...", "pitch": 0.0, "speed": 1.0},
          "character": {"id": "...", "traits": ["..."]},
          "scene": {"style_anchor": "...", "lighting": "...", "palette": "..."},
          "object": [{"identity_tags": ["..."], "material": "...", "size": "..."}]
        }
      ]
    }
    """
    results: list[RuleResult] = []
    frames = dataset.get("frames", [])
    if not isinstance(frames, list) or not frames:
        return [_fail("dataset_frames", "dataset.frames is missing or empty")]

    # Voice consistency
    p_voice = profile["voice"]
    for i, frame in enumerate(frames, start=1):
        voice = frame.get("voice", {})
        if voice.get("speaker_id") != p_voice.get("speaker_id"):
            results.append(_fail("voice_speaker_consistency", f"frame {i}: speaker_id drift"))
            break
    else:
        results.append(_ok("voice_speaker_consistency", "all frames keep same speaker_id"))

    # Character consistency
    p_char = profile["character"]
    required_traits = set(p_char.get("core_traits", []))
    forbidden = set(p_char.get("forbidden_drifts", []))
    for i, frame in enumerate(frames, start=1):
        ch = frame.get("character", {})
        if ch.get("id") != p_char.get("id"):
            results.append(_fail("character_id_consistency", f"frame {i}: character id drift"))
            break
        traits = set(ch.get("traits", []))
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
        tags = set(first.get("identity_tags", []))
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
