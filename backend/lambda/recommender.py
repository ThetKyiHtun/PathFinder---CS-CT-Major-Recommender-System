"""PathFinder rule-based recommender engine.

Deterministic fallback used when the Bedrock Knowledge Base is not
configured (or unreachable). It maps a freshman's interests, strengths and
career ambitions to CS/CT academic tracks and returns a career roadmap.
"""

import json

TRACKS = [
    {
        "id": "ai-ml",
        "name": "AI & Machine Learning",
        "summary": "Build systems that learn from data: models, agents and intelligent interfaces.",
        "interests": ["AI", "machine learning", "data science", "computer vision", "NLP", "chatbots"],
        "strengths": ["mathematics", "logic", "programming", "statistics"],
        "ambitions": ["AI Researcher", "Machine Learning Engineer", "Data Scientist", "AI Engineer"],
        "core_courses": [
            "Data Structures & Algorithms",
            "Calculus III & Linear Algebra",
            "Probability & Statistics",
            "Introduction to Machine Learning",
            "Artificial Intelligence",
            "Neural Networks & Deep Learning",
        ],
        "starter_projects": [
            "Spam Classifier with Naive Bayes (Scikit-learn)",
            "Handwritten Digit Recognizer (MNIST + CNN)",
            "Movie Recommendation System",
            "Simple Rule-Based Chatbot",
        ],
        "career_paths": [
            "AI Engineer",
            "Machine Learning Engineer",
            "Data Scientist",
            "AI Researcher",
        ],
    },
    {
        "id": "web-mobile",
        "name": "Web & Mobile Development",
        "summary": "Design and ship user-facing applications across the browser and the phone.",
        "interests": ["web development", "mobile development", "frontend", "backend", "full-stack", "UI/UX"],
        "strengths": ["programming", "design", "communication", "logic"],
        "ambitions": ["Full-Stack Developer", "Technical Architect", "Frontend Developer", "Mobile Developer"],
        "core_courses": [
            "Object-Oriented Programming",
            "Web Programming (HTML/CSS/JS)",
            "Database Systems",
            "Human-Computer Interaction",
            "Mobile Application Development",
            "Software Engineering",
        ],
        "starter_projects": [
            "Responsive Portfolio Website",
            "To-Do REST API with a Database",
            "Weather App with a Public API",
            "Full-Stack Note-Taking App",
        ],
        "career_paths": [
            "Full-Stack Developer",
            "Frontend Developer",
            "Backend Developer",
            "Mobile Developer",
            "Technical Architect",
        ],
    },
    {
        "id": "cybersecurity",
        "name": "Cybersecurity & Networking",
        "summary": "Protect systems, data and networks from threats through offensive and defensive practice.",
        "interests": ["cybersecurity", "security", "networking", "hacking", "network", "privacy"],
        "strengths": ["logic", "systems", "mathematics", "programming"],
        "ambitions": ["Security Engineer", "Network Engineer", "Penetration Tester", "SOC Analyst"],
        "core_courses": [
            "Computer Networks",
            "Operating Systems",
            "Introduction to Cryptography",
            "Network & Application Security",
            "Ethical Hacking",
            "Secure Software Development",
        ],
        "starter_projects": [
            "Password Strength Analyzer",
            "Caesar / Vigenere Cipher Tool",
            "Network Packet Analyzer (Python)",
            "Capture The Flag (CTF) Challenges",
        ],
        "career_paths": [
            "Security Engineer",
            "Penetration Tester",
            "SOC Analyst",
            "Network Engineer",
            "Security Architect",
        ],
    },
    {
        "id": "cloud-systems",
        "name": "Cloud & Systems Infrastructure",
        "summary": "Architect scalable, resilient infrastructure and automation that powers modern software.",
        "interests": ["cloud computing", "devops", "systems", "infrastructure", "serverless", "containers", "linux"],
        "strengths": ["systems", "logic", "mathematics", "programming"],
        "ambitions": ["DevOps Engineer", "Technical Architect", "Cloud Architect", "Site Reliability Engineer"],
        "core_courses": [
            "Computer Architecture",
            "Operating Systems",
            "Cloud Computing",
            "Distributed Systems",
            "Database Systems",
            "System & Network Administration",
        ],
        "starter_projects": [
            "Static Website Hosted on AWS S3",
            "Serverless To-Do API (Lambda + DynamoDB)",
            "Containerized App with Docker",
            "Simple CI/CD Pipeline",
        ],
        "career_paths": [
            "Cloud Architect",
            "DevOps Engineer",
            "Site Reliability Engineer",
            "Systems Administrator",
        ],
    },
    {
        "id": "data-engineering",
        "name": "Data Engineering & Analytics",
        "summary": "Collect, transform and visualize data to power decisions at scale.",
        "interests": ["data science", "analytics", "big data", "databases", "data engineering", "BI"],
        "strengths": ["mathematics", "statistics", "logic", "systems"],
        "ambitions": ["Data Scientist", "Data Engineer", "Data Analyst", "BI Developer"],
        "core_courses": [
            "Probability & Statistics",
            "Database Systems",
            "Data Mining",
            "Big Data Technologies",
            "Data Visualization",
            "Python for Data Analysis",
        ],
        "starter_projects": [
            "Sales Data Dashboard",
            "COVID-19 Data Analysis (Pandas)",
            "Web Scraper + ETL Pipeline",
            "CSV-to-SQLite Import Tool",
        ],
        "career_paths": [
            "Data Engineer",
            "Data Analyst",
            "BI Developer",
            "Data Scientist",
        ],
    },
    {
        "id": "gamedev-hci",
        "name": "Game Development & HCI",
        "summary": "Create interactive experiences and study how people use technology.",
        "interests": ["game development", "HCI", "design", "computer graphics", "virtual reality", "animation"],
        "strengths": ["design", "programming", "creativity", "logic"],
        "ambitions": ["Game Developer", "UI/UX Designer", "Creative Technologist", "Technical Architect"],
        "core_courses": [
            "Object-Oriented Programming",
            "Computer Graphics",
            "Introduction to Game Development",
            "Human-Computer Interaction",
            "Data Structures & Algorithms",
            "Software Engineering",
        ],
        "starter_projects": [
            "2D Platformer (Pygame)",
            "Tic-Tac-Toe with a Minimax AI",
            "Interactive Portfolio",
            "Audio Visualizer",
        ],
        "career_paths": [
            "Game Developer",
            "Gameplay Programmer",
            "UI/UX Designer",
            "HCI Researcher",
        ],
    },
]


