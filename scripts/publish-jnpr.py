#!/usr/bin/env python3
"""Publish a de-branded copy of this repository to a downstream org.

This repository is upstream. The published copy deliberately shares no git
history with it, so no merge can carry mechub branding downstream, and no
downstream contribution can pull third-party copyright back into upstream.
Syncing is one-way, by design; bring downstream fixes back by hand.

The de-branding is verified, not assumed: `gate()` fails the run if any
forbidden token survives into the staged tree. A silent transform is not proof.

Default behaviour is a dry run that stages and verifies without touching any
target clone. Pushing is never automated -- the command to run is printed.

The whole catalog is published or nothing is. A partial export fails six of the
repo's own validators -- they assert the full inventory, and the skill-specific
checks crash outright when their skill is absent -- so shipping one would mean a
distribution that cannot pass its own checks. Curate by choosing when to sync,
not by choosing which skills go.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BRAND_DIR = ROOT / "docs" / "publish"

UPSTREAM_SLUG = "mechubsec/fwskillsshare"

# Allowlist, not denylist: anything not named here is never published, so a new
# directory of lab notes cannot leak by being forgotten.
PUBLISH_FILES = (
    "install.sh",
    "LICENSE",
    "README.md",
    "CONTRIBUTORS.md",
    "QUALITY.md",
    "SKILLS.md",
    "CHANGELOG.md",
    "justfile",
    "mise.toml",
    ".editorconfig",
    ".gitignore",
    ".python-version",
    ".pre-commit-config.yaml",
    ".gitleaks.toml",  # downstream keeps its own security workflow; ship the config it reads
    ".gitleaks-vendor.toml",  # vendor rules extended by .gitleaks.toml
)
PUBLISH_DIRS = ("skills", "scripts", "evals")  # evals/: scripts/check-evals.py requires it

# Files the downstream keeps that must survive the sync. These are neither
# published nor deleted -- they are preserved as-is when present in the target.
PRESERVE_DOWNSTREAM = (
    ".github/workflows/security.yml",
)

# Excluded even though their parent directory is published.
# These read from docs/, which is upstream-only process material, so they cannot
# run downstream. gate() independently detects this class of breakage.
EXCLUDE_PATHS = (
    "scripts/check-readme-branding.py",      # asserts upstream branding
    "scripts/check-audit-rule-contract.py",  # reads docs/skill-tests/
    "scripts/check-runtime-intake-safety.py",
    "scripts/test-runtime-intake-safety.py",  # imports the checker above
    "scripts/publish-jnpr.py",                # upstream tooling; not part of the distribution
)

FORBIDDEN = re.compile(r"mechub|fastrevmd|violet", re.IGNORECASE)

# Citations of real field evidence, kept deliberately: stripping the URL turns a
# sourced claim into a bare assertion, which is the failure mode these skills exist
# to prevent. Attribution in the footer is an MIT courtesy, not branding.
# The rust-junosmcp slug is the source of a cited tool dependency.
PROVENANCE_OK = re.compile(
    "(?:" + re.escape(UPSTREAM_SLUG) + "|" + re.escape("mechubsec/rustjunosmcp") + ")"
)

# Nested metadata.sources[].author entries are left as the upstream author on
# purpose -- they credit whoever did the underlying lab work, and rewriting them
# would attribute that evidence to the downstream org. They are provenance, not
# branding, so the gate must not treat them as a leak.
SOURCE_ATTRIBUTION_LINE = re.compile(r"^\s+author:\s*fastrevmd-lab\s*$")

# Lab-specific values that are fine upstream but must not ship downstream.
SANITIZE = (
    ("O=mechub", "O=example"),
)

BROKEN_LINK = re.compile(r"\]\((?:\./)?docs/")


def run(args: list[str], cwd: Path | None = None, env: dict[str, str] | None = None) -> str:
    """Run a command, returning stdout; raises CalledProcessError on failure."""
    return subprocess.run(
        args, cwd=cwd, env=env, check=True, capture_output=True, text=True
    ).stdout


def head_sha() -> str:
    """Return the full SHA of upstream HEAD."""
    return run(["git", "rev-parse", "HEAD"], cwd=ROOT).strip()


def working_tree_is_clean() -> bool:
    """True when there are no staged or unstaged changes."""
    return not run(["git", "status", "--porcelain"], cwd=ROOT).strip()


def archive_ref(allow_dirty: bool) -> tuple[str, bool]:
    """Return (ref to export, whether it differs from HEAD).

    With --allow-dirty the export must be the working tree, so it is captured by
    building a throwaway index rather than with `git stash create`. A stash
    commit holds only tracked changes -- untracked files hang off a separate
    parent and never appear in `git archive` -- so a newly added, uncommitted
    skill would have been silently omitted while the provenance claimed a clean,
    reproducible HEAD. Writing a tree from a scratch index picks up tracked
    modifications, deletions, and untracked files alike, still honours
    .gitignore, and leaves the real index untouched.

    Comparing that tree to HEAD's is also an exact dirtiness test, rather than
    inferring it from the flag.
    """
    head_tree = run(["git", "rev-parse", "HEAD^{tree}"], cwd=ROOT).strip()
    if not allow_dirty:
        return "HEAD", False

    with tempfile.TemporaryDirectory(prefix="publish-jnpr-index-") as tmp:
        env = {**os.environ, "GIT_INDEX_FILE": str(Path(tmp) / "index")}
        try:
            run(["git", "read-tree", "HEAD"], cwd=ROOT, env=env)
            run(["git", "add", "-A"], cwd=ROOT, env=env)
            tree = run(["git", "write-tree"], cwd=ROOT, env=env).strip()
        except subprocess.CalledProcessError as error:
            raise SystemExit(
                f"could not snapshot the working tree for a dirty export: "
                f"{error.stderr.strip() or error}"
            ) from error
    return tree, tree != head_tree


def stage_tree(dest: Path, ref: str) -> None:
    """Export tracked files at ref into dest, then apply the allowlist."""
    dest.mkdir(parents=True, exist_ok=True)
    # A fixed name beside dest would truncate, then delete, an unrelated file
    # that happened to sit there. Keep the archive in its own temp directory.
    with tempfile.TemporaryDirectory(prefix="publish-jnpr-archive-") as tmp:
        archive = Path(tmp) / "export.tar"
        with archive.open("wb") as handle:
            subprocess.run(
                ["git", "archive", "--format=tar", ref],
                cwd=ROOT, check=True, stdout=handle,
            )
        run(["tar", "-xf", str(archive), "-C", str(dest)])

    keep = {Path(name) for name in PUBLISH_FILES}
    for path in sorted(dest.rglob("*"), reverse=True):
        rel = path.relative_to(dest)
        if path.is_dir():
            if not any(path.iterdir()):
                path.rmdir()
            continue
        allowed = rel in keep or rel.parts[0] in PUBLISH_DIRS
        if not allowed or str(rel) in EXCLUDE_PATHS:
            path.unlink()

    for cache in dest.rglob("__pycache__"):
        shutil.rmtree(cache, ignore_errors=True)


def load_reviewed_count(staged: Path) -> int:
    """Load the reviewed count from skills/inventory.json in the staged tree."""
    inventory_path = staged / "skills" / "inventory.json"
    if not inventory_path.is_file():
        raise SystemExit(f"cannot find {inventory_path} in staged tree")

    with inventory_path.open(encoding="utf-8") as f:
        manifest = json.load(f)

    return sum(1 for skill in manifest if skill.get("reviewed", False))


def brand_block(name: str, **fields: str) -> str:
    """Load a neutral brand block template and fill its {PLACEHOLDERS}."""
    text = (BRAND_DIR / f"brand-{name}-neutral.md").read_text(encoding="utf-8").rstrip("\n")
    for key, value in fields.items():
        text = text.replace("{" + key + "}", value)
    return text


def swap_marked_block(text: str, name: str, replacement: str) -> str:
    """Replace the content between <!-- brand:NAME:start/end --> markers."""
    pattern = re.compile(
        rf"<!-- brand:{name}:start -->\n.*?\n<!-- brand:{name}:end -->",
        re.DOTALL,
    )
    if not pattern.search(text):
        raise SystemExit(f"README.md is missing the brand:{name} markers")
    return pattern.sub(lambda _: replacement, text)


def transform_readme(dest: Path, repo_slug: str, skill_count: int, reviewed_count: int) -> None:
    """Swap branded blocks for neutral ones and repoint upstream-only links."""
    path = dest / "README.md"
    text = path.read_text(encoding="utf-8")
    repo_name = repo_slug.split("/")[-1]

    # Sweep first: clone URLs, installer URLs, issue links all point downstream.
    # The brand blocks swapped in below deliberately reintroduce upstream credit.
    text = text.replace(UPSTREAM_SLUG, repo_slug)
    # The clone directory is named after the repo, so the `cd` that follows the
    # clone must follow the rewritten slug too or the quickstart fails.
    upstream_name = UPSTREAM_SLUG.split("/")[-1]
    text = re.sub(
        rf"^cd {re.escape(upstream_name)}$", f"cd {repo_name}", text, flags=re.MULTILINE
    )

    text = swap_marked_block(
        text, "header",
        brand_block(
            "header",
            REPO_NAME=repo_name,
            SKILL_COUNT=str(skill_count),
            REVIEWED_COUNT=str(reviewed_count),
        ),
    )
    text = swap_marked_block(text, "disclaimer", brand_block("disclaimer"))
    text = swap_marked_block(text, "trademark", brand_block("trademark"))
    text = swap_marked_block(text, "footer", brand_block("footer"))

    path.write_text(repoint_docs_links(text), encoding="utf-8")


def repoint_docs_links(text: str) -> str:
    """Point ./docs/ links at upstream, where they still resolve.

    docs/ is upstream-only, so a published copy that keeps the relative link
    ships a 404. gate() fails the run on any such link rather than trusting
    this transform to have caught them all.
    """
    return BROKEN_LINK.sub(f"](https://github.com/{UPSTREAM_SLUG}/blob/main/docs/", text)


def transform_quality(dest: Path) -> None:
    """Repoint the review history's skill-test links; it carries no brand blocks."""
    path = dest / "QUALITY.md"
    path.write_text(repoint_docs_links(path.read_text(encoding="utf-8")), encoding="utf-8")


