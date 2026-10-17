# Give Nev the choice, give Nesso3 the call

This Mac CPU example explores a specific division of work: **Nev chooses one
function from a catalog; Nesso3 generates its arguments and describes the tool
result.** It uses supported single-operation requests, with all required values
present. It does not ask either model to apply refund or escalation policies.

The catalog contains 12 read-only mock tools for notes, temperature sensors,
battery readings and music. The same controller validates calls in every arm.
No real files, sensors or accounts are accessed.

## Run it on your Mac

From the GitHub checkout, after the CPU setup:

```bash
cd experiments/cpu_gguf
./setup.sh --model both --precision q8

# Compare all three approaches on 12 English + 12 Italian requests.
.venv/bin/python compare_routing.py --precision q8 \
  --output "results/routing-$(date +%Y%m%d-%H%M%S).json"
```

The command writes a JSON report and a matching **`.txt` file with readable
traces**: request, Nev's selection, Nesso3's proposed calls, validation, mock
results, final answer and timing. Choose a new output filename for each run.
Both model workers stay loaded throughout the run.

Use `--language en` or `--language it` for one language, and `--case find_note-it`
for a single request. Add `--precision f16` after installing the F16 files if you
want a separate precision comparison. F16 results must be measured separately.

## What is compared

| Arm | Nev's role | What Nesso3 sees |
| --- | --- | --- |
| `nesso_only` | None | All 12 schemas in a seeded order |
| `nev_ranked` | Rank the 12 tools once | All 12 schemas, ordered by Nev |
| `nev_selected` | Select the highest-ranked tool once | Only that tool's schema |

Requests, generation settings, validation, mock results and turn limits are the
same. Arm order rotates between cases. Both models are resident in all arms, so
this does not measure the memory saving of deploying Nesso3 alone. Warm request
timings include Nev's work and controller overhead but exclude loading.

The selected-tool design applies only when one available tool can fulfill the
request. A wrong Nev selection restricts Nesso3 to the wrong tool. It has no
validated abstention mechanism and does not solve missing arguments, unsupported
actions or dependent multi-step work. The existing generic multi-tool workflow
remains available in `demo.py`.

## How to read the evidence

- **Exact execution:** executed tool names and arguments exactly match the
  expected single call, with no extra calls.
- **Answer-anchor proxy:** exact execution plus all expected answer fragments in
  a completed final answer. This is a mechanical screen, not proof that all
  statements in the answer are correct. Read the traces.
- **Latency:** warm whole-request time on this Mac, including model routing.

Cases and expected outputs are fixed in `routing_cases.json` before the run.
The models never receive the expected calls or answer anchors. The fixtures
reuse earlier tool definitions and some earlier request patterns: this is a
**development demonstration, not an independent benchmark**. All 24 cases are
retained, including failures. Any highlighted example is selected after review.

## Recorded Mac results — 17 October 2026

Apple M3 Pro, Q8 for both backbones, four CPU threads, 24 requests per arm.
The complete run contains **72 trials**, with all results retained.

| Approach | Exact call EN | Exact call IT | Reviewed task success EN | Reviewed task success IT | Median request |
| --- | ---: | ---: | ---: | ---: | ---: |
| Nesso3, all 12 tools | 9/12 | 9/12 | 8/12 | 6/12 | 2.57 s |
| Nev orders all 12 tools | 11/12 | 11/12 | 8/12 | 8/12 | 3.66 s |
| **Nev selects one tool** | **12/12** | **10/12** | **11/12** | **9/12** | **1.72 s** |

Selecting one tool improves exact execution from **18/24 to 22/24** and reviewed
task success from **14/24 to 20/24** (58.3% → 83.3%, +25 percentage points).
Median latency is approximately **33% lower** in this run. Average total Nesso3
prompt tokens per request fall from 1,546 to 316. Simply ordering the full catalog
improves execution too, but is slower and leaves more final-answer mistakes.

Task success was reviewed by the assistant against all recorded requests,
executed calls and tool results; it is **not an independent human audit**. This
review catches wrong units that the answer-anchor proxy misses. It also accepts
one valid alternative: Nesso3 listed both notes and correctly counted them,
instead of calling `note_count`. That case fails strict exact-call matching but
succeeds at the user's task. An unrelated extra tool call is a workflow failure,
even if the final answer happens to contain the correct value.

### English example: finding a note

**User:** “Find the identifier of the note titled Aurora.”

**Nesso3 with all tools:**

1. Calls `track_details(track_id="Aurora")` — a music tool.
2. Mock tool returns `not_found`.
3. Answers: “The note titled Aurora is not found.” **Incorrect.**

**Nev + Nesso3:**

1. Nev selects `find_note` from all 12 options.
2. Nesso3 sees that schema and generates `find_note(query="Aurora")`.
3. The controller validates the call; the mock returns `note_id="N-7Q2"`.
4. Nesso3 answers: “The identifier of the note titled Aurora is N-7Q2.” **Correct.**

### Italian example: the same workflow

**Utente:** “Trova l’identificativo della nota intitolata Aurora.”

**Nesso3 con tutti gli strumenti:** chiama `note_count(folder="Aurora")` e
risponde “L'identificativo della nota Aurora non è presente.” **Errato.**

**Nev + Nesso3:** Nev seleziona `find_note`; Nesso3 genera
`find_note(query="Aurora")`; il controller riceve `N-7Q2` dallo strumento.
Risposta: “La nota Aurora ha l'identificativo N-7Q2.” **Corretto.**

These are selected examples from the full candidate set, not additional tests.
Run the Italian comparison alone:

```bash
.venv/bin/python compare_routing.py --precision q8 --case find_note-it \
  --output "results/find-note-it-$(date +%Y%m%d-%H%M%S).json"
```

### Failures retained

The selected-tool workflow still fails four requests:

- English note listing: correct tool and returned titles, but the answer omits Atlas.
- Italian sensor lookup: Nev selects `read_sensor` instead of `find_sensor`;
  Nesso3 invents a sensor ID and the controller rejects it.
- Italian track details: Nev selects `playlist_duration` instead of `track_details`.
- Italian playlist listing: correct tool execution, but no completed final answer.

All 12 English calls are correct; that does not mean all English answers are
complete. Nev's two wrong Italian choices demonstrate the cost of restricting
the generator to one function. No prompts, cases or weights were adjusted to
remove these failures.

## Files and reproduction

- [Runner](compare_routing.py) and [all 24 cases](routing_cases.json).
- [Full JSON evidence](results/routing-comparison-q8.json), including model pins,
  source hashes, assistant review, probabilities, calls and final answers.
- [Readable traces for every trial](results/routing-comparison-q8.txt).

The full-run report embeds the exact runner source used. The published runner
subsequently gained stable case indexing for filtered runs and embeds its own
source in future reports; the default full-run inputs and inference are
unchanged. Case selection now retains the original tool order, making a single
example directly comparable to its full-run trace. The filtered Italian note example was rerun and reproduced tool order, executed
calls, final answers and scores exactly in all three arms; its [verification
report](results/routing-example-it-q8.json) is retained. Timing is a single local
measurement per case, not a controlled performance benchmark.
