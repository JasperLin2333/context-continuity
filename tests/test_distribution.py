import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import shutil
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("distribution", ROOT / "scripts/distribute.py")
distribution = importlib.util.module_from_spec(spec)
spec.loader.exec_module(distribution)


class DistributionTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="context-distribution-")
        self.addCleanup(self.temporary.cleanup)
        self.workspace = Path(self.temporary.name)

    def source(self):
        target = self.workspace / "source"
        target.mkdir()
        config = json.loads((ROOT / "distribution.json").read_text(encoding="utf-8"))
        for name in ["distribution.json", *config["files"]]:
            output = target / name
            output.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / name, output)
        return target

    def symlink(self, link, target, directory=False):
        try:
            link.symlink_to(target, target_is_directory=directory)
        except OSError as error:
            self.skipTest("当前环境不允许测试符号链接：" + str(error))

    def test_all_channels_keep_identical_instruction_body(self):
        _, original = distribution.split_skill((ROOT / "SKILL.md").read_text(encoding="utf-8"))
        for target in distribution.TARGETS:
            with self.subTest(target=target):
                config, files = distribution.package_files(target=target)
                prefix = "skills/context-continuity/" if target in ("claude", "openai") else ""
                packed = files[prefix + "SKILL.md"].decode()
                self.assertEqual(packed.split("\n---\n", 1)[1], original)
                self.assertIn('version: "' + config["version"] + '"', packed)

    def test_platform_fields_are_injected_only_in_target(self):
        _, generic = distribution.package_files(target="generic")
        _, workbuddy = distribution.package_files(target="workbuddy")
        _, skillhub = distribution.package_files(target="skillhub")
        self.assertNotIn(b"\nslug:", generic["SKILL.md"])
        self.assertNotIn(b"\ndescription_en:", generic["SKILL.md"])
        self.assertIn(b'\nslug: "context-continuity"', skillhub["SKILL.md"])
        self.assertIn(b"\ndisplayName:", skillhub["SKILL.md"])
        self.assertIn(b"\ndescription_en:", workbuddy["SKILL.md"])
        self.assertIn("LICENSE.txt", workbuddy)
        self.assertIn("LICENSE.txt", skillhub)

    def test_plugins_resolve_their_nested_skill(self):
        config, claude = distribution.package_files(target="claude")
        marketplace = json.loads(claude[".claude-plugin/marketplace.json"])
        plugin = json.loads(claude[".claude-plugin/plugin.json"])
        self.assertEqual(marketplace["plugins"][0]["source"], "./")
        self.assertEqual(marketplace["plugins"][0]["name"], plugin["name"])
        self.assertEqual(plugin["version"], config["version"])
        _, openai = distribution.package_files(target="openai")
        manifest = json.loads(openai["plugin.json"])
        self.assertEqual(manifest["version"], config["version"])
        self.assertIn("$schema", manifest)
        self.assertIn("skills/context-continuity/SKILL.md", openai)

    def test_undeclared_private_files_cannot_enter_packages(self):
        root = self.source()
        (root / "private-notes.md").write_text("PRIVATE_SENTINEL", encoding="utf-8")
        (root / ".git").mkdir()
        (root / ".git/config").write_text("PRIVATE_SENTINEL", encoding="utf-8")
        for target in distribution.TARGETS:
            _, files = distribution.package_files(root, target)
            self.assertFalse(any(b"PRIVATE_SENTINEL" in content for content in files.values()))
            self.assertFalse(any("private-notes" in name or ".git/" in name for name in files))

    def test_missing_resource_is_rejected(self):
        root = self.source()
        (root / "references/handoff.md").unlink()
        with self.assertRaisesRegex(ValueError, "缺少分发文件"):
            distribution.package_files(root)

    def test_undeclared_relative_dependency_is_rejected(self):
        root = self.source()
        with (root / "SKILL.md").open("a", encoding="utf-8") as file:
            file.write("\n[缺失依赖](references/private.md)\n")
        with self.assertRaisesRegex(ValueError, "引用不在包内"):
            distribution.package_files(root)

    def test_path_traversal_in_file_list_is_rejected(self):
        root = self.source()
        file = root / "distribution.json"
        config = json.loads(file.read_text(encoding="utf-8"))
        config["files"].append("../private.md")
        file.write_text(json.dumps(config), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "仓库内相对路径"):
            distribution.package_files(root)

    def test_symlinked_source_directory_is_rejected(self):
        root = self.source()
        elsewhere = self.workspace / "external"
        (root / "references").rename(elsewhere)
        self.symlink(root / "references", elsewhere, directory=True)
        with self.assertRaisesRegex(ValueError, "符号链接"):
            distribution.package_files(root)

    def test_archive_is_reproducible_and_standalone(self):
        config, files = distribution.package_files()
        first = distribution.archive_bytes(config["name"], files)
        self.assertEqual(first, distribution.archive_bytes(config["name"], files))
        with zipfile.ZipFile(io.BytesIO(first)) as archive:
            self.assertTrue(all(name.startswith("context-continuity/") for name in archive.namelist()))
            archive.extractall(self.workspace / "isolated with spaces")
        installed = self.workspace / "isolated with spaces/context-continuity"
        payload = {p.relative_to(installed).as_posix(): p.read_bytes() for p in installed.rglob("*") if p.is_file()}
        distribution.validate_links(payload)
        self.assertEqual(payload, files)

    def test_checksums_only_include_this_build(self):
        root = self.source()
        old = root / "dist/generic/private-old.zip"
        old.parent.mkdir(parents=True)
        old.write_bytes(b"DO_NOT_PUBLISH")
        outputs = distribution.pack(root, ("generic",))
        checksum = (root / "dist/SHA256SUMS").read_text(encoding="utf-8")
        self.assertEqual(checksum, hashlib.sha256(outputs[0].read_bytes()).hexdigest() + "  context-continuity.zip\n")
        self.assertEqual(old.read_bytes(), b"DO_NOT_PUBLISH")

    def test_existing_install_is_preserved(self):
        destination = self.workspace / "skills/context-continuity"
        destination.mkdir(parents=True)
        (destination / "user.txt").write_text("用户修改", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "目标已存在"):
            distribution.install(destination)
        self.assertEqual((destination / "user.txt").read_text(encoding="utf-8"), "用户修改")

    def test_broken_install_symlink_is_preserved(self):
        destination = self.workspace / "context-continuity"
        self.symlink(destination, self.workspace / "missing", directory=True)
        with self.assertRaisesRegex(ValueError, "目标已存在"):
            distribution.install(destination)
        self.assertTrue(destination.is_symlink())

    def test_install_is_independent_of_working_directory(self):
        destination = self.workspace / "host with spaces/skills/context-continuity"
        original = Path.cwd()
        self.addCleanup(os.chdir, original)
        os.chdir(self.workspace)
        distribution.install(destination)
        self.assertTrue((destination / "SKILL.md").is_file())
        self.assertFalse((destination / "scripts").exists())
        self.assertFalse((destination / "tests").exists())

    def test_install_cannot_write_inside_source(self):
        root = self.source()
        with self.assertRaisesRegex(ValueError, "维护仓库内部"):
            distribution.install(root / "nested/context-continuity", root)

    def test_pack_does_not_follow_output_symlink(self):
        root = self.source()
        elsewhere = self.workspace / "external-output"
        elsewhere.mkdir()
        self.symlink(root / "dist", elsewhere, directory=True)
        with self.assertRaisesRegex(ValueError, "符号链接"):
            distribution.pack(root)
        self.assertEqual(list(elsewhere.iterdir()), [])

    def test_invalid_semver_cannot_be_published(self):
        root = self.source()
        file = root / "distribution.json"
        config = json.loads(file.read_text(encoding="utf-8"))
        config["version"] = "01.0.0"
        file.write_text(json.dumps(config), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "SemVer"):
            distribution.pack(root)


if __name__ == "__main__":
    unittest.main()