def transform_contributors(dest: Path) -> None:
    """Neutralize the maintainer handle and repoint CONTRIBUTING.md link."""
    path = dest / "CONTRIBUTORS.md"
    if not path.is_file():
        return

    text = path.read_text(encoding="utf-8")
    # Replace the maintainer line with upstream provenance
    text = re.sub(
        r"\[fastrevmd-lab\]\(https://github\.com/fastrevmd-lab\)",
        f"Maintained upstream at [{UPSTREAM_SLUG}](https://github.com/{UPSTREAM_SLUG})",
        text,
    )
    # Repoint CONTRIBUTING.md to upstream (not published downstream)
    text = text.replace(
        "[CONTRIBUTING.md](CONTRIBUTING.md)",
        f"[CONTRIBUTING.md](https://github.com/{UPSTREAM_SLUG}/blob/main/CONTRIBUTING.md)"
    )
    path.write_text(text, encoding="utf-8")


def transform_changelog(dest: Path) -> None:
    """Repoint the changelog's skill-test links; it carries no brand blocks.

    Release notes cite validation records under docs/, which is upstream-only,
    for the same reason QUALITY.md does. Without this the gate fails the run.

    Targeted rewrites neutralize historical org references in release notes.
    """
    path = dest / "CHANGELOG.md"
    text = repoint_docs_links(path.read_text(encoding="utf-8"))
    # v1.8.0 Hygiene line mentions the upstream org and its shared workflow
    text = text.replace(
        "the shared mechubsec gitleaks workflow",
        "a shared gitleaks workflow"
    )
    text = text.replace(
        "the `mechubsec` organization",
        "the upstream organization"
    )
    # Repoint TODO.md (unpublished) to upstream
    text = text.replace(
        "](./TODO.md)",
        f"](https://github.com/{UPSTREAM_SLUG}/blob/main/TODO.md)"
    )
    path.write_text(text, encoding="utf-8")


