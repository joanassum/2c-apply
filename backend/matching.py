from openai import OpenAI
from database import JobPost, SeekerProfile
import json
import os
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(api_key=os.environ["DEEPSEEK_API_KEY"], base_url="https://api.deepseek.com")


def _parse(raw: str) -> list:
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    return json.loads(raw.strip())


def match_post_to_seekers(post: JobPost, company_name: str, seekers: list[SeekerProfile]) -> list[dict]:
    if not seekers:
        return []
    seekers_text = "\n\n".join([
        f"Seeker ID {s.user_id}:\nName: {s.full_name}\nTitle: {s.title}\nSkills: {s.skills}\n"
        f"Experience: {s.experience_years} years\nLocation: {s.location}\nDesired Role: {s.desired_role}\nBio: {s.bio}"
        for s in seekers
    ])
    prompt = f"""You are a job matching AI. Score each seeker against this job posting.

Company: {company_name}
Job Title: {post.title}
Job Description: {post.description}
Required Skills: {post.required_skills}
Location: {post.location}
Salary Range: {post.salary_range}

Job Seekers:
{seekers_text}

Return a JSON array only:
[{{"seeker_user_id": <id>, "score": <0.0-1.0>, "reasoning": "<1-2 sentences>"}}]"""

    raw = client.chat.completions.create(
        model="deepseek-chat",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
    ).choices[0].message.content
    return _parse(raw)


def match_seeker_to_posts(seeker: SeekerProfile, posts_with_company: list[tuple]) -> list[dict]:
    """posts_with_company: list of (JobPost, company_name)"""
    if not posts_with_company:
        return []
    posts_text = "\n\n".join([
        f"Job Post ID {p.id}:\nCompany: {name}\nTitle: {p.title}\nDescription: {p.description}\n"
        f"Required Skills: {p.required_skills}\nLocation: {p.location}\nSalary: {p.salary_range}"
        for p, name in posts_with_company
    ])
    prompt = f"""You are a job matching AI. Score each job posting against this seeker.

Seeker: {seeker.full_name}
Title: {seeker.title}
Skills: {seeker.skills}
Experience: {seeker.experience_years} years
Location: {seeker.location}
Desired Role: {seeker.desired_role}
Bio: {seeker.bio}

Job Postings:
{posts_text}

Return a JSON array only:
[{{"job_post_id": <id>, "score": <0.0-1.0>, "reasoning": "<1-2 sentences>"}}]"""

    raw = client.chat.completions.create(
        model="deepseek-chat",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
    ).choices[0].message.content
    return _parse(raw)
