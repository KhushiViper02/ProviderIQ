# Video script (about 3 minutes)

**0:00 Hook.** "AI can extract data from websites in seconds, but it can also invent a phone number that looks completely real. For healthcare data, that is a problem. So I built ProviderIQ, which uses AI to extract data and then proves each value before anyone trusts it."

**0:20 Tools.** Name the AI tools you actually used and why (for example Claude for design and code review, Gemini API for extraction). Mention Python, n8n and openpyxl.

**0:45 Prompt engineering.** Show PROMPTS.md. "v1 changed keys and guessed missing values. v2 fixed the schema. v3 forbade guessing and added a repair retry. Then I stopped relying on the prompt alone and added a grounding check in code."

**1:20 Approach and background.** Link your AI/ML degree: evaluation, validation, and treating model output as untrusted.

**1:40 Demo.** Run `--extractor mock-llm`. Show the terminal summary, then the dashboard: one clean record, one record flagged for an invented phone, one postcode/state mismatch, one duplicate. Open the Excel file and its three sheets. Say clearly that the sample pages are fictional and the model errors are simulated.

**2:20 Challenges.** Example: the duplicate detector kept the worse copy, so I sorted by quality first. Add one real problem you hit.

**2:40 Outcome and next steps.** Real scraping with robots.txt respect, nightly n8n run, reviewer email. "I would extend this to nurses and hospital directories and add a feedback loop from reviewers into the prompt."

Tips: screen-record, speak naturally, stay over 2 minutes, show the live links.
