# ============================================
# SkillBridge - AI Models
# File: models.py
# Machine Learning + Skill Gap Analysis
# ============================================

import pandas as pd
import numpy as np
from sklearn.tree import DecisionTreeClassifier
from sklearn.preprocessing import LabelEncoder
import pickle
import os

# ============================================
# CLASS 1: Skill Gap Analyzer (Core AI)
# ============================================
class SkillGapAnalyzer:
    """
    Analyzes the gap between student skills
    and job requirements.
    Uses set-based matching + TF-IDF weighting.
    """

    def __init__(self):
        # High demand skills get more weight
        self.skill_weights = {
            'python': 1.5,
            'java': 1.5,
            'machine learning': 2.0,
            'sql': 1.3,
            'javascript': 1.4,
            'react': 1.4,
            'docker': 1.2,
            'aws': 1.3,
            'spring boot': 1.4,
            'flask': 1.2,
            'html': 1.0,
            'css': 1.0,
            'git': 1.1,
            'data science': 1.8,
            'rest api': 1.3
        }

    def analyze_gap(self, student_skills, required_skills):
        """
        Compare student skills with job requirements.
        
        Parameters:
            student_skills (list): Skills the student has
            required_skills (list): Skills job needs
        
        Returns:
            dict: Analysis results with match percentage
        """
        # Normalize to lowercase
        student_set = set([s.lower().strip() for s in student_skills])
        required_set = set([s.lower().strip() for s in required_skills])

        # Find matched and missing skills
        matched_skills = student_set.intersection(required_set)
        missing_skills = required_set - student_set

        # Calculate weighted match score
        total_weight = 0
        matched_weight = 0

        for skill in required_set:
            weight = self.skill_weights.get(skill, 1.0)
            total_weight += weight
            if skill in matched_skills:
                matched_weight += weight

        # Calculate match percentage
        if total_weight > 0:
            match_percentage = round(
                (matched_weight / total_weight) * 100, 2
            )
        else:
            match_percentage = 0.0

        # Generate feedback message
        message = self._generate_message(match_percentage)

        return {
            'match_percentage': match_percentage,
            'matched_skills': list(matched_skills),
            'missing_skills': list(missing_skills),
            'total_required': len(required_set),
            'total_matched': len(matched_skills),
            'message': message
        }

    def _generate_message(self, match_percentage):
        """Generate human readable feedback"""
        if match_percentage >= 80:
            return 'Excellent match! You are highly eligible for this role.'
        elif match_percentage >= 60:
            return 'Good match! Learn a few missing skills to boost chances.'
        elif match_percentage >= 40:
            return 'Average match. Focus on upskilling the missing areas.'
        elif match_percentage >= 20:
            return 'Low match. Consider building foundational skills first.'
        else:
            return 'Very low match. This role needs significant skill development.'

    def get_course_recommendations(self, missing_skills):
        """
        Recommend courses for missing skills.
        In production, this fetches from the DB.
        Here we use a static mapping for demo.
        """
        course_map = {
            'python': {
                'course': 'Python for Everybody',
                'platform': 'Coursera',
                'url': 'https://www.coursera.org/specializations/python',
                'duration': '7 months'
            },
            'machine learning': {
                'course': 'ML by Andrew Ng',
                'platform': 'Coursera',
                'url': 'https://www.coursera.org/learn/machine-learning',
                'duration': '3 months'
            },
            'java': {
                'course': 'Java Programming Masterclass',
                'platform': 'Udemy',
                'url': 'https://www.udemy.com/course/java-the-complete-java-developer-course',
                'duration': '2 months'
            },
            'sql': {
                'course': 'SQL for Data Science',
                'platform': 'Coursera',
                'url': 'https://www.coursera.org/learn/sql-for-data-science',
                'duration': '4 weeks'
            },
            'react': {
                'course': 'React - The Complete Guide',
                'platform': 'Udemy',
                'url': 'https://www.udemy.com/course/react-the-complete-guide-incl-redux',
                'duration': '2 months'
            },
            'docker': {
                'course': 'Docker and Kubernetes',
                'platform': 'Udemy',
                'url': 'https://www.udemy.com/course/docker-and-kubernetes-the-complete-guide',
                'duration': '6 weeks'
            },
            'aws': {
                'course': 'AWS Certified Solutions Architect',
                'platform': 'AWS Training',
                'url': 'https://aws.amazon.com/training',
                'duration': '3 months'
            }
        }

        recommendations = []
        for skill in missing_skills:
            skill_lower = skill.lower()
            if skill_lower in course_map:
                rec = course_map[skill_lower].copy()
                rec['skill'] = skill
                recommendations.append(rec)
            else:
                recommendations.append({
                    'skill': skill,
                    'course': f'Search: {skill} Tutorial',
                    'platform': 'YouTube / Google',
                    'url': f'https://www.youtube.com/results?search_query={skill}+tutorial',
                    'duration': 'Self-paced'
                })

        return recommendations


