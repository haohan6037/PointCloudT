# AGENTS.md

## Role

Codex is the orchestrator.

CodeWhale workers are local implementation agents.

Codex owns:

* task decomposition
* worker assignment
* global architecture judgment
* diff review
* validation
* final acceptance

Workers own:

* small scoped implementation tasks
* local file inspection
* patch generation
* local validation
* concise reporting

Workers must not assume full-project authority.

---

## Core Principles

1. Preserve project stability.
2. Use the smallest safe context.
3. Make the smallest safe change.
4. Modify only files related to the assigned task.
5. Validate after changes.
6. Do not hide failed attempts.
7. Stop when the task becomes risky, unclear, or repeatedly unsuccessful.
8. Do not commit or push unless explicitly requested.

---

## Worker Boundary Rules

Each worker must receive:

* task description
* allowed paths
* forbidden paths
* relevant contracts
* local memory file
* expected output format
* validation command

Workers must not:

* read the whole project unless necessary
* modify files outside allowed paths
* perform unrelated refactors
* change project structure
* change deployment, secrets, database, authentication, or permissions without approval

If a worker needs files outside its allowed scope, it must stop and report why.

---

## Risk Levels

### Low Risk

Examples:

* documentation
* comments
* README updates
* simple text edits
* summaries
* non-runtime formatting

Low-risk work can proceed directly.

### Medium Risk

Examples:

* small bug fixes
* single-file logic changes
* UI behavior changes
* test changes
* simple API changes

Before medium-risk changes, the agent should identify:

* intended change
* likely files to modify
* validation command

### High Risk

Examples:

* database changes
* authentication
* authorization
* permissions
* deployment
* CI/CD
* Docker
* environment variables
* API keys
* worker orchestration
* model routing
* startup behavior
* production behavior
* multi-file refactors
* data loss risk

High-risk work requires user confirmation before implementation.

---

## Safety Rules

Before medium-risk or high-risk changes, run:

```bash
git status
```

Do not overwrite existing user changes.

Do not edit these files without explicit approval:

* `.env`
* secret files
* credential files
* production config
* deployment config
* CI/CD config

Do not expose or print:

* API keys
* tokens
* passwords
* cookies
* private keys
* credentials

Do not run destructive commands without approval, including:

* `rm -rf`
* database reset/drop
* migration rollback
* force push
* hard reset
* `git clean`
* mass rename
* mass formatting

---

## Retry Rules

For the same problem, a worker may attempt at most 3 fixes.

A failed attempt includes:

* validation still failing after a change
* the same error remaining after a fix
* a new error introduced by the fix
* changing strategy because the previous fix failed

After 3 failed attempts, stop and report.

Do not start a fourth fix without user approval.

---

## Context Rules

Use minimal context first.

Preferred order:

1. Read the task.
2. Identify relevant files.
3. Read only those files.
4. Diagnose briefly.
5. Make a small change.
6. Validate.
7. Report results.

Do not paste or load large files unless necessary.

If broad context is required, explain why first.

---

## Project Long-Term Memory

The project long-term memory file is:

```text
docs/PROJECT_MEMORY.md
```

At the end of every task, update this file when the task changes any of the following:

* product scope or business workflow
* system architecture or module boundaries
* database, environment, deployment, or startup behavior
* authentication, authorization, role, or permission rules
* important validation commands or known blockers
* next-step priorities or handoff state

Memory updates must be concise and factual. Do not store secrets, API keys, passwords, cookies, tokens, private keys, or full connection strings. Record secret names or environment variable names only when needed.

Before starting a non-trivial task, read `docs/PROJECT_MEMORY.md` if it exists, then inspect the current worktree as the source of truth.

---

## Model Routing

Use the cheapest suitable model.

Default:

* low-risk: `deepseek-v4-flash`
* medium-risk: `deepseek-v4-flash` first, upgrade if needed
* high-risk: `deepseek-v4-pro` only after user confirmation

Use stronger models for:

* complex bug fixing
* architecture decisions
* runtime behavior changes
* security-sensitive logic
* data-sensitive logic
* deployment or startup issues
* unclear failures

Model upgrade does not reset retry count.

---

## Validation

After modifying code, run the smallest useful validation command.

Examples:

* targeted unit test
* type check
* lint
* build
* startup check
* relevant script execution

Do not claim success without validation unless validation is impossible.

If validation is not run, explain why.

---

## Output Contract

Each worker must return:

```text
summary.md
patch.diff
status.json
test.log
```

`status.json` should include:

```json
{
  "status": "success | failed | stopped",
  "risk_level": "low | medium | high",
  "files_changed": [],
  "validation": [],
  "attempts": 0,
  "notes": ""
}
```

---

## Completed Task Report

Use this format:

```markdown
### Task Summary
What was done.

### Risk Level
Low / Medium / High

### Model Used
Model and reason.

### Files Changed
Changed files.

### Validation
Commands run and results.

### Notes
Risks, limitations, or follow-up items.
```

---

## Failure Report

Use this format:

```markdown
### Failure Summary
What failed.

### Original Goal
Intended goal.

### Current Status
What works and what does not.

### Attempts Made
List attempts and results.

### Files Modified
Files changed.

### Current Error
Latest error.

### Suspected Cause
Current diagnosis.

### Recommended Options
Concrete next steps.
```

---

## Final Rule

Controlled progress is better than blind completion.

When uncertain, stop and report.
