"""
Unit tests for resume_service.py
Tests resume parsing, text extraction, and data validation.
"""

import pytest
from backend.services.resume_service import (
    extract_name,
    extract_email,
    extract_contact_number,
    extract_skills,
    extract_education,
    clean_line_for_name,
    looks_like_section_header,
    guess_name_from_email,
)


class TestNameExtraction:
    """Test cases for candidate name extraction."""
    
    def test_extract_name_simple(self):
        """Test extracting a simple name from the first line."""
        text = "John Doe\nEmail: john@example.com\nPhone: 1234567890"
        result = extract_name(text)
        assert result == "John Doe"
    
    def test_extract_name_with_middle_name(self):
        """Test extracting name with middle name."""
        text = "Jane Mary Smith\nSoftware Engineer\njane.smith@email.com"
        result = extract_name(text)
        assert result == "Jane Mary Smith"
    
    def test_extract_name_with_initials(self):
        """Test extracting name with initials."""
        text = "R. Kumar\nData Scientist\nrkumar@company.com"
        result = extract_name(text)
        assert result == "R. Kumar" or "Kumar" in result
    
    def test_extract_name_uppercase(self):
        """Test extracting name in all caps."""
        text = "MICHAEL JOHNSON\n123 Main St\nmichael@example.com"
        result = extract_name(text)
        assert result == "MICHAEL JOHNSON"
    
    def test_extract_name_with_contact_info(self):
        """Test extracting name when contact info is on same line."""
        text = "Alice Brown | alice.brown@email.com | +1-555-0100"
        result = extract_name(text)
        assert result == "Alice Brown"
    
    def test_extract_name_from_email_fallback(self):
        """Test name extraction fallback using email."""
        text = "john.doe123@example.com\nExperience: 5 years"
        result = extract_name(text)
        assert "John" in result and "Doe" in result
    
    def test_extract_name_empty_text(self):
        """Test name extraction with empty text."""
        result = extract_name("")
        assert result is None
    
    def test_extract_name_no_valid_name(self):
        """Test when no valid name is found."""
        text = "Education\nExperience\nSkills"
        result = extract_name(text)
        assert result is None or result == ""


class TestEmailExtraction:
    """Test cases for email extraction."""
    
    def test_extract_email_simple(self):
        """Test extracting a simple email."""
        text = "Name: John Doe\nEmail: john.doe@example.com"
        result = extract_email(text)
        assert result == "john.doe@example.com"
    
    def test_extract_email_with_label(self):
        """Test extracting email with 'Email:' label."""
        text = "Email: alice@company.org\nPhone: 1234567890"
        result = extract_email(text)
        assert result == "alice@company.org"
    
    def test_extract_email_in_middle(self):
        """Test extracting email from middle of document."""
        text = "John Smith\nSoftware Engineer\nContact: john.smith@tech.com\nExperience"
        result = extract_email(text)
        assert result == "john.smith@tech.com"
    
    def test_extract_email_multiple_emails(self):
        """Test extracting first valid email when multiple present."""
        text = "Primary: user@example.com\nSecondary: backup@test.com"
        result = extract_email(text)
        assert result in ["user@example.com", "backup@test.com"]
    
    def test_extract_email_none(self):
        """Test when no email is present."""
        text = "John Doe\nSoftware Engineer\nExperience: 5 years"
        result = extract_email(text)
        assert result is None
    
    def test_extract_email_invalid(self):
        """Test that invalid emails are skipped."""
        text = "Contact: notanemail.com\nReal: valid@email.com"
        result = extract_email(text)
        assert result == "valid@email.com"


class TestPhoneExtraction:
    """Test cases for phone number extraction."""
    
    def test_extract_phone_simple(self):
        """Test extracting a simple 10-digit phone number."""
        text = "John Doe\n1234567890\njohn@example.com"
        result = extract_contact_number(text)
        assert result is not None
        assert "1234567890" in result.replace("-", "").replace(" ", "").replace("+", "")
    
    def test_extract_phone_with_country_code(self):
        """Test extracting phone with country code."""
        text = "Contact: +91-98765-43210"
        result = extract_contact_number(text)
        assert result is not None
        assert "91" in result or "98765" in result
    
    def test_extract_phone_formatted(self):
        """Test extracting formatted phone number."""
        text = "Phone: (123) 456-7890"
        result = extract_contact_number(text)
        assert result is not None
    
    def test_extract_phone_indian_format(self):
        """Test extracting Indian phone number format."""
        text = "Mobile: 98765 43210"
        result = extract_contact_number(text)
        assert result is not None
    
    def test_extract_phone_none(self):
        """Test when no phone number is present."""
        text = "John Doe\nSoftware Engineer"
        result = extract_contact_number(text)
        assert result is None


