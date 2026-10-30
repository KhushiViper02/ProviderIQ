# Prompt documentation

Edit Part B so it matches the prompts you actually used. Reviewers value honesty over polish.

## Part A: the extraction prompt (used inside the pipeline)

### v1: first attempt
```
Extract the clinic details from this page and give them as JSON: {text}
```
**What went wrong:** keys changed between runs, answers were wrapped in markdown, and missing fields were filled with plausible guesses (for example an invented phone number).

### v2: fixed schema
Added the exact key list, "return only JSON", and allowed states and types.
**Improved:** consistent keys and parseable output. **Still wrong:** the model still guessed missing values instead of leaving them empty.

### v3: grounded extraction (current, see `PROMPT_V3` in `src/provideriq/extract.py`)
Added: "use ONLY information present in the text", "if a field is missing return null, do not invent", copy phone numbers exactly, and one repair retry if the JSON is malformed. Temperature 0.
**Why it matters:** the prompt reduces invention, and `validate.py` independently checks that every returned value appears in the page, so a prompt failure is caught instead of trusted.

### Measure it (fill in from your own run)
Run each prompt version on the same 15-20 real pages and record:

| Metric | v1 | v2 | v3 |
|---|---|---|---|
| Valid JSON on first try | | | |
| Fields flagged `ungrounded_*` | | | |
| Records auto-verified | | | |

Use `summary.flag_counts` printed by the pipeline. Do not publish numbers you did not measure.

## Part B: build prompts (replace with your real ones)
1. Role analysis: "Here is the job description and Task 1. Which project type fits the company's healthcare, RPA and AI focus, and what would 7,000 other applicants likely build?"
2. Architecture: "Design a Python pipeline for public healthcare provider data with a verification step. List modules and data flow."
3. Validation layer: "Write Australian phone, email and postcode-vs-state validation with unit tests."
4. Revision: "The duplicate detector kept the lower-quality copy. Sort by score first, then dedupe."
5. Dashboard and docs: "Build a static dashboard that reads providers.json and filters by status."

For each, note what the AI got wrong and how you corrected it.

## Measured results (5 real clinic pages, Gemini)

| Prompt | Valid JSON | Exact schema | Ungrounded fields | Verified | Avg score |
|---|---|---|---|---|---|
| v1 (basic) | 5/5 | 0/5 | 1 | 0/5 | 23.0 |
| v2 (schema) | 5/5 | 5/5 | 0 | 5/5 | 94.0 |
| v3 (grounded) | 5/5 | 5/5 | 0 | 5/5 | 94.0 |


How to read this:
- v1 to v2 is the big gain. With no schema, the model chose its own key names, so none of the 5 answers matched my fields (0/5) and the average quality score was 23. Naming the exact keys fixed that (5/5, average 94).
- v2 to v3 showed no measurable difference on these 5 pages: both scored 94 with no ungrounded fields. The "use only the text, never guess" rules are a safeguard, and this small test cannot prove they help. A larger test is needed.
- v1 produced the only value in the run that could not be found on the page. That is the kind of error the verification layer is built to catch.
- Caveats: only 5 pages, and the code switched between Gemini versions during the run because of rate limits, so treat the comparison as indicative.
