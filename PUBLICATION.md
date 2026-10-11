# Published release

Published 2026-10-11 to the user-requested private destinations.

- Models: https://huggingface.co/giux78/nev/tree/c5c84121263b423f8846811a24790ab96e66cee3
- Model revision: `c5c84121263b423f8846811a24790ab96e66cee3`
- Separate standalone folders: `v2/` and `v3/`.
- Code: https://github.com/mii-llm/nev
- Initial code release: `68ee8ae5642f99bd9c0e8636280cc1f7438e6abd`. Subsequent documentation records this model revision.
- Hugging Face privacy and remote weight sizes/LFS SHA-256 were checked after upload. All evaluated core hashes are unchanged.
- GitHub's existing private visibility was preserved.

The upload used the existing LUMI credential; no A100 transfer was needed.
The initial launcher stalled in environment module startup. The corrected
uploader ran directly in the same container without loading GPU binding modules.
This affected publishing only, not the evaluated weights or runtime.

See `docs/nesso2/evidence/huggingface-publication.json` for the completion receipt.
The exact root Hugging Face card is preserved in `models/README.md`; variant
cards are in `models/v2/README.md` and `models/v3/README.md`.

Validation for the code snapshot: all Python files parsed, all JSON files parsed,
17 frozen runtime source hashes verified, local Markdown links resolved, six
comparison/regression tests passed, and the source snapshot was checked for
embedded token/private-key patterns. The earlier GPU inference/export checks
are recorded in `smoke-report.json` and `EXPORT_COMPARISON.md`.
