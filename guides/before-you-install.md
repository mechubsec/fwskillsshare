# Before you install

[Back to the README](../README.md)

These skills change how your agent behaves. Read this before you install.

**A skill is instructions your agent will follow.** Every `SKILL.md` here is plain
markdown that gets loaded into your agent's context and acted on. Installing one —
from this repo or any other — means letting someone else's text steer a tool that
can read your configs and, if you permit it, reach your devices. **Read the whole skill
directory before you install it — not just `SKILL.md`.** Most of a skill is markdown
you can read straight through, but the two Proxmox deployment skills also ship Python
helpers under `scripts/` that the instructions tell the agent to run, and every skill
carries an `agents/openai.yaml`. Nothing is obfuscated or generated at runtime, but
"read the skill" has to mean the directory, not one file. Some skills also direct the
agent at your own equipment — the deployment and operational ones run commands
against your devices, which is the point of them, and the reason to know what you
installed.

**Treat every config you paste as untrusted input.** The parsing and audit skills
ingest whatever you hand them, and a config file can carry text written to redirect
the agent — in a comment, a description field, an object name. That is prompt
injection, and nothing in this repository defends against it. Read what comes back:
if the agent proposes something you did not ask for, or reaches for a device when
you asked for a parse, stop.

These skills default to parse / read / analyze / plan / dry-run, and anything that
changes a device — configuration, commits, upgrades, reboots, failovers — is written
to require explicit approval and post-change verification. That is authoring intent,
not a sandbox. What actually constrains the agent is the permissions you give it.

**Do not paste secrets you would not send to your model provider.** Firewall configs
carry pre-shared keys, SNMP communities, RADIUS secrets, certificate material, and
password hashes. Pasting a config into a hosted assistant discloses it to whoever
runs that model. That may be perfectly fine — but make it a decision you took, not
one you backed into. If the policy you are working on should not leave your control,
you have two options:

- **Sanitize first, carefully.** An anonymizer can rewrite addresses, hostnames and
  secrets, but it has to preserve address *semantics* — a consistent, containment-
  preserving mapping. The audits reason about real relationships: shadowed and
  overlapping rules, supernets, `0.0.0.0/0`, host versus subnet. An anonymizer that
  changes prefix lengths or breaks containment will hand you a clean-looking report
  about a policy you do not have. Read the output before you paste it, too: no
  anonymizer knows which of your zone, object, or policy names are themselves
  sensitive.
- **Or keep it on your own equipment.** These skills are plain markdown with no
  runtime dependency on any particular provider, so they work with a model you host
  yourself. Nothing here needs a hosted assistant to function.

**Install only the skills you need.** A skill's body loads only when the skill is
invoked, so what an installed-but-unused skill costs you is its description sitting
in the discovery surface. How much that costs depends on the runtime and version —
Codex 0.147.0 routes discovery through a dynamic selector and treats a flat
concatenated list as a fallback, truncating metadata to fit its budget rather than
failing — so the direct token cost is modest and not worth optimizing: all 33
descriptions together are on the order of ten thousand characters, and
`scripts/check-skill-packages.py` reports the current figure rather than this page
pinning a number that goes stale. The cost that matters is **selection**: the more
overlapping descriptions compete, the likelier your agent reaches for a near-miss
instead of the right skill, and truncation degrades that quietly rather than
visibly. Install the families you actually use.

**Skills are copied, not linked.** The installer copies files into your skills
directory, so they do not change when this repository does. Re-run the installer to
pick up updates — approving the overwrite when prompted, or passing `--force`, since
a non-interactive run (`-y`) skips a skill that is already installed and would
otherwise leave you on a stale copy.

**Verify against your own platform and release.** Behavior here is reported as
observed on specific versions. Commit-check on your release before trusting a stanza
in production.
