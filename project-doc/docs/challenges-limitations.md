# Challenges and Limitations

## Private workflow dependency

Some end-to-end automations depend on private n8n workflow exports.
Without importing private workflows, parts of scheduling and feedback automation remain partially functional.

## Environment configuration sensitivity

The system depends on correct .env and secret values.
Misconfigured API keys or webhook URLs can degrade AI and automation behavior.

## Local resource variability

Model loading and resume processing times can vary by machine resources,
especially during cold starts.

## Documentation boundary

This documentation avoids exposing private business logic.
Teams should keep private workflow runbooks in the authorized internal repository.
