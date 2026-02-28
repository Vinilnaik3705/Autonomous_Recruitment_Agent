# Error 06: N8N Loop Data "Poisoning" — Wrong Data in Loop Nodes

## Symptom
Inside an n8n loop (e.g., `SplitInBatches` → Process Item → Update DB → back to Split):
- A node that should output **candidate data** instead outputs `{ "success": true }` or a database update result
- Subsequent nodes crash with "missing field" errors (e.g., `email` not found)
- The loop seems to process correctly in the first iteration but breaks on the second+

## Root Cause — Loop Feedback
When the **last node** in a loop (e.g., "Update DB") connects back to the **`SplitInBatches`** node, its output can "pollute" the context of nodes earlier in the loop.

```
Split → Score Resume → Update DB ──┐
  ▲                                 │
  └─────────────────────────────────┘
         (feedback connection)
```

When "Update DB" returns `{ "success": true }` and it loops back, n8n can incorrectly show that `{ "success": true }` as the output of the `Split` node in certain UI views or execution contexts — breaking all subsequent `$json` references that expect candidate fields.

## Solution

### Fix 1 — Break the Loop, Debug Clean
1. **Temporarily disconnect** the line that goes from "Update DB" back to `SplitInBatches`
2. Re-run the nodes before the loop (e.g., "Fetch Resumes")
3. Check the `Split` node output — it should now show real candidate data
4. Reconnect and use Fix 2 below

### Fix 2 — Use Explicit Node References
Instead of using `$json` (which can be poisoned), reference the source node explicitly:

```javascript
// ❌ Fragile — may pick up poisoned data
const email = $json['email'];

// ✅ Explicit — always reads from the named node
const email = $node["Split In Batches"].json['email'];
```

### Fix 3 — Clear Execution History
n8n sometimes caches a "poisoned" result from a previous failed run:
1. Go to **Executions** tab in n8n sidebar
2. Delete recent failed executions
3. Re-run the workflow fresh

### Fix 4 — Separate the Loop Return
Instead of feeding the update result back into the loop, structure it differently:

```
Split → Score → Update DB  (no feedback to Split)
         |
      Aggregate Results (use Merge or Set node after the loop)
```

## Key Lesson
> In n8n loops, **always use `$node["NodeName"].json`** to reference data from a specific node rather than plain `$json` when inside a loop. This prevents data "poisoning" from later nodes overwriting the context.
