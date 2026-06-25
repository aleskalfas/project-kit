#!/usr/bin/env python3
"""Mine diagnose logs for butter-command candidates.

The redaction keeps the VERB and the ISSUE NUMBER but hides args — enough to see
which operations the agent repeats (surgery) and which it pipes (friction).
"""
import json, re, os
from collections import Counter, defaultdict

base = '/Users/kalfas/Documents/Projects/bee'
PATHS = [
    f'{base}/git-public/project-kit/.pkit/permissions/project/diagnose-log.jsonl',
    f'{base}/git-public/project-kit-2/.pkit/permissions/project/diagnose-log.jsonl',
    f'{base}/git/trip-planner-agent/.pkit/permissions/project/diagnose-log.jsonl',
    f'{base}/git-public/trip-planner-agent-app/.pkit/permissions/project/diagnose-log.jsonl',
]

recs = []
for p in PATHS:
    if not os.path.exists(p):
        continue
    for line in open(p):
        try:
            recs.append(json.loads(line))
        except json.JSONDecodeError:
            pass

def strip_cd(c):
    m = re.match(r'\s*cd\s+\S+\s*(?:&&|;)\s*(.*)', c, re.S)
    return m.group(1) if m else c

bash = [r for r in recs if r.get('tool') == 'Bash']

# --- 1. pkit project-management verbs: frequency + compound rate -------------
pm_verb = Counter()
pm_verb_piped = Counter()
pm_issue_edits = Counter()          # issue number -> how many edit-issue calls
for r in bash:
    c = strip_cd(r.get('command', ''))
    m = re.search(r'pkit project-management (\S+)', c)
    if not m:
        continue
    verb = m.group(1)
    pm_verb[verb] += 1
    if '|' in c:
        pm_verb_piped[verb] += 1
    # capture issue number for edit-ish verbs
    mnum = re.search(r'pkit project-management \S+\s+(\d+)', c)
    if mnum and verb in ('edit-issue', 'edit-pr', 'promote-issue', 'start-work',
                          'review-work', 'review-pr', 'close-issue', 'check-issue'):
        pm_issue_edits[(verb, mnum.group(1))] += 1

print("=== pkit project-management verbs (deferral frequency) ===")
print(f"{'verb':22s} {'total':>6s} {'piped':>6s}")
for verb, n in pm_verb.most_common():
    print(f"  {verb:20s} {n:6d} {pm_verb_piped[verb]:6d}")
print()

print("=== repeated mutations on the SAME issue (surgery signal → batch/butter win) ===")
for (verb, num), n in sorted(pm_issue_edits.items(), key=lambda x: -x[1]):
    if n >= 2:
        print(f"  {verb} #{num}: {n}x  → {n} prompts that 1 batched call would collapse")
print()

# --- 2. raw 'surgery' commands the agent uses (sed/awk/for/until/grep chains) -
surgery = Counter()
SURGERY_HEADS = {'sed', 'awk', 'for', 'until', 'while', 'tr', 'cut', 'paste'}
for r in bash:
    c = strip_cd(r.get('command', '')).strip()
    toks = c.split()
    while toks and re.match(r'^[A-Z_][A-Z0-9_]*=', toks[0]):
        toks = toks[1:]
    if toks and toks[0].split('/')[-1] in SURGERY_HEADS:
        surgery[toks[0].split('/')[-1]] += 1
print("=== text-surgery heads (sed/awk/loops) — manual body manipulation the agent does ===")
for h, n in surgery.most_common():
    print(f"  {h:8s} {n}")
print()

# --- 3. gh issue/pr read ops (output the agent then greps) ------------------
ghops = Counter()
for r in bash:
    c = strip_cd(r.get('command', ''))
    m = re.search(r'gh (issue|pr) (\S+)', c)
    if m:
        ghops[f'gh {m.group(1)} {m.group(2)}'] += 1
print("=== gh issue/pr operations (reads the agent filters with grep) ===")
for op, n in ghops.most_common():
    print(f"  {op:22s} {n}")
print()

# --- 4. pipe-target breakdown (what the agent pipes INTO) --------------------
pipe_into = Counter()
for r in bash:
    c = strip_cd(r.get('command', ''))
    for seg in c.split('|')[1:]:
        seg = seg.strip()
        toks = seg.split()
        if toks:
            pipe_into[toks[0].split('/')[-1]] += 1
print("=== what the agent pipes INTO (the filtering it bolts on) ===")
for h, n in pipe_into.most_common(12):
    print(f"  {h:8s} {n}")
