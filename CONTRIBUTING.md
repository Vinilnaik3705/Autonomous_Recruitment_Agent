# Contributing to Autonomous Recruitment Agent

Thank you for your interest in contributing! This document provides guidelines and best practices for contributing to this project.

---

## 📋 Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [How to Contribute](#how-to-contribute)
- [Coding Standards](#coding-standards)
- [Testing Guidelines](#testing-guidelines)
- [Commit Message Guidelines](#commit-message-guidelines)
- [Pull Request Process](#pull-request-process)

---

## 🤝 Code of Conduct

- Be respectful and inclusive
- Provide constructive feedback
- Focus on what is best for the community
- Show empathy towards other community members

---

## 🚀 Getting Started

### Prerequisites

- Docker Desktop installed and running
- Git installed
- Python 3.9+ (for local development)
- Node.js 18+ (for frontend development)
- Basic understanding of FastAPI, React, and PostgreSQL

### Fork the Repository

1. Fork the repository on GitHub
2. Clone your fork locally:
   ```bash
   git clone https://github.com/YOUR_USERNAME/Autonomous_Recruitment_Agent.git
   cd Autonomous_Recruitment_Agent
   ```

3. Add the original repository as upstream:
   ```bash
   git remote add upstream https://github.com/Vinilnaik3705/Autonomous_Recruitment_Agent.git
   ```

---

## 💻 Development Setup

### Quick Start with Docker

```bash
# Copy environment variables
cp .env.example .env

# Edit .env and add your API keys
# - OPENAI_API_KEY
# - Firebase credentials

# Start all services
docker compose up -d --build

# View logs
docker compose logs -f
```

### Local Development (Backend)

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run database migrations
python init_db.py

# Start FastAPI server
uvicorn main:app --reload --port 8000
```

### Local Development (Frontend)

```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

---

## 🛠️ How to Contribute

### Types of Contributions

1. **Bug Fixes**: Fix existing issues
2. **New Features**: Add new functionality
3. **Documentation**: Improve docs, add examples
4. **Tests**: Add or improve test coverage
5. **Performance**: Optimize code performance
6. **Refactoring**: Improve code quality without changing functionality

### Finding Issues

- Check the [Issues](https://github.com/Vinilnaik3705/Autonomous_Recruitment_Agent/issues) page
- Look for issues labeled `good first issue` or `help wanted`
- Ask in discussions if you're unsure where to start

### Creating Issues

Before creating a new issue:
- Search existing issues to avoid duplicates
- Provide a clear, descriptive title
- Include steps to reproduce (for bugs)
- Add relevant labels

**Bug Report Template:**
```markdown
**Describe the bug**
A clear description of what the bug is.

**To Reproduce**
Steps to reproduce the behavior:
1. Go to '...'
2. Click on '...'
3. See error

**Expected behavior**
What you expected to happen.

**Environment:**
- OS: [e.g., Windows 10]
- Docker version: [e.g., 20.10.17]
- Browser: [e.g., Chrome 96]
```

---

## 📝 Coding Standards

### Python (Backend)

- Follow [PEP 8](https://pep8.org/) style guide
- Use type hints for function parameters and return values
- Maximum line length: 100 characters
- Use docstrings for functions and classes

**Example:**
```python
from typing import List, Optional
from backend.utils.logger import get_logger

logger = get_logger(__name__)


def process_resume(
    resume_text: str,
    job_id: Optional[int] = None
) -> Dict[str, Any]:
    """
    Process a resume and extract structured information.
    
    Args:
        resume_text: Raw text content of the resume
        job_id: Optional job ID for matching
        
    Returns:
        Dictionary containing extracted resume data
        
    Raises:
        ValueError: If resume_text is empty
    """
    if not resume_text.strip():
        logger.error("Empty resume text provided")
        raise ValueError("Resume text cannot be empty")
    
    logger.info(f"Processing resume (job_id={job_id})")
    # ... processing logic
    return result
```

### TypeScript/JavaScript (Frontend)

- Use TypeScript for type safety
- Follow Airbnb style guide
- Use functional components with hooks
- Use meaningful variable names

**Example:**
```typescript
interface CandidateData {
  id: number;
  name: string;
  email: string;
  score: number;
}

export const CandidateCard: React.FC<{ candidate: CandidateData }> = ({ 
  candidate 
}) => {
  const [isExpanded, setIsExpanded] = useState(false);
  
  return (
    <div className="candidate-card">
      {/* Component JSX */}
    </div>
  );
};
```

### File Organization

```
backend/
├── agents/          # AI agents (resume analyzer, matcher)
├── api/             # API route handlers
├── services/        # Business logic services
├── utils/           # Utility functions and helpers
├── tests/           # Test files (mirror structure)
└── workers/         # Background task workers

frontend/
├── src/
│   ├── components/  # Reusable UI components
│   ├── pages/       # Next.js pages
│   ├── hooks/       # Custom React hooks
│   ├── utils/       # Helper functions
│   └── types/       # TypeScript type definitions
```

---

## 🧪 Testing Guidelines

### Backend Tests

```bash
# Run all tests
cd backend
pytest

# Run specific test file
pytest tests/test_resume_service.py

# Run with coverage
pytest --cov=backend --cov-report=html
```

**Test Structure:**
```python
import pytest
from backend.services.resume_service import parse_resume

class TestResumeService:
    def test_parse_resume_valid_pdf(self):
        """Test parsing a valid PDF resume."""
        # Arrange
        with open("test_data/sample_resume.pdf", "rb") as f:
            content = f.read()
        
        # Act
        result = parse_resume(content, "sample_resume.pdf")
        
        # Assert
        assert result["name"] is not None
        assert result["email"] is not None
        assert len(result["skills"]) > 0
    
    def test_parse_resume_invalid_format(self):
        """Test parsing with unsupported file format."""
        with pytest.raises(ValueError):
            parse_resume(b"invalid content", "test.xyz")
```

### Frontend Tests

```bash
cd frontend
npm test

# Run with coverage
npm test -- --coverage
```

### Test Coverage Goals

- Aim for **80%+ code coverage**
- All new features must include tests
- Bug fixes should include regression tests

---

## 📨 Commit Message Guidelines

Follow [Conventional Commits](https://www.conventionalcommits.org/) format:

```
<type>(<scope>): <subject>

<body>

<footer>
```

### Types

- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, no logic change)
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks, dependency updates
- `perf`: Performance improvements

### Examples

```bash
feat(resume): add support for DOCX file parsing

Added python-docx library to parse Word documents.
Includes unit tests for DOCX parsing.

Closes #45
```

```bash
fix(scheduling): resolve timezone conversion bug

Fixed incorrect UTC conversion causing interview
scheduling errors for non-UTC timezones.

Fixes #78
```

```bash
docs(api): add OpenAPI examples for all endpoints

Added request/response examples to improve API
documentation usability.
```

---

## 🔄 Pull Request Process

### Before Submitting

1. **Create a new branch:**
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes** and commit following the commit guidelines

3. **Update documentation** if needed

4. **Add/update tests** for your changes

5. **Run tests locally:**
   ```bash
   # Backend
   cd backend && pytest
   
   # Frontend
   cd frontend && npm test
   ```

6. **Update your branch with latest main:**
   ```bash
   git fetch upstream
   git rebase upstream/main
   ```

### Submitting PR

1. Push your branch to your fork:
   ```bash
   git push origin feature/your-feature-name
   ```

2. Open a Pull Request on GitHub

3. Fill out the PR template completely

4. Link related issues using keywords:
   - `Fixes #123`
   - `Closes #456`
   - `Related to #789`

### PR Template

```markdown
## Description
Brief description of changes made.

## Type of Change
- [ ] Bug fix (non-breaking change)
- [ ] New feature (non-breaking change)
- [ ] Breaking change (fix or feature that would cause existing functionality to change)
- [ ] Documentation update

## How Has This Been Tested?
Describe the tests you ran and how to reproduce.

## Checklist
- [ ] My code follows the project's coding standards
- [ ] I have added tests that prove my fix/feature works
- [ ] All new and existing tests pass locally
- [ ] I have updated the documentation accordingly
- [ ] My changes generate no new warnings
- [ ] I have added comments to complex code sections

## Screenshots (if applicable)
Add screenshots to demonstrate UI changes.
```

### Review Process

- Maintainers will review your PR within 1-3 business days
- Address review comments by pushing new commits
- Once approved, a maintainer will merge your PR
- Your contribution will be credited in release notes

---

## 🎯 Priority Areas for Contribution

### High Priority
- [ ] Adding unit tests for existing services
- [ ] Improving error handling and logging
- [ ] API documentation and examples
- [ ] Performance optimization

### Medium Priority
- [ ] Frontend UI/UX improvements
- [ ] Additional AI model integrations
- [ ] Analytics and reporting features
- [ ] Mobile responsiveness

### Low Priority
- [ ] Code refactoring
- [ ] Additional export formats
- [ ] Theme customization
- [ ] Advanced scheduling features

---

## 📚 Additional Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Next.js Documentation](https://nextjs.org/docs)
- [Docker Documentation](https://docs.docker.com/)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [LangChain Documentation](https://python.langchain.com/)

---

## ❓ Questions?

- Open a [Discussion](https://github.com/Vinilnaik3705/Autonomous_Recruitment_Agent/discussions)
- Check existing [Issues](https://github.com/Vinilnaik3705/Autonomous_Recruitment_Agent/issues)
- Review the [README](README.md)

---

## 🙏 Thank You!

Every contribution, no matter how small, is valuable and appreciated. Happy coding! 🚀