def pad_to_width(line: str, old: str, new: str) -> str:
    """Swap old->new inside a box-drawn banner line, preserving its display width.

    Padding is adjusted against the closing bar, so a shorter or longer slug does
    not shear the box. Box characters are single-column, so len() is the width.
    """
    if old not in line or "\u2551" not in line:
        return line
    swapped = line.replace(old, new)
    delta = len(line) - len(swapped)
    if delta == 0:
        return swapped
    head, bar, tail = swapped.rpartition("\u2551")
    if delta > 0:
        return head + " " * delta + bar + tail
    return re.sub(r" {0,%d}$" % -delta, "", head) + bar + tail


def transform_install(dest: Path, repo_slug: str) -> None:
    """Repoint the installer at the downstream repo."""
    path = dest / "install.sh"
    out: list[str] = []
    for line in path.read_text(encoding="utf-8").split("\n"):
        line = pad_to_width(line, UPSTREAM_SLUG, repo_slug)
        out.append(line.replace(UPSTREAM_SLUG, repo_slug))
    path.write_text("\n".join(out), encoding="utf-8")
    path.chmod(0o755)


def transform_skill_frontmatter(dest: Path, author: str) -> None:
    """Rewrite only the top-level author list in every published SKILL.md.

    Scoped deliberately. `metadata.sources[].author` credits the person who did
    the underlying lab work, and rewriting those would attribute upstream field
    evidence to the downstream org -- a false provenance claim, and the exact
    thing these skills exist to prevent. Only the package's own author list,
    which is a top-level key with two-space list items, is rewritten.
    """
    for skill in sorted((dest / "skills").rglob("SKILL.md")):
        lines = skill.read_text(encoding="utf-8").split("\n")
        if not lines or lines[0].strip() != "---":
            continue
        try:
            end = lines.index("---", 1)
        except ValueError:
            continue

        in_author_block = False
        for index in range(1, end):
            line = lines[index]
            if not line.startswith((" ", "\t")) and line.rstrip().endswith(":"):
                in_author_block = line.rstrip() == "author:"
                continue
            if in_author_block and line == "  - fastrevmd-lab":
                lines[index] = f"  - {author}"
        skill.write_text("\n".join(lines), encoding="utf-8")


