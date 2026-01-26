import requests

url = "http://127.0.0.1:5678/webhook-test/hr-intake"
files = [
    ('resumes', ('test_resume.txt', 'This is a test resume content', 'text/plain'))
]
data = {
    'jd_text': 'This is a test JD'
}

try:
    print(f"Sending POST request to {url}...")
    response = requests.post(url, files=files, data=data)
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.text}")
except Exception as e:
    print(f"Error: {e}")
