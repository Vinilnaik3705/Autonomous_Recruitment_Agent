#!/usr/bin/env python3
import requests
import json

print("Testing OA Email Template Endpoint...")
print("=" * 60)

# Test the thank you email template
email_payload = {
    'candidate_email': 'test@example.com',
    'candidate_name': 'John Doe',
    'oa_score': 75,
    'report_url': 'https://example.com/report'
}

try:
    response = requests.post('http://127.0.0.1:8000/email/oa-completion-thank-you', json=email_payload, timeout=10)
    if response.status_code == 200:
        data = response.json()
        print("[OK] Email Template Generated Successfully!")
        print(f"Subject: {data['subject']}")
        print(f"Recipient: {data['recipient_name']} <{data['recipient_email']}>")
        print(f"Body Preview (first 200 chars):")
        print(data['body'][:200] + "...")
        print()
        print("Email template contains:")
        print(f"  [*] Score display: {'Your Score' in data['body']}")
        print(f"  [*] Next steps section: {'What Happens Next' in data['body']}")
        print(f"  [*] Report link section: {'View Your Assessment Report' in data['body']}")
    else:
        print(f"[ERROR] {response.status_code}")
        print(response.text)
except Exception as e:
    print(f"[ERROR] Connection error: {e}")

print("\n" + "=" * 60)
print("Testing OA Result Submission with Failing Score...")
print("=" * 60)

# Test with a failing score
failing_payload = {
    'candidate_email': 'failing_candidate@example.com',
    'candidate_name': 'Jane Smith',
    'score': 45,
    'report_url': 'https://example.com/report2'
}

try:
    response = requests.post('http://127.0.0.1:8000/oa/submit-result', json=failing_payload, timeout=10)
    if response.status_code == 200:
        data = response.json()
        print("[OK] Failing score submitted successfully")
        print(f"Response: {json.dumps(data, indent=2)}")
        print("\nNote: Failing scores (< 60) will not trigger scheduling workflow")
    else:
        print(f"[ERROR] {response.status_code}")
except Exception as e:
    print(f"[ERROR] Connection error: {e}")
