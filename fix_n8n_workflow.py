"""Fix n8n workflow JSON: replace .item.json with .first().json in Log Interview Schedule2 node."""
import json

with open("02_Interview_Scheduling_updated.json", "r", encoding="utf-8") as f:
    data = json.load(f)

for node in data.get("nodes", []):
    if node.get("name") == "Log Interview Schedule2":
        opts = node["parameters"].get("options", {})
        old = opts.get("queryReplacement", "")

        new_val = old.replace(
            "$('Calculate Interview Slot2').item.json.candidate_name",
            "($('Calculate Interview Slot2').first().json.candidate_name || 'Candidate')",
        ).replace(
            "$('Calculate Interview Slot2').item.json.candidate_email",
            "($('Calculate Interview Slot2').first().json.candidate_email || '')",
        ).replace(
            "$('Calculate Interview Slot2').item.json.interviewerId",
            "($('Calculate Interview Slot2').first().json.interviewerId || 1)",
        ).replace(
            "$('Calculate Interview Slot2').item.json.audit_start",
            "$('Calculate Interview Slot2').first().json.audit_start",
        ).replace(
            "$('Calculate Interview Slot2').item.json.round_number",
            "($('Calculate Interview Slot2').first().json.round_number || 1)",
        ).replace(
            "$('Calculate Interview Slot2').item.json.round_label",
            "($('Calculate Interview Slot2').first().json.round_label || 'HR Round')",
        )

        # Also fix Create Google Calendar Event2 references
        new_val = new_val.replace(
            "$('Create Google Calendar Event2').item?.",
            "$('Create Google Calendar Event2').first().",
        )

        opts["queryReplacement"] = new_val
        print("Fixed Log Interview Schedule2 queryReplacement")
        break

    # Also fix Update Candidate Status2 node
    if node.get("name") == "Update Candidate Status2":
        opts = node["parameters"].get("options", {})
        old = opts.get("queryReplacement", "")
        new_val = old.replace(
            "$('Calculate Interview Slot2').item.json.",
            "$('Calculate Interview Slot2').first().json.",
        )
        opts["queryReplacement"] = new_val
        print("Fixed Update Candidate Status2 queryReplacement")

with open("02_Interview_Scheduling_updated.json", "w", encoding="utf-8") as f:
    json.dump(data, f, indent=4, ensure_ascii=False)

print("Done! Workflow JSON updated.")