class TestSkillsExtraction:
    """Test cases for skills extraction."""
    
    def test_extract_skills_programming(self):
        """Test extracting programming language skills."""
        text = "Skills: Python, Java, JavaScript, C++"
        result = extract_skills(text)
        assert "python" in result
        assert "java" in result
        assert "javascript" in result
    
    def test_extract_skills_frameworks(self):
        """Test extracting framework skills."""
        text = "Experience with React, Django, Flask, and FastAPI"
        result = extract_skills(text)
        assert "react" in result
        assert "django" in result
        assert "flask" in result
        assert "fastapi" in result
    
    def test_extract_skills_cloud(self):
        """Test extracting cloud platform skills."""
        text = "Cloud: AWS, Azure, GCP, Docker, Kubernetes"
        result = extract_skills(text)
        assert "aws" in result
        assert "docker" in result
        assert "kubernetes" in result
    
    def test_extract_skills_database(self):
        """Test extracting database skills."""
        text = "Databases: PostgreSQL, MongoDB, MySQL, Redis"
        result = extract_skills(text)
        assert "postgresql" in result
        assert "mongodb" in result
        assert "mysql" in result
        assert "redis" in result
    
    def test_extract_skills_mixed_case(self):
        """Test that skill extraction is case-insensitive."""
        text = "PYTHON, Java, reactJS, postgresql"
        result = extract_skills(text)
        assert "python" in result
        assert "java" in result
    
    def test_extract_skills_empty(self):
        """Test when no skills are present."""
        text = "John Doe\nSoftware Engineer"
        result = extract_skills(text)
        assert isinstance(result, list)
    
    def test_extract_skills_machine_learning(self):
        """Test extracting ML/AI skills."""
        text = "ML: TensorFlow, PyTorch, scikit-learn, pandas, numpy"
        result = extract_skills(text)
        assert "tensorflow" in result or "pytorch" in result
        assert "pandas" in result
        assert "numpy" in result


class TestEducationExtraction:
    """Test cases for education extraction."""
    
    def test_extract_education_btech(self):
        """Test extracting B.Tech degree."""
        text = """
        Education
        B.Tech in Computer Science
        IIT Delhi, 2020
        CGPA: 8.5
        """
        result = extract_education(text)
        assert len(result) > 0
        assert any("tech" in edu.lower() for edu in result)
    
    def test_extract_education_masters(self):
        """Test extracting Master's degree."""
        text = """
        M.Tech in Data Science
        NIT Trichy, 2022
        CGPA: 9.0
        """
        result = extract_education(text)
        assert len(result) > 0
        assert any("m.tech" in edu.lower() or "m tech" in edu.lower() for edu in result)
    
    def test_extract_education_bachelor(self):
        """Test extracting Bachelor's degree."""
        text = """
        Bachelor of Science in Computer Science
        University of California
        GPA: 3.8
        """
        result = extract_education(text)
        assert len(result) > 0
        assert any("bachelor" in edu.lower() for edu in result)
    
    def test_extract_education_multiple(self):
        """Test extracting multiple degrees."""
        text = """
        Education:
        M.Tech in AI, IIT Bombay, 2023, CGPA: 9.2
        B.Tech in CSE, NIT Surathkal, 2021, CGPA: 8.7
        """
        result = extract_education(text)
        assert len(result) >= 1
    
    def test_extract_education_none(self):
        """Test when no education information is present."""
        text = "Experience: 5 years in software development"
        result = extract_education(text)
        assert isinstance(result, list)


