"""Labeled prompts. Each case: (category, prompt, acceptable tiers)."""
import random
random.seed(7)
F, S, D, M = "fast", "standard", "deep", "max"

def log_lines(n):
    lv = ["INFO", "WARN", "ERROR", "DEBUG"]
    words = ["production worker performance ok", "refactor flag pending", "migration step 3 done",
             "race condition guard hit", "debug sampling on", "scaling pool to 12", "architecture v2 route"]
    return "\n".join(f"2026-10-01 10:{i//60:02d}:{i%60:02d} {random.choice(lv)} {random.choice(words)}" for i in range(n))

def code_block(n, lang="ts"):
    body = "\n".join(f"  const item{i} = await repo.find({{ id: {i} }}); // optimize later, performance" for i in range(n))
    return f"```{lang}\nexport async function load() {{\n{body}\n}}\n```"

def bare_code(n):
    return "\n".join([f"def handler_{i}(event):" + "\n    return process(event)  # refactor" for i in range(n)])

def json_blob(n):
    return "{\n" + ",\n".join(f'  "key_{i}": "architecture performance migration value {i}"' for i in range(n)) + "\n}"

def csv_rows(n):
    return "id,name,region,revenue\n" + "\n".join(f"{i},Customer {i},West,{i*100}" for i in range(n))

ARTICLE = ("Distributed systems teams often debate the tradeoffs between monoliths and microservices. "
           "Performance, scalability, and the cost of migration all factor into the architecture decision. "
           "Many teams refactor gradually, investigating bottlenecks and race conditions as they go. ") * 12

TRACE = """Traceback (most recent call last):
  File "/app/api/views.py", line 88, in get_user
    user = User.objects.get(id=user_id)
  File "/venv/lib/django/db/models/manager.py", line 85, in manager_method
    return getattr(self.get_queryset(), name)(*args, **kwargs)
django.contrib.auth.models.User.DoesNotExist: User matching query does not exist."""

TRANSCRIPT = "\n".join(f"Speaker {i%3}: We discussed the architecture and performance of the billing service, and the migration plan." for i in range(40))

