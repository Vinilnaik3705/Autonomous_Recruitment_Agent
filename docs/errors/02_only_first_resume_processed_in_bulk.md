# Error 02: Only the First Resume Processed in Bulk Upload

## Symptom
When uploading 10+ resumes and clicking "Start Screening", only the **first resume** gets a score. The rest are ignored or show 0.

## Root Cause
The original n8n workflow received **all resumes in a single webhook call** as a JSON array. The n8n "HTTP Request" node processed the entire array as one item, not iterating over each resume individually. Only the first item in the array was actually scored.

Additionally, the workflow was a single monolithic flow — upload + scoring were in the same workflow, causing timeout issues for large batches.

## Solution — Split Into Two Atomic Workflows

### Workflow 1: `00_resume_upload_atomic.json` (Upload)
- **Trigger:** `POST /webhook/resume-upload-atomic`
- **Purpose:** Handles **one resume at a time** — extracts text, saves to DB with status `NEW`, returns 200 OK immediately
- **Why:** Eliminates timeout issues by doing minimal work per request

### Workflow 2: `01_resume_screening_ATOMIC.json` (Screening)
- **Trigger:** `POST /webhook/start-screening`
- **Purpose:** Fetches all `NEW` resumes from DB, iterates using `SplitInBatches` node, scores each one, updates DB
- **Fix:** Using `SplitInBatches` ensures every resume is processed, not just the first

### Frontend Change (`HRScreening.jsx`)
The `startScreening` function was refactored to a **two-step process**:
1. **Upload Loop:** Upload each resume individually to `resume-upload-atomic`
2. **Screening Trigger:** Call `start-screening` once to process the entire batch

```javascript
// Step 1: Upload each file individually
for (const file of files) {
    await uploadToWebhook(file);  // calls /webhook/resume-upload-atomic
}
// Step 2: Trigger batch screening
await triggerScreening(jobDescription);  // calls /webhook/start-screening
```

## Key Lesson
> In n8n, always use a **`SplitInBatches`** node when iterating over multiple items. Sending an array directly to a single HTTP Request node will **not** loop — it treats the whole array as one item.