class TestHelperFunctions:
    """Test cases for helper utility functions."""
    
    def test_clean_line_for_name(self):
        """Test line cleaning for name extraction."""
        result = clean_line_for_name("  John    Doe  ")
        assert result == "John Doe"
    
    def test_looks_like_section_header_true(self):
        """Test detecting section headers."""
        assert looks_like_section_header("Education")
        assert looks_like_section_header("Work Experience")
        assert looks_like_section_header("SKILLS")
    
    def test_looks_like_section_header_false(self):
        """Test that regular text is not detected as header."""
        assert not looks_like_section_header("John Doe is a software engineer")
        assert not looks_like_section_header("jane@example.com")
    
    def test_guess_name_from_email(self):
        """Test name guessing from email."""
        result = guess_name_from_email("john.doe@example.com")
        assert "John" in result
        assert "Doe" in result
    
    def test_guess_name_from_email_with_numbers(self):
        """Test name guessing with numbers in email."""
        result = guess_name_from_email("alice.smith123@company.com")
        assert "Alice" in result
        assert "Smith" in result
        assert "123" not in result


class TestEdgeCases:
    """Test edge cases and error handling."""
    
    def test_empty_text_handling(self):
        """Test handling of empty text."""
        assert extract_name("") is None
        assert extract_email("") is None
        assert extract_contact_number("") is None
        assert extract_skills("") == []
        assert extract_education("") == []
    
    def test_special_characters(self):
        """Test handling of special characters."""
        text = "Jöhn Döe\njohn@example.com\n☎ 1234567890"
        name = extract_name(text)
        email = extract_email(text)
        phone = extract_contact_number(text)
        
        assert email == "john@example.com"
        assert phone is not None
    
    def test_very_long_text(self):
        """Test handling of very long resume text."""
        text = ("Lorem ipsum " * 10000) + "\nJohn Doe\njohn@example.com\n1234567890"
        result = extract_email(text)
        assert result is not None
    
    def test_unicode_handling(self):
        """Test handling of Unicode characters."""
        text = "राज कुमार\nEmail: raj@example.com\nPhone: 9876543210"
        email = extract_email(text)
        assert email == "raj@example.com"


# Fixtures for test data
@pytest.fixture
def sample_resume_text():
    """Sample resume text for testing."""
    return """
    JOHN DOE
    Email: john.doe@example.com | Phone: +1-555-0100
    LinkedIn: linkedin.com/in/johndoe | GitHub: github.com/johndoe
    
    PROFESSIONAL SUMMARY
    Experienced Software Engineer with 5+ years in full-stack development.
    
    SKILLS
    Programming: Python, Java, JavaScript, TypeScript, C++
    Web: React, Node.js, Django, FastAPI, HTML, CSS
    Databases: PostgreSQL, MongoDB, Redis
    Cloud: AWS, Docker, Kubernetes
    Tools: Git, Jenkins, Jira
    
    EXPERIENCE
    Senior Software Engineer | Tech Corp | 2020-Present
    - Developed scalable microservices using FastAPI
    - Led team of 5 developers
    
    Software Engineer | StartupXYZ | 2018-2020
    - Built full-stack web applications
    
    EDUCATION
    M.S. in Computer Science
    Stanford University, 2018
    GPA: 3.9/4.0
    
    B.Tech in Computer Engineering
    IIT Delhi, 2016
    CGPA: 8.7/10
    """


@pytest.fixture
def minimal_resume_text():
    """Minimal resume text for testing."""
    return """
    Jane Smith
    jane.smith@email.com
    9876543210
    
    Skills: Python, SQL, Excel
    """


class TestCompleteResumeProcessing:
    """Integration tests for complete resume processing."""
    
    def test_process_complete_resume(self, sample_resume_text):
        """Test processing a complete resume."""
        name = extract_name(sample_resume_text)
        email = extract_email(sample_resume_text)
        phone = extract_contact_number(sample_resume_text)
        skills = extract_skills(sample_resume_text)
        education = extract_education(sample_resume_text)
        
        assert name is not None
        assert "john" in name.lower() or "doe" in name.lower()
        assert email == "john.doe@example.com"
        assert phone is not None
        assert len(skills) > 0
        assert "python" in skills
        assert len(education) > 0
    
    def test_process_minimal_resume(self, minimal_resume_text):
        """Test processing a minimal resume."""
        name = extract_name(minimal_resume_text)
        email = extract_email(minimal_resume_text)
        phone = extract_contact_number(minimal_resume_text)
        skills = extract_skills(minimal_resume_text)
        
        assert name == "Jane Smith"
        assert email == "jane.smith@email.com"
        assert phone is not None
        assert len(skills) > 0