CASES = [
  # short fast
  ("short_fast", "rename getUser to fetchUser", {F}),
  ("short_fast", "fix the typo in README", {F}),
  ("short_fast", "what is a closure in js", {F, S}),
  ("short_fast", "git status", {F}),
  ("short_fast", "write a commit message for these changes", {F, S}),
  ("short_fast", "convert this function to arrow syntax", {F, S}),
  ("short_fast", "list all python files in src", {F}),
  ("short_fast", "where is the env config loaded", {F, S}),
  ("short_fast", "bump the version to 2.1.0", {F}),
  ("short_fast", "add comments to utils.ts", {F, S}),
  ("short_fast", "format this file", {F}),
  ("short_fast", "install axios", {F}),
  ("short_fast", "sort the imports in app.tsx", {F, S}),
  ("short_fast", "translate the error message to Hindi", {F, S}),
  # short standard
  ("short_std", "add a loading state to the login button", {S}),
  ("short_std", "write a unit test for parseDate", {S}),
  ("short_std", "add pagination to the /orders endpoint", {S}),
  ("short_std", "create a React hook for debounced search", {S}),
  ("short_std", "fix the failing test in cart.spec.ts", {S}),
  ("short_std", "add input validation to the signup form", {S}),
  ("short_std", "write a dockerfile for this node app", {S}),
  ("short_std", "add dark mode toggle to settings page", {S}),
  ("short_std", "make the navbar responsive", {S}),
  ("short_std", "bhai login wala bug fix kar do, button click pe kuch nahi hota", {S}),
  # short deep
  ("short_deep", "refactor the auth module across the codebase to fix the race condition causing intermittent logouts", {D, M}),
  ("short_deep", "design a schema for multi tenant billing with tradeoffs", {D, M}),
  ("short_deep", "why does the websocket reconnect loop only fail in production", {D, M}),
  ("short_deep", "investigate the memory leak in the worker service", {D, M}),
  ("short_deep", "plan the migration from REST to GraphQL", {D, M}),
  ("short_deep", "find the root cause of the deadlock in the payment queue", {D, M}),
  ("short_deep", "do a security review of the file upload flow", {D, M}),
  ("short_deep", "build a RAG pipeline from scratch with evals", {D, M}),
  ("short_deep", "the checkout is flaky, debug it", {D, M}),
  ("short_deep", "optimize the dashboard query, it takes 9 seconds", {S, D, M}),
  # keyword traps: deep words but conceptual / simple
  ("trap", "what is a race condition", {F, S}),
  ("trap", "explain microservices architecture briefly", {F, S}),
  ("trap", "what are the tradeoffs of REST vs gRPC", {S}),
  ("trap", "don't refactor anything, just rename the file to index.ts", {F, S}),
  ("trap", "rename refactorHelper to helper", {F, S}),
  ("trap", "list the performance metrics we log", {F, S}),
  ("trap", "summarize the migration doc", {F, S}),
  ("trap", "how does the event loop work", {F, S}),
  # BIG prompt, Sonnet level work  (the scenario you asked about)
  ("big_simple", "Here is my server log, just tell me which line has the timestamp 10:42:13:\n" + log_lines(120), {S}),
  ("big_simple", log_lines(200) + "\n\nhow many ERROR lines are there?", {S}),
  ("big_simple", "Summarize this in 3 bullets:\n" + ARTICLE, {S}),
  ("big_simple", ARTICLE + "\n\nCan you proofread the above and fix grammar?", {S}),
  ("big_simple", "Add JSDoc comments to this:\n" + code_block(60), {S}),
  ("big_simple", code_block(80) + "\nrename load to loadItems", {S}),
  ("big_simple", "convert this to python:\n" + bare_code(40), {S}),
  ("big_simple", "Format this JSON nicely and sort keys:\n" + json_blob(80), {S}),
  ("big_simple", "Which customer has the highest revenue?\n" + csv_rows(150), {S}),
  ("big_simple", "What does this error mean?\n" + TRACE, {S}),
  ("big_simple", TRACE + "\nfix this", {S}),
  ("big_simple", "Extract the action items from this meeting transcript:\n" + TRANSCRIPT, {S}),
  ("big_simple", "Translate the following to Hindi:\n\n" + ARTICLE, {S}),
  ("big_simple", ("Hey, so some context first. I've been working on this dashboard project for a few weeks "
                  "and the team keeps arguing about naming. My lead wants everything consistent before the demo. "
                  "We use camelCase mostly, but some older files have snake case. Anyway it's not urgent but "
                  "it bugs me. ") * 3 + "Can you rename user_name to userName in profile.ts?", {S}),
  ("big_simple", "write tests for this function\n" + code_block(40, "py"), {S}),
  # BIG prompt, genuinely deep
  ("big_deep", "This production error happens intermittently under load. Find the root cause and fix it; I suspect a race condition in the connection pool.\n" + log_lines(100), {D, M}),
  ("big_deep", "Refactor this into a proper repository pattern across the codebase and optimize the N+1 queries:\n" + code_block(60), {D, M}),
  ("big_deep", """I need you to design and implement a multi tenant notification service.
Requirements:
1. Each tenant has isolated queues and rate limits.
2. Support email, SMS and push with pluggable providers.
3. Retries with exponential backoff and a dead letter queue.
4. Must scale to 50k messages per minute.
5. Audit log of every delivery attempt.
6. Migrate existing notifications from the legacy cron job without downtime.
Touch api/routes.ts, services/notify.ts, workers/queue.ts and db/schema.sql. Explain tradeoffs.""", {D, M}),
  ("big_deep", ("We're seeing p99 latency spikes every few minutes on the order service. The spikes correlate with GC pauses "
                "but also with a cron that rebuilds a cache. I want you to investigate both, profile, and propose an "
                "architecture change so the cache rebuild doesn't block request threads. ") * 2, {D, M}),
  ("big_deep", "Why does this test pass locally but fail in CI? Debug it.\n" + TRACE + "\n" + code_block(30, "py"), {D, M}),
  # work still taking shape (Anthropic: start or stay with Opus)
  ("taking_shape", "not sure how to structure the billing module, what's the best way to approach it", {D, M}),
  ("taking_shape", "should we use Redis or Postgres for the job queue, pros and cons", {D, M}),
  ("taking_shape", "brainstorm approaches for offline sync", {D, M}),
  ("taking_shape", "not sure where this bug comes from, the totals look off", {D, M}),
  # overrides
  ("override", "!deep rename x", {D}),
  ("override", "!fast " + ARTICLE, {F}),
  ("override", "!std design a distributed system", {S}),
  ("override", "!max hi", {M}),
]
