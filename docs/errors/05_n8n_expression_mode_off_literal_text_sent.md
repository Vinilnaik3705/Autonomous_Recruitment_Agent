# Error 05: N8N Expression Mode OFF — Literal Text Sent Instead of Value

## Symptom
An n8n node (e.g., Send Email via Brevo, HTTP Request) sends the **literal template text** instead of the actual variable value:

```
# What was actually sent to the API:
"to": "{{$json['email']}}"

# What should have been sent:
"to": "john.doe@example.com"
```

Error returned from API:
```
400 Bad Request: "email is not valid in to"
```

## Root Cause
In n8n, every input field has two modes:
- **Fixed mode** — Treats the input as plain text/string (default)
- **Expression mode** — Evaluates `{{ }}` templates as JavaScript expressions

If you type `{{$json['email']}}` in a field that is in **Fixed mode**, n8n sends it literally as a string, not as the resolved value.

## Solution

### Step 1 — Enable Expression Mode on the Field
1. Hover over the input field in the n8n node
2. Look for a small **Fx** button or **Expression** toggle on the right side of the field
3. **Click it** — it should turn blue/highlighted
4. The field now evaluates `{{ }}` expressions

### Step 2 — Verify the Resolved Value
After enabling Expression mode, n8n shows a preview of the resolved value below the field. Verify it shows the actual data (e.g., an email address), not the template string.

### Alternative — Use Code Node
For complex payloads, bypass field-by-field configuration and use a **Code node** to build the body manually:

```javascript
// n8n Code Node
const candidate = $input.first().json;

return [{
  json: {
    to: [{ email: candidate.email, name: candidate.name }],
    subject: `Interview Invitation - ${candidate.name}`,
    body: `Dear ${candidate.name}, you have been shortlisted...`
  }
}];
```

## Also Related — JSON Field Type Issues
When an n8n node field expects a **specific JSON type** (like an array or object) but receives a plain string:

```
# Wrong: Brevo "to" field as string
"john@example.com"

# Correct: Brevo "to" field as array of objects
[{ "email": "john@example.com", "name": "John" }]
```

**Fix:** Use `JSON.stringify` in a Code node or set the field type to "Expression" and use proper array syntax.

## Key Lesson
> In n8n, **never assume** a field interprets template syntax. Always toggle the **Fx / Expression** button on fields where you use `{{ }}`. Fixed mode = plain text only.