# ============================================
# CLASS 2: Placement Readiness Predictor (ML)
# ============================================
class PlacementPredictor:
    """
    Predicts whether a student is placement-ready
    using a Decision Tree Classifier.
    """

    def __init__(self):
        self.model = None
        self.model_path = 'ml_models/placement_model.pkl'
        self._load_or_train_model()

    def _generate_training_data(self):
        """
        Generate synthetic training data.
        In production, use real historical placement data.
        """
        np.random.seed(42)
        n_samples = 500

        # Features: cgpa, skills_count, backlogs, test_score
        cgpa = np.random.uniform(5.0, 10.0, n_samples)
        skills_count = np.random.randint(2, 20, n_samples)
        backlogs = np.random.randint(0, 5, n_samples)
        test_score = np.random.uniform(20, 100, n_samples)

        # Create labels based on realistic logic
        placement_ready = []
        for i in range(n_samples):
            score = (
                (cgpa[i] / 10) * 40 +
                (min(skills_count[i], 15) / 15) * 30 +
                ((5 - backlogs[i]) / 5) * 10 +
                (test_score[i] / 100) * 20
            )
            placement_ready.append(1 if score >= 55 else 0)

        data = pd.DataFrame({
            'cgpa': cgpa,
            'skills_count': skills_count,
            'backlogs': backlogs,
            'test_score': test_score,
            'placed': placement_ready
        })

        return data

    def _load_or_train_model(self):
        """Load existing model or train a new one"""
        os.makedirs('ml_models', exist_ok=True)

        if os.path.exists(self.model_path):
            with open(self.model_path, 'rb') as f:
                self.model = pickle.load(f)
        else:
            self._train_model()

    def _train_model(self):
        """Train the Decision Tree model"""
        data = self._generate_training_data()

        features = ['cgpa', 'skills_count', 'backlogs', 'test_score']
        X = data[features]
        y = data['placed']

        self.model = DecisionTreeClassifier(
            max_depth=5,
            random_state=42,
            min_samples_split=10
        )
        self.model.fit(X, y)

        # Save trained model
        with open(self.model_path, 'wb') as f:
            pickle.dump(self.model, f)

        print("Model trained and saved successfully!")

    def predict_readiness(self, cgpa, skills_count, backlogs, test_score=60):
        """
        Predict placement readiness score (0-100).
        
        Parameters:
            cgpa (float): Student CGPA
            skills_count (int): Number of skills student has
            backlogs (int): Number of backlogs
            test_score (float): Average test score
        
        Returns:
            float: Readiness score between 0 and 100
        """
        if self.model is None:
            self._train_model()

        features = np.array([[cgpa, skills_count, backlogs, test_score]])
        probability = self.model.predict_proba(features)[0]

        # Convert to percentage
        if len(probability) > 1:
            readiness_score = round(probability[1] * 100, 2)
        else:
            readiness_score = round(probability[0] * 100, 2)

        return readiness_score

    def get_readiness_label(self, score):
        """Convert score to human readable label"""
        if score >= 75:
            return {'label': 'HIGH', 'color': 'success', 'emoji': '🟢'}
        elif score >= 50:
            return {'label': 'MEDIUM', 'color': 'warning', 'emoji': '🟡'}
        else:
            return {'label': 'LOW', 'color': 'danger', 'emoji': '🔴'}