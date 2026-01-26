
from backend.services.resume_service import extract_email, extract_skills, parse_resume
import io

def test_extraction():
    print("Testing extraction logic...")

    # Test Email Extraction
    case1 = "Name: John Doe\nEmail: john.doe@example.com\nPhone: 1234567890"
    assert extract_email(case1) == "john.doe@example.com", f"Failed case 1: {extract_email(case1)}"

    case2 = "Contact me at jane_smith123@gmail.co.in for more info."
    assert extract_email(case2) == "jane_smith123@gmail.co.in", f"Failed case 2: {extract_email(case2)}"

    case3 = "Email : contact@startup.io" # Space before colon
    assert extract_email(case3) == "contact@startup.io", f"Failed case 3: {extract_email(case3)}"

    print("Email extraction passed!")

    # Test Skill Extraction
    text = """
    Experienced Software Engineer with expertise in Python, Django, and React.
    Familiar with AWS services like EC2 and S3.
    Also used Docker and Kubernetes for deployment.
    """
    skills = extract_skills(text)
    expected = {"python", "django", "react", "aws", "docker", "kubernetes"}
    # Note: set comparison checks if all elements are present, ignoring order
    assert expected.issubset(set(skills)), f"Failed skills: {skills}"
    
    print("Skill extraction passed!")
    print("All tests passed!")

if __name__ == "__main__":
    test_extraction()
