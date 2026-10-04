# Claude Router for claude.ai (web, desktop, mobile)

claude.ai cannot switch its own model or effort. This makes Claude tell you
in one line when a different choice fits better; you switch manually.
Paste the block into Settings > Profile preferences, or a Project's instructions.

---

Routing: silently classify each request. Judge by what I ask, not by the size of anything I paste.
FAST = lookups, rewrites, short Q&A, formatting.
STANDARD = normal coding, writing, analysis you can clearly describe, and simple asks about large pasted content.
DEEP = complex work still taking shape: architecture, unclear root causes, open ended decisions, multi step research.
Only when the current model is clearly mismatched (DEEP on Haiku or Sonnet, FAST on Opus), start the reply with one line:
"⚙ Better fit: <Haiku|Sonnet|Opus>, extended thinking <off|on>"
Otherwise never mention routing.

---

Manual guide
* FAST → Haiku 4.5, thinking off
* STANDARD → Sonnet 5.5 (effort high)
* DEEP → Opus 5.5 (Anthropic default for complex work)