def _tokens(value):
    return [str(value).strip().lower()]


def _matches(selection, keywords):
    selected = set(tok for item in selection for tok in _tokens(item))
    keywords = set(keywords)
    return selected & keywords


def score_tracks(interests, strengths, ambitions):
    interests = interests or []
    strengths = strengths or []
    ambitions = ambitions or []

    results = []
    for track in TRACKS:
        score = 0
        score += len(_matches(interests, track["interests"])) * 3
        score += len(_matches(strengths, track["strengths"])) * 2
        score += len(_matches(ambitions, track["ambitions"])) * 3
        results.append({
            "id": track["id"],
            "name": track["name"],
            "summary": track["summary"],
            "score": score,
            "core_courses": track["core_courses"],
            "starter_projects": track["starter_projects"],
            "career_paths": track["career_paths"],
        })

    results.sort(key=lambda t: t["score"], reverse=True)
    return results


def build_roadmap(interests, strengths, ambitions):
    ranked = score_tracks(interests, strengths, ambitions)
    top = ranked[0]
    alternatives = [t for t in ranked[1:4] if t["score"] > 0]
    no_match = ranked[0]["score"] == 0 and not interests and not strengths and not ambitions

    return {
        "primary_track": top["name"],
        "primary_summary": top["summary"],
        "top_tracks": ranked,
        "alternative_tracks": [
            {
                "name": t["name"],
                "summary": t["summary"],
                "core_courses": t["core_courses"],
                "starter_projects": t["starter_projects"],
                "career_paths": t["career_paths"],
            }
            for t in alternatives
        ],
        "core_courses": top["core_courses"],
        "starter_projects": top["starter_projects"],
        "career_paths": top["career_paths"],
        "recommended": not no_match,
    }


def build_prompt(interests, strengths, ambitions):
    return json.dumps(
        {
            "task": "recommend_cs_ct_track",
            "interests": interests,
            "strengths": strengths,
            "ambitions": ambitions,
        },
        indent=2,
    )
