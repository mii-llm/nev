# Published release

Current downloads are public under `mii-llm`: [Nev](https://huggingface.co/mii-llm/nev),
[Nev GGUF](https://huggingface.co/mii-llm/nev-gguf), and
[Nesso3 GGUF](https://huggingface.co/mii-llm/nesso3-0.4B-agentic-gguf).
The sections below record the initial publication history.


Published 2026-10-11 to the user-requested private destinations.

- Models: https://huggingface.co/mii-llm/nev/tree/c5c84121263b423f8846811a24790ab96e66cee3
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

## CPU GGUF release — 2026-10-14

- Historical combined package: see `experiments/cpu_gguf/results/huggingface-publication.json` (retired; use the separate public models).
- Pinned revision: `3b7b4d8d74a3bfb520f782a54033424b3ca75549`.
- Four GGUF files: Nesso3 and Nev v3, each in F16 and Q8_0.
- Original Nev FP32 decision head, tokenizers, configuration and model provenance included.
- All 14 inference artifact sizes and all seven LFS SHA-256 hashes were verified remotely, including all four GGUFs. Private visibility was verified after upload.
- Source, install/download/conversion guide, bilingual examples and tests: `experiments/cpu_gguf/`.
- Build and F16/Q8 smoke checks were rerun in the publication checkout using the existing Python environment. A fresh OS/environment installation was not tested.
- Receipt: `experiments/cpu_gguf/results/huggingface-publication.json`; exact model card: `experiments/cpu_gguf/HF_MODEL_CARD.md`.

The original model repositories and their visibility were preserved. The GGUF
release retains the original source revisions; it does not use a newer model
checkpoint or retrain/calibrate the decision head.

The pinned HF download check passed in a separate folder: all ten ancillary
files were fetched and verified; the existing Q8 pair passed remote-manifest
SHA-256 checks, then bilingual and standalone inference passed. Large GGUFs
were not redundantly downloaded. See the CPU download receipt and smoke trace.

## Independent GGUF model repositories

The user-requested distribution now separates Nev and Nesso3:

- `mii-llm/nev-gguf`: Nev v3 backbone, original FP32 decision head and tokenizer, with standalone decision instructions.
- `mii-llm/nesso3-0.4B-agentic-gguf`: Nesso3 F16/Q8 generation weights and tokenizer, with standalone generation instructions.
- Both repositories were private at initial publication and are now public under `mii-llm`. The existing GGUF artifacts were copied server-side without conversion or retraining, and their sizes/LFS hashes verified.
- GitHub retains the combined CPU workflow and adds model-selective downloads and independent smoke tests.
- `experiments/cpu_gguf/release.json` pins both repositories; `model_cards/` stores their model cards.
- `results/split-huggingface-publication.json` records the split publication; earlier combined-release receipts remain historical evidence.

The previous combined repository has been retired. Use the two separate public
releases; the original receipts remain as historical evidence.

## Public organization migration — 2026-10-16

Nev, Nesso3 and their two GGUF releases are public and ungated under `mii-llm`.
The GitHub repository is also public. The install guides use HTTPS cloning and
public model downloads without requiring HF login. Runtime download IDs and
GGUF release pins use the organization repositories; evaluated model weights
and source-model revisions remain unchanged. Current generators use
`mii-llm/nesso3-0.4B-agentic`; Nesso2 remains a historical comparison.

Historical result/provenance JSON retains the identity and visibility observed
when each experiment ran. Current visibility and revisions are recorded in
`experiments/cpu_gguf/results/public-organization-migration.json`.
