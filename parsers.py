# ============================================
# SkillBridge - Resume Parser
# File: parsers.py
# Uses NLP to extract skills from PDF resumes
# ============================================

import re
import os

# Install these: pip install PyPDF2 python-docx
try:
    import PyPDF2
    PDF_SUPPORT = True
except ImportError:
    PDF_SUPPORT = False

try:
    from docx import Document
    DOCX_SUPPORT = True
except ImportError:
    DOCX_SUPPORT = False


class ResumeParser:
    """
    Parses PDF/DOCX resumes and extracts:
    - Technical Skills
    - Education Details
    - Work Experience
    - ATS Score
    """

    def __init__(self):
        # Master skill list to search for in resume
        self.skill_keywords = [
            # Programming Languages
            'python', 'java', 'javascript', 'c++', 'c#', 'ruby',
            'php', 'swift', 'kotlin', 'golang', 'rust', 'scala',
            'typescript', 'r', 'matlab',

            # Web Technologies
            'html', 'css', 'html5', 'css3', 'bootstrap', 'tailwind',
            'react', 'angular', 'vue', 'nodejs', 'express', 'django',
            'flask', 'spring boot', 'rest api', 'graphql',

            # Databases
            'sql', 'mysql', 'postgresql', 'mongodb', 'oracle',
            'sqlite', 'redis', 'cassandra', 'firebase',

            # AI/ML
            'machine learning', 'deep learning', 'nlp',
            'natural language processing', 'computer vision',
            'tensorflow', 'pytorch', 'keras', 'scikit-learn',
            'pandas', 'numpy', 'opencv', 'data science',

            # Cloud & DevOps
            'aws', 'azure', 'gcp', 'docker', 'kubernetes',
            'jenkins', 'ci/cd', 'terraform', 'ansible',

            # Tools
            'git', 'github', 'linux', 'excel', 'tableau',
            'power bi', 'jira', 'figma', 'postman',

            # Android/Mobile
            'android', 'ios', 'flutter', 'react native',
            'android development', 'mobile development'
        ]

        # ATS important keywords
        self.ats_keywords = [
            'experience', 'project', 'internship', 'education',
            'skills', 'achievement', 'certification', 'training',
            'volunteer', 'leadership', 'communication', 'team'
        ]

    def parse_resume(self, file_path):
        """
        Main method to parse resume file.
        
        Parameters:
            file_path (str): Path to resume file
        
        Returns:
            dict: Extracted resume data
        """
        # Extract raw text based on file type
        file_extension = file_path.rsplit('.', 1)[1].lower()

        if file_extension == 'pdf':
            raw_text = self._extract_from_pdf(file_path)
        elif file_extension == 'docx':
            raw_text = self._extract_from_docx(file_path)
        else:
            raw_text = ""

        if not raw_text:
            return {
                'skills': [],
                'education': '',
                'experience': '',
                'ats_score': 0.0,
                'word_count': 0
            }

        # Extract components
        skills = self._extract_skills(raw_text)
        education = self._extract_education(raw_text)
        experience = self._extract_experience(raw_text)
        ats_score = self._calculate_ats_score(raw_text, skills)

        return {
            'skills': skills,
            'education': education,
            'experience': experience,
            'ats_score': ats_score,
            'word_count': len(raw_text.split()),
            'raw_text_preview': raw_text[:500]
        }

    def _extract_from_pdf(self, file_path):
        """Extract text from PDF file"""
        if not PDF_SUPPORT:
            return ""

        text = ""
        try:
            with open(file_path, 'rb') as pdf_file:
                reader = PyPDF2.PdfReader(pdf_file)
                for page_num in range(len(reader.pages)):
                    page = reader.pages[page_num]
                    text += page.extract_text() + "\n"
        except Exception as e:
            print(f"PDF parsing error: {e}")
            text = ""

        return text.lower()

    def _extract_from_docx(self, file_path):
        """Extract text from DOCX file"""
        if not DOCX_SUPPORT:
            return ""

        text = ""
        try:
            doc = Document(file_path)
            for paragraph in doc.paragraphs:
                text += paragraph.text + "\n"
        except Exception as e:
            print(f"DOCX parsing error: {e}")
            text = ""

        return text.lower()

    def _extract_skills(self, text):
        """Extract technical skills from resume text"""
        found_skills = []
        text_lower = text.lower()

        for skill in self.skill_keywords:
            # Use word boundary matching
            pattern = r'\b' + re.escape(skill) + r'\b'
            if re.search(pattern, text_lower):
                # Capitalize properly for display
                found_skills.append(skill.title())

        # Remove duplicates while preserving order
        seen = set()
        unique_skills = []
        for skill in found_skills:
            if skill.lower() not in seen:
                seen.add(skill.lower())
                unique_skills.append(skill)

        return unique_skills

    def _extract_education(self, text):
        """Extract education details"""
        education_patterns = [
            r'b\.?tech|bachelor|b\.?e\.|engineering',
            r'm\.?tech|master|m\.?e\.',
            r'10th|12th|ssc|hsc|cbse|state board',
            r'cgpa|gpa|percentage|aggregate'
        ]

        education_lines = []
        lines = text.split('\n')

        for line in lines:
            line = line.strip()
            for pattern in education_patterns:
                if re.search(pattern, line.lower()) and len(line) > 5:
                    education_lines.append(line)
                    break

        return ' | '.join(education_lines[:5])

    def _extract_experience(self, text):
        """Extract work experience section"""
        experience_patterns = [
            r'internship|intern|worked at|experience',
            r'project|developed|built|created|implemented',
            r'company|organization|firm'
        ]

        experience_lines = []
        lines = text.split('\n')

        for line in lines:
            line = line.strip()
            for pattern in experience_patterns:
                if re.search(pattern, line.lower()) and len(line) > 10:
                    experience_lines.append(line)
                    break

        return ' | '.join(experience_lines[:5])

    def _calculate_ats_score(self, text, skills):
        """
        Calculate ATS (Applicant Tracking System) Score.
        Score based on:
        - Number of skills found (40%)
        - Important sections present (30%)
        - Resume length/completeness (20%)
        - Action verbs used (10%)
        """
        score = 0

        # Component 1: Skills score (40 points)
        skills_score = min(len(skills) * 3, 40)
        score += skills_score

        # Component 2: Important sections (30 points)
        important_sections = [
            'education', 'experience', 'project', 'skill',
            'certification', 'achievement', 'objective', 'summary'
        ]
        sections_found = sum(
            1 for section in important_sections
            if section in text.lower()
        )
        sections_score = min(sections_found * 4, 30)
        score += sections_score

        # Component 3: Resume length (20 points)
        word_count = len(text.split())
        if word_count >= 400:
            score += 20
        elif word_count >= 250:
            score += 15
        elif word_count >= 150:
            score += 10
        else:
            score += 5

        # Component 4: Action verbs (10 points)
        action_verbs = [
            'developed', 'implemented', 'designed', 'built',
            'created', 'managed', 'led', 'achieved', 'improved',
            'analyzed', 'collaborated', 'coordinated'
        ]
        verbs_found = sum(
            1 for verb in action_verbs
            if verb in text.lower()
        )
        verbs_score = min(verbs_found * 2, 10)
        score += verbs_score

        return round(min(score, 100), 2)