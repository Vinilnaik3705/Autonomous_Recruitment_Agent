# Workflows

## Repository policy

n8n workflow exports are not included in this public repository.
This is intentional to protect proprietary logic and sensitive automation details.

## Where workflows live

Workflow JSON files are maintained in a private repository accessible only to authorized team members.

## Expected import process

1. Access the private workflow repository
2. Export or copy required workflow JSON files
3. Import into your n8n instance
4. Validate webhook URLs and credentials

## Expected backend integration points

Current backend integration references include:

- N8N_SCHEDULE_WEBHOOK_URL
- N8N_FEEDBACK_COLLECTION_WEBHOOK

Ensure these values are available in runtime environment before testing end-to-end automations.