def transform_skill_checker(dest: Path, author: str) -> None:
    """Point the package checker at the downstream author it will actually see."""
    path = dest / "scripts" / "check-skill-packages.py"
    if not path.is_file():
        return
    text = re.sub(r'"fastrevmd-lab"', f'"{author}"', path.read_text(encoding="utf-8"))
    path.write_text(text, encoding="utf-8")


def sanitize(dest: Path) -> None:
    """Strip lab-specific values that carry no meaning downstream."""
    for path in sorted(dest.rglob("*")):
        if not path.is_file() or path.suffix not in {".md", ".py", ".sh"}:
            continue
        text = path.read_text(encoding="utf-8")
        updated = text
        for needle, replacement in SANITIZE:
            updated = updated.replace(needle, replacement)
        if updated != text:
            path.write_text(updated, encoding="utf-8")


def transform_justfile(dest: Path) -> None:
    """Drop recipe lines invoking checks that do not ship downstream."""
    dropped = {Path(p).name for p in EXCLUDE_PATHS}
    path = dest / "justfile"
    kept = [
        line for line in path.read_text(encoding="utf-8").split("\n")
        if not any(name in line for name in dropped)
    ]
    path.write_text("\n".join(kept), encoding="utf-8")


def write_provenance(dest: Path, sha: str, dirty: bool, skills: list[str]) -> None:
    """Record what this copy was built from, so the next sync knows the delta.

    A dirty export comes from a `git stash create` object, not HEAD, so naming
    HEAD would point the next sync at a revision that cannot reproduce this
    tree. Say so instead.
    """
    provenance = (
        f"- Upstream commit: `{sha}`\n" if not dirty else
        f"- Upstream commit: `{sha}` **plus uncommitted changes** -- this export\n"
        f"  was taken from the working tree and cannot be reproduced from that\n"
        f"  commit. Re-publish from a clean tree before relying on it.\n"
    )
    (dest / "UPSTREAM.md").write_text(
        "# Upstream\n\n"
        f"This repository is a de-branded distribution of [{UPSTREAM_SLUG}]"
        f"(https://github.com/{UPSTREAM_SLUG}), published under the MIT License.\n\n"
        f"{provenance}"
        f"- Skills published: {len(skills)}\n\n"
        "Changes are made upstream and synced here one-way by "
        "`scripts/publish-jnpr.py`. Downstream fixes are welcome; they are "
        "carried back upstream by hand so that authorship stays unambiguous.\n",
        encoding="utf-8",
    )


