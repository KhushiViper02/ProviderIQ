# Architecture
See the diagram in the README. Modules: `collect.py` (fetching), `textutil.py` (HTML to text), `extract.py` (extractors and prompt), `validate.py` (checks and scoring), `export.py` (Excel/CSV/JSON), `pipeline.py` (orchestration).
Scoring: completeness up to 100, minus penalties (ungrounded field 30, postcode/state mismatch 25, invalid format 10). Status: under 50 rejected; 80+ with no hard flags and no duplicate is verified; everything else needs review.
