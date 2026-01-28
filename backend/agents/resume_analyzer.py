import os
import toml

class ResumeAnalyzerAgent:
    def __init__(self):
        self.llm = self._get_llm()
    
    def _get_llm(self):
        # Load API Key
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            if os.path.exists("secrets.toml"):
                secrets = toml.load("secrets.toml")
                api_key = secrets.get("OPENAI_API_KEY") or secrets.get("openai_api_key")
            elif os.path.exists("../secrets.toml"):
                secrets = toml.load("../secrets.toml")
                api_key = secrets.get("OPENAI_API_KEY") or secrets.get("openai_api_key")
        
        if not api_key:
            # Fallback or error - for now returning None to avoid crash during import if not set
            return None
            
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(temperature=0, openai_api_key=api_key, model_name="gpt-4o-mini")

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