def scrub_source_attribution(rel: Path, text: str) -> str:
    """Blank out author lines that sit under metadata.sources in SKILL.md frontmatter.

    Scoped rather than global: an indented `author: fastrevmd-lab` anywhere else
    is branding that must still trip the gate, so only entries proven to be
    inside the sources block are exempt.
    """
    if rel.name != "SKILL.md":
        return text
    lines = text.split("\n")
    if not lines or lines[0].strip() != "---":
        return text
    try:
        end = lines.index("---", 1)
    except ValueError:
        return text

    in_metadata = False
    in_sources = False
    for index in range(1, end):
        line = lines[index]
        indent = len(line) - len(line.lstrip())
        if line.strip() and indent == 0:
            in_metadata = line.rstrip() == "metadata:"
            in_sources = False
            continue
        if in_metadata and indent == 2 and line.strip() == "sources:":
            in_sources = True
            continue
        if in_metadata and in_sources and indent <= 2 and line.strip():
            in_sources = False
        if in_sources and SOURCE_ATTRIBUTION_LINE.match(line):
            lines[index] = ""
    return "\n".join(lines)


def _check_gitleaks_extend(config_path: Path, staged_root: Path) -> list[str]:
    """Check if a gitleaks config's [extend] path target exists in the staged tree.

    Returns a list of violations (empty if all extend targets are present).
    """
    import tomllib

    violations: list[str] = []
    rel = config_path.relative_to(staged_root)

    try:
        with config_path.open("rb") as f:
            data = tomllib.load(f)
    except (tomllib.TOMLDecodeError, OSError) as e:
        violations.append(f"{rel}: could not parse TOML: {e}")
        return violations

    extend = data.get("extend")
    if not extend or not isinstance(extend, dict):
        return violations

    path_value = extend.get("path")
    if not path_value or not isinstance(path_value, str):
        return violations

    # Resolve the extend path relative to the config file's directory
    config_dir = config_path.parent
    target_path = (config_dir / path_value).resolve()

    if not target_path.is_file():
        violations.append(
            f"{rel}: [extend] path = {path_value!r} does not exist in the staged tree"
        )

    return violations


def _load_staged_module(path: Path, name: str):
    """Import a staged module without writing bytecode to the staged tree.

    Sets sys.dont_write_bytecode for the duration so no __pycache__ is created.
    """
    import importlib.util
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise SystemExit(f"cannot import {path}")

    prev_dont_write = sys.dont_write_bytecode
    try:
        sys.dont_write_bytecode = True
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    finally:
        sys.dont_write_bytecode = prev_dont_write


def regenerate_checksums(dest: Path) -> None:
    """Regenerate skills/CHECKSUMS.sha256 for the staged tree after transformations.

    The staged tree's skills/ files are transformed (frontmatter rewritten,
    sanitized), so the checksum manifest must be regenerated to match. install.sh
    refuses a payload whose manifest does not match byte-for-byte.
    """
    gen_script = dest / "scripts" / "gen-checksums.py"
    if not gen_script.is_file():
        raise SystemExit("cannot regenerate checksums: gen-checksums.py not published")

    gen = _load_staged_module(gen_script, "gen_checksums")

    skills_dir = dest / "skills"
    manifest = gen.generate(skills_dir)
    manifest_path = skills_dir / gen.MANIFEST_NAME
    manifest_path.write_text(manifest, encoding="utf-8")


