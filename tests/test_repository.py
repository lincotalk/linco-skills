from __future__ import annotations

import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "material-to-video"
SCRIPTS = SKILL / "scripts"
ASSETS = SKILL / "assets"


def run_script(name: str, *arguments: object, expected: int = 0) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    environment.pop("VOXCPM_TTS_URL", None)
    environment.pop("VOXCPM_TTS_TOKEN", None)
    result = subprocess.run(
        [sys.executable, str(SCRIPTS / name), *(str(value) for value in arguments)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=environment,
    )
    if result.returncode != expected:
        raise AssertionError(
            f"{name} exited {result.returncode}, expected {expected}\n"
            f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )
    return result


def load_script_module(name: str):
    path = SCRIPTS / name
    spec = importlib.util.spec_from_file_location(path.stem, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class RepositoryContractTests(unittest.TestCase):
    def test_skill_metadata_and_local_links(self) -> None:
        skill_text = (SKILL / "SKILL.md").read_text(encoding="utf-8")
        self.assertTrue(skill_text.startswith("---\nname: material-to-video\n"))
        self.assertIn("\ndescription:", skill_text.split("---", 2)[1])
        markdown_files = [ROOT / "README.md", ROOT / "CONTRIBUTING.md", ROOT / "SECURITY.md"]
        markdown_files.extend(SKILL.rglob("*.md"))
        for markdown in markdown_files:
            text = markdown.read_text(encoding="utf-8")
            for target in __import__("re").findall(r"\[[^\]]+\]\(([^)]+)\)", text):
                if target.startswith(("http://", "https://", "#")):
                    continue
                local = target.split("#", 1)[0]
                self.assertTrue((markdown.parent / local).exists(), f"broken link {markdown}: {target}")

    def test_all_json_assets_parse(self) -> None:
        for path in ASSETS.glob("*.json"):
            with self.subTest(path=path.name):
                self.assertIsInstance(json.loads(path.read_text(encoding="utf-8")), dict)

    def test_example_validators(self) -> None:
        commands = [
            ("validate_research_sources.py", "--input", ASSETS / "research-sources.example.json"),
            (
                "validate_content_model.py",
                "--input",
                ASSETS / "content-model.example.json",
                "--materials",
                ASSETS / "materials.example.json",
            ),
            (
                "validate_content_model.py",
                "--input",
                ASSETS / "content-model.research.example.json",
                "--research-sources",
                ASSETS / "research-sources.example.json",
            ),
            (
                "validate_content_model.py",
                "--input",
                ASSETS / "content-model.technical.example.json",
                "--research-sources",
                ASSETS / "research-sources.example.json",
            ),
            (
                "validate_visual_plan.py",
                "--input",
                ASSETS / "visual-plan.example.json",
                "--content-model",
                ASSETS / "content-model.example.json",
                "--config",
                ASSETS / "config.example.json",
            ),
            (
                "validate_visual_plan.py",
                "--input",
                ASSETS / "visual-plan.technical.example.json",
                "--content-model",
                ASSETS / "content-model.technical.example.json",
                "--config",
                ASSETS / "config.example.json",
            ),
            (
                "validate_audio_plan.py",
                "--input",
                ASSETS / "audio-plan.example.json",
                "--visual-plan",
                ASSETS / "visual-plan.technical.example.json",
            ),
            (
                "validate_cover_plan.py",
                "--input",
                ASSETS / "cover-plan.example.json",
                "--config",
                ASSETS / "config.example.json",
                "--visual-plan",
                ASSETS / "visual-plan.example.json",
                "--content-model",
                ASSETS / "content-model.example.json",
            ),
        ]
        for command in commands:
            with self.subTest(script=command[0]):
                run_script(*command)

    def test_complete_layout_review_fixture(self) -> None:
        plan = json.loads((ASSETS / "visual-plan.example.json").read_text(encoding="utf-8"))
        with tempfile.TemporaryDirectory() as temporary:
            review_dir = Path(temporary) / "review"
            review_dir.mkdir()
            checks = []
            for scene in plan["scenes"]:
                container_ids = scene["containment"]["containerIds"]
                for moment in scene["reviewMoments"]:
                    filename = f"{scene['id']}-{moment['phase']}.png"
                    (review_dir / filename).write_bytes(b"test-image")
                    checks.append(
                        {
                            "sceneId": scene["id"],
                            "phase": moment["phase"],
                            "atSec": moment["atSec"],
                            "screenshot": filename,
                            "checkedContainerIds": container_ids,
                            "fontResult": {
                                "primaryFamily": plan["fontPolicy"]["primaryCjkFamily"],
                                "loaded": True,
                                "fallbackMismatch": False,
                            },
                            "blankFrame": False,
                            "safeAreaOk": True,
                            "captionOverlap": False,
                            "clippedText": False,
                            "violations": [],
                        }
                    )
            review = {"schemaVersion": 1, "containmentTolerancePx": 1, "checks": checks}
            review_path = review_dir / "LAYOUT_REVIEW.json"
            review_path.write_text(json.dumps(review), encoding="utf-8")
            run_script(
                "validate_layout_review.py",
                "--input",
                review_path,
                "--visual-plan",
                ASSETS / "visual-plan.example.json",
            )


class MaterialPipelineTests(unittest.TestCase):
    def create_materials(self, root: Path) -> None:
        (root / "note.md").write_text("# Topic\n\nA source-backed explanation.", encoding="utf-8")
        (root / "page.html").write_text(
            "<html><style>hidden</style><body><h1>Visible title</h1><p>Visible body.</p></body></html>",
            encoding="utf-8",
        )
        with zipfile.ZipFile(root / "document.docx", "w") as archive:
            archive.writestr(
                "word/document.xml",
                '<w:document xmlns:w="urn:w"><w:body><w:p><w:r><w:t>DOCX text</w:t></w:r></w:p></w:body></w:document>',
            )
        with zipfile.ZipFile(root / "slides.pptx", "w") as archive:
            archive.writestr(
                "ppt/slides/slide1.xml",
                '<p:sld xmlns:p="urn:p" xmlns:a="urn:a"><a:t>Slide text</a:t></p:sld>',
            )

    def test_scan_extract_validate_and_prepare(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "source"
            source.mkdir()
            self.create_materials(source)
            job = root / "job"
            project = job / "project"
            manifest = job / "MATERIALS.json"
            extracted = job / "EXTRACTED_MATERIALS.json"
            assets = job / "ASSETS.json"
            run_script("scan_materials.py", "--input", source, "--output", manifest)
            run_script("extract_materials.py", "--manifest", manifest, "--output", extracted)
            run_script(
                "validate_extracted_materials.py",
                "--input",
                extracted,
                "--manifest",
                manifest,
                "--require-reviewed",
            )
            payload = json.loads(extracted.read_text(encoding="utf-8"))
            combined = "\n".join(item.get("text") or "" for item in payload["items"])
            self.assertIn("Visible title", combined)
            self.assertNotIn("hidden", combined)
            self.assertIn("DOCX text", combined)
            self.assertIn("Slide text", combined)

            ids = job / "SELECTED_ASSET_IDS.txt"
            ids.write_text("\n".join(item["id"] for item in payload["items"]) + "\n", encoding="utf-8")
            run_script(
                "prepare_assets.py",
                "--manifest",
                manifest,
                "--project",
                project,
                "--output",
                assets,
                "--selected-ids",
                ids,
            )
            prepared = json.loads(assets.read_text(encoding="utf-8"))
            self.assertEqual(len(prepared["assets"]), 4)

    def test_prepare_assets_rejects_manifest_id_path_traversal(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "source"
            source.mkdir()
            (source / "note.md").write_text("safe", encoding="utf-8")
            manifest_path = root / "MATERIALS.json"
            run_script("scan_materials.py", "--input", source, "--output", manifest_path)
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["items"][0]["id"] = "../../outside"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            run_script(
                "prepare_assets.py",
                "--manifest",
                manifest_path,
                "--project",
                root / "project",
                "--output",
                root / "ASSETS.json",
                expected=2,
            )
            self.assertFalse((root / "outside.md").exists())


class TtsSafetyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.module = load_script_module("generate_voxcpm_voice.py")

    def test_endpoint_rejects_embedded_credentials_and_query_tokens(self) -> None:
        with self.assertRaises(self.module.TtsConfigError):
            self.module.normalized_endpoint("https://user:secret@example.com")
        with self.assertRaises(self.module.TtsConfigError):
            self.module.normalized_endpoint("https://example.com?token=secret")
        with self.assertRaises(self.module.TtsConfigError):
            self.module.normalized_endpoint("https://example.com/generate")

    def test_auth_header_is_bearer_without_logging_token(self) -> None:
        self.assertEqual(
            self.module.request_headers("secret", accept="application/json"),
            {"Accept": "application/json", "Authorization": "Bearer secret"},
        )

    def test_unconfigured_tts_is_a_local_failure(self) -> None:
        result = run_script(
            "generate_voxcpm_voice.py",
            "--check",
            "--config",
            ASSETS / "config.example.json",
            expected=2,
        )
        payload = json.loads(result.stdout)
        self.assertEqual(payload["code"], "tts_not_configured")
        self.assertEqual(
            payload["deployment"]["repository"],
            "https://github.com/OpenBMB/VoxCPM",
        )
        self.assertIn("deployed", payload["action"])
        self.assertIn("Gradio service base URL", payload["action"])

    def test_unconfigured_offline_tts_preflight_is_informational(self) -> None:
        result = run_script(
            "generate_voxcpm_voice.py",
            "--check-config",
            "--config",
            ASSETS / "config.example.json",
        )
        payload = json.loads(result.stdout)
        self.assertTrue(payload["ok"])
        self.assertFalse(payload["configured"])
        self.assertEqual(payload["code"], "tts_not_configured")
        self.assertFalse(payload["networkChecked"])

    def test_configured_offline_tts_preflight_does_not_check_network(self) -> None:
        result = run_script(
            "generate_voxcpm_voice.py",
            "--check-config",
            "--endpoint",
            "https://tts.example.com",
            "--config",
            ASSETS / "config.example.json",
        )
        payload = json.loads(result.stdout)
        self.assertTrue(payload["ok"])
        self.assertTrue(payload["configured"])
        self.assertEqual(payload["code"], "tts_configured")
        self.assertEqual(payload["endpoint"], "https://tts.example.com")
        self.assertFalse(payload["networkChecked"])

    def test_invalid_offline_tts_config_is_a_local_failure(self) -> None:
        result = run_script(
            "generate_voxcpm_voice.py",
            "--check-config",
            "--endpoint",
            "https://example.com?token=x",
            "--config",
            ASSETS / "config.example.json",
            expected=2,
        )
        payload = json.loads(result.stdout)
        self.assertFalse(payload["ok"])
        self.assertEqual(payload["code"], "tts_config_invalid")
        self.assertFalse(payload["networkChecked"])


@unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "FFmpeg is unavailable")
class VideoVerificationTests(unittest.TestCase):
    def test_delivery_video_contract_and_wrong_fps_rejection(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "sample.mp4"
            result = subprocess.run(
                [
                    shutil.which("ffmpeg") or "ffmpeg",
                    "-v",
                    "error",
                    "-f",
                    "lavfi",
                    "-i",
                    "color=c=black:s=64x96:r=30:d=0.3",
                    "-f",
                    "lavfi",
                    "-i",
                    "sine=frequency=1000:duration=0.3",
                    "-c:v",
                    "libx264",
                    "-pix_fmt",
                    "yuv420p",
                    "-c:a",
                    "aac",
                    "-shortest",
                    "-y",
                    str(output),
                ],
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            run_script(
                "verify_video.py",
                "--input",
                output,
                "--width",
                64,
                "--height",
                96,
                "--fps",
                30,
                "--require-audio",
            )
            run_script(
                "verify_video.py",
                "--input",
                output,
                "--width",
                64,
                "--height",
                96,
                "--fps",
                25,
                "--require-audio",
                expected=2,
            )


if __name__ == "__main__":
    unittest.main()
