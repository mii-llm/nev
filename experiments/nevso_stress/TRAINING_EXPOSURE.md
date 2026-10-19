# Training-exposure note

The public Nesso3 model card checked on 19 October 2026 lists xLAM, ToolACE and
When2Call among its public function-calling training sources. When2Call's dataset
documentation identifies BFCL source categories and source IDs. This makes
possible indirect BFCL overlap a concrete concern, not just a generic caveat.
We have not compared the selected 30 BFCL items against the actual SFT records,
so neither overlap nor absence of overlap is established for these items.

- [Nesso3 model card](https://huggingface.co/mii-llm/nesso3-0.4B-agentic)
- [When2Call source fields](https://github.com/NVIDIA/When2Call)
- [Local scan scope](source/overlap_check.json)

The external panel should therefore be described as a public-data transfer check,
not proof of unseen-task generalization. The authored panel contains new concrete
requests and fixtures, but uses familiar task families and was written by the
same assistant that designed the evaluation. It is also not an independent audit.

This disclosure does not change frozen inputs, selection, prompts or scoring.

Public model-card snapshot SHA-256: `cb7706f42ebf7443878dee1c72492e1cffb84a888bcffa215f1f9f7bdcf5080e` (main branch read on the date above; training disclosure is not a new model-weight revision).
