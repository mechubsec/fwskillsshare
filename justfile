set dotenv-load := false
set export := false

setup:
    pre-commit install

dev:
    python3 scripts/check-skill-packages.py

fmt:
    git diff --check

lint:
    python3 scripts/sync-installer-inventory.py --check
    python3 scripts/check-inventory.py
    python3 scripts/check-catalog-counts.py
    python3 scripts/check-skill-packages.py
    python3 scripts/check-markdown-links.py
    python3 scripts/test-runtime-intake-validator.py
    python3 scripts/check-runtime-intake.py
    python3 scripts/check-runtime-intake-safety.py
    python3 scripts/test-runtime-intake-safety.py
    python3 scripts/check-readme-branding.py
    python3 scripts/check-checksums.py
    python3 scripts/check-evals.py

test:
    python3 scripts/test-inventory.py
    python3 scripts/test-skill-packages.py
    python3 scripts/test-markdown-links.py
    python3 scripts/check-shared-schema.py
    python3 scripts/check-installer.py
    python3 scripts/test-installer-supply-chain.py
    python3 scripts/test-codex-review-optin.py
    python3 scripts/test-codex-review-verdict.py
    python3 scripts/check-sd-bundle-server.py
    python3 scripts/check-srx-policy-global-default.py
    python3 scripts/check-audit-rule-contract.py
    python3 scripts/check-srx-stig-catalog.py
    python3 scripts/check-srx-stig-behavior.py
    python3 scripts/check-srx-license-signature-contract.py
    python3 scripts/test-check-evals.py

guard: lint test shell

# Stage a de-branded copy for the downstream org and verify it. Dry run by
# default; pass --target <clone> --commit to land it. Never pushes.
publish-jnpr *ARGS:
    python3 scripts/publish-jnpr.py {{ARGS}}

# Codex review gate for one commit (default: HEAD)
#
# Must go through the wrapper, not `codex exec review`: the wrapper parks the
# superpowers skill (which made seven consecutive runs end with no verdict),
# denies MCP servers, and exits non-zero when no verdict is produced. A raw
# `codex ... | jq` pipeline exits 0 on an empty stream, reporting success for a
# gate that never ran. See AGENTS.md "Codex review gate".
#
# Sends your diff to OpenAI's Codex service (off-box). Requires explicit
# opt-in: FWSKILLS_ALLOW_CODEX_REVIEW=1 just review
review COMMIT="HEAD":
    scripts/codex-review.sh "$(git rev-parse {{COMMIT}})"

integration:
    @echo "Real-device validation is intentionally opt-in and is not automated by this repository."

e2e:
    ./install.sh --help >/dev/null
    python3 scripts/test-installer.py
    python3 scripts/check-installer.py

# Shell linting. install.sh is the only shell in the tree besides the codex
# review wrapper; both are expected to stay shellcheck-clean.
shell:
    shellcheck install.sh scripts/*.sh

# Trivy runs all three scanners, but this repository has no dependency
# manifests or configuration files the vuln/misconfig scanners recognize, so a
# clean run attests to secret hygiene only. See QUALITY.md.
security:
    trivy fs --scanners vuln,misconfig,secret --exit-code 1 .

release-check: lint test guard security
