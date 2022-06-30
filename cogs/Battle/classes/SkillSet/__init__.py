from .skills.Skill import get_skill

class SkillSet:
    def __init__(self):
        self.skills = []

    def dict(self):
        return {
            'skills': [skill.dict() for skill in self.skills]
        }
    
    @classmethod
    def from_data(cls, data):
        skill_set = cls()
        skill_set.skills = [get_skill(skill) for skill in data['skills']]
        return skill_set
    