import os
import toml
import sys

class ResumeAnalyzerAgent:
    def __init__(self):
        print("Initializing ResumeAnalyzerAgent...")
        self.llm = self._get_llm()
        if self.llm:
            print("ResumeAnalyzerAgent: LLM successfully configured.")
        else:
            print("ResumeAnalyzerAgent: LLM FAILED to configure.")
    
    def _get_llm(self):
        # 1. Check Environment Variable
        api_key = os.getenv("OPENAI_API_KEY")
        if api_key:
            print("ResumeAnalyzerAgent: Found OPENAI_API_KEY in environment variables.")
        
        # 2. Check secrets.toml if not in env
        if not api_key:
            try:
                # Strategy A: Relative to this file
                current_dir = os.path.dirname(os.path.abspath(__file__))
                project_root = os.path.dirname(os.path.dirname(current_dir))
                secrets_path_a = os.path.join(project_root, "secrets.toml")
                
                # Strategy B: Current Working Directory
                secrets_path_b = os.path.join(os.getcwd(), "secrets.toml")
                
                secrets_path = None
                if os.path.exists(secrets_path_a):
                    secrets_path = secrets_path_a
                elif os.path.exists(secrets_path_b):
                    secrets_path = secrets_path_b
                
                if secrets_path:
                    print(f"ResumeAnalyzerAgent: Found secrets.toml at {secrets_path}")
                    secrets = toml.load(secrets_path)
                    api_key = secrets.get("OPENAI_API_KEY") or secrets.get("openai_api_key")
                    if api_key:
                        print("ResumeAnalyzerAgent: Loaded API Key from secrets.toml")
                    else:
                        print("ResumeAnalyzerAgent: secrets.toml found but NO 'OPENAI_API_KEY' inside.")
                else:
                     print(f"ResumeAnalyzerAgent: secrets.toml NOT found at {secrets_path_a} or {secrets_path_b}")

            except Exception as e:
                print(f"ResumeAnalyzerAgent: Error loading secrets.toml: {e}")

        if not api_key:
            print("ResumeAnalyzerAgent: CRITICAL ERROR - OPENAI_API_KEY not found.")
            return None
            
        # Ensure it's in env for other libs
        os.environ["OPENAI_API_KEY"] = api_key
        
        try:
            from langchain_openai import ChatOpenAI
            # Use gpt-4o-mini or gpt-3.5-turbo as fallback
            return ChatOpenAI(temperature=0, openai_api_key=api_key, model_name="gpt-4o-mini")
        except Exception as e:
            print(f"ResumeAnalyzerAgent: Error initializing ChatOpenAI: {e}")
            return None

    def analyze_sentiment_and_summary(self, resume_text: str) -> dict:
        if not self.llm:
            return {"error": "LLM not configured"}

        template = """
        You are an expert HR AI assistant. Analyze the following resume text.
        
        RESUME TEXT:
        {resume_text}
        
        Please provide:
        1. "professional_summary": A brief professional summary (max 3 sentences).
        2. "sentiment_analysis": Sentiment analysis of the candidate's tone (Confident, Passive, Academic, etc.).
        3. "top_functional_skills": A list of top 5 functional skills.
        4. "hiring_potential_score": A "Hiring Potential" score from 1-10 based on clarity and depth.
        
        Output as a valid JSON object only. Do not include any markdown formatting or backticks.
        """
        
        from langchain_core.prompts import PromptTemplate
        prompt = PromptTemplate(template=template, input_variables=["resume_text"])
        chain = prompt | self.llm
        
        try:
            response = chain.invoke({"resume_text": resume_text[:4000]}) # Truncate for token limits if needed
            
            content = response.content.strip()
            # Clean up potential markdown code blocks
            if content.startswith("```json"):
                content = content[7:]
            if content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]
            
            import json
            try:
                return json.loads(content.strip())
            except json.JSONDecodeError:
                # Fallback if parsing fails, but return structure so it doesn't break frontend
                return {
                    "error": "Failed to parse JSON",
                    "raw_content": content
                }
                
        except Exception as e:
            return {"error": str(e)}

    def generate_job_description(self, role: str, experience: str, skills: str) -> str:
        if not self.llm:
            return "Error: LLM not configured."

        template = """
        You are an expert HR Manager. Write a professional Job Description (JD) for the following role.
        
        Role: {role}
        Experience Level: {experience}
        Must-Have Skills: {skills}
        
        The JD should include:
        1. Job Title
        2. Brief Role Overview
        3. Key Responsibilities (bullet points)
        4. Required Skills & Qualifications
        5. Preferred Skills
        6. Salary Range (Estimate based on role/experience, standard market rates)
        
        Tone: Professional, Engaging.
        """
        
        from langchain_core.prompts import PromptTemplate
        prompt = PromptTemplate(template=template, input_variables=["role", "experience", "skills"])
        chain = prompt | self.llm
        
        try:
            response = chain.invoke({
                "role": role, 
                "experience": experience, 
                "skills": skills
            })
            return response.content
        except Exception as e:
            return f"Error generating JD: {str(e)}"
