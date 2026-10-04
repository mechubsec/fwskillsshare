# Runtime Intake

## Contents

- [When to ask](#when-to-ask)
- [Tool adaptation](#tool-adaptation)
- [Question catalog](#question-catalog)

## When to ask

Use this catalog only after inspecting the request and evidence. Ask an entry
when its `ask_when` condition is true and the answer would materially affect
the result. Skip answered or irrelevant entries. Prioritize safety, scope,
platform or framework basis, evidence quality, then output preference.

## Tool adaptation

- Claude: select at most three neutral entries, project each to only `question`,
  `header`, and `options`, then add `multiSelect: false`; do not send `id` or
  `ask_when`.
- Codex: select at most three neutral entries and project each to only `id`,
  `header`, `question`, and `options`; do not send `ask_when` or `multiSelect`.
- Fallback: ask the same questions in concise plain text with a free-text
  `Other` path.
- Never request secrets.

## Question catalog

```json
{
  "questions": [
    {
      "id": "convert_source",
      "ask_when": "The source platform cannot be determined confidently.",
      "header": "Source",
      "question": "How should an ambiguous source platform be handled?",
      "options": [
        {
          "label": "Confirm platform first (Recommended)",
          "description": "Confirm the vendor and platform before platform-specific conversion."
        },
        {
          "label": "Use supplied exact platform",
          "description": "Use the exact platform supplied through `Other`."
        },
        {
          "label": "Analyze as unknown source",
          "description": "Parse conservatively, report ambiguity, and avoid implementation-ready conversion."
        }
      ]
    },
    {
      "id": "convert_target",
      "ask_when": "The exact target is absent.",
      "header": "Target",
      "question": "What exact target vendor and platform should receive the conversion?",
      "options": [
        {
          "label": "Specify target (Recommended)",
          "description": "Supply the exact target through Other."
        },
        {
          "label": "Family only",
          "description": "Generate conservative family-level output."
        },
        {
          "label": "Undecided",
          "description": "Produce feasibility analysis only."
        }
      ]
    },
    {
      "id": "convert_release",
      "ask_when": "Target model or release affects syntax or support and is absent.",
      "header": "Release",
      "question": "How should missing target model or release details be handled?",
      "options": [
        {
          "label": "Discover first (Recommended)",
          "description": "Identify the exact target model and release before conversion."
        },
        {
          "label": "Exact details supplied",
          "description": "Apply capabilities for the supplied target."
        },
        {
          "label": "Infer conservatively",
          "description": "Limit output to family-safe syntax and disclose uncertainty."
        }
      ]
    },
    {
      "id": "convert_scope",
      "ask_when": "Conversion components are absent.",
      "header": "Scope",
      "question": "What should be converted?",
      "options": [
        {
          "label": "Full migration (Recommended)",
          "description": "Convert all supported components."
        },
        {
          "label": "Policy and NAT",
          "description": "Limit work to objects, policy, and NAT."
        },
        {
          "label": "Named sections",
          "description": "Convert components named through Other."
        }
      ]
    },
    {
      "id": "convert_base",
      "ask_when": "Existing target state is unknown.",
      "header": "Baseline",
      "question": "How should uncertain target baseline state be handled?",
      "options": [
        {
          "label": "Inspect target first (Recommended)",
          "description": "Determine whether target state exists before generating configuration."
        },
        {
          "label": "Use supplied clean target",
          "description": "Generate for a supplied empty target baseline."
        },
        {
          "label": "Use supplied merge target",
          "description": "Account for a supplied existing target configuration."
        }
      ]
    },
    {
      "id": "convert_loss",
      "ask_when": "Unsupported behavior needs a disposition.",
      "header": "Fidelity",
      "question": "How should unsupported source behavior be handled?",
      "options": [
        {
          "label": "Caveat and map (Recommended)",
          "description": "Use the closest safe behavior and document loss."
        },
        {
          "label": "Manual placeholder",
          "description": "Emit an engineer-resolved placeholder."
        },
        {
          "label": "Stop on loss",
          "description": "Stop dependent output after material loss."
        }
      ]
    },
    {
      "id": "convert_output",
      "ask_when": "Deliverable format is absent.",
      "header": "Output",
      "question": "What conversion deliverable is required?",
      "options": [
        {
          "label": "Config and report (Recommended)",
          "description": "Produce candidate configuration and fidelity report."
        },
        {
          "label": "Fidelity report",
          "description": "Analyze without configuration."
        },
        {
          "label": "Config only",
          "description": "Produce syntax with compact caveats."
        }
      ]
    }
  ]
}
```