def gate(dest: Path) -> list[str]:
    """Fail-closed verification. Returns human-readable violations."""
    violations: list[str] = []
    for path in sorted(dest.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(dest)
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            violations.append(f"{rel}: binary file in published tree")
            continue

        scrubbed = PROVENANCE_OK.sub("", scrub_source_attribution(rel, text))
        for number, line in enumerate(scrubbed.split("\n"), start=1):
            if FORBIDDEN.search(line):
                violations.append(f"{rel}:{number}: forbidden token -> {line.strip()[:90]}")
        if path.suffix == ".py" and rel.parts[0] == "scripts" and re.search(r'"docs"|docs/', text):
            violations.append(f"{rel}: published script depends on unpublished docs/")
        if path.suffix == ".md":
            for number, line in enumerate(text.split("\n"), start=1):
                if BROKEN_LINK.search(line):
                    violations.append(f"{rel}:{number}: link into unpublished docs/")

        # Verify gitleaks config extend targets are present in the staged tree
        if path.suffix == ".toml" and path.name.startswith(".gitleaks"):
            violations.extend(_check_gitleaks_extend(path, dest))

    # Verify that the staged checksum manifest matches the staged skills/ tree.
    # This catches a manifest that was either not regenerated after transforms or
    # was regenerated incorrectly.
    gen_script = dest / "scripts" / "gen-checksums.py"
    if gen_script.is_file():
        gen = _load_staged_module(gen_script, "gen_checksums")
        skills_dir = dest / "skills"
        manifest_path = skills_dir / gen.MANIFEST_NAME
        if manifest_path.is_file():
            expected = gen.generate(skills_dir)
            actual = manifest_path.read_text(encoding="utf-8")
            if expected != actual:
                violations.append(
                    "skills/CHECKSUMS.sha256 does not match the staged skills/ tree; "
                    "regenerate_checksums() was not called or ran incorrectly"
                )

    # Fail-closed: detect any bytecode that leaked into the staged tree.
    # This must run after the manifest check above, since that imports a staged
    # module, so ordering matters even though the import itself is now guarded.
    for path in sorted(dest.rglob("*")):
        if path.is_file() and (path.suffix == ".pyc" or path.name == "__pycache__"):
            rel = path.relative_to(dest)
            violations.append(f"{rel}: bytecode file in staged tree")
        elif path.is_dir() and path.name == "__pycache__":
            rel = path.relative_to(dest)
            violations.append(f"{rel}/: __pycache__ directory in staged tree")

    return violations


def remote_slug(url: str) -> str | None:
    """Normalize a git remote URL to owner/repo, lowercased.

    A substring test is not enough: `JNPRAutomate/fw-skills-share` is a substring
    of `JNPRAutomate/fw-skills-share-backup`, and accepting the wrong clone means
    staging the deletion of every tracked file in it.
    """
    cleaned = url.strip().removesuffix(".git")
    match = re.search(r"[:/]([^/:]+)/([^/]+)$", cleaned)
    return f"{match.group(1)}/{match.group(2)}".lower() if match else None


def validate_target(target: Path, repo_slug: str) -> str | None:
    """Check everything about the target that can refuse the run, mutating nothing.

    Split out from sync_to_target so it can run before the export is staged.
    Left inside, a bad target was only detected after stage_tree() had already
    written the export, so a refused run still left generated files behind.

    Returns an error message, or None when the target is usable.
    """
    # `.git` is a file, not a directory, inside a linked worktree -- and this repo
    # uses worktrees -- so test with git itself rather than by inspecting the path.
    probe = subprocess.run(
        ["git", "rev-parse", "--is-inside-work-tree"],
        cwd=target, capture_output=True, text=True,
    )
    if probe.returncode != 0 or probe.stdout.strip() != "true":
        return f"not a git working tree: {target}"
    if target == ROOT or target in ROOT.parents or ROOT in target.parents:
        return f"refusing to sync into the upstream repo or a path containing it: {target}"
    try:
        remote = run(["git", "remote", "get-url", "origin"], cwd=target).strip()
    except subprocess.CalledProcessError:
        return f"target has no origin remote to verify: {target}"
    if remote_slug(remote) != repo_slug.lower():
        return f"target origin {remote!r} does not match --repo-slug {repo_slug!r}"
    if run(["git", "status", "--porcelain"], cwd=target).strip():
        return f"target clone has uncommitted changes: {target}"
    return None


def ignored_collisions(staged: Path, target: Path) -> list[str]:
    """Return target paths holding ignored files that the export would overwrite.

    `git rm` leaves ignored files alone and `git status` never reports them, so
    they survive the removal step and then get clobbered by the copy. That
    contradicts the preservation this sync promises, and the loss is silent and
    unrecoverable -- the file was never in git. Detect the overlap and refuse.
    """
    candidates = [
        str(path.relative_to(staged))
        for path in staged.rglob("*")
        if path.is_file() and (target / path.relative_to(staged)).is_file()
    ]
    if not candidates:
        return []
    result = subprocess.run(
        ["git", "check-ignore", "--stdin"],
        cwd=target, input="\n".join(candidates),
        capture_output=True, text=True,
    )
    # exit 0 = some ignored, 1 = none ignored, >1 = real error
    if result.returncode > 1:
        raise SystemExit(f"could not check ignored paths in {target}: {result.stderr.strip()}")
    return sorted(line for line in result.stdout.split("\n") if line.strip())


def sync_to_target(staged: Path, target: Path, sha: str, dirty: bool, repo_slug: str, commit: bool) -> None:
    """Mirror the staged tree into a target clone as a single squashed commit.

    Stale files are removed with `git rm`, never with a recursive filesystem
    delete. That keeps every removal recoverable from git history and leaves
    untracked and ignored files (a local .env, for instance) alone -- a plain
    wipe would take those with it, and `git status --porcelain` would not even
    have shown them.

    The target is revalidated here even though main() already checked it.
    Staging and gating take time and the clone is not held, so between the
    preflight and this point another process can dirty it, change its remote,
    or add untracked files the copy would overwrite. Check once to fail early,
    again immediately before mutating.
    """
    problem = validate_target(target, repo_slug)
    if problem:
        raise SystemExit(problem)
    collisions = ignored_collisions(staged, target)
    if collisions:
        listed = "\n  ".join(collisions[:10])
        more = f"\n  ... and {len(collisions) - 10} more" if len(collisions) > 10 else ""
        raise SystemExit(
            "refusing to sync: these target paths hold ignored local files that the "
            f"export would overwrite:\n  {listed}{more}\n"
            "Move or delete them, or drop them from the export."
        )

    # Save downstream-specific files before removing everything.
    preserved: dict[str, bytes] = {}
    for rel in PRESERVE_DOWNSTREAM:
        path = target / rel
        if path.is_file():
            preserved[rel] = path.read_bytes()

    if run(["git", "ls-files"], cwd=target).strip():
        run(["git", "rm", "-r", "-q", "--", "."], cwd=target)

    ignore = shutil.ignore_patterns("__pycache__", "*.pyc")
    for entry in staged.iterdir():
        dst = target / entry.name
        if entry.is_dir():
            # dirs_exist_ok: `git rm` leaves a directory behind when it still
            # holds ignored files (a stray __pycache__), and a plain copytree
            # would raise FileExistsError in exactly the case this preserves.
            shutil.copytree(entry, dst, ignore=ignore, dirs_exist_ok=True)
        else:
            shutil.copy2(entry, dst)

    # Restore downstream-specific files the sync must not touch.
    for rel, content in preserved.items():
        path = target / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)

    run(["git", "add", "-A"], cwd=target)
    if not run(["git", "status", "--porcelain"], cwd=target).strip():
        print("target already matches upstream; nothing to commit")
        return
    if not commit:
        print(f"staged into {target} (not committed; pass --commit)")
        return

    message = (
        f"chore: sync skills from upstream\n\n"
        f"De-branded export of {UPSTREAM_SLUG}.\n\n"
        f"Upstream-Commit: {sha}\n"
    )
    run(["git", "commit", "-m", message], cwd=target)
    print(f"committed to {target}")
    print("\nReview, then push yourself:")
    print(f"  git -C {target} push origin HEAD")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--repo-slug", default="JNPRAutomate/fw-skills-share",
                        help="downstream org/repo (default: %(default)s)")
    parser.add_argument("--author", default="JNPRAutomate",
                        help="value for the authors: frontmatter field")
    parser.add_argument("--out", type=Path, help="keep the staged tree at this path")
    parser.add_argument("--target", type=Path, help="local clone of the downstream repo")
    parser.add_argument("--commit", action="store_true", help="commit in the target clone")
    parser.add_argument("--allow-dirty", action="store_true",
                        help="publish from a dirty working tree (not recommended)")
    args = parser.parse_args()

    if not args.allow_dirty and not working_tree_is_clean():
        print("ERROR: working tree is dirty; commit first or pass --allow-dirty", file=sys.stderr)
        return 1

    sha = head_sha()
    ref, dirty = archive_ref(args.allow_dirty)

    # Everything that can refuse the run happens before a single file is
    # written. The refusal inside sync_to_target() is too late on its own: with
    # --out pointing inside --target, staging populates the target before the
    # sync is ever called.
    if args.target:
        target = args.target.resolve()
        problem = validate_target(target, args.repo_slug)
        if problem:
            print(f"ERROR: {problem}", file=sys.stderr)
            return 1
        if dirty and args.commit:
            print("ERROR: refusing to commit a dirty export: the trailer would name a "
                  "commit that cannot reproduce this tree. Re-run from a clean working "
                  "tree.", file=sys.stderr)
            return 1
        if args.out:
            out = args.out.resolve()
            if out == target or target in out.parents or out in target.parents:
                print(f"ERROR: --out {out} overlaps --target {target}; staging would "
                      "write into the clone being synced.", file=sys.stderr)
                return 1

    scratch = Path(tempfile.mkdtemp(prefix="publish-jnpr-"))
    staged = args.out.resolve() if args.out else scratch / "tree"
    if staged.exists() and any(staged.iterdir()):
        print(f"ERROR: --out path is not empty, refusing to write into it: {staged}",
              file=sys.stderr)
        return 1

    try:
        stage_tree(staged, ref)
        skills = sorted(p.name for p in (staged / "skills").iterdir() if p.is_dir())
        reviewed_count = load_reviewed_count(staged)
        transform_readme(staged, args.repo_slug, len(skills), reviewed_count)
        transform_quality(staged)
        transform_changelog(staged)
        transform_contributors(staged)
        transform_install(staged, args.repo_slug)
        transform_skill_frontmatter(staged, args.author)
        transform_skill_checker(staged, args.author)
        transform_justfile(staged)
        sanitize(staged)
        write_provenance(staged, sha, dirty, skills)

        # Regenerate the checksum manifest after all transforms that modify skills/.
        # The staged tree's SKILL.md files have been rewritten (author, sanitize),
        # so the manifest must match the transformed tree, not the upstream one.
        regenerate_checksums(staged)

        violations = gate(staged)
        if violations:
            print(f"ERROR: de-branding gate failed ({len(violations)} violation(s)):", file=sys.stderr)
            for violation in violations:
                print(f"  {violation}", file=sys.stderr)
            return 1

        print(f"OK: staged {len(skills)} skill(s) from {sha[:12]}, de-branding gate clean")
        print(f"    tree: {staged}")

        if args.target:
            sync_to_target(staged, args.target.resolve(), sha, dirty, args.repo_slug, args.commit)
        else:
            print("    dry run -- pass --target <clone> to sync")
    except SystemExit:
        shutil.rmtree(scratch, ignore_errors=True)
        raise
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
