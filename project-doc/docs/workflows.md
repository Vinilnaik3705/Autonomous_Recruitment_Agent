# Workflows

## Where workflows live

Workflow JSON files are maintained in the [workflows/](file:///c:/Users/VINIL NAIK/OneDrive/Desktop/Projects/automated_res/workflows) directory at the root of the project:
- [01_Resume_Screening_Atomic_updated.json](file:///c:/Users/VINIL NAIK/OneDrive/Desktop/Projects/automated_res/workflows/01_Resume_Screening_Atomic_updated.json)
- [02_Interview_Scheduling_updated.json](file:///c:/Users/VINIL NAIK/OneDrive/Desktop/Projects/automated_res/workflows/02_Interview_Scheduling_updated.json)
- [03_Interview_Feedback_Collection_updated.json](file:///c:/Users/VINIL NAIK/OneDrive/Desktop/Projects/automated_res/workflows/03_Interview_Feedback_Collection_updated.json)
- [04_Onboarding_Automation_updated.json](file:///c:/Users/VINIL NAIK/OneDrive/Desktop/Projects/automated_res/workflows/04_Onboarding_Automation_updated.json)

## Expected import process

1. Locate the JSON files in the `workflows/` directory.
2. Import these files into your n8n instance.
3. Validate webhook URLs and credentials in n8n.

## Expected backend integration points

Current backend integration references include:

- `N8N_SCHEDULE_WEBHOOK_URL`
- `N8N_FEEDBACK_COLLECTION_WEBHOOK`

Ensure these values are available in your runtime environment (in the `.env` file) before testing end-to-end automations.

