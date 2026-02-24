"""
Career Hub - Career Guidance Platform for Hong Kong University Students
A Flask web application with web scraping for job search integration.
Enhanced with user authentication, expanded assessments, and dream job features.
"""

import json
import os
import re
import time
import uuid
from datetime import datetime, timedelta
from functools import wraps

from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = os.urandom(24)
app.permanent_session_lifetime = timedelta(days=7)

# ============================================================
# IN-MEMORY DATA STORES
# ============================================================

# User database: {email: {user_id, password_hash, profile, verified, ...}}
users_db = {}

# User likes tracking: {user_id: {post_id: timestamp, ...}}
user_likes = {}

# Company votes tracking: {company_id: {user_id: timestamp, ...}}
company_votes = {}

# Dream job post votes: {post_id: {user_id: timestamp, ...}}
dream_job_votes = {}

# User achievements/badges: {user_id: {badges: [], points: 0, offers_shared: 0, votes_cast: 0}}
user_achievements = {
    "demo_user1": {"badges": ["first_vote", "voter_10", "voter_50", "offer_shared", "top_contributor"], "points": 850, "votes_cast": 65, "offers_shared": 3, "name": "Alex Chen"},
    "demo_user2": {"badges": ["first_vote", "voter_10", "offer_shared", "verified_offer"], "points": 520, "votes_cast": 35, "offers_shared": 2, "name": "Sarah Lam"},
    "demo_user3": {"badges": ["first_vote", "voter_10", "voter_50", "top_contributor"], "points": 480, "votes_cast": 52, "offers_shared": 1, "name": "Michael Wong"},
    "demo_user4": {"badges": ["first_vote", "voter_10", "offer_shared"], "points": 320, "votes_cast": 28, "offers_shared": 2, "name": "Emily Ho"},
    "demo_user5": {"badges": ["first_vote", "voter_10"], "points": 180, "votes_cast": 15, "offers_shared": 0, "name": "David Ng"},
    "demo_user6": {"badges": ["first_vote", "offer_shared"], "points": 160, "votes_cast": 8, "offers_shared": 1, "name": "Jessica Liu"},
    "demo_user7": {"badges": ["first_vote", "voter_10"], "points": 140, "votes_cast": 12, "offers_shared": 0, "name": "Kevin Zhang"},
    "demo_user8": {"badges": ["first_vote"], "points": 95, "votes_cast": 6, "offers_shared": 0, "name": "Amy Tsui"},
    "demo_user9": {"badges": ["first_vote", "offer_shared"], "points": 120, "votes_cast": 5, "offers_shared": 1, "name": "Peter Leung"},
    "demo_user10": {"badges": ["first_vote"], "points": 75, "votes_cast": 4, "offers_shared": 0, "name": "Rachel Yip"},
}

# Offer showcase: [{id, user_id, company, position, salary, location, offer_date, anonymous, verified, created_at}, ...]
offer_showcase = [
    {
        "id": "offer1",
        "user_id": "system",
        "author_name": "CS Graduate 2025",
        "company": "Google",
        "company_id": "google",
        "position": "Software Engineer",
        "salary": "HK$50,000/month",
        "location": "Hong Kong",
        "offer_date": "2025-11-01",
        "anonymous": False,
        "verified": True,
        "university": "CUHK",
        "likes": 45,
        "created_at": "2025-11-05"
    },
    {
        "id": "offer2",
        "user_id": "system",
        "author_name": "Finance Major",
        "company": "Goldman Sachs",
        "company_id": "goldman",
        "position": "Investment Banking Analyst",
        "salary": "HK$45,000/month + Bonus",
        "location": "Central, HK",
        "offer_date": "2025-10-15",
        "anonymous": False,
        "verified": True,
        "university": "HKU",
        "likes": 67,
        "created_at": "2025-10-20"
    },
    {
        "id": "offer3",
        "user_id": "system",
        "author_name": "Anonymous",
        "company": "McKinsey",
        "company_id": "mckinsey",
        "position": "Business Analyst",
        "salary": "HK$42,000/month",
        "location": "Hong Kong",
        "offer_date": "2025-09-20",
        "anonymous": True,
        "verified": True,
        "university": "HKUST",
        "likes": 38,
        "created_at": "2025-09-25"
    },
    {
        "id": "offer4",
        "user_id": "system",
        "author_name": "Tech Enthusiast",
        "company": "Meta",
        "company_id": "meta",
        "position": "Product Manager",
        "salary": "HK$55,000/month",
        "location": "Singapore (Relocation)",
        "offer_date": "2025-12-01",
        "anonymous": False,
        "verified": True,
        "university": "HKU",
        "likes": 52,
        "created_at": "2025-12-05"
    },
    {
        "id": "offer5",
        "user_id": "system",
        "author_name": "Accounting Graduate",
        "company": "Deloitte",
        "company_id": "deloitte",
        "position": "Audit Associate",
        "salary": "HK$22,000/month",
        "location": "Hong Kong",
        "offer_date": "2025-08-15",
        "anonymous": False,
        "verified": True,
        "university": "PolyU",
        "likes": 28,
        "created_at": "2025-08-20"
    }
]

# Achievement badges configuration
ACHIEVEMENT_BADGES = {
    "first_vote": {"name": "First Vote", "icon": "star", "desc": "Cast your first vote", "points": 10},
    "voter_10": {"name": "Active Voter", "icon": "fire", "desc": "Cast 10 votes", "points": 50},
    "voter_50": {"name": "Super Voter", "icon": "trophy", "desc": "Cast 50 votes", "points": 200},
    "offer_shared": {"name": "Offer Sharer", "icon": "gift", "desc": "Share your first offer", "points": 100},
    "verified_offer": {"name": "Verified Winner", "icon": "check-circle", "desc": "Share a verified offer", "points": 150},
    "top_contributor": {"name": "Top Contributor", "icon": "award", "desc": "Reach 500 points", "points": 0},
}

# Custom tags history per user: {user_id: [tag1, tag2, ...]}
custom_tags_history = {}

# User favorites: {user_id: [post_id1, post_id2, ...]}
user_favorites = {}

# User notifications: {user_id: [{id, type, content, source_user, post_id, read, created_at}, ...]}
user_notifications = {}

# Private messages: {conversation_id: [{id, sender_id, receiver_id, content, read, created_at}, ...]}
private_messages = {}

# User settings: {user_id: {receive_messages: bool, ...}}
user_settings = {}

# Dream companies list with enhanced details
dream_companies = [
    {"id": "google", "name": "Google", "industry": "Technology", "votes": 156, "logo": "G", "description": "Global tech leader known for innovation and great culture", "offer_count": 12, "salary_range": "HK$45,000 - 70,000", "hiring_status": "active", "trending": True},
    {"id": "goldman", "name": "Goldman Sachs", "industry": "Finance", "votes": 134, "logo": "GS", "description": "Premier investment banking and securities firm", "offer_count": 8, "salary_range": "HK$40,000 - 65,000", "hiring_status": "active", "trending": True},
    {"id": "mckinsey", "name": "McKinsey & Company", "industry": "Consulting", "votes": 128, "logo": "M", "description": "World's most prestigious management consulting firm", "offer_count": 6, "salary_range": "HK$38,000 - 55,000", "hiring_status": "active", "trending": False},
    {"id": "meta", "name": "Meta", "industry": "Technology", "votes": 112, "logo": "M", "description": "Social media and metaverse technology leader", "offer_count": 9, "salary_range": "HK$48,000 - 72,000", "hiring_status": "active", "trending": True},
    {"id": "jpmorgan", "name": "J.P. Morgan", "industry": "Finance", "votes": 105, "logo": "JP", "description": "Leading global financial services firm", "offer_count": 7, "salary_range": "HK$38,000 - 60,000", "hiring_status": "active", "trending": False},
    {"id": "hsbc", "name": "HSBC", "industry": "Finance", "votes": 98, "logo": "H", "description": "Hong Kong's premier banking institution", "offer_count": 15, "salary_range": "HK$25,000 - 50,000", "hiring_status": "active", "trending": False},
    {"id": "tencent", "name": "Tencent", "industry": "Technology", "votes": 95, "logo": "T", "description": "China's largest tech conglomerate", "offer_count": 11, "salary_range": "HK$35,000 - 65,000", "hiring_status": "active", "trending": True},
    {"id": "bcg", "name": "BCG", "industry": "Consulting", "votes": 89, "logo": "B", "description": "Top-tier strategy consulting firm", "offer_count": 5, "salary_range": "HK$36,000 - 52,000", "hiring_status": "limited", "trending": False},
    {"id": "apple", "name": "Apple", "industry": "Technology", "votes": 87, "logo": "A", "description": "World's most valuable tech company", "offer_count": 4, "salary_range": "HK$42,000 - 68,000", "hiring_status": "limited", "trending": False},
    {"id": "deloitte", "name": "Deloitte", "industry": "Professional Services", "votes": 82, "logo": "D", "description": "Big 4 firm with diverse service offerings", "offer_count": 20, "salary_range": "HK$20,000 - 45,000", "hiring_status": "active", "trending": False},
]

# Prohibited words for content moderation
PROHIBITED_WORDS = ["广告", "微信", "加我", "买卖", "代写", "代考", "赚钱", "兼职刷单", "招代理"]

# ============================================================
# TAG SYSTEM CATEGORIES
# ============================================================

TAG_CATEGORIES = {
    "interview": {
        "label": "Interview",
        "color": "#8b5cf6",
        "subcategories": ["skills", "questions", "lightning_protection", "group_experience"]
    },
    "resume": {
        "label": "Resume",
        "color": "#f59e0b",
        "subcategories": ["writing", "modification", "template", "lightning_protection"]
    },
    "internal_promotion": {
        "label": "Internal Promotion",
        "color": "#10b981",
        "subcategories": ["channels", "processes", "skills", "enterprise_info"]
    },
    "internship": {
        "label": "Internship",
        "color": "#0ea5e9",
        "subcategories": ["application", "experience", "tips"]
    },
    "career_advice": {
        "label": "Career Advice",
        "color": "#22c55e",
        "subcategories": ["planning", "switching", "growth"]
    },
    "dream_job": {
        "label": "Dream Job",
        "color": "#ec4899",
        "subcategories": ["goals", "inspiration", "journey"]
    }
}

# ============================================================
# CAREER DATA (EXPANDED with new categories)
# ============================================================

CAREER_DATA = {
    "finance_business": {
        "label": "Finance & Business",
        "icon": "💰",
        "roles": [
            {
                "title": "Investment Banking Analyst",
                "skills": ["Financial Modeling", "Valuation", "Excel/VBA", "Accounting", "Corporate Finance"],
                "career_path": ["Analyst (2-3 yrs)", "Associate (3 yrs)", "VP (3-4 yrs)", "Director", "Managing Director"],
                "avg_salary_hkd": "30,000 - 50,000/month (entry)",
                "companies": [
                    {"name": "Goldman Sachs", "url": "https://www.goldmansachs.com/careers/"},
                    {"name": "J.P. Morgan", "url": "https://careers.jpmorgan.com/"},
                    {"name": "Morgan Stanley", "url": "https://www.morganstanley.com/careers"},
                    {"name": "HSBC", "url": "https://www.hsbc.com/careers"},
                    {"name": "UBS", "url": "https://www.ubs.com/global/en/careers.html"}
                ],
                "job_board_url": "https://hk.indeed.com/jobs?q=investment+banking+analyst",
                "description": "Assist in M&A deals, IPOs, and capital raising. Requires strong analytical and financial modeling skills."
            },
            {
                "title": "Management Consultant",
                "skills": ["Problem Solving", "Data Analysis", "Presentation", "Business Strategy", "Communication"],
                "career_path": ["Analyst (2 yrs)", "Consultant (2 yrs)", "Manager (3 yrs)", "Principal", "Partner"],
                "avg_salary_hkd": "25,000 - 45,000/month (entry)",
                "companies": [
                    {"name": "McKinsey", "url": "https://www.mckinsey.com/careers"},
                    {"name": "BCG", "url": "https://careers.bcg.com/"},
                    {"name": "Bain", "url": "https://www.bain.com/careers/"},
                    {"name": "Deloitte", "url": "https://www2.deloitte.com/cn/en/careers.html"},
                    {"name": "PwC", "url": "https://www.pwc.com/gx/en/careers.html"}
                ],
                "job_board_url": "https://hk.indeed.com/jobs?q=management+consultant",
                "description": "Help organizations solve complex business problems and improve performance."
            },
            {
                "title": "Accountant / Auditor",
                "skills": ["HKFRS/IFRS", "Auditing", "Taxation", "Excel", "Analytical Skills"],
                "career_path": ["Associate (2-3 yrs)", "Senior Associate (2 yrs)", "Manager (3 yrs)", "Senior Manager", "Partner"],
                "avg_salary_hkd": "18,000 - 28,000/month (entry)",
                "companies": [
                    {"name": "Deloitte", "url": "https://www2.deloitte.com/cn/en/careers.html"},
                    {"name": "PwC", "url": "https://www.pwc.com/gx/en/careers.html"},
                    {"name": "EY", "url": "https://www.ey.com/en_gl/careers"},
                    {"name": "KPMG", "url": "https://home.kpmg/xx/en/home/careers.html"},
                    {"name": "BDO", "url": "https://www.bdo.global/en-gb/careers"}
                ],
                "job_board_url": "https://hk.indeed.com/jobs?q=auditor+accountant",
                "description": "Prepare and examine financial records, ensure compliance with regulations."
            },
            {
                "title": "Financial Analyst",
                "skills": ["Financial Analysis", "Data Modeling", "Bloomberg Terminal", "SQL", "Excel"],
                "career_path": ["Junior Analyst", "Financial Analyst", "Senior Analyst", "Finance Manager", "CFO"],
                "avg_salary_hkd": "20,000 - 35,000/month (entry)",
                "companies": [
                    {"name": "HSBC", "url": "https://www.hsbc.com/careers"},
                    {"name": "Standard Chartered", "url": "https://www.sc.com/en/careers/"},
                    {"name": "Bank of China", "url": "https://www.boc.cn/en/aboutboc/ab6/"},
                    {"name": "Hang Seng Bank", "url": "https://www.hangseng.com/en-hk/careers/"},
                    {"name": "AIA", "url": "https://www.aia.com/en/careers"}
                ],
                "job_board_url": "https://hk.indeed.com/jobs?q=financial+analyst",
                "description": "Analyze financial data to guide business decisions and investment strategies."
            },
            {
                "title": "Risk Analyst",
                "skills": ["Risk Management", "Statistics", "Python/R", "Regulatory Knowledge", "Financial Modeling"],
                "career_path": ["Analyst", "Senior Analyst", "Risk Manager", "Head of Risk", "CRO"],
                "avg_salary_hkd": "22,000 - 38,000/month (entry)",
                "companies": [
                    {"name": "HKMA", "url": "https://www.hkma.gov.hk/eng/about-the-hkma/career-opportunities/"},
                    {"name": "SFC", "url": "https://www.sfc.hk/en/Careers"},
                    {"name": "HSBC", "url": "https://www.hsbc.com/careers"},
                    {"name": "Standard Chartered", "url": "https://www.sc.com/en/careers/"},
                    {"name": "Manulife", "url": "https://www.manulife.com/en/careers.html"}
                ],
                "job_board_url": "https://hk.indeed.com/jobs?q=risk+analyst",
                "description": "Identify and assess risks to help organizations minimize potential losses."
            }
        ]
    },
    "it_engineering": {
        "label": "IT / CS-Engineering",
        "icon": "💻",
        "roles": [
            {
                "title": "Software Engineer",
                "skills": ["Data Structures & Algorithms", "Python/Java/C++", "System Design", "Git", "APIs"],
                "career_path": ["Junior Engineer", "Software Engineer", "Senior Engineer", "Staff Engineer", "Principal Engineer"],
                "avg_salary_hkd": "25,000 - 45,000/month (entry)",
                "companies": [
                    {"name": "Google", "url": "https://careers.google.com/"},
                    {"name": "Meta", "url": "https://www.metacareers.com/"},
                    {"name": "Amazon", "url": "https://www.amazon.jobs/"},
                    {"name": "Tencent", "url": "https://careers.tencent.com/"},
                    {"name": "ByteDance", "url": "https://jobs.bytedance.com/"}
                ],
                "job_board_url": "https://hk.indeed.com/jobs?q=software+engineer",
                "description": "Design, develop, and maintain software applications and systems."
            },
            {
                "title": "Data Scientist",
                "skills": ["Python/R", "Machine Learning", "Statistics", "SQL", "Data Visualization"],
                "career_path": ["Junior Data Scientist", "Data Scientist", "Senior Data Scientist", "Lead DS", "Head of Data"],
                "avg_salary_hkd": "25,000 - 40,000/month (entry)",
                "companies": [
                    {"name": "Alibaba", "url": "https://careers.alibabagroup.com/"},
                    {"name": "Tencent", "url": "https://careers.tencent.com/"},
                    {"name": "HSBC", "url": "https://www.hsbc.com/careers"},
                    {"name": "AXA", "url": "https://www.axa.com/en/careers"},
                    {"name": "Lalamove", "url": "https://www.lalamove.com/careers"}
                ],
                "job_board_url": "https://hk.indeed.com/jobs?q=data+scientist",
                "description": "Extract insights from data using statistical methods and machine learning."
            },
            {
                "title": "Cybersecurity Analyst",
                "skills": ["Network Security", "Penetration Testing", "SIEM", "Risk Assessment", "Incident Response"],
                "career_path": ["Junior Analyst", "Security Analyst", "Senior Analyst", "Security Architect", "CISO"],
                "avg_salary_hkd": "22,000 - 38,000/month (entry)",
                "companies": [
                    {"name": "CyberPort", "url": "https://www.cyberport.hk/en/careers"},
                    {"name": "HKMA", "url": "https://www.hkma.gov.hk/eng/about-the-hkma/career-opportunities/"},
                    {"name": "Deloitte", "url": "https://www2.deloitte.com/cn/en/careers.html"},
                    {"name": "PwC", "url": "https://www.pwc.com/gx/en/careers.html"},
                    {"name": "HSBC", "url": "https://www.hsbc.com/careers"}
                ],
                "job_board_url": "https://hk.indeed.com/jobs?q=cybersecurity+analyst",
                "description": "Protect organizations from cyber threats and ensure data security."
            },
            {
                "title": "Product Manager",
                "skills": ["User Research", "Agile/Scrum", "Data Analysis", "Wireframing", "Communication"],
                "career_path": ["APM", "Product Manager", "Senior PM", "Director of Product", "VP of Product"],
                "avg_salary_hkd": "25,000 - 42,000/month (entry)",
                "companies": [
                    {"name": "Google", "url": "https://careers.google.com/"},
                    {"name": "Meta", "url": "https://www.metacareers.com/"},
                    {"name": "Shopee", "url": "https://careers.shopee.sg/"},
                    {"name": "Klook", "url": "https://www.klook.com/careers/"},
                    {"name": "WeLab", "url": "https://www.welab.co/careers"}
                ],
                "job_board_url": "https://hk.indeed.com/jobs?q=product+manager",
                "description": "Define product strategy and work with engineering teams to build products users love."
            },
            {
                "title": "DevOps / Cloud Engineer",
                "skills": ["AWS/Azure/GCP", "Docker/Kubernetes", "CI/CD", "Linux", "Terraform"],
                "career_path": ["Junior Engineer", "DevOps Engineer", "Senior Engineer", "Lead Engineer", "Head of Infrastructure"],
                "avg_salary_hkd": "25,000 - 42,000/month (entry)",
                "companies": [
                    {"name": "AWS", "url": "https://www.amazon.jobs/en/teams/aws"},
                    {"name": "Microsoft", "url": "https://careers.microsoft.com/"},
                    {"name": "Google Cloud", "url": "https://careers.google.com/"},
                    {"name": "Alibaba Cloud", "url": "https://careers.alibabagroup.com/"},
                    {"name": "HSBC", "url": "https://www.hsbc.com/careers"}
                ],
                "job_board_url": "https://hk.indeed.com/jobs?q=devops+engineer",
                "description": "Automate and optimize cloud infrastructure and deployment pipelines."
            }
        ]
    },
    "arts": {
        "label": "Faculty of Arts",
        "icon": "🎨",
        "roles": [
            {
                "title": "Marketing Executive",
                "skills": ["Digital Marketing", "Content Creation", "Social Media", "Analytics", "Copywriting"],
                "career_path": ["Executive", "Senior Executive", "Marketing Manager", "Head of Marketing", "CMO"],
                "avg_salary_hkd": "16,000 - 25,000/month (entry)",
                "companies": [
                    {"name": "L'Oreal", "url": "https://careers.loreal.com/"},
                    {"name": "P&G", "url": "https://www.pgcareers.com/"},
                    {"name": "Ogilvy", "url": "https://www.ogilvy.com/careers"},
                    {"name": "Leo Burnett", "url": "https://www.leoburnett.com/careers"},
                    {"name": "SCMP", "url": "https://www.scmp.com/career"}
                ],
                "job_board_url": "https://hk.indeed.com/jobs?q=marketing+executive",
                "description": "Plan and execute marketing campaigns to promote products and services."
            },
            {
                "title": "Journalist / Editor",
                "skills": ["Writing", "Research", "Interviewing", "Content Management", "Media Law"],
                "career_path": ["Junior Reporter", "Reporter", "Senior Reporter", "Editor", "Chief Editor"],
                "avg_salary_hkd": "15,000 - 22,000/month (entry)",
                "companies": [
                    {"name": "SCMP", "url": "https://www.scmp.com/career"},
                    {"name": "RTHK", "url": "https://www.rthk.hk/about/career"},
                    {"name": "Bloomberg", "url": "https://careers.bloomberg.com/"},
                    {"name": "Reuters", "url": "https://www.thomsonreuters.com/en/careers.html"},
                    {"name": "TVB", "url": "https://corporate.tvb.com/careers"}
                ],
                "job_board_url": "https://hk.indeed.com/jobs?q=journalist+editor",
                "description": "Research, write, and edit news stories and articles for media outlets."
            },
            {
                "title": "Public Relations Specialist",
                "skills": ["Communication", "Media Relations", "Event Planning", "Crisis Management", "Writing"],
                "career_path": ["PR Assistant", "PR Executive", "PR Manager", "PR Director", "VP Communications"],
                "avg_salary_hkd": "16,000 - 24,000/month (entry)",
                "companies": [
                    {"name": "Edelman", "url": "https://www.edelman.com/careers"},
                    {"name": "Weber Shandwick", "url": "https://www.webershandwick.com/careers/"},
                    {"name": "FleishmanHillard", "url": "https://fleishmanhillard.com/careers/"},
                    {"name": "Burson", "url": "https://www.bursonglobal.com/careers"},
                    {"name": "MSL", "url": "https://msl.com/careers/"}
                ],
                "job_board_url": "https://hk.indeed.com/jobs?q=public+relations",
                "description": "Manage public image and communications for organizations."
            },
            {
                "title": "UX/UI Designer",
                "skills": ["Figma/Sketch", "User Research", "Prototyping", "Visual Design", "Interaction Design"],
                "career_path": ["Junior Designer", "UX Designer", "Senior Designer", "Lead Designer", "Design Director"],
                "avg_salary_hkd": "18,000 - 30,000/month (entry)",
                "companies": [
                    {"name": "Google", "url": "https://careers.google.com/"},
                    {"name": "Apple", "url": "https://www.apple.com/careers/"},
                    {"name": "Klook", "url": "https://www.klook.com/careers/"},
                    {"name": "HSBC", "url": "https://www.hsbc.com/careers"},
                    {"name": "Lalamove", "url": "https://www.lalamove.com/careers"}
                ],
                "job_board_url": "https://hk.indeed.com/jobs?q=ux+ui+designer",
                "description": "Design intuitive and beautiful user interfaces and experiences."
            },
            {
                "title": "Human Resources Specialist",
                "skills": ["Recruitment", "Employee Relations", "HRIS", "Employment Law", "Communication"],
                "career_path": ["HR Assistant", "HR Officer", "HR Manager", "HR Director", "CHRO"],
                "avg_salary_hkd": "16,000 - 24,000/month (entry)",
                "companies": [
                    {"name": "Adecco", "url": "https://www.adeccogroup.com/careers/"},
                    {"name": "Randstad", "url": "https://www.randstad.com/careers/"},
                    {"name": "Michael Page", "url": "https://www.michaelpage.com/careers"},
                    {"name": "HSBC", "url": "https://www.hsbc.com/careers"},
                    {"name": "Cathay Pacific", "url": "https://careers.cathaypacific.com/"}
                ],
                "job_board_url": "https://hk.indeed.com/jobs?q=human+resources",
                "description": "Manage recruitment, employee relations, and organizational development."
            }
        ]
    },
    "academic": {
        "label": "Professors & Academic",
        "icon": "🎓",
        "roles": [
            {
                "title": "Assistant Professor",
                "skills": ["Research", "Teaching", "Academic Writing", "Grant Applications", "Mentoring"],
                "career_path": ["Postdoc", "Assistant Professor", "Associate Professor", "Full Professor", "Chair Professor"],
                "avg_salary_hkd": "60,000 - 90,000/month",
                "companies": [
                    {"name": "HKU", "url": "https://jobs.hku.hk/"},
                    {"name": "CUHK", "url": "https://www.cuhk.edu.hk/english/career/"},
                    {"name": "HKUST", "url": "https://career.hkust.edu.hk/"},
                    {"name": "PolyU", "url": "https://www.polyu.edu.hk/hro/job_opportunities/"},
                    {"name": "CityU", "url": "https://www.cityu.edu.hk/hro/en/job/"}
                ],
                "job_board_url": "https://www.timeshighereducation.com/unijobs/",
                "description": "Conduct research, teach courses, and supervise graduate students at universities."
            },
            {
                "title": "Research Scientist",
                "skills": ["Research Methodology", "Data Analysis", "Academic Writing", "Lab Management", "Collaboration"],
                "career_path": ["Research Assistant", "Postdoc", "Research Scientist", "Senior Scientist", "Principal Investigator"],
                "avg_salary_hkd": "35,000 - 60,000/month",
                "companies": [
                    {"name": "HKUST", "url": "https://career.hkust.edu.hk/"},
                    {"name": "HKU", "url": "https://jobs.hku.hk/"},
                    {"name": "HKSTP", "url": "https://www.hkstp.org/careers/"},
                    {"name": "CityU", "url": "https://www.cityu.edu.hk/hro/en/job/"},
                    {"name": "Research Institutes", "url": "https://www.ugc.edu.hk/eng/ugc/"}
                ],
                "job_board_url": "https://www.nature.com/naturecareers",
                "description": "Design and conduct research projects to advance scientific knowledge."
            },
            {
                "title": "Postdoctoral Researcher",
                "skills": ["Independent Research", "Publication", "Grant Writing", "Teaching", "Mentoring"],
                "career_path": ["PhD", "Postdoc (2-4 yrs)", "Assistant Professor", "Research Scientist"],
                "avg_salary_hkd": "28,000 - 45,000/month",
                "companies": [
                    {"name": "HKU", "url": "https://jobs.hku.hk/"},
                    {"name": "CUHK", "url": "https://www.cuhk.edu.hk/english/career/"},
                    {"name": "HKUST", "url": "https://career.hkust.edu.hk/"},
                    {"name": "CityU", "url": "https://www.cityu.edu.hk/hro/en/job/"},
                    {"name": "PolyU", "url": "https://www.polyu.edu.hk/hro/job_opportunities/"}
                ],
                "job_board_url": "https://academicpositions.com/",
                "description": "Conduct post-PhD research to build expertise and prepare for faculty positions."
            },
            {
                "title": "Lecturer / Teaching Fellow",
                "skills": ["Teaching", "Curriculum Design", "Student Assessment", "Communication", "Subject Expertise"],
                "career_path": ["Tutor", "Teaching Fellow", "Lecturer", "Senior Lecturer", "Principal Lecturer"],
                "avg_salary_hkd": "35,000 - 55,000/month",
                "companies": [
                    {"name": "HKU SPACE", "url": "https://hkuspace.hku.hk/about-us/career"},
                    {"name": "CUHK", "url": "https://www.cuhk.edu.hk/english/career/"},
                    {"name": "PolyU", "url": "https://www.polyu.edu.hk/hro/job_opportunities/"},
                    {"name": "CityU", "url": "https://www.cityu.edu.hk/hro/en/job/"},
                    {"name": "HKBU", "url": "https://pers.hkbu.edu.hk/job_vacancies/"}
                ],
                "job_board_url": "https://hk.indeed.com/jobs?q=lecturer",
                "description": "Focus on teaching excellence and course development at universities."
            }
        ]
    },
    "entrepreneurship": {
        "label": "Entrepreneurship & Startup",
        "icon": "🚀",
        "roles": [
            {
                "title": "Startup Founder / Co-founder",
                "skills": ["Business Planning", "Fundraising", "Product Development", "Leadership", "Sales"],
                "career_path": ["Employee", "Side Project", "Seed Stage", "Series A", "Scale-up", "Exit/IPO"],
                "avg_salary_hkd": "Varies (equity-based)",
                "companies": [
                    {"name": "Cyberport", "url": "https://www.cyberport.hk/en/incubation"},
                    {"name": "HKSTP", "url": "https://www.hkstp.org/"},
                    {"name": "Alibaba Entrepreneurs Fund", "url": "https://www.ent-fund.org/"},
                    {"name": "Y Combinator", "url": "https://www.ycombinator.com/"},
                    {"name": "500 Global", "url": "https://500.co/"}
                ],
                "job_board_url": "https://www.startbase.hk/jobs",
                "description": "Build and lead a new venture from idea to market."
            },
            {
                "title": "Startup Team Member",
                "skills": ["Adaptability", "Full-stack Skills", "Problem Solving", "Communication", "Resilience"],
                "career_path": ["Early Employee", "Team Lead", "Department Head", "VP", "Co-founder of next venture"],
                "avg_salary_hkd": "20,000 - 40,000/month + equity",
                "companies": [
                    {"name": "Startup Jobs HK", "url": "https://www.startbase.hk/jobs"},
                    {"name": "AngelList", "url": "https://angel.co/"},
                    {"name": "Cyberport Startups", "url": "https://www.cyberport.hk/en/incubation"},
                    {"name": "HKSTP Startups", "url": "https://www.hkstp.org/"},
                    {"name": "WHub", "url": "https://www.whub.io/jobs"}
                ],
                "job_board_url": "https://angel.co/location/hong-kong",
                "description": "Join an early-stage company and wear multiple hats to build something new."
            },
            {
                "title": "Venture Builder",
                "skills": ["Business Development", "Market Research", "Financial Modeling", "Networking", "Operations"],
                "career_path": ["Analyst", "Associate", "Principal", "Partner", "Founder"],
                "avg_salary_hkd": "30,000 - 60,000/month",
                "companies": [
                    {"name": "Brinc", "url": "https://www.brinc.io/careers/"},
                    {"name": "Zeroth.AI", "url": "https://www.zeroth.ai/"},
                    {"name": "Betatron", "url": "https://www.betatron.co/"},
                    {"name": "Nest.vc", "url": "https://nest.vc/"},
                    {"name": "Mind Fund", "url": "https://mindfund.hk/"}
                ],
                "job_board_url": "https://hk.indeed.com/jobs?q=venture+builder",
                "description": "Help create and launch new startups within an accelerator or studio."
            }
        ]
    },
    "freelance": {
        "label": "Freelance & Independent",
        "icon": "🎯",
        "roles": [
            {
                "title": "Freelance Developer",
                "skills": ["Web Development", "Mobile Development", "Client Management", "Project Management", "Marketing"],
                "career_path": ["Part-time gigs", "Freelance", "Agency", "Consultancy", "Tech Founder"],
                "avg_salary_hkd": "$300-800/hour",
                "companies": [
                    {"name": "Upwork", "url": "https://www.upwork.com/"},
                    {"name": "Toptal", "url": "https://www.toptal.com/"},
                    {"name": "Fiverr", "url": "https://www.fiverr.com/"},
                    {"name": "Freelancer", "url": "https://www.freelancer.com/"},
                    {"name": "99designs", "url": "https://99designs.hk/"}
                ],
                "job_board_url": "https://www.upwork.com/freelance-jobs/web-development/",
                "description": "Provide software development services as an independent contractor."
            },
            {
                "title": "Freelance Designer",
                "skills": ["Graphic Design", "UI/UX", "Brand Identity", "Portfolio Building", "Client Relations"],
                "career_path": ["Part-time", "Freelance", "Studio", "Agency Founder", "Creative Director"],
                "avg_salary_hkd": "$250-600/hour",
                "companies": [
                    {"name": "Dribbble", "url": "https://dribbble.com/jobs"},
                    {"name": "Behance", "url": "https://www.behance.net/joblist"},
                    {"name": "99designs", "url": "https://99designs.hk/"},
                    {"name": "Upwork", "url": "https://www.upwork.com/"},
                    {"name": "Fiverr", "url": "https://www.fiverr.com/"}
                ],
                "job_board_url": "https://dribbble.com/jobs",
                "description": "Offer design services to clients on a project basis."
            },
            {
                "title": "Content Creator / Influencer",
                "skills": ["Content Strategy", "Video Production", "Social Media", "Personal Branding", "Monetization"],
                "career_path": ["Hobbyist", "Part-time Creator", "Full-time Creator", "Brand Owner", "Media Company"],
                "avg_salary_hkd": "Varies widely",
                "companies": [
                    {"name": "YouTube", "url": "https://www.youtube.com/creators/"},
                    {"name": "Instagram", "url": "https://business.instagram.com/"},
                    {"name": "TikTok", "url": "https://www.tiktok.com/creators/"},
                    {"name": "Patreon", "url": "https://www.patreon.com/"},
                    {"name": "Substack", "url": "https://substack.com/"}
                ],
                "job_board_url": "https://www.influencer.com/",
                "description": "Build an audience and create content across digital platforms."
            },
            {
                "title": "Independent Consultant",
                "skills": ["Domain Expertise", "Client Management", "Business Development", "Presentation", "Problem Solving"],
                "career_path": ["Industry Expert", "Part-time Consulting", "Full-time Independent", "Boutique Firm"],
                "avg_salary_hkd": "$500-2000/hour",
                "companies": [
                    {"name": "LinkedIn ProFinder", "url": "https://www.linkedin.com/profinder/"},
                    {"name": "Catalant", "url": "https://gocatalant.com/"},
                    {"name": "Expert360", "url": "https://expert360.com/"},
                    {"name": "Upwork", "url": "https://www.upwork.com/"},
                    {"name": "Clarity.fm", "url": "https://clarity.fm/"}
                ],
                "job_board_url": "https://www.linkedin.com/profinder/",
                "description": "Provide expert advice to organizations on a contract basis."
            }
        ]
    },
    "government": {
        "label": "Government & Public Sector",
        "icon": "🏛️",
        "roles": [
            {
                "title": "Administrative Officer (AO)",
                "skills": ["Policy Analysis", "Communication", "Leadership", "Critical Thinking", "Public Administration"],
                "career_path": ["AO (Entry)", "Senior AO", "Principal AO", "Deputy Secretary", "Permanent Secretary"],
                "avg_salary_hkd": "35,000 - 55,000/month (entry)",
                "companies": [
                    {"name": "Civil Service Bureau", "url": "https://www.csb.gov.hk/"},
                    {"name": "HK Government", "url": "https://www.gov.hk/en/about/job/"},
                    {"name": "Various Policy Bureaux", "url": "https://www.gov.hk/en/about/govdirectory/"},
                    {"name": "District Offices", "url": "https://www.had.gov.hk/"},
                    {"name": "ICAC", "url": "https://www.icac.org.hk/en/careers/"}
                ],
                "job_board_url": "https://www.csb.gov.hk/english/recruit/",
                "description": "Formulate and implement government policies across various bureaux."
            },
            {
                "title": "Executive Officer (EO)",
                "skills": ["Administration", "Resource Management", "Communication", "Problem Solving", "IT Skills"],
                "career_path": ["EO II", "EO I", "Senior EO", "Chief EO", "Assistant Director"],
                "avg_salary_hkd": "28,000 - 40,000/month (entry)",
                "companies": [
                    {"name": "Civil Service Bureau", "url": "https://www.csb.gov.hk/"},
                    {"name": "Immigration Department", "url": "https://www.immd.gov.hk/eng/careers/"},
                    {"name": "Inland Revenue", "url": "https://www.ird.gov.hk/eng/career/"},
                    {"name": "Various Departments", "url": "https://www.gov.hk/en/about/job/"},
                    {"name": "Hospital Authority", "url": "https://www3.ha.org.hk/career/"}
                ],
                "job_board_url": "https://www.csb.gov.hk/english/recruit/",
                "description": "Handle administrative and managerial duties in government departments."
            },
            {
                "title": "Police Inspector",
                "skills": ["Leadership", "Physical Fitness", "Decision Making", "Communication", "Crisis Management"],
                "career_path": ["Inspector", "Senior Inspector", "Chief Inspector", "Superintendent", "Commissioner"],
                "avg_salary_hkd": "42,000 - 55,000/month (entry)",
                "companies": [
                    {"name": "Hong Kong Police Force", "url": "https://www.police.gov.hk/ppp_en/15_recruit/"},
                    {"name": "HKPF", "url": "https://www.police.gov.hk/"},
                    {"name": "Disciplined Services", "url": "https://www.csb.gov.hk/english/recruit/"},
                    {"name": "Security Bureau", "url": "https://www.sb.gov.hk/"},
                    {"name": "Immigration", "url": "https://www.immd.gov.hk/eng/careers/"}
                ],
                "job_board_url": "https://www.police.gov.hk/ppp_en/15_recruit/",
                "description": "Maintain law and order and ensure public safety in Hong Kong."
            },
            {
                "title": "Government Teacher",
                "skills": ["Teaching", "Curriculum Development", "Classroom Management", "Communication", "Subject Expertise"],
                "career_path": ["CM/AM", "GM", "SGM", "Principal GM", "Principal"],
                "avg_salary_hkd": "32,000 - 45,000/month (entry)",
                "companies": [
                    {"name": "Education Bureau", "url": "https://www.edb.gov.hk/en/teacher/"},
                    {"name": "Government Schools", "url": "https://www.edb.gov.hk/"},
                    {"name": "DSS Schools", "url": "https://www.edb.gov.hk/en/edu-system/primary-secondary/applicable-to-primary-secondary/direct-subsidy-scheme/"},
                    {"name": "Aided Schools", "url": "https://www.edb.gov.hk/"},
                    {"name": "International Schools", "url": "https://www.edb.gov.hk/"}
                ],
                "job_board_url": "https://www.edb.gov.hk/en/teacher/",
                "description": "Educate students in government or aided schools."
            }
        ]
    },
    "college_teacher": {
        "label": "College Teaching",
        "icon": "📚",
        "roles": [
            {
                "title": "Community College Instructor",
                "skills": ["Teaching", "Course Design", "Student Support", "Subject Knowledge", "Assessment"],
                "career_path": ["Part-time Tutor", "Instructor", "Senior Instructor", "Programme Leader", "Principal"],
                "avg_salary_hkd": "25,000 - 40,000/month",
                "companies": [
                    {"name": "HKU SPACE CC", "url": "https://hkuspace.hku.hk/about-us/career"},
                    {"name": "CUHK-affiliated colleges", "url": "https://www.cuhk.edu.hk/english/career/"},
                    {"name": "HKBU-affiliated colleges", "url": "https://pers.hkbu.edu.hk/job_vacancies/"},
                    {"name": "PolyU HKCC", "url": "https://www.polyu.edu.hk/hro/job_opportunities/"},
                    {"name": "VTC", "url": "https://www.vtc.edu.hk/html/en/career/"}
                ],
                "job_board_url": "https://hk.indeed.com/jobs?q=community+college+instructor",
                "description": "Teach associate degree or higher diploma programmes."
            },
            {
                "title": "Language Instructor",
                "skills": ["Language Proficiency", "Teaching Methodology", "Cultural Knowledge", "Patience", "Communication"],
                "career_path": ["Part-time Teacher", "Full-time Instructor", "Senior Instructor", "Course Coordinator", "Centre Head"],
                "avg_salary_hkd": "20,000 - 35,000/month",
                "companies": [
                    {"name": "British Council", "url": "https://www.britishcouncil.hk/en/about/careers"},
                    {"name": "Wall Street English", "url": "https://www.wallstreetenglish.com/careers"},
                    {"name": "HKU SPACE", "url": "https://hkuspace.hku.hk/about-us/career"},
                    {"name": "Alliance Française", "url": "https://www.afhongkong.org/en/work-with-us/"},
                    {"name": "Goethe-Institut", "url": "https://www.goethe.de/ins/cn/en/sta/hon/ueb/kar.html"}
                ],
                "job_board_url": "https://hk.indeed.com/jobs?q=language+instructor",
                "description": "Teach languages in schools, language centres, or corporate settings."
            },
            {
                "title": "Vocational Trainer",
                "skills": ["Industry Experience", "Training Design", "Practical Skills", "Assessment", "Mentoring"],
                "career_path": ["Part-time Trainer", "Trainer", "Senior Trainer", "Programme Manager", "Director"],
                "avg_salary_hkd": "22,000 - 38,000/month",
                "companies": [
                    {"name": "VTC", "url": "https://www.vtc.edu.hk/html/en/career/"},
                    {"name": "HKPC", "url": "https://www.hkpc.org/en/career"},
                    {"name": "ERB", "url": "https://www.erb.org/"},
                    {"name": "Construction Industry Council", "url": "https://www.cic.hk/eng/main/career/"},
                    {"name": "HKQF", "url": "https://www.hkqf.gov.hk/"}
                ],
                "job_board_url": "https://hk.indeed.com/jobs?q=vocational+trainer",
                "description": "Provide practical training in trades and technical fields."
            }
        ]
    }
}

# ============================================================
# ASSESSMENT CONFIGURATION (EXPANDED)
# ============================================================

ASSESSMENT_WEIGHTS = {
    "gpa": {"label": "GPA / Grade Points", "weight": 0.15, "max_score": 10},
    "internships": {"label": "Internships", "weight": 0.15, "max_score": 10},
    "certifications": {"label": "Certifications", "weight": 0.10, "max_score": 10},
    "competitions": {"label": "Competitions", "weight": 0.10, "max_score": 10},
    "projects": {"label": "Projects", "weight": 0.10, "max_score": 10},
}

EXPANDED_ASSESSMENT = {
    "career_cognition": {
        "label": "Career Cognition",
        "weight": 0.10,
        "dimensions": [
            {"id": "positioning", "label": "Career Positioning", "desc": "How clear is your career goal?"},
            {"id": "industry", "label": "Industry Understanding", "desc": "How well do you understand your target industry?"},
            {"id": "path", "label": "Career Development Path", "desc": "Can you articulate your 3-5 year career plan?"}
        ]
    },
    "abilities": {
        "label": "Ability Assessment",
        "weight": 0.15,
        "dimensions": [
            {"id": "professional", "label": "Professional Skills", "desc": "Technical/domain-specific skills"},
            {"id": "communication", "label": "Communication", "desc": "Written and verbal communication"},
            {"id": "learning", "label": "Learning Ability", "desc": "Ability to learn new skills quickly"},
            {"id": "execution", "label": "Executive Ability", "desc": "Ability to execute and deliver results"},
            {"id": "stress", "label": "Stress Resistance", "desc": "Ability to work under pressure"}
        ]
    },
    "interests": {
        "label": "Interests & Preferences",
        "weight": 0.05,
        "work_types": ["Analytical", "Creative", "Management", "Technical", "Social/People-oriented"],
        "industries": ["Finance", "Technology", "Media", "Healthcare", "Education", "Government", "Startups"],
        "work_patterns": ["9-6 stable", "Flexible hours", "Remote work", "Fast-paced startup", "Corporate environment"]
    }
}

COMPETITIVENESS_LEVELS = [
    {"min": 0, "max": 30, "level": "Needs Improvement", "color": "#ef4444", "advice": "Focus on building foundational skills and gaining initial experience."},
    {"min": 30, "max": 50, "level": "Developing", "color": "#f97316", "advice": "You're on the right track. Seek more internships and certifications."},
    {"min": 50, "max": 70, "level": "Competitive", "color": "#eab308", "advice": "Good progress! Aim for leadership roles and high-impact projects."},
    {"min": 70, "max": 85, "level": "Strong", "color": "#22c55e", "advice": "Excellent profile! Focus on networking and targeting top-tier firms."},
    {"min": 85, "max": 100, "level": "Outstanding", "color": "#06b6d4", "advice": "Outstanding! You're a top candidate. Aim for the most selective opportunities."},
]

# Industry-specific subcategories with refined assessment guidelines
CAREER_SUBCATEGORIES = {
    "finance_business": {
        "label": "Finance & Business",
        "subcategories": {
            "investment_banking": {
                "label": "Investment Banking",
                "guidelines": [
                    "Financial modeling & valuation proficiency (DCF, LBO, comps)",
                    "Understanding of M&A processes and capital markets",
                    "Proficiency in Excel/VBA and PowerPoint for pitch decks",
                    "Relevant internships at bulge-bracket or boutique banks",
                    "CFA Level 1 or progress toward CFA is a strong plus"
                ]
            },
            "consulting": {
                "label": "Management Consulting",
                "guidelines": [
                    "Case interview preparation (market sizing, profitability, M&A cases)",
                    "Strong analytical reasoning and structured problem-solving",
                    "Excellent presentation and client communication skills",
                    "Leadership experience in student organizations or projects",
                    "Knowledge of major industries and business strategy frameworks"
                ]
            },
            "accounting_auditing": {
                "label": "Accounting / Auditing (AMPB)",
                "guidelines": [
                    "Solid understanding of HKFRS/IFRS accounting standards",
                    "Progress toward HKICPA QP, CPA, or ACCA qualification",
                    "Attention to detail and analytical thinking for audit work",
                    "Experience with audit software (e.g., SAP, Oracle, IDEA)",
                    "Internship at Big 4 or mid-tier accounting firms"
                ]
            },
            "financial_analysis": {
                "label": "Financial Analysis / Risk",
                "guidelines": [
                    "Proficiency in Bloomberg Terminal, FactSet, or Reuters",
                    "Strong quantitative and statistical analysis skills",
                    "Knowledge of financial regulations (SFC, HKMA guidelines)",
                    "Experience with Python/R for data analysis is a plus",
                    "FRM or CFA progress demonstrates commitment"
                ]
            }
        }
    },
    "it_engineering": {
        "label": "IT / CS-Engineering",
        "subcategories": {
            "software_engineering": {
                "label": "Software Engineering",
                "guidelines": [
                    "Data structures & algorithms proficiency (LeetCode 200+ recommended)",
                    "System design understanding (scalability, databases, APIs)",
                    "Proficiency in at least 2 programming languages (Python, Java, C++, Go)",
                    "Open-source contributions or side projects on GitHub",
                    "Internship experience at tech companies (FAANG-level preferred)"
                ]
            },
            "data_science": {
                "label": "Data Science / AI",
                "guidelines": [
                    "Strong foundation in statistics, probability, and linear algebra",
                    "Machine learning frameworks (TensorFlow, PyTorch, scikit-learn)",
                    "SQL proficiency and experience with large datasets",
                    "Kaggle competition participation or research publications",
                    "Domain knowledge in a specific industry (finance, healthcare, etc.)"
                ]
            },
            "cybersecurity": {
                "label": "Cybersecurity",
                "guidelines": [
                    "Knowledge of network protocols, firewalls, and encryption",
                    "Security certifications progress (CompTIA Security+, CEH, CISSP)",
                    "Hands-on CTF competition experience",
                    "Understanding of compliance frameworks (ISO 27001, NIST)",
                    "Penetration testing and vulnerability assessment skills"
                ]
            },
            "product_management": {
                "label": "Product Management",
                "guidelines": [
                    "User research and UX design thinking skills",
                    "Agile/Scrum methodology experience",
                    "Data-driven decision making (A/B testing, analytics tools)",
                    "Technical understanding to communicate with engineering teams",
                    "APM program applications require strong case study preparation"
                ]
            }
        }
    },
    "arts": {
        "label": "Faculty of Arts",
        "subcategories": {
            "marketing": {
                "label": "Marketing / Digital Marketing",
                "guidelines": [
                    "Digital marketing certifications (Google Ads, Meta Blueprint, HubSpot)",
                    "Content creation portfolio (social media, copywriting, video)",
                    "Analytics proficiency (Google Analytics, social media insights)",
                    "Campaign management and A/B testing experience",
                    "Understanding of SEO/SEM and paid advertising strategies"
                ]
            },
            "media_journalism": {
                "label": "Media / Journalism",
                "guidelines": [
                    "Published writing portfolio (articles, blogs, reports)",
                    "Multimedia skills (video editing, podcasting, photography)",
                    "Understanding of media law, ethics, and press freedom",
                    "Internship at news outlets (SCMP, RTHK, Bloomberg, Reuters)",
                    "Bilingual proficiency (English/Chinese) is essential in HK"
                ]
            },
            "public_relations": {
                "label": "Public Relations / Communications",
                "guidelines": [
                    "Strong written and verbal communication skills",
                    "Crisis communication and media relations knowledge",
                    "Event planning and management experience",
                    "Portfolio of press releases, media kits, or campaign work",
                    "Agency internship experience (Ogilvy, Edelman, Weber Shandwick)"
                ]
            }
        }
    },
    "academic": {
        "label": "Academic / Research",
        "subcategories": {
            "research": {
                "label": "Academic Research",
                "guidelines": [
                    "Research methodology and academic writing skills",
                    "Published papers or conference presentations",
                    "Strong GPA (First Class Honours / 3.7+ for PhD admissions)",
                    "Research assistant experience under faculty members",
                    "Grant writing and funding application experience"
                ]
            },
            "teaching": {
                "label": "Teaching / Education",
                "guidelines": [
                    "PGDE or equivalent teaching qualification progress",
                    "Tutoring or teaching assistant experience",
                    "Classroom management and curriculum design skills",
                    "Understanding of education technology and e-learning tools",
                    "Passion for student development and mentorship"
                ]
            }
        }
    },
    "government": {
        "label": "Government / Public Sector",
        "subcategories": {
            "administrative_officer": {
                "label": "Administrative Officer (AO/EO)",
                "guidelines": [
                    "CRE (Common Recruitment Exam) preparation and strong scores",
                    "JRE (Joint Recruitment Exam) readiness",
                    "Current affairs knowledge (HK policy, Greater Bay Area, RCEP)",
                    "Group discussion and panel interview skills",
                    "Understanding of government structure and policy-making process"
                ]
            },
            "policy_research": {
                "label": "Policy Research / Think Tank",
                "guidelines": [
                    "Policy analysis and research methodology skills",
                    "Quantitative and qualitative research experience",
                    "Published policy briefs or research reports",
                    "Internship at government departments or think tanks",
                    "Knowledge of HK public policy issues and regional dynamics"
                ]
            }
        }
    },
    "entrepreneurship": {
        "label": "Entrepreneurship",
        "subcategories": {
            "startup_founder": {
                "label": "Startup Founder",
                "guidelines": [
                    "Business plan writing and pitch deck preparation",
                    "Understanding of funding stages (seed, Series A, B, C)",
                    "MVP development and lean startup methodology",
                    "Incubator/accelerator program participation (Cyberport, HKSTP)",
                    "Market validation and customer discovery experience"
                ]
            },
            "venture_capital": {
                "label": "Venture Capital / Private Equity",
                "guidelines": [
                    "Financial modeling and company valuation skills",
                    "Industry trend analysis and deal sourcing experience",
                    "Network building in the startup/VC ecosystem",
                    "Due diligence process understanding",
                    "Investment thesis development and portfolio management"
                ]
            }
        }
    }
}

# ============================================================
# ROUTE TEMPLATES
# ============================================================

ROUTE_TEMPLATES = {
    "finance_business": {
        "year1": {
            "title": "Freshman Year - Build Foundations",
            "tasks": [
                "Maintain GPA above 3.3 (First Class Honours target)",
                "Join finance/business student societies (e.g., Investment Club)",
                "Start learning Excel and financial modeling basics",
                "Attend career talks and networking events",
                "Read financial news daily (Bloomberg, SCMP Business)",
                "Begin CFA Level 1 preparation or ACCA fundamentals",
            ]
        },
        "year2": {
            "title": "Sophomore Year - Gain Experience",
            "tasks": [
                "Apply for spring/summer internships at Big 4 or banks",
                "Take courses in accounting, corporate finance, and statistics",
                "Participate in case competitions (e.g., HSBC/McKinsey)",
                "Build financial models and valuation projects",
                "Network with alumni in target industries",
                "Obtain Bloomberg Market Concepts certification",
            ]
        },
        "year3": {
            "title": "Junior Year - Specialize & Lead",
            "tasks": [
                "Secure summer internship at target firm (IB, consulting, PE)",
                "Take advanced electives in your specialization",
                "Lead a student organization or major project",
                "Complete CFA Level 1 or equivalent certification",
                "Build strong relationships with 3-5 industry mentors",
                "Prepare for full-time recruiting (resume, cover letters, technicals)",
            ]
        },
        "year4": {
            "title": "Senior Year - Convert & Launch",
            "tasks": [
                "Convert internship to full-time offer or apply broadly",
                "Complete capstone/thesis with industry relevance",
                "Continue networking and interview preparation",
                "Attend on-campus recruiting events",
                "Finalize professional certifications",
                "Prepare for transition from university to professional life",
            ]
        }
    },
    "it_engineering": {
        "year1": {
            "title": "Freshman Year - Build Foundations",
            "tasks": [
                "Master fundamentals: data structures, algorithms, OOP",
                "Learn Python/Java thoroughly with personal projects",
                "Set up GitHub and start contributing to open source",
                "Join coding clubs and attend hackathons",
                "Complete online courses (CS50, freeCodeCamp)",
                "Start LeetCode practice (Easy problems)",
            ]
        },
        "year2": {
            "title": "Sophomore Year - Gain Experience",
            "tasks": [
                "Apply for software engineering internships",
                "Build 2-3 substantial projects for portfolio",
                "Learn web development (React/Node.js) or mobile dev",
                "Study system design fundamentals",
                "Participate in hackathons and coding competitions",
                "Get cloud certification (AWS/Azure fundamentals)",
            ]
        },
        "year3": {
            "title": "Junior Year - Specialize & Lead",
            "tasks": [
                "Secure internship at top tech company",
                "Specialize in an area (ML, security, cloud, mobile)",
                "Lead technical projects or open source contributions",
                "Practice LeetCode Medium/Hard problems regularly",
                "Study system design for interviews",
                "Build industry connections through tech meetups",
            ]
        },
        "year4": {
            "title": "Senior Year - Convert & Launch",
            "tasks": [
                "Convert internship or apply for new grad positions",
                "Complete FYP with real-world impact",
                "Prepare for technical interviews intensively",
                "Contribute to significant open source projects",
                "Consider graduate school if interested in research",
                "Network at industry conferences and events",
            ]
        }
    },
    "arts": {
        "year1": {
            "title": "Freshman Year - Build Foundations",
            "tasks": [
                "Maintain strong GPA across humanities courses",
                "Join relevant student media, PR, or creative societies",
                "Start building a portfolio (writing samples, designs, etc.)",
                "Learn digital tools (Adobe Suite, Canva, WordPress)",
                "Attend career exploration workshops",
                "Start a blog or social media presence in your area",
            ]
        },
        "year2": {
            "title": "Sophomore Year - Gain Experience",
            "tasks": [
                "Apply for internships in media, PR, marketing, or NGOs",
                "Take cross-disciplinary courses (business, digital media)",
                "Participate in writing/design/case competitions",
                "Freelance or volunteer for real-world projects",
                "Build a professional portfolio website",
                "Learn basic data analytics and social media marketing",
            ]
        },
        "year3": {
            "title": "Junior Year - Specialize & Lead",
            "tasks": [
                "Secure competitive internship in target industry",
                "Develop specialization (content, UX, PR, journalism)",
                "Lead creative projects or student publications",
                "Build professional network through events and LinkedIn",
                "Consider certifications (Google Analytics, HubSpot)",
                "Start informational interviews with industry professionals",
            ]
        },
        "year4": {
            "title": "Senior Year - Convert & Launch",
            "tasks": [
                "Convert internship or apply strategically",
                "Complete thesis/capstone showcasing expertise",
                "Finalize and polish professional portfolio",
                "Leverage alumni network for job opportunities",
                "Prepare for interviews specific to your industry",
                "Consider postgraduate study if relevant to career goals",
            ]
        }
    }
}

# Copy templates for new categories (simplified)
ROUTE_TEMPLATES["academic"] = ROUTE_TEMPLATES["arts"]
ROUTE_TEMPLATES["entrepreneurship"] = ROUTE_TEMPLATES["it_engineering"]
ROUTE_TEMPLATES["freelance"] = ROUTE_TEMPLATES["arts"]
ROUTE_TEMPLATES["government"] = ROUTE_TEMPLATES["finance_business"]
ROUTE_TEMPLATES["college_teacher"] = ROUTE_TEMPLATES["arts"]

# ============================================================
# EXPERIENCE POSTS (with tags support)
# ============================================================

experience_posts = [
    {
        "id": "1",
        "author": "Anonymous Senior",
        "author_id": "system",
        "author_verified": False,
        "anonymous": True,
        "university": "HKU",
        "faculty": "finance_business",
        "title": "My Journey to Goldman Sachs as a HKU Finance Student",
        "content": "I started preparing in Year 1 by joining the Investment Society. By Year 2, I had completed the Bloomberg terminal certification and secured a Big 4 internship. Key tips: network early, perfect your technicals, and don't underestimate the importance of soft skills in interviews. The 'Why Hong Kong?' question always comes up - have a genuine answer ready.",
        "category": "internship",
        "tags": [{"category": "interview", "subcategory": "skills"}, {"category": "internship", "subcategory": "experience"}],
        "custom_tags": [],
        "likes": 42,
        "liked_by": [],
        "votes": 0,
        "voted_by": [],
        "is_dream_job": False,
        "created_at": "2025-11-15",
        "comments": [
            {"id": "c1", "author": "Anonymous", "author_id": "user1", "author_verified": False, "content": "This is super helpful! Did you do CFA Level 1 before applying?", "created_at": "2025-11-16", "replies": []},
            {"id": "c2", "author": "Year 2 Student", "author_id": "user2", "author_verified": False, "content": "Thanks for sharing! What case competitions did you join?", "created_at": "2025-11-17", "replies": []},
            {"id": "c1a", "author": "Finance Junior", "author_id": "user6", "author_verified": False, "content": "Great insights! How important was networking for getting the interview?", "created_at": "2025-11-18", "replies": []},
            {"id": "c1b", "author": "HKU Year 3", "author_id": "user7", "author_verified": True, "content": "I also got into GS! The technicals were tough but manageable with prep.", "created_at": "2025-11-19", "replies": []},
            {"id": "c1c", "author": "Aspiring Banker", "author_id": "user8", "author_verified": False, "content": "Did you apply through on-campus recruiting or online?", "created_at": "2025-11-20", "replies": []},
            {"id": "c1d", "author": "Anonymous", "author_id": "user9", "author_verified": False, "content": "How long was the entire interview process from application to offer?", "created_at": "2025-11-21", "replies": []},
            {"id": "c1e", "author": "CUHK Finance", "author_id": "user24", "author_verified": False, "content": "What was your GPA when you applied? Does it matter a lot?", "created_at": "2025-11-22", "replies": []},
            {"id": "c1f", "author": "Banking Hopeful", "author_id": "user25", "author_verified": False, "content": "Did you have any connections or referrals at GS?", "created_at": "2025-11-23", "replies": []},
            {"id": "c1g", "author": "Year 1 Student", "author_id": "user26", "author_verified": False, "content": "As a freshman, what should I focus on first?", "created_at": "2025-11-24", "replies": []},
            {"id": "c1h", "author": "Anonymous", "author_id": "user27", "author_verified": False, "content": "How many rounds of interviews did you have?", "created_at": "2025-11-25", "replies": []},
            {"id": "c1i", "author": "HKU Senior", "author_id": "user28", "author_verified": True, "content": "The soft skills part is so true! They really test your communication.", "created_at": "2025-11-26", "replies": []},
            {"id": "c1j", "author": "Finance Society", "author_id": "user29", "author_verified": False, "content": "Would love to invite you to share at our next event!", "created_at": "2025-11-27", "replies": []}
        ]
    },
    {
        "id": "2",
        "author": "CS Graduate 2025",
        "author_id": "system",
        "author_verified": True,
        "anonymous": False,
        "university": "CUHK",
        "faculty": "it_engineering",
        "title": "How I Landed a Google Offer from CUHK",
        "content": "Three things that mattered most: 1) Consistent LeetCode practice (I did 300+ problems over 2 years), 2) Real project experience - I contributed to an open source project that became my best talking point, 3) Mock interviews with friends. Start early, the process takes months. Also, don't ignore behavioral questions - Google cares about Googleyness.",
        "category": "interview",
        "tags": [{"category": "interview", "subcategory": "skills"}, {"category": "interview", "subcategory": "questions"}],
        "custom_tags": ["LeetCode"],
        "likes": 67,
        "liked_by": [],
        "votes": 25,
        "voted_by": [],
        "is_dream_job": True,
        "created_at": "2025-10-20",
        "comments": [
            {"id": "c3", "author": "Anonymous", "author_id": "user3", "author_verified": False, "content": "Which open source projects do you recommend for beginners?", "created_at": "2025-10-21", "replies": []},
            {"id": "c3a", "author": "CS Year 2", "author_id": "user10", "author_verified": False, "content": "300+ LeetCode problems is impressive! How did you stay motivated?", "created_at": "2025-10-22", "replies": []},
            {"id": "c3b", "author": "Tech Enthusiast", "author_id": "user11", "author_verified": True, "content": "What was the hardest part of the Google interview process?", "created_at": "2025-10-23", "replies": []},
            {"id": "c3c", "author": "CUHK Junior", "author_id": "user12", "author_verified": False, "content": "Did you do any internships before Google?", "created_at": "2025-10-24", "replies": []},
            {"id": "c3d", "author": "Anonymous", "author_id": "user13", "author_verified": False, "content": "How long did it take from first application to final offer?", "created_at": "2025-10-25", "replies": []},
            {"id": "c3e", "author": "Coding Newbie", "author_id": "user14", "author_verified": False, "content": "Any tips for someone just starting LeetCode?", "created_at": "2025-10-26", "replies": []},
            {"id": "c3f", "author": "HKUST CS", "author_id": "user30", "author_verified": False, "content": "Did you use LeetCode Premium? Is it worth it?", "created_at": "2025-10-27", "replies": []},
            {"id": "c3g", "author": "Software Eng", "author_id": "user31", "author_verified": True, "content": "System design is often overlooked. Good that you mentioned it!", "created_at": "2025-10-28", "replies": []},
            {"id": "c3h", "author": "Anonymous", "author_id": "user32", "author_verified": False, "content": "What programming languages did they test you on?", "created_at": "2025-10-29", "replies": []},
            {"id": "c3i", "author": "Year 3 CUHK", "author_id": "user33", "author_verified": False, "content": "How did you balance LeetCode with coursework?", "created_at": "2025-10-30", "replies": []},
            {"id": "c3j", "author": "Tech Recruiter", "author_id": "user34", "author_verified": True, "content": "Great advice! Behavioral questions are often underestimated.", "created_at": "2025-10-31", "replies": []},
            {"id": "c3k", "author": "Freshman CS", "author_id": "user35", "author_verified": False, "content": "This is so inspiring! Starting my prep journey now.", "created_at": "2025-11-01", "replies": []},
            {"id": "c3l", "author": "Anonymous", "author_id": "user36", "author_verified": False, "content": "What was your TC (total compensation)?", "created_at": "2025-11-02", "replies": []}
        ]
    },
    {
        "id": "3",
        "author": "Anonymous",
        "author_id": "system",
        "author_verified": False,
        "anonymous": True,
        "university": "HKUST",
        "faculty": "arts",
        "title": "Breaking Into Marketing from an Arts Background",
        "content": "Don't let anyone tell you arts degrees are useless. I leveraged my writing skills and critical thinking to land a marketing role at L'Oreal. Key: learn digital marketing on the side (Google certifications are free!), build a social media portfolio, and emphasize your unique perspective. Employers value creativity and communication skills highly.",
        "category": "career_advice",
        "tags": [{"category": "career_advice", "subcategory": "switching"}],
        "custom_tags": ["Arts", "Marketing"],
        "likes": 35,
        "liked_by": [],
        "votes": 0,
        "voted_by": [],
        "is_dream_job": False,
        "created_at": "2025-12-01",
        "comments": [
            {"id": "c4a", "author": "Arts Student", "author_id": "user15", "author_verified": False, "content": "This gives me so much hope! I was worried my degree wouldn't be practical.", "created_at": "2025-12-02", "replies": []},
            {"id": "c4b", "author": "Marketing Intern", "author_id": "user16", "author_verified": True, "content": "Can confirm - creativity is highly valued in marketing. Good advice!", "created_at": "2025-12-03", "replies": []},
            {"id": "c4c", "author": "HKUST Year 2", "author_id": "user17", "author_verified": False, "content": "Which Google certifications did you complete?", "created_at": "2025-12-04", "replies": []},
            {"id": "c4d", "author": "Anonymous", "author_id": "user18", "author_verified": False, "content": "How did you build your social media portfolio?", "created_at": "2025-12-05", "replies": []},
            {"id": "c4e", "author": "Creative Writer", "author_id": "user37", "author_verified": False, "content": "Did you do any marketing internships during university?", "created_at": "2025-12-06", "replies": []},
            {"id": "c4f", "author": "PR Student", "author_id": "user38", "author_verified": False, "content": "How competitive was the L'Oreal application process?", "created_at": "2025-12-07", "replies": []},
            {"id": "c4g", "author": "Anonymous", "author_id": "user39", "author_verified": False, "content": "What's the salary like for entry-level marketing roles?", "created_at": "2025-12-08", "replies": []},
            {"id": "c4h", "author": "Digital Marketer", "author_id": "user40", "author_verified": True, "content": "Google Analytics certification is a must-have! Great tip.", "created_at": "2025-12-09", "replies": []},
            {"id": "c4i", "author": "Arts Year 3", "author_id": "user41", "author_verified": False, "content": "Did you find it hard to compete against business majors?", "created_at": "2025-12-10", "replies": []},
            {"id": "c4j", "author": "Anonymous", "author_id": "user42", "author_verified": False, "content": "How long did it take to get the job after graduation?", "created_at": "2025-12-11", "replies": []}
        ]
    },
    {
        "id": "4",
        "author": "PolyU Alumni",
        "author_id": "system",
        "author_verified": True,
        "anonymous": False,
        "university": "PolyU",
        "faculty": "it_engineering",
        "title": "Resume Tips That Actually Worked For Me",
        "content": "After getting rejected 20+ times, I revamped my resume with these changes: 1) Quantified every achievement (increased X by Y%), 2) Tailored keywords to each job description, 3) Added a 'Projects' section above 'Education', 4) Got it reviewed by 3 different people. Went from 0 callbacks to 5 interviews in 2 weeks.",
        "category": "resume",
        "tags": [{"category": "resume", "subcategory": "writing"}, {"category": "resume", "subcategory": "modification"}],
        "custom_tags": [],
        "likes": 89,
        "liked_by": [],
        "votes": 0,
        "voted_by": [],
        "is_dream_job": False,
        "created_at": "2025-09-10",
        "comments": [
            {"id": "c4", "author": "Anonymous", "author_id": "user4", "author_verified": False, "content": "Could you share a template?", "created_at": "2025-09-11", "replies": []},
            {"id": "c5", "author": "Year 3 HKUST", "author_id": "user5", "author_verified": True, "content": "Quantifying achievements was a game changer for me too!", "created_at": "2025-09-12", "replies": []},
            {"id": "c5a", "author": "Job Seeker", "author_id": "user19", "author_verified": False, "content": "20 rejections before success - that's so inspiring! Thanks for sharing.", "created_at": "2025-09-13", "replies": []},
            {"id": "c5b", "author": "Fresh Grad", "author_id": "user20", "author_verified": False, "content": "Which ATS software do most companies use?", "created_at": "2025-09-14", "replies": []}
        ]
    },
    {
        "id": "5",
        "author": "Dream Chaser",
        "author_id": "system",
        "author_verified": False,
        "anonymous": False,
        "university": "HKU",
        "faculty": "it_engineering",
        "title": "My Dream Job: Becoming a Product Manager at a Top Tech Company",
        "content": "Ever since I used my first smartphone, I knew I wanted to build products that change how people live. My dream is to become a PM at Google or Apple. I'm currently doing APM prep, learning about user research, A/B testing, and product strategy. The path is tough but I believe in starting with clear goals and working backwards.",
        "category": "dream_job",
        "tags": [{"category": "dream_job", "subcategory": "goals"}],
        "custom_tags": ["PM", "Tech"],
        "likes": 28,
        "liked_by": [],
        "votes": 45,
        "voted_by": [],
        "is_dream_job": True,
        "created_at": "2026-01-05",
        "comments": [
            {"id": "c6a", "author": "PM Aspirant", "author_id": "user21", "author_verified": False, "content": "Same dream here! What resources are you using for APM prep?", "created_at": "2026-01-06", "replies": []},
            {"id": "c6b", "author": "Tech PM", "author_id": "user22", "author_verified": True, "content": "Great mindset! Having a clear goal makes all the difference.", "created_at": "2026-01-07", "replies": []},
            {"id": "c6c", "author": "Anonymous", "author_id": "user23", "author_verified": False, "content": "Are you doing any PM internships this summer?", "created_at": "2026-01-08", "replies": []}
        ]
    }
]

# ============================================================
# JOB RESOURCES (EXPANDED)
# ============================================================

JOB_RESOURCES = {
    "referrals": [
        {"title": "LinkedIn HK University Alumni Groups", "url": "https://www.linkedin.com/", "desc": "Connect with alumni for referrals"},
        {"title": "HKU Career Services", "url": "https://cedars.hku.hk/careers.html", "desc": "Official HKU career platform with referral programs"},
        {"title": "CUHK Career Planning & Development Centre", "url": "https://cpdc.osa.cuhk.edu.hk/", "desc": "CUHK career resources and networking"},
        {"title": "HKUST Career Center", "url": "https://career.hkust.edu.hk/", "desc": "HKUST internship and job referral network"},
    ],
    "resumes": [
        {"title": "Harvard Resume Template", "url": "https://ocs.fas.harvard.edu/resumes-cvs-cover-letters", "desc": "Professional resume template widely used in finance"},
        {"title": "Overleaf CV Templates", "url": "https://www.overleaf.com/latex/templates/tagged/cv", "desc": "LaTeX-based professional CV templates"},
        {"title": "Resume Worded", "url": "https://resumeworded.com/", "desc": "AI-powered resume optimization tool"},
    ],
    "interviews": [
        {"title": "LeetCode", "url": "https://leetcode.com/", "desc": "Technical interview preparation for CS roles"},
        {"title": "Glassdoor Interview Questions", "url": "https://www.glassdoor.com/Interview/", "desc": "Company-specific interview experiences"},
        {"title": "Wall Street Oasis", "url": "https://www.wallstreetoasis.com/", "desc": "Finance interview prep and networking"},
        {"title": "PrepLounge", "url": "https://www.preplounge.com/", "desc": "Case interview preparation for consulting"},
    ],
    "internships": [
        {"title": "Indeed HK", "url": "https://hk.indeed.com/", "desc": "Largest job board with HK internship listings"},
        {"title": "JobsDB", "url": "https://hk.jobsdb.com/", "desc": "Hong Kong's leading job platform"},
        {"title": "CTgoodjobs", "url": "https://www.ctgoodjobs.hk/", "desc": "Popular HK job search platform"},
        {"title": "LinkedIn Jobs", "url": "https://www.linkedin.com/jobs/", "desc": "Professional networking and job search"},
        {"title": "Government Jobs", "url": "https://www.csb.gov.hk/english/recruit/", "desc": "HK Government civil service recruitment"},
    ],
    "salaries": [
        {"title": "Glassdoor HK Salaries", "url": "https://www.glassdoor.com/Salaries/hong-kong-salary-SRCH_IL.0,9_IM1023.htm", "desc": "Salary data by company and position in HK"},
        {"title": "PayScale Hong Kong", "url": "https://www.payscale.com/research/HK/Country=Hong_Kong_(SAR)/Salary", "desc": "Market salary data for HK roles"},
        {"title": "Hays Salary Guide", "url": "https://www.hays.com.hk/salary-guide", "desc": "Annual salary guide for HK professionals across industries"},
        {"title": "Robert Half Salary Guide", "url": "https://www.roberthalf.com.hk/salary-guide", "desc": "Finance, tech, and admin salary benchmarks"},
        {"title": "JobsDB Salary Report", "url": "https://hk.jobsdb.com/en-hk/pages/salary", "desc": "Salary trends and reports from JobsDB HK data"},
    ],
    "company_research": [
        {"title": "Glassdoor Company Reviews", "url": "https://www.glassdoor.com/Reviews/", "desc": "Employee reviews and salary data"},
        {"title": "LinkedIn Company Pages", "url": "https://www.linkedin.com/company/", "desc": "Company culture and employee insights"},
        {"title": "Bloomberg Company Search", "url": "https://www.bloomberg.com/", "desc": "Financial data for public companies"},
    ],
    "industry_reports": [
        {"title": "HKTDC Research", "url": "https://research.hktdc.com/", "desc": "Hong Kong and China market research"},
        {"title": "HK Government Statistics", "url": "https://www.censtatd.gov.hk/", "desc": "Official HK economic and labour statistics"},
        {"title": "Labour Department Reports", "url": "https://www.labour.gov.hk/", "desc": "Employment data and labour market trends"},
    ]
}

INDUSTRY_REPORTS = {
    "finance": [
        {"title": "HKMA Annual Report", "url": "https://www.hkma.gov.hk/eng/publications-and-research/annual-report/", "desc": "Hong Kong Monetary Authority annual overview", "date": "2025"},
        {"title": "SFC Annual Report", "url": "https://www.sfc.hk/en/Published-resources/Corporate-publications/Annual-reports", "desc": "Securities and Futures Commission report", "date": "2025"},
        {"title": "FSDC Research Reports", "url": "https://www.fsdc.org.hk/en/publications", "desc": "Financial Services Development Council insights", "date": "2025"},
    ],
    "technology": [
        {"title": "HKSTP Annual Report", "url": "https://www.hkstp.org/about-us/corporate-information/", "desc": "Science and Technology Parks Corporation report", "date": "2025"},
        {"title": "Cyberport Annual Report", "url": "https://www.cyberport.hk/en/about_us/annual_report", "desc": "Cyberport digital tech ecosystem overview", "date": "2025"},
        {"title": "ITC Innovation Report", "url": "https://www.itc.gov.hk/", "desc": "Innovation and Technology Commission updates", "date": "2025"},
    ],
    "employment": [
        {"title": "Labour Force Statistics", "url": "https://www.censtatd.gov.hk/en/scode210.html", "desc": "Official unemployment and employment data", "date": "Monthly"},
        {"title": "Quarterly Employment Survey", "url": "https://www.censtatd.gov.hk/", "desc": "Detailed sector employment statistics", "date": "Quarterly"},
        {"title": "Wage and Payroll Statistics", "url": "https://www.censtatd.gov.hk/", "desc": "Salary trends across industries", "date": "Quarterly"},
    ]
}

GOVERNMENT_POLICIES = [
    {"title": "Youth Employment and Training Programme", "url": "https://www.yes.labour.gov.hk/", "desc": "Training and job placement for youth aged 15-24", "category": "Youth"},
    {"title": "Continuing Education Fund", "url": "https://www.wfsfaa.gov.hk/cef/", "desc": "Up to HK$25,000 subsidy for approved courses", "category": "Training"},
    {"title": "ERB Courses", "url": "https://www.erb.org/", "desc": "Employees Retraining Board skills upgrading courses", "category": "Training"},
    {"title": "StartmeupHK", "url": "https://www.startmeup.hk/", "desc": "Government support for startups and entrepreneurs", "category": "Entrepreneurship"},
    {"title": "Technology Talent Admission Scheme", "url": "https://www.itc.gov.hk/en/techtas/", "desc": "Fast-track visa for tech talent", "category": "Immigration"},
    {"title": "Graduate Employment Support Scheme", "url": "https://www.labour.gov.hk/", "desc": "Subsidy for employers hiring fresh graduates", "category": "Employment"},
]

# ============================================================
# WEB SCRAPING
# ============================================================

import requests
from bs4 import BeautifulSoup


def scrape_jobs(query="graduate", location="hong kong"):
    """Scrape job listings. Falls back to curated data if scraping fails."""
    jobs = []
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
    }

    try:
        url = f"https://hk.indeed.com/jobs?q={query}&l={location}"
        resp = requests.get(url, headers=headers, timeout=8)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, "html.parser")
            cards = soup.select(".job_seen_beacon, .jobsearch-ResultsList .result, .tapItem")
            for card in cards[:10]:
                title_el = card.select_one("h2 a, .jobTitle a, h2 span")
                company_el = card.select_one(".companyName, [data-testid='company-name'], .company")
                location_el = card.select_one(".companyLocation, [data-testid='text-location'], .location")
                link_el = card.select_one("h2 a, .jobTitle a")

                if title_el:
                    link = ""
                    if link_el and link_el.get("href"):
                        href = link_el["href"]
                        link = href if href.startswith("http") else f"https://hk.indeed.com{href}"

                    jobs.append({
                        "title": title_el.get_text(strip=True),
                        "company": company_el.get_text(strip=True) if company_el else "Company",
                        "location": location_el.get_text(strip=True) if location_el else location,
                        "link": link,
                        "source": "Indeed HK"
                    })
    except Exception:
        pass

    if len(jobs) < 3:
        curated = get_curated_jobs(query)
        jobs.extend(curated)

    return jobs[:12]


def get_curated_jobs(query):
    """Return curated job listings based on query keywords."""
    query_lower = query.lower()
    all_jobs = [
        {"title": "Graduate Analyst - Investment Banking", "company": "J.P. Morgan", "location": "Central, HK", "link": "https://careers.jpmorgan.com/", "source": "JPMorgan Careers"},
        {"title": "Management Consulting Analyst", "company": "McKinsey & Company", "location": "Hong Kong", "link": "https://www.mckinsey.com/careers", "source": "McKinsey Careers"},
        {"title": "Audit Associate - Graduate Programme", "company": "Deloitte", "location": "Hong Kong", "link": "https://www2.deloitte.com/cn/en/careers.html", "source": "Deloitte Careers"},
        {"title": "Software Engineer - New Graduate", "company": "Google", "location": "Hong Kong", "link": "https://careers.google.com/", "source": "Google Careers"},
        {"title": "Data Analyst Intern / Graduate", "company": "Tencent", "location": "Hong Kong", "link": "https://careers.tencent.com/", "source": "Tencent Careers"},
        {"title": "Graduate Software Developer", "company": "HSBC Technology", "location": "Quarry Bay, HK", "link": "https://www.hsbc.com/careers", "source": "HSBC Careers"},
        {"title": "Marketing Executive - Graduate", "company": "L'Oreal Hong Kong", "location": "Tsim Sha Tsui, HK", "link": "https://careers.loreal.com/", "source": "L'Oreal Careers"},
        {"title": "PR & Communications Associate", "company": "Edelman", "location": "Central, HK", "link": "https://www.edelman.com/careers", "source": "Edelman Careers"},
        {"title": "Junior UX Designer", "company": "Klook", "location": "Kwun Tong, HK", "link": "https://www.klook.com/careers/", "source": "Klook Careers"},
        {"title": "Cybersecurity Analyst - Graduate", "company": "PwC", "location": "Hong Kong", "link": "https://www.pwc.com/gx/en/careers.html", "source": "PwC Careers"},
        {"title": "Product Manager - Associate", "company": "Shopee", "location": "Hong Kong", "link": "https://careers.shopee.sg/", "source": "Shopee Careers"},
        {"title": "Financial Risk Analyst - Graduate", "company": "Standard Chartered", "location": "Hong Kong", "link": "https://www.sc.com/en/careers/", "source": "StanChart Careers"},
        {"title": "Trainee Reporter", "company": "South China Morning Post", "location": "Causeway Bay, HK", "link": "https://www.scmp.com/career", "source": "SCMP Careers"},
        {"title": "HR Graduate Programme", "company": "Cathay Pacific", "location": "Hong Kong International Airport", "link": "https://careers.cathaypacific.com/", "source": "Cathay Careers"},
        {"title": "Cloud Engineer - Junior", "company": "Alibaba Cloud", "location": "Hong Kong", "link": "https://careers.alibabagroup.com/", "source": "Alibaba Careers"},
        {"title": "Administrative Officer (AO)", "company": "HK Government", "location": "Hong Kong", "link": "https://www.csb.gov.hk/english/recruit/", "source": "Civil Service"},
        {"title": "Executive Officer (EO)", "company": "HK Government", "location": "Hong Kong", "link": "https://www.csb.gov.hk/english/recruit/", "source": "Civil Service"},
        {"title": "Assistant Professor", "company": "HKU", "location": "Hong Kong", "link": "https://jobs.hku.hk/", "source": "HKU Careers"},
        {"title": "Research Associate", "company": "HKUST", "location": "Clear Water Bay", "link": "https://career.hkust.edu.hk/", "source": "HKUST Careers"},
        {"title": "Startup Associate", "company": "Cyberport", "location": "Pok Fu Lam", "link": "https://www.cyberport.hk/en/incubation", "source": "Cyberport"},
    ]

    if any(kw in query_lower for kw in ["finance", "banking", "accounting", "business"]):
        return [j for j in all_jobs if any(k in j["title"].lower() for k in ["analyst", "banking", "audit", "financial", "consulting"])]
    elif any(kw in query_lower for kw in ["software", "engineer", "developer", "it", "tech", "data", "cs"]):
        return [j for j in all_jobs if any(k in j["title"].lower() for k in ["software", "data", "cloud", "cyber", "product", "developer", "engineer"])]
    elif any(kw in query_lower for kw in ["marketing", "arts", "media", "writing", "design", "pr"]):
        return [j for j in all_jobs if any(k in j["title"].lower() for k in ["marketing", "pr", "ux", "reporter", "hr", "communications", "designer"])]
    elif any(kw in query_lower for kw in ["government", "civil", "public"]):
        return [j for j in all_jobs if any(k in j["title"].lower() for k in ["officer", "government"])]
    elif any(kw in query_lower for kw in ["professor", "academic", "research", "lecturer"]):
        return [j for j in all_jobs if any(k in j["title"].lower() for k in ["professor", "research", "lecturer"])]
    elif any(kw in query_lower for kw in ["startup", "entrepreneur"]):
        return [j for j in all_jobs if any(k in j["title"].lower() for k in ["startup", "associate"])]
    else:
        return all_jobs[:10]


# ============================================================
# AUTHENTICATION HELPERS
# ============================================================

def login_required(f):
    """Decorator to require login for routes."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            if request.is_json:
                return jsonify({"success": False, "message": "Please login first", "redirect": "/login"})
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


def get_current_user():
    """Get current logged-in user or None."""
    if 'user_id' not in session:
        return None
    email = session.get('email')
    return users_db.get(email)


def check_content_moderation(text):
    """Check if content contains prohibited words."""
    for word in PROHIBITED_WORDS:
        if word in text:
            return False, f"Content contains prohibited word: {word}"
    return True, ""


def can_like_post(user_id, post_id):
    """Check if user can like a post (once per day, max 50/day)."""
    if user_id not in user_likes:
        user_likes[user_id] = {}

    user_post_likes = user_likes[user_id]
    now = datetime.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    # Check if already liked this post today
    if post_id in user_post_likes:
        last_like = datetime.fromisoformat(user_post_likes[post_id])
        if last_like >= today_start:
            return False, "Today's like, cannot be repeated"

    # Check daily limit (50 likes per day)
    today_likes = sum(1 for ts in user_post_likes.values()
                      if datetime.fromisoformat(ts) >= today_start)
    if today_likes >= 50:
        return False, "Daily like limit reached (50/day)"

    return True, ""


def can_vote_for_company(user_id, company_id):
    """Check if user can vote for a company (once per day)."""
    if company_id not in company_votes:
        company_votes[company_id] = {}

    now = datetime.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    if user_id in company_votes[company_id]:
        last_vote = datetime.fromisoformat(company_votes[company_id][user_id])
        if last_vote >= today_start:
            return False, "You already voted for this company today"

    return True, ""


def validate_custom_tag(tag):
    """Validate custom tag format: 2-10 chars, Chinese/English/numbers only."""
    if not tag or len(tag) < 2 or len(tag) > 10:
        return False, "Tag must be 2-10 characters"
    if not re.match(r'^[a-zA-Z0-9\u4e00-\u9fa5]+$', tag):
        return False, "Tag can only contain Chinese, English, or numbers"
    return True, ""


def add_notification(user_id, notif_type, content, source_user_id, post_id=None):
    """Add a notification for a user."""
    if user_id not in user_notifications:
        user_notifications[user_id] = []
    notif = {
        "id": str(uuid.uuid4())[:8],
        "type": notif_type,
        "content": content,
        "source_user": source_user_id,
        "post_id": post_id,
        "read": False,
        "created_at": datetime.now().isoformat()
    }
    user_notifications[user_id].insert(0, notif)
    # Keep only last 100 notifications
    user_notifications[user_id] = user_notifications[user_id][:100]


# ============================================================
# ROUTES: Authentication
# ============================================================

@app.route("/login")
def login():
    if 'user_id' in session:
        return redirect(url_for('index'))
    return render_template("login.html")


@app.route("/api/login", methods=["POST"])
def api_login():
    data = request.json
    email = data.get("email", "").strip().lower()
    password = data.get("password", "")

    if not email or not password:
        return jsonify({"success": False, "message": "Please enter email and password"})

    user = users_db.get(email)
    if not user:
        return jsonify({"success": False, "message": "Account not registered. Please sign up first."})

    if not check_password_hash(user["password_hash"], password):
        return jsonify({"success": False, "message": "Incorrect password. Please try again."})

    # Set session
    session.permanent = True
    session['user_id'] = user['user_id']
    session['email'] = email
    session['name'] = user.get('profile', {}).get('name', 'User')
    session['verified'] = user.get('verified', False)
    session['profile_completed'] = user.get('profile_completed', False)

    redirect_url = "/profile" if not user.get('profile_completed') else "/"
    return jsonify({"success": True, "message": "Login successful!", "redirect": redirect_url})


@app.route("/register")
def register():
    if 'user_id' in session:
        return redirect(url_for('index'))
    return render_template("register.html")


@app.route("/api/register", methods=["POST"])
def api_register():
    data = request.json
    email = data.get("email", "").strip().lower()
    password = data.get("password", "")
    confirm = data.get("confirm_password", "")

    if not email or not password:
        return jsonify({"success": False, "message": "Please fill in all fields"})

    if "@" not in email:
        return jsonify({"success": False, "message": "Please enter a valid email address"})

    if len(password) < 6:
        return jsonify({"success": False, "message": "Password must be at least 6 characters"})

    if password != confirm:
        return jsonify({"success": False, "message": "Passwords do not match"})

    if email in users_db:
        return jsonify({"success": False, "message": "Email already registered. Please login."})

    # Create user
    user_id = str(uuid.uuid4())[:8]
    users_db[email] = {
        "user_id": user_id,
        "email": email,
        "password_hash": generate_password_hash(password, method='pbkdf2:sha256'),
        "profile": {},
        "profile_completed": False,
        "verified": False,
        "verification_status": "none",
        "message_settings": {
            "system_notifications": True,
            "interactive_messages": True,
            "push_messages": False
        },
        "created_at": datetime.now().isoformat()
    }

    # Auto login
    session.permanent = True
    session['user_id'] = user_id
    session['email'] = email
    session['name'] = 'User'
    session['verified'] = False
    session['profile_completed'] = False

    return jsonify({"success": True, "message": "Registration successful!", "redirect": "/profile"})


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for('index'))


@app.route("/profile")
@login_required
def profile():
    user = get_current_user()
    return render_template("profile.html", user=user)


@app.route("/api/profile", methods=["GET"])
@login_required
def api_get_profile():
    user = get_current_user()
    if not user:
        return jsonify({"success": False, "message": "User not found"})
    return jsonify({"success": True, "profile": user.get("profile", {}), "message_settings": user.get("message_settings", {})})


@app.route("/api/profile", methods=["POST"])
@login_required
def api_save_profile():
    data = request.json
    user = get_current_user()
    if not user:
        return jsonify({"success": False, "message": "User not found"})

    # Update profile
    user["profile"] = {
        "name": data.get("name", "").strip(),
        "gender": data.get("gender", ""),
        "age": data.get("age", ""),
        "education": data.get("education", ""),
        "major": data.get("major", "").strip(),
        "employment_status": data.get("employment_status", ""),
        "institution": data.get("institution", "")
    }

    user["message_settings"] = {
        "system_notifications": data.get("system_notifications", True),
        "interactive_messages": data.get("interactive_messages", True),
        "push_messages": data.get("push_messages", False)
    }

    user["profile_completed"] = bool(user["profile"]["name"])
    session['name'] = user["profile"]["name"] or "User"
    session['profile_completed'] = user["profile_completed"]

    return jsonify({"success": True, "message": "Profile saved successfully!"})


@app.route("/verification")
@login_required
def verification():
    user = get_current_user()
    return render_template("verification.html", user=user)


@app.route("/api/verification", methods=["POST"])
@login_required
def api_verification():
    data = request.json
    user = get_current_user()
    if not user:
        return jsonify({"success": False, "message": "User not found"})

    institution = data.get("institution", "")
    student_number = data.get("student_number", "").strip()

    if not institution or not student_number:
        return jsonify({"success": False, "message": "Please fill in institution and student number"})

    # Simulate verification (auto-approve for prototype)
    user["verification_status"] = "approved"
    user["verified"] = True
    user["verification_data"] = {
        "institution": institution,
        "student_number": student_number,
        "submitted_at": datetime.now().isoformat(),
        "approved_at": datetime.now().isoformat()
    }
    session['verified'] = True

    return jsonify({"success": True, "message": "Verification approved! You now have full access.", "status": "approved"})


@app.route("/api/verification/status", methods=["GET"])
@login_required
def api_verification_status():
    user = get_current_user()
    if not user:
        return jsonify({"success": False})
    return jsonify({
        "success": True,
        "status": user.get("verification_status", "none"),
        "verified": user.get("verified", False)
    })


# ============================================================
# ROUTES: Main Pages
# ============================================================

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/global-search", methods=["GET"])
def api_global_search():
    """Global search across jobs, posts, and resources."""
    query = request.args.get("q", "").lower().strip()
    if not query or len(query) < 2:
        return jsonify({"success": True, "results": []})
    
    results = []
    
    # Search in career paths
    career_keywords = {
        "finance": {"title": "Finance Careers", "url": "/career-exploration", "icon": "&#x1F4B0;", "type": "Career Path"},
        "tech": {"title": "Technology Careers", "url": "/career-exploration", "icon": "&#x1F4BB;", "type": "Career Path"},
        "software": {"title": "Software Engineering", "url": "/career-exploration", "icon": "&#x1F4BB;", "type": "Career Path"},
        "marketing": {"title": "Marketing Careers", "url": "/career-exploration", "icon": "&#x1F4E3;", "type": "Career Path"},
        "consulting": {"title": "Consulting Careers", "url": "/career-exploration", "icon": "&#x1F4BC;", "type": "Career Path"},
    }
    
    for keyword, data in career_keywords.items():
        if keyword in query:
            results.append(data)
    
    # Search in experience posts
    for post in experience_posts[:10]:
        if query in post["title"].lower() or query in post["content"].lower():
            results.append({
                "title": post["title"][:50] + "..." if len(post["title"]) > 50 else post["title"],
                "url": f"/experience-sharing?post={post['id']}",
                "icon": "&#x1F4DD;",
                "type": "Experience Post"
            })
            if len(results) >= 8:
                break
    
    # Search in pages
    pages = [
        {"keywords": ["job", "search", "find", "apply"], "title": "Job Search", "url": "/job-search", "icon": "&#x1F50D;", "type": "Page"},
        {"keywords": ["resume", "cv"], "title": "Resume Tips", "url": "/experience-sharing", "icon": "&#x1F4C4;", "type": "Resource"},
        {"keywords": ["interview", "prep"], "title": "Interview Preparation", "url": "/experience-sharing", "icon": "&#x1F3A4;", "type": "Resource"},
        {"keywords": ["intern", "internship"], "title": "Internship Opportunities", "url": "/job-search", "icon": "&#x1F393;", "type": "Page"},
        {"keywords": ["roadmap", "plan", "route"], "title": "Career Roadmap", "url": "/personalized-route", "icon": "&#x1F5FA;", "type": "Page"},
        {"keywords": ["assess", "test", "evaluation"], "title": "Self-Assessment", "url": "/career-center/assessment", "icon": "&#x1F4CA;", "type": "Page"},
    ]
    
    for page in pages:
        if any(kw in query for kw in page["keywords"]):
            results.append({k: v for k, v in page.items() if k != "keywords"})
    
    # Remove duplicates
    seen = set()
    unique_results = []
    for r in results:
        if r["url"] not in seen:
            seen.add(r["url"])
            unique_results.append(r)
    
    return jsonify({"success": True, "results": unique_results[:8]})


@app.route("/career-exploration")
@app.route("/career-matching")
def career_exploration():
    return render_template("career_exploration.html", career_data=CAREER_DATA)


@app.route("/api/career-match", methods=["POST"])
def api_career_match():
    data = request.json
    faculty = data.get("faculty", "")
    if faculty in CAREER_DATA:
        # Enhance roles with salary progression and traits
        enhanced_roles = enhance_career_roles(CAREER_DATA[faculty]["roles"], faculty)
        return jsonify({"success": True, "roles": enhanced_roles, "label": CAREER_DATA[faculty]["label"]})
    return jsonify({"success": False, "message": "Invalid faculty selected"})


def enhance_career_roles(roles, faculty):
    """Add salary progression and traits data to career roles."""
    # Salary progression templates by role type
    salary_data = {
        "Investment Banking Analyst": {
            "salary_progression": [
                {"stage": "Analyst", "salary": "HK$35,000-50,000/mo", "years": "0-3 years"},
                {"stage": "Associate", "salary": "HK$60,000-85,000/mo", "years": "3-6 years"},
                {"stage": "VP", "salary": "HK$100,000-150,000/mo", "years": "6-10 years"},
                {"stage": "Director/MD", "salary": "HK$200,000+/mo", "years": "10+ years"}
            ],
            "traits": ["Analytical Mindset", "High Attention to Detail", "Strong Work Ethic", "Resilience Under Pressure", "Team Player"]
        },
        "Management Consultant": {
            "salary_progression": [
                {"stage": "Analyst/Associate", "salary": "HK$30,000-45,000/mo", "years": "0-2 years"},
                {"stage": "Consultant", "salary": "HK$50,000-70,000/mo", "years": "2-4 years"},
                {"stage": "Manager", "salary": "HK$80,000-120,000/mo", "years": "4-7 years"},
                {"stage": "Partner", "salary": "HK$200,000+/mo", "years": "10+ years"}
            ],
            "traits": ["Strategic Thinking", "Client-Facing Skills", "Structured Problem Solver", "Adaptable", "Leadership Potential"]
        },
        "Software Engineer": {
            "salary_progression": [
                {"stage": "Junior/Entry", "salary": "HK$25,000-35,000/mo", "years": "0-2 years"},
                {"stage": "Mid-Level", "salary": "HK$40,000-55,000/mo", "years": "2-4 years"},
                {"stage": "Senior", "salary": "HK$60,000-85,000/mo", "years": "4-7 years"},
                {"stage": "Staff/Principal", "salary": "HK$100,000+/mo", "years": "7+ years"}
            ],
            "traits": ["Logical Thinking", "Continuous Learner", "Problem Solver", "Attention to Detail", "Collaborative"]
        },
        "Data Scientist": {
            "salary_progression": [
                {"stage": "Junior", "salary": "HK$28,000-38,000/mo", "years": "0-2 years"},
                {"stage": "Data Scientist", "salary": "HK$45,000-60,000/mo", "years": "2-4 years"},
                {"stage": "Senior DS", "salary": "HK$70,000-90,000/mo", "years": "4-7 years"},
                {"stage": "Lead/Head", "salary": "HK$100,000+/mo", "years": "7+ years"}
            ],
            "traits": ["Statistical Mindset", "Curious & Inquisitive", "Business Acumen", "Strong Communicator", "Detail-Oriented"]
        },
        "Product Manager": {
            "salary_progression": [
                {"stage": "APM/Junior", "salary": "HK$28,000-40,000/mo", "years": "0-2 years"},
                {"stage": "Product Manager", "salary": "HK$45,000-65,000/mo", "years": "2-4 years"},
                {"stage": "Senior PM", "salary": "HK$70,000-95,000/mo", "years": "4-7 years"},
                {"stage": "Director/VP", "salary": "HK$120,000+/mo", "years": "7+ years"}
            ],
            "traits": ["User Empathy", "Strategic Vision", "Cross-functional Leadership", "Data-Driven", "Excellent Communicator"]
        },
        "Marketing Executive": {
            "salary_progression": [
                {"stage": "Executive", "salary": "HK$16,000-22,000/mo", "years": "0-2 years"},
                {"stage": "Senior Executive", "salary": "HK$25,000-35,000/mo", "years": "2-4 years"},
                {"stage": "Manager", "salary": "HK$40,000-55,000/mo", "years": "4-7 years"},
                {"stage": "Head/Director", "salary": "HK$70,000+/mo", "years": "7+ years"}
            ],
            "traits": ["Creative Thinker", "Trend-Aware", "Strong Writer", "Analytical", "Brand Sensibility"]
        },
        "UX/UI Designer": {
            "salary_progression": [
                {"stage": "Junior Designer", "salary": "HK$18,000-25,000/mo", "years": "0-2 years"},
                {"stage": "Designer", "salary": "HK$28,000-40,000/mo", "years": "2-4 years"},
                {"stage": "Senior Designer", "salary": "HK$45,000-60,000/mo", "years": "4-7 years"},
                {"stage": "Lead/Director", "salary": "HK$70,000+/mo", "years": "7+ years"}
            ],
            "traits": ["Visual Aesthetic", "User-Centric", "Empathetic", "Detail-Oriented", "Collaborative"]
        },
        "Accountant / Auditor": {
            "salary_progression": [
                {"stage": "Associate", "salary": "HK$18,000-24,000/mo", "years": "0-2 years"},
                {"stage": "Senior Associate", "salary": "HK$28,000-38,000/mo", "years": "2-4 years"},
                {"stage": "Manager", "salary": "HK$45,000-60,000/mo", "years": "4-7 years"},
                {"stage": "Partner", "salary": "HK$150,000+/mo", "years": "12+ years"}
            ],
            "traits": ["Meticulous", "Ethical", "Analytical", "Deadline-Driven", "Professional Skepticism"]
        },
        "Assistant Professor": {
            "salary_progression": [
                {"stage": "Postdoc", "salary": "HK$30,000-40,000/mo", "years": "0-3 years"},
                {"stage": "Assistant Prof", "salary": "HK$60,000-80,000/mo", "years": "3-6 years"},
                {"stage": "Associate Prof", "salary": "HK$90,000-120,000/mo", "years": "6-12 years"},
                {"stage": "Full/Chair Prof", "salary": "HK$150,000+/mo", "years": "12+ years"}
            ],
            "traits": ["Research Excellence", "Intellectual Curiosity", "Persistence", "Strong Writer", "Mentoring Ability"]
        },
        "Journalist / Editor": {
            "salary_progression": [
                {"stage": "Junior Reporter", "salary": "HK$15,000-20,000/mo", "years": "0-2 years"},
                {"stage": "Reporter", "salary": "HK$22,000-30,000/mo", "years": "2-4 years"},
                {"stage": "Senior/Editor", "salary": "HK$35,000-50,000/mo", "years": "4-8 years"},
                {"stage": "Chief Editor", "salary": "HK$60,000+/mo", "years": "8+ years"}
            ],
            "traits": ["Curiosity", "Strong Writing", "Deadline-Oriented", "Ethical", "Persistence"]
        }
    }
    
    # Default traits by faculty
    default_traits = {
        "finance_business": ["Analytical", "Detail-Oriented", "Professional", "Resilient", "Team Player"],
        "it_engineering": ["Logical", "Problem Solver", "Continuous Learner", "Collaborative", "Innovative"],
        "arts": ["Creative", "Strong Communicator", "Culturally Aware", "Adaptable", "Self-Motivated"],
        "academic": ["Research-Oriented", "Intellectual Curiosity", "Persistent", "Strong Writer", "Mentor"],
        "government": ["Public Service Minded", "Ethical", "Structured", "Policy-Aware", "Diplomatic"],
        "entrepreneurship": ["Risk-Tolerant", "Visionary", "Resilient", "Adaptable", "Resourceful"],
        "freelance": ["Self-Disciplined", "Client-Focused", "Versatile", "Business-Savvy", "Independent"]
    }
    
    enhanced = []
    for role in roles:
        role_copy = dict(role)
        title = role_copy.get("title", "")
        
        # Add salary progression if available
        if title in salary_data:
            role_copy["salary_progression"] = salary_data[title]["salary_progression"]
            role_copy["traits"] = salary_data[title]["traits"]
        else:
            # Use default traits for faculty
            role_copy["traits"] = default_traits.get(faculty, ["Professional", "Dedicated", "Team Player"])
        
        enhanced.append(role_copy)
    
    return enhanced


# ============================================================
# ROUTES: Career Center (Self-Assessment)
# ============================================================

@app.route("/career-center")
def career_center():
    return render_template("career_center.html")


@app.route("/self-assessment")
@app.route("/career-center/assessment")
def self_assessment():
    return render_template("self_assessment.html", dimensions=ASSESSMENT_WEIGHTS, expanded=EXPANDED_ASSESSMENT, subcategories=CAREER_SUBCATEGORIES)


@app.route("/api/assess", methods=["POST"])
def api_assess():
    data = request.json
    scores = data.get("scores", {})
    total = 0
    breakdown = {}

    # Original dimensions (30%)
    for key, config in ASSESSMENT_WEIGHTS.items():
        raw = min(max(int(scores.get(key, 0)), 0), config["max_score"])
        weighted = (raw / config["max_score"]) * config["weight"] * 100
        total += weighted
        breakdown[key] = {"raw": raw, "weighted": round(weighted, 1), "label": config["label"]}

    # Career cognition (10%)
    cognition_scores = scores.get("career_cognition", {})
    cognition_total = sum(int(cognition_scores.get(d["id"], 3)) for d in EXPANDED_ASSESSMENT["career_cognition"]["dimensions"])
    cognition_max = len(EXPANDED_ASSESSMENT["career_cognition"]["dimensions"]) * 5
    cognition_weighted = (cognition_total / cognition_max) * 0.10 * 100
    total += cognition_weighted
    breakdown["career_cognition"] = {"raw": round(cognition_total / len(EXPANDED_ASSESSMENT["career_cognition"]["dimensions"]), 1), "weighted": round(cognition_weighted, 1), "label": "Career Cognition"}

    # Abilities (15%)
    ability_scores = scores.get("abilities", {})
    ability_total = sum(int(ability_scores.get(d["id"], 3)) for d in EXPANDED_ASSESSMENT["abilities"]["dimensions"])
    ability_max = len(EXPANDED_ASSESSMENT["abilities"]["dimensions"]) * 5
    ability_weighted = (ability_total / ability_max) * 0.15 * 100
    total += ability_weighted
    breakdown["abilities"] = {"raw": round(ability_total / len(EXPANDED_ASSESSMENT["abilities"]["dimensions"]), 1), "weighted": round(ability_weighted, 1), "label": "Abilities"}

    total = round(total, 1)
    level_info = COMPETITIVENESS_LEVELS[0]
    for lvl in COMPETITIVENESS_LEVELS:
        if lvl["min"] <= total <= lvl["max"]:
            level_info = lvl
            break

    return jsonify({
        "success": True,
        "total": total,
        "breakdown": breakdown,
        "level": level_info["level"],
        "color": level_info["color"],
        "advice": level_info["advice"]
    })


@app.route("/career-center/planning")
def career_planning():
    return render_template("career_planning.html")


# ============================================================
# ROUTES: Consultation Pages
# ============================================================

@app.route("/consultation/advisor")
def consultation_advisor():
    return render_template("consultation_advisor.html")


@app.route("/consultation/mentor")
def consultation_mentor():
    return render_template("consultation_mentor.html")


@app.route("/consultation/interview")
def consultation_interview():
    return render_template("consultation_interview.html")


@app.route("/api/career-plan", methods=["POST"])
@login_required
def api_save_career_plan():
    data = request.json
    user = get_current_user()
    if not user:
        return jsonify({"success": False, "message": "User not found"})

    user["career_plan"] = {
        "short_term": data.get("short_term", ""),
        "long_term": data.get("long_term", ""),
        "implementation": data.get("implementation", ""),
        "updated_at": datetime.now().isoformat()
    }

    return jsonify({"success": True, "message": "Career plan saved!"})


@app.route("/api/career-plan", methods=["GET"])
@login_required
def api_get_career_plan():
    user = get_current_user()
    if not user:
        return jsonify({"success": False})
    return jsonify({"success": True, "plan": user.get("career_plan", {})})


# ============================================================
# ROUTES: Personalized Route
# ============================================================

@app.route("/personalized-route")
def personalized_route():
    return render_template("personalized_route.html")


@app.route("/api/generate-route", methods=["POST"])
def api_generate_route():
    data = request.json
    faculty = data.get("faculty", "")
    year = data.get("current_year", 1)

    if faculty not in ROUTE_TEMPLATES:
        return jsonify({"success": False, "message": "Invalid faculty"})

    template = ROUTE_TEMPLATES[faculty]
    route = {}
    for yr_key, yr_data in template.items():
        yr_num = int(yr_key.replace("year", ""))
        status = "completed" if yr_num < year else ("current" if yr_num == year else "upcoming")
        route[yr_key] = {**yr_data, "status": status, "year_num": yr_num}

    return jsonify({"success": True, "route": route, "current_year": year})


@app.route("/api/generate-roadmap", methods=["POST"])
def api_generate_roadmap():
    """Generate enhanced roadmap with faculty-major classification and learning resources."""
    data = request.json
    faculty = data.get("faculty", "")
    major = data.get("major", "")
    year = data.get("current_year", "1")
    career_goal = data.get("career_goal", "corporate")
    
    # Convert year to int if not postgrad
    current_year = 5 if year == "postgrad" else int(year)
    
    # Generate roadmap based on faculty and career goal
    roadmap = generate_faculty_roadmap(faculty, major, career_goal, current_year)
    
    # Get learning resources
    resources = get_learning_resources(faculty, major, career_goal)
    
    # Count completed phases
    completed_count = sum(1 for p in roadmap.values() if p.get("status") == "completed")
    current_phase = next((p.get("title", "") for p in roadmap.values() if p.get("status") == "current"), "")
    resource_count = sum(len(r) for r in resources.values())
    
    return jsonify({
        "success": True,
        "roadmap": roadmap,
        "resources": resources,
        "completed_count": completed_count,
        "current_phase": current_phase,
        "resource_count": resource_count
    })


def generate_faculty_roadmap(faculty, major, career_goal, current_year):
    """Generate detailed roadmap based on faculty, major and career goal."""
    
    # Base roadmap templates by faculty category
    roadmaps = {
        "business": {
            "year1": {
                "title": "Year 1: Foundation Building",
                "tasks": [
                    "Complete core business courses (Accounting, Economics, Statistics)",
                    "Join at least 2 business-related student societies",
                    "Attend career talks and networking events",
                    "Start building your LinkedIn profile",
                    "Explore different career paths within business"
                ],
                "key_skills": ["Excel", "Financial Literacy", "Communication"]
            },
            "year2": {
                "title": "Year 2: Skill Development",
                "tasks": [
                    "Secure your first internship (Big 4, bank, or corporate)",
                    "Complete Bloomberg Market Concepts certification",
                    "Start CFA Level 1 preparation if targeting finance",
                    "Lead a committee position in student organizations",
                    "Build case competition experience"
                ],
                "key_skills": ["Financial Modeling", "Data Analysis", "Leadership"]
            },
            "year3": {
                "title": "Year 3: Career Focus",
                "tasks": [
                    "Complete summer internship at target company",
                    "Network with alumni in your target industry",
                    "Prepare for full-time recruitment",
                    "Complete relevant certifications (CPA, CFA, FRM)",
                    "Refine your resume and practice interviews"
                ],
                "key_skills": ["Valuation", "Due Diligence", "Presentation"]
            },
            "year4": {
                "title": "Year 4: Transition",
                "tasks": [
                    "Secure full-time graduate offer",
                    "Complete final year capstone project",
                    "Mentor junior students",
                    "Prepare for professional certifications",
                    "Build industry knowledge and stay updated"
                ],
                "key_skills": ["Professional Networking", "Industry Expertise"]
            }
        },
        "engineering": {
            "year1": {
                "title": "Year 1: Technical Foundation",
                "tasks": [
                    "Master programming fundamentals (Python, Java, or C++)",
                    "Complete math and physics prerequisites",
                    "Start personal coding projects on GitHub",
                    "Join tech clubs and hackathons",
                    "Learn basic data structures and algorithms"
                ],
                "key_skills": ["Programming", "Mathematics", "Problem Solving"]
            },
            "year2": {
                "title": "Year 2: Specialization",
                "tasks": [
                    "Choose your specialization area",
                    "Complete 200+ LeetCode problems",
                    "Contribute to open source projects",
                    "Secure first tech internship",
                    "Learn cloud platforms (AWS/GCP/Azure)"
                ],
                "key_skills": ["Algorithms", "System Design", "Cloud Computing"]
            },
            "year3": {
                "title": "Year 3: Industry Readiness",
                "tasks": [
                    "Complete summer internship at tech company",
                    "Build a strong portfolio of projects",
                    "Practice system design interviews",
                    "Learn DevOps and CI/CD practices",
                    "Network with engineers at target companies"
                ],
                "key_skills": ["System Design", "DevOps", "Technical Communication"]
            },
            "year4": {
                "title": "Year 4: Career Launch",
                "tasks": [
                    "Secure full-time SWE/DS/PM offer",
                    "Complete final year project",
                    "Obtain relevant certifications (AWS, Google Cloud)",
                    "Consider graduate school options",
                    "Build professional network on LinkedIn"
                ],
                "key_skills": ["Full-Stack Development", "ML/AI", "Leadership"]
            }
        },
        "arts": {
            "year1": {
                "title": "Year 1: Exploration",
                "tasks": [
                    "Explore various arts and humanities courses",
                    "Develop strong writing and communication skills",
                    "Join cultural and creative student groups",
                    "Start building a portfolio of work",
                    "Learn digital tools (Adobe Creative Suite, etc.)"
                ],
                "key_skills": ["Writing", "Critical Thinking", "Creativity"]
            },
            "year2": {
                "title": "Year 2: Skill Building",
                "tasks": [
                    "Secure internship in media, PR, or creative industry",
                    "Build social media presence and personal brand",
                    "Complete digital marketing certifications",
                    "Develop multimedia skills (video, design)",
                    "Network with industry professionals"
                ],
                "key_skills": ["Digital Marketing", "Content Creation", "Design"]
            },
            "year3": {
                "title": "Year 3: Professional Development",
                "tasks": [
                    "Complete summer internship at target company",
                    "Build strong portfolio of published work",
                    "Consider postgraduate options",
                    "Expand professional network",
                    "Develop specialized expertise"
                ],
                "key_skills": ["Project Management", "Client Relations", "Strategy"]
            },
            "year4": {
                "title": "Year 4: Career Transition",
                "tasks": [
                    "Secure full-time position",
                    "Complete capstone or thesis project",
                    "Build industry connections",
                    "Consider further education",
                    "Prepare for professional life"
                ],
                "key_skills": ["Professional Communication", "Industry Knowledge"]
            }
        }
    }
    
    # Map faculty to template category
    faculty_map = {
        "business": "business",
        "engineering": "engineering",
        "science": "engineering",
        "arts": "arts",
        "social_sciences": "arts",
        "law": "business",
        "medicine": "engineering",
        "education": "arts"
    }
    
    template_key = faculty_map.get(faculty, "business")
    template = roadmaps.get(template_key, roadmaps["business"])
    
    # Add status based on current year
    roadmap = {}
    for phase_key, phase_data in template.items():
        phase_num = int(phase_key.replace("year", ""))
        status = "completed" if phase_num < current_year else ("current" if phase_num == current_year else "upcoming")
        roadmap[phase_key] = {**phase_data, "status": status}
    
    return roadmap


def get_learning_resources(faculty, major, career_goal):
    """Get recommended learning resources based on faculty and career goal."""
    
    resources = {
        "courses": [],
        "certifications": [],
        "books": [],
        "tools": []
    }
    
    # Common resources
    common_courses = [
        {"title": "LinkedIn Learning - Career Development", "description": "Professional skills and career advancement courses", "url": "https://www.linkedin.com/learning/", "provider": "LinkedIn", "icon": "&#x1F4BB;"},
    ]
    
    # Faculty-specific resources
    if faculty in ["business", "law"]:
        resources["courses"] = [
            {"title": "Financial Markets by Yale", "description": "Understanding financial markets, risk management, and behavioral finance", "url": "https://www.coursera.org/learn/financial-markets-global", "provider": "Coursera", "icon": "&#x1F4C8;"},
            {"title": "Investment Banking Fundamentals", "description": "Learn valuation, M&A, and financial modeling", "url": "https://www.wallstreetoasis.com/", "provider": "Wall Street Oasis", "icon": "&#x1F4B0;"},
            {"title": "Excel for Finance", "description": "Master Excel for financial analysis and modeling", "url": "https://www.coursera.org/learn/excel-for-finance", "provider": "Coursera", "icon": "&#x1F4CA;"},
        ] + common_courses
        resources["certifications"] = [
            {"title": "CFA Program", "description": "Chartered Financial Analyst - Gold standard for investment professionals", "url": "https://www.cfainstitute.org/", "provider": "CFA Institute", "icon": "&#x1F3C6;"},
            {"title": "CPA Hong Kong", "description": "Certified Public Accountant qualification", "url": "https://www.hkicpa.org.hk/", "provider": "HKICPA", "icon": "&#x1F4DD;"},
            {"title": "Bloomberg Market Concepts", "description": "Self-paced e-learning course on financial markets", "url": "https://www.bloomberg.com/professional/", "provider": "Bloomberg", "icon": "&#x1F4F1;"},
        ]
        resources["books"] = [
            {"title": "Investment Banking by Rosenbaum", "description": "The definitive guide to investment banking", "url": "https://www.amazon.com/Investment-Banking-Valuation-Leveraged-Buyouts/dp/1118656210", "provider": "Amazon", "icon": "&#x1F4D6;"},
            {"title": "The Intelligent Investor", "description": "Benjamin Graham's timeless investment wisdom", "url": "https://www.amazon.com/Intelligent-Investor-Definitive-Investing-Essentials/dp/0060555661", "provider": "Amazon", "icon": "&#x1F4D6;"},
        ]
        resources["tools"] = [
            {"title": "Bloomberg Terminal", "description": "Professional financial data and analytics platform", "url": "https://www.bloomberg.com/professional/", "provider": "Bloomberg", "icon": "&#x1F5A5;"},
            {"title": "Capital IQ", "description": "Financial research and analysis platform", "url": "https://www.capitaliq.com/", "provider": "S&P Global", "icon": "&#x1F4CA;"},
        ]
    elif faculty in ["engineering", "science"]:
        resources["courses"] = [
            {"title": "CS50 by Harvard", "description": "Introduction to Computer Science", "url": "https://cs50.harvard.edu/", "provider": "Harvard", "icon": "&#x1F4BB;"},
            {"title": "Machine Learning by Stanford", "description": "Andrew Ng's famous ML course", "url": "https://www.coursera.org/learn/machine-learning", "provider": "Coursera", "icon": "&#x1F916;"},
            {"title": "System Design Primer", "description": "Learn how to design large-scale systems", "url": "https://github.com/donnemartin/system-design-primer", "provider": "GitHub", "icon": "&#x2699;"},
        ] + common_courses
        resources["certifications"] = [
            {"title": "AWS Certified Solutions Architect", "description": "Cloud architecture certification", "url": "https://aws.amazon.com/certification/", "provider": "Amazon AWS", "icon": "&#x2601;"},
            {"title": "Google Cloud Professional", "description": "GCP professional certifications", "url": "https://cloud.google.com/certification", "provider": "Google", "icon": "&#x2601;"},
            {"title": "TensorFlow Developer Certificate", "description": "Machine learning certification", "url": "https://www.tensorflow.org/certificate", "provider": "Google", "icon": "&#x1F916;"},
        ]
        resources["books"] = [
            {"title": "Cracking the Coding Interview", "description": "The bible for technical interviews", "url": "https://www.amazon.com/Cracking-Coding-Interview-Programming-Questions/dp/0984782850", "provider": "Amazon", "icon": "&#x1F4D6;"},
            {"title": "Designing Data-Intensive Applications", "description": "System design fundamentals", "url": "https://www.amazon.com/Designing-Data-Intensive-Applications-Reliable-Maintainable/dp/1449373321", "provider": "Amazon", "icon": "&#x1F4D6;"},
        ]
        resources["tools"] = [
            {"title": "LeetCode", "description": "Practice coding problems for interviews", "url": "https://leetcode.com/", "provider": "LeetCode", "icon": "&#x1F4BB;"},
            {"title": "GitHub", "description": "Code hosting and collaboration platform", "url": "https://github.com/", "provider": "GitHub", "icon": "&#x1F4BB;"},
        ]
    else:  # arts, social sciences, education
        resources["courses"] = [
            {"title": "Google Digital Marketing", "description": "Free digital marketing certification", "url": "https://learndigital.withgoogle.com/", "provider": "Google", "icon": "&#x1F4F1;"},
            {"title": "Content Strategy by Northwestern", "description": "Learn content marketing strategies", "url": "https://www.coursera.org/specializations/content-strategy", "provider": "Coursera", "icon": "&#x270F;"},
            {"title": "Adobe Creative Cloud Training", "description": "Master design tools", "url": "https://www.adobe.com/creativecloud/", "provider": "Adobe", "icon": "&#x1F3A8;"},
        ] + common_courses
        resources["certifications"] = [
            {"title": "Google Analytics Certification", "description": "Data analytics for marketing", "url": "https://analytics.google.com/analytics/academy/", "provider": "Google", "icon": "&#x1F4CA;"},
            {"title": "HubSpot Marketing Certification", "description": "Inbound marketing certification", "url": "https://academy.hubspot.com/", "provider": "HubSpot", "icon": "&#x1F4E3;"},
        ]
        resources["books"] = [
            {"title": "Made to Stick", "description": "Why some ideas survive and others die", "url": "https://www.amazon.com/Made-Stick-Ideas-Survive-Others/dp/1400064287", "provider": "Amazon", "icon": "&#x1F4D6;"},
        ]
        resources["tools"] = [
            {"title": "Canva", "description": "Design tool for non-designers", "url": "https://www.canva.com/", "provider": "Canva", "icon": "&#x1F3A8;"},
            {"title": "Notion", "description": "All-in-one workspace for notes and projects", "url": "https://www.notion.so/", "provider": "Notion", "icon": "&#x1F4DD;"},
        ]
    
    return resources


# ============================================================
# ROUTES: Job Search
# ============================================================

@app.route("/job-search")
def job_search():
    return render_template("job_search.html", resources=JOB_RESOURCES)


@app.route("/api/search-jobs", methods=["POST"])
def api_search_jobs():
    data = request.json
    query = data.get("query", "graduate")
    region = data.get("region", "hong_kong")
    industry = data.get("industry", "all")
    job_type = data.get("job_type", "all")
    experience = data.get("experience", "all")
    
    # Get jobs with enhanced filtering
    jobs = get_enhanced_jobs(query, region, industry, job_type, experience)
    
    # Calculate region counts
    region_counts = {
        "hong_kong": sum(1 for j in jobs if j.get("region") == "hong_kong"),
        "mainland": sum(1 for j in jobs if j.get("region") == "mainland"),
        "singapore": sum(1 for j in jobs if j.get("region") == "singapore"),
        "international": sum(1 for j in jobs if j.get("region") == "international")
    }
    
    # Prioritize HK jobs if region filter is "hong_kong" or "all"
    if region in ["hong_kong", "all"]:
        hk_jobs = [j for j in jobs if j.get("region") == "hong_kong"]
        other_jobs = [j for j in jobs if j.get("region") != "hong_kong"]
        jobs = hk_jobs + other_jobs
    
    return jsonify({
        "success": True,
        "jobs": jobs,
        "query": query,
        "region_counts": region_counts
    })


def get_enhanced_jobs(query, region="all", industry="all", job_type="all", experience="all"):
    """Get jobs with enhanced filtering and multi-region support."""
    # Enhanced curated jobs with metadata
    all_jobs = [
        # Hong Kong Jobs
        {"title": "Graduate Analyst - Investment Banking", "company": "J.P. Morgan", "location": "Central, HK", "link": "https://careers.jpmorgan.com/", "source": "JPMorgan Careers", "region": "hong_kong", "industry": "finance", "job_type": "graduate", "experience": "entry", "salary": "HK$50-80K/month", "posted": "2 days ago"},
        {"title": "Management Consulting Analyst", "company": "McKinsey & Company", "location": "Hong Kong", "link": "https://www.mckinsey.com/careers", "source": "McKinsey Careers", "region": "hong_kong", "industry": "consulting", "job_type": "full_time", "experience": "entry", "salary": "HK$60-90K/month", "posted": "1 week ago"},
        {"title": "Audit Associate - Graduate Programme", "company": "Deloitte", "location": "Hong Kong", "link": "https://www2.deloitte.com/cn/en/careers.html", "source": "Deloitte Careers", "region": "hong_kong", "industry": "finance", "job_type": "graduate", "experience": "entry", "salary": "HK$25-35K/month", "posted": "3 days ago"},
        {"title": "Software Engineer - New Graduate", "company": "Google", "location": "Hong Kong", "link": "https://careers.google.com/", "source": "Google Careers", "region": "hong_kong", "industry": "technology", "job_type": "graduate", "experience": "entry", "salary": "HK$45-70K/month", "posted": "5 days ago"},
        {"title": "Data Analyst Intern", "company": "Tencent", "location": "Hong Kong", "link": "https://careers.tencent.com/", "source": "Tencent Careers", "region": "hong_kong", "industry": "technology", "job_type": "internship", "experience": "entry", "salary": "HK$18-25K/month", "posted": "Today"},
        {"title": "Graduate Software Developer", "company": "HSBC Technology", "location": "Quarry Bay, HK", "link": "https://www.hsbc.com/careers", "source": "HSBC Careers", "region": "hong_kong", "industry": "technology", "job_type": "graduate", "experience": "entry", "salary": "HK$30-45K/month", "posted": "1 week ago"},
        {"title": "Marketing Executive - Graduate", "company": "L'Oreal Hong Kong", "location": "Tsim Sha Tsui, HK", "link": "https://careers.loreal.com/", "source": "L'Oreal Careers", "region": "hong_kong", "industry": "marketing", "job_type": "graduate", "experience": "entry", "salary": "HK$22-30K/month", "posted": "4 days ago"},
        {"title": "Administrative Officer (AO)", "company": "HK Government", "location": "Hong Kong", "link": "https://www.csb.gov.hk/english/recruit/", "source": "Civil Service", "region": "hong_kong", "industry": "government", "job_type": "full_time", "experience": "entry", "salary": "HK$35-55K/month", "posted": "Ongoing"},
        {"title": "Executive Officer (EO)", "company": "HK Government", "location": "Hong Kong", "link": "https://www.csb.gov.hk/english/recruit/", "source": "Civil Service", "region": "hong_kong", "industry": "government", "job_type": "full_time", "experience": "entry", "salary": "HK$32-45K/month", "posted": "Ongoing"},
        {"title": "Legal Associate", "company": "Baker McKenzie", "location": "Central, HK", "link": "https://www.bakermckenzie.com/careers", "source": "Baker McKenzie", "region": "hong_kong", "industry": "legal", "job_type": "full_time", "experience": "entry", "salary": "HK$55-80K/month", "posted": "1 week ago"},
        {"title": "Junior UX Designer", "company": "Klook", "location": "Kwun Tong, HK", "link": "https://www.klook.com/careers/", "source": "Klook Careers", "region": "hong_kong", "industry": "technology", "job_type": "full_time", "experience": "junior", "salary": "HK$28-40K/month", "posted": "3 days ago"},
        {"title": "Research Associate", "company": "HKU", "location": "Pok Fu Lam", "link": "https://jobs.hku.hk/", "source": "HKU Careers", "region": "hong_kong", "industry": "education", "job_type": "contract", "experience": "entry", "salary": "HK$25-35K/month", "posted": "2 weeks ago"},
        
        # GBA/Mainland China Jobs
        {"title": "Product Manager - Shenzhen", "company": "Huawei", "location": "Shenzhen, GBA", "link": "https://career.huawei.com/", "source": "Huawei Careers", "region": "mainland", "industry": "technology", "job_type": "full_time", "experience": "junior", "salary": "RMB 25-40K/month", "posted": "1 week ago"},
        {"title": "Data Scientist - Guangzhou", "company": "Alibaba", "location": "Guangzhou, GBA", "link": "https://careers.alibabagroup.com/", "source": "Alibaba Careers", "region": "mainland", "industry": "technology", "job_type": "full_time", "experience": "mid", "salary": "RMB 35-55K/month", "posted": "5 days ago"},
        {"title": "Finance Analyst - GBA", "company": "PingAn", "location": "Shenzhen, GBA", "link": "https://talent.pingan.com/", "source": "PingAn Careers", "region": "mainland", "industry": "finance", "job_type": "full_time", "experience": "entry", "salary": "RMB 18-28K/month", "posted": "3 days ago"},
        {"title": "Marketing Manager - Mainland", "company": "ByteDance", "location": "Shanghai", "link": "https://jobs.bytedance.com/", "source": "ByteDance Careers", "region": "mainland", "industry": "marketing", "job_type": "full_time", "experience": "mid", "salary": "RMB 30-50K/month", "posted": "Today"},
        {"title": "Graduate Developer - Beijing", "company": "Baidu", "location": "Beijing", "link": "https://talent.baidu.com/", "source": "Baidu Careers", "region": "mainland", "industry": "technology", "job_type": "graduate", "experience": "entry", "salary": "RMB 20-35K/month", "posted": "1 week ago"},
        {"title": "Consulting Analyst - GBA", "company": "BCG", "location": "Shenzhen, GBA", "link": "https://www.bcg.com/careers", "source": "BCG Careers", "region": "mainland", "industry": "consulting", "job_type": "full_time", "experience": "entry", "salary": "RMB 25-40K/month", "posted": "4 days ago"},
        
        # Singapore Jobs
        {"title": "Software Engineer", "company": "Grab", "location": "Singapore", "link": "https://grab.careers/", "source": "Grab Careers", "region": "singapore", "industry": "technology", "job_type": "full_time", "experience": "junior", "salary": "SGD 5-8K/month", "posted": "2 days ago"},
        {"title": "Investment Banking Analyst", "company": "DBS", "location": "Singapore", "link": "https://www.dbs.com/careers/", "source": "DBS Careers", "region": "singapore", "industry": "finance", "job_type": "full_time", "experience": "entry", "salary": "SGD 6-10K/month", "posted": "1 week ago"},
        {"title": "Data Analyst Intern", "company": "Shopee", "location": "Singapore", "link": "https://careers.shopee.sg/", "source": "Shopee Careers", "region": "singapore", "industry": "technology", "job_type": "internship", "experience": "entry", "salary": "SGD 2-3K/month", "posted": "3 days ago"},
        
        # International Jobs
        {"title": "Management Consultant - London", "company": "Bain & Company", "location": "London, UK", "link": "https://www.bain.com/careers/", "source": "Bain Careers", "region": "international", "industry": "consulting", "job_type": "full_time", "experience": "entry", "salary": "GBP 5-8K/month", "posted": "1 week ago"},
        {"title": "Software Engineer - US", "company": "Meta", "location": "Menlo Park, USA", "link": "https://www.metacareers.com/", "source": "Meta Careers", "region": "international", "industry": "technology", "job_type": "full_time", "experience": "junior", "salary": "USD 10-15K/month", "posted": "5 days ago"},
        {"title": "Finance Graduate - Tokyo", "company": "Goldman Sachs", "location": "Tokyo, Japan", "link": "https://www.goldmansachs.com/careers/", "source": "Goldman Careers", "region": "international", "industry": "finance", "job_type": "graduate", "experience": "entry", "salary": "JPY 500-800K/month", "posted": "2 weeks ago"},
    ]
    
    filtered = all_jobs
    query_lower = query.lower()
    
    # Filter by region
    if region != "all":
        filtered = [j for j in filtered if j.get("region") == region]
    
    # Filter by industry
    if industry != "all":
        filtered = [j for j in filtered if j.get("industry") == industry]
    
    # Filter by job type
    if job_type != "all":
        filtered = [j for j in filtered if j.get("job_type") == job_type]
    
    # Filter by experience level
    if experience != "all":
        filtered = [j for j in filtered if j.get("experience") == experience]
    
    # Filter by query keywords
    if query_lower:
        keywords = query_lower.split()
        filtered = [j for j in filtered if any(
            kw in j["title"].lower() or kw in j["company"].lower() or kw in j.get("industry", "")
            for kw in keywords
        )]
    
    # If no results after filtering, return broader matches
    if not filtered:
        filtered = [j for j in all_jobs if region == "all" or j.get("region") == region][:12]
    
    return filtered[:15]


@app.route("/industry-reports")
def industry_reports():
    return render_template("industry_reports.html", reports=INDUSTRY_REPORTS)


@app.route("/government-policies")
def government_policies():
    return render_template("government_policies.html", policies=GOVERNMENT_POLICIES)


# ============================================================
# ROUTES: Experience Sharing
# ============================================================

@app.route("/experience-sharing")
def experience_sharing():
    user = get_current_user()
    user_id = user['user_id'] if user else None
    return render_template("experience_sharing.html", tag_categories=TAG_CATEGORIES, current_user_id=user_id)


@app.route("/experience-sharing/hottest")
def hottest_posts():
    user = get_current_user()
    user_id = user['user_id'] if user else None
    return render_template("hottest_posts.html", current_user_id=user_id, tag_categories=TAG_CATEGORIES)


@app.route("/api/posts/hottest", methods=["GET"])
def api_get_hottest_posts():
    """Get hottest posts (likes >= 20) with time filters."""
    time_filter = request.args.get("time", "all")  # today, week, month, all
    
    now = datetime.now()
    filtered = []
    
    for post in experience_posts:
        if post.get("likes", 0) < 20:
            continue
        
        # Parse created_at date
        try:
            if " " in post.get("created_at", ""):
                post_date = datetime.strptime(post["created_at"], "%Y-%m-%d %H:%M")
            else:
                post_date = datetime.strptime(post["created_at"], "%Y-%m-%d")
        except:
            continue
        
        # Apply time filter
        if time_filter == "today":
            if post_date.date() != now.date():
                continue
        elif time_filter == "week":
            week_ago = now - timedelta(days=7)
            if post_date < week_ago:
                continue
        elif time_filter == "month":
            month_ago = now - timedelta(days=30)
            if post_date < month_ago:
                continue
        
        filtered.append(post)
    
    # Sort by likes desc, then comments count, then date
    filtered.sort(key=lambda x: (
        -x.get("likes", 0),
        -len(x.get("comments", [])),
        x.get("created_at", "")
    ), reverse=False)
    
    # Add user status
    user = get_current_user()
    if user:
        uid = user['user_id']
        fav_ids = user_favorites.get(uid, [])
        for post in filtered:
            post['user_liked'] = uid in post.get('liked_by', [])
            post['user_favorited'] = post['id'] in fav_ids
    else:
        for post in filtered:
            post['user_liked'] = False
            post['user_favorited'] = False
    
    return jsonify({"success": True, "posts": filtered, "count": len(filtered)})


@app.route("/api/tags", methods=["GET"])
def api_get_tags():
    return jsonify({"success": True, "categories": TAG_CATEGORIES})


@app.route("/api/posts", methods=["GET"])
def api_get_posts():
    category = request.args.get("category", "all")
    faculty = request.args.get("faculty", "all")
    tag = request.args.get("tag", "")
    search = request.args.get("search", "").lower()
    dream_only = request.args.get("dream_only", "false") == "true"

    filtered = experience_posts

    if dream_only:
        filtered = [p for p in filtered if p.get("is_dream_job")]

    if category != "all":
        filtered = [p for p in filtered if p["category"] == category]
    if faculty != "all":
        filtered = [p for p in filtered if p["faculty"] == faculty]
    if tag:
        parts = tag.split(":")
        if len(parts) == 2:
            cat, subcat = parts
            filtered = [p for p in filtered if any(
                t.get("category") == cat and t.get("subcategory") == subcat
                for t in p.get("tags", [])
            )]

    if search:
        filtered = [p for p in filtered if
                    search in p["title"].lower() or
                    search in p["content"].lower() or
                    any(search in c["content"].lower() for c in p.get("comments", []))]

    # Add user like and favorite status
    user = get_current_user()
    if user:
        user_id = user['user_id']
        fav_ids = user_favorites.get(user_id, [])
        for post in filtered:
            post['user_liked'] = user_id in post.get('liked_by', [])
            post['user_voted'] = user_id in post.get('voted_by', [])
            post['user_favorited'] = post['id'] in fav_ids
    else:
        for post in filtered:
            post['user_liked'] = False
            post['user_voted'] = False
            post['user_favorited'] = False

    # Sort: verified alumni posts first, then by date (newest first)
    filtered.sort(key=lambda p: (not p.get('author_verified', False), p.get('created_at', '')), reverse=False)
    # Re-sort to put verified first then newest
    filtered.sort(key=lambda p: (0 if p.get('author_verified', False) else 1, p.get('created_at', '')), reverse=False)
    filtered.sort(key=lambda p: p.get('created_at', ''), reverse=True)
    # Final sort: verified first, then by date desc
    verified_posts = [p for p in filtered if p.get('author_verified', False)]
    non_verified = [p for p in filtered if not p.get('author_verified', False)]
    verified_posts.sort(key=lambda p: p.get('created_at', ''), reverse=True)
    non_verified.sort(key=lambda p: p.get('created_at', ''), reverse=True)
    filtered = verified_posts + non_verified

    return jsonify({"success": True, "posts": filtered})


@app.route("/api/posts", methods=["POST"])
def api_create_post():
    data = request.json
    user = get_current_user()

    # Content moderation
    title = data.get("title", "")
    content = data.get("content", "")
    ok, msg = check_content_moderation(title + " " + content)
    if not ok:
        return jsonify({"success": False, "message": f"Post rejected: {msg}"})

    # Validate custom tags
    custom_tags = data.get("custom_tags", [])
    validated_custom_tags = []
    for tag in custom_tags[:2]:  # Max 2 custom tags
        valid, err = validate_custom_tag(tag)
        if valid:
            validated_custom_tags.append(tag)

    # Save to custom tags history
    if user and validated_custom_tags:
        uid = user['user_id']
        if uid not in custom_tags_history:
            custom_tags_history[uid] = []
        for tag in validated_custom_tags:
            if tag not in custom_tags_history[uid]:
                custom_tags_history[uid].insert(0, tag)
        custom_tags_history[uid] = custom_tags_history[uid][:10]  # Keep last 10

    post = {
        "id": str(uuid.uuid4())[:8],
        "author": "Anonymous" if data.get("anonymous", True) else data.get("author", "Student"),
        "author_id": user['user_id'] if user else "anonymous",
        "author_verified": user.get('verified', False) if user else False,
        "anonymous": data.get("anonymous", True),
        "university": data.get("university", ""),
        "faculty": data.get("faculty", ""),
        "title": title,
        "content": content,
        "category": data.get("category", "career_advice"),
        "tags": data.get("tags", [])[:3],  # Max 3 system tags
        "custom_tags": validated_custom_tags,
        "likes": 0,
        "liked_by": [],
        "votes": 0,
        "voted_by": [],
        "is_dream_job": data.get("category") == "dream_job",
        "created_at": datetime.now().strftime("%Y-%m-%d"),
        "comments": []
    }
    experience_posts.insert(0, post)
    return jsonify({"success": True, "post": post})


@app.route("/api/posts/<post_id>/like", methods=["POST"])
def api_like_post(post_id):
    user = get_current_user()
    if not user:
        return jsonify({"success": False, "message": "Please login to like posts"})

    user_id = user['user_id']

    for post in experience_posts:
        if post["id"] == post_id:
            if "liked_by" not in post:
                post["liked_by"] = []

            # Toggle: if already liked, unlike
            if user_id in post["liked_by"]:
                post["liked_by"].remove(user_id)
                post["likes"] = max(0, post["likes"] - 1)
                # Remove from tracking
                if user_id in user_likes and post_id in user_likes[user_id]:
                    del user_likes[user_id][post_id]
                return jsonify({"success": True, "likes": post["likes"], "liked": False})

            # Check like limits for new like
            can_like, msg = can_like_post(user_id, post_id)
            if not can_like:
                return jsonify({"success": False, "message": msg, "already_liked": True})

            post["likes"] += 1
            post["liked_by"].append(user_id)

            # Record like timestamp
            if user_id not in user_likes:
                user_likes[user_id] = {}
            user_likes[user_id][post_id] = datetime.now().isoformat()

            return jsonify({"success": True, "likes": post["likes"], "liked": True})

    return jsonify({"success": False, "message": "Post not found"})


@app.route("/api/posts/<post_id>/vote", methods=["POST"])
def api_vote_post(post_id):
    """Vote for dream job post."""
    user = get_current_user()
    if not user:
        return jsonify({"success": False, "message": "Please login to vote"})

    user_id = user['user_id']

    for post in experience_posts:
        if post["id"] == post_id:
            if not post.get("is_dream_job"):
                return jsonify({"success": False, "message": "This post is not in Dream Job category"})

            if user_id in post.get("voted_by", []):
                return jsonify({"success": False, "message": "You already voted for this post", "already_voted": True})

            post["votes"] = post.get("votes", 0) + 1
            if "voted_by" not in post:
                post["voted_by"] = []
            post["voted_by"].append(user_id)

            return jsonify({"success": True, "votes": post["votes"]})

    return jsonify({"success": False, "message": "Post not found"})


@app.route("/api/posts/<post_id>/comment", methods=["POST"])
def api_add_comment(post_id):
    data = request.json
    user = get_current_user()
    if not user:
        return jsonify({"success": False, "message": "Please complete registration and login to participate in comment interactions", "redirect": "/register"})

    # Content moderation
    content = data.get("content", "")
    ok, msg = check_content_moderation(content)
    if not ok:
        return jsonify({"success": False, "message": f"Comment rejected: {msg}"})

    for post in experience_posts:
        if post["id"] == post_id:
            comment = {
                "id": str(uuid.uuid4())[:8],
                "author": user.get('profile', {}).get('name', 'User') if not data.get("anonymous", True) else "Anonymous",
                "author_id": user['user_id'],
                "author_verified": user.get('verified', False),
                "content": content,
                "replies": [],
                "created_at": datetime.now().strftime("%Y-%m-%d %H:%M")
            }
            post["comments"].append(comment)
            
            # Notify post author
            if post.get("author_id") and post["author_id"] != user['user_id']:
                add_notification(post["author_id"], "comment", f"New comment on your post: {content[:50]}...", user['user_id'], post_id)
            
            return jsonify({"success": True, "comment": comment})
    return jsonify({"success": False, "message": "Post not found"})


@app.route("/api/posts/<post_id>/comments/<comment_id>/reply", methods=["POST"])
def api_add_reply(post_id, comment_id):
    """Add a reply to a primary comment (max 2 levels)."""
    data = request.json
    user = get_current_user()
    if not user:
        return jsonify({"success": False, "message": "Please complete registration and login to participate in comment interactions", "redirect": "/register"})

    content = data.get("content", "")
    if len(content) > 300:
        return jsonify({"success": False, "message": "Reply must be 300 characters or less"})
    
    ok, msg = check_content_moderation(content)
    if not ok:
        return jsonify({"success": False, "message": f"Reply rejected: {msg}"})

    for post in experience_posts:
        if post["id"] == post_id:
            for comment in post.get("comments", []):
                if comment["id"] == comment_id:
                    reply = {
                        "id": str(uuid.uuid4())[:8],
                        "author": user.get('profile', {}).get('name', 'User') if not data.get("anonymous", True) else "Anonymous",
                        "author_id": user['user_id'],
                        "author_verified": user.get('verified', False),
                        "content": content,
                        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M")
                    }
                    if "replies" not in comment:
                        comment["replies"] = []
                    comment["replies"].append(reply)
                    
                    # Notify comment author
                    if comment.get("author_id") and comment["author_id"] != user['user_id']:
                        add_notification(comment["author_id"], "reply", f"New reply to your comment: {content[:50]}...", user['user_id'], post_id)
                    
                    return jsonify({"success": True, "reply": reply})
            return jsonify({"success": False, "message": "Comment not found"})
    return jsonify({"success": False, "message": "Post not found"})


@app.route("/api/custom-tags-history", methods=["GET"])
@login_required
def api_custom_tags_history():
    user = get_current_user()
    if not user:
        return jsonify({"success": False, "tags": []})
    return jsonify({"success": True, "tags": custom_tags_history.get(user['user_id'], [])})


@app.route("/api/notifications", methods=["GET"])
@login_required
def api_get_notifications():
    """Get user notifications."""
    user = get_current_user()
    if not user:
        return jsonify({"success": False, "notifications": []})
    uid = user['user_id']
    notifs = user_notifications.get(uid, [])
    unread_count = sum(1 for n in notifs if not n.get("read"))
    return jsonify({"success": True, "notifications": notifs[:50], "unread_count": unread_count})


@app.route("/api/notifications/read", methods=["POST"])
@login_required
def api_mark_notifications_read():
    """Mark notifications as read."""
    user = get_current_user()
    if not user:
        return jsonify({"success": False})
    uid = user['user_id']
    data = request.json
    notif_ids = data.get("ids", [])
    
    if uid in user_notifications:
        for notif in user_notifications[uid]:
            if not notif_ids or notif["id"] in notif_ids:
                notif["read"] = True
    return jsonify({"success": True})


# ============================================================
# ROUTES: Private Messaging
# ============================================================

@app.route("/messages")
@login_required
def messages_page():
    """Messages inbox page."""
    return render_template("messages.html")


def get_conversation_id(user1_id, user2_id):
    """Generate a consistent conversation ID for two users."""
    return "_".join(sorted([user1_id, user2_id]))


@app.route("/api/messages/conversations", methods=["GET"])
@login_required
def api_get_conversations():
    """Get all conversations for the current user."""
    user = get_current_user()
    if not user:
        return jsonify({"success": False, "conversations": []})
    
    uid = user['user_id']
    conversations = []
    
    for conv_id, messages in private_messages.items():
        if uid in conv_id.split("_"):
            if messages:
                # Get the other user
                other_id = [u for u in conv_id.split("_") if u != uid][0]
                
                # Get other user's info
                other_user = users_db.get(next((email for email, u in users_db.items() if u.get('user_id') == other_id), None), {})
                other_name = other_user.get('profile', {}).get('name', 'User')
                other_verified = other_user.get('verified', False)
                
                # Get last message and unread count
                last_msg = messages[-1]
                unread_count = sum(1 for m in messages if m['receiver_id'] == uid and not m.get('read', False))
                
                conversations.append({
                    "id": conv_id,
                    "other_user_id": other_id,
                    "other_user_name": other_name,
                    "other_user_verified": other_verified,
                    "last_message": last_msg['content'][:50] + ('...' if len(last_msg['content']) > 50 else ''),
                    "last_message_time": last_msg['created_at'],
                    "unread_count": unread_count
                })
    
    # Sort by last message time (newest first)
    conversations.sort(key=lambda c: c['last_message_time'], reverse=True)
    
    return jsonify({"success": True, "conversations": conversations})


@app.route("/api/messages/<other_user_id>", methods=["GET"])
@login_required
def api_get_messages(other_user_id):
    """Get messages with a specific user."""
    user = get_current_user()
    if not user:
        return jsonify({"success": False, "messages": []})
    
    uid = user['user_id']
    conv_id = get_conversation_id(uid, other_user_id)
    
    messages = private_messages.get(conv_id, [])
    
    # Mark messages as read
    for msg in messages:
        if msg['receiver_id'] == uid:
            msg['read'] = True
    
    # Get other user info
    other_user = users_db.get(next((email for email, u in users_db.items() if u.get('user_id') == other_user_id), None), {})
    other_name = other_user.get('profile', {}).get('name', 'User')
    other_verified = other_user.get('verified', False)
    
    return jsonify({
        "success": True,
        "messages": messages,
        "other_user": {
            "id": other_user_id,
            "name": other_name,
            "verified": other_verified
        }
    })


@app.route("/api/messages/<other_user_id>", methods=["POST"])
@login_required
def api_send_message(other_user_id):
    """Send a message to another user."""
    user = get_current_user()
    if not user:
        return jsonify({"success": False, "message": "Please login to send messages"})
    
    uid = user['user_id']
    
    # Check if user can receive messages
    other_settings = user_settings.get(other_user_id, {})
    if not other_settings.get('receive_messages', True):
        return jsonify({"success": False, "message": "This user has disabled private messages"})
    
    data = request.json
    content = data.get('content', '').strip()
    
    if not content:
        return jsonify({"success": False, "message": "Message cannot be empty"})
    
    if len(content) > 1000:
        return jsonify({"success": False, "message": "Message too long (max 1000 characters)"})
    
    # Content moderation
    ok, msg = check_content_moderation(content)
    if not ok:
        return jsonify({"success": False, "message": f"Message rejected: {msg}"})
    
    conv_id = get_conversation_id(uid, other_user_id)
    
    if conv_id not in private_messages:
        private_messages[conv_id] = []
    
    message = {
        "id": str(uuid.uuid4())[:8],
        "sender_id": uid,
        "receiver_id": other_user_id,
        "content": content,
        "read": False,
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M")
    }
    
    private_messages[conv_id].append(message)
    
    # Notify the receiver
    sender_name = user.get('profile', {}).get('name', 'Someone')
    add_notification(other_user_id, "message", f"New message from {sender_name}: {content[:30]}...", uid, None)
    
    return jsonify({"success": True, "message": message})


@app.route("/api/messages/unread-count", methods=["GET"])
@login_required
def api_messages_unread_count():
    """Get total unread message count."""
    user = get_current_user()
    if not user:
        return jsonify({"success": True, "count": 0})
    
    uid = user['user_id']
    total_unread = 0
    
    for conv_id, messages in private_messages.items():
        if uid in conv_id.split("_"):
            total_unread += sum(1 for m in messages if m['receiver_id'] == uid and not m.get('read', False))
    
    return jsonify({"success": True, "count": total_unread})


@app.route("/api/user/settings", methods=["GET", "POST"])
@login_required
def api_user_settings():
    """Get or update user settings."""
    user = get_current_user()
    if not user:
        return jsonify({"success": False})
    
    uid = user['user_id']
    
    if request.method == "GET":
        settings = user_settings.get(uid, {"receive_messages": True})
        return jsonify({"success": True, "settings": settings})
    
    # POST - update settings
    data = request.json
    if uid not in user_settings:
        user_settings[uid] = {}
    
    if 'receive_messages' in data:
        user_settings[uid]['receive_messages'] = data['receive_messages']
    
    return jsonify({"success": True, "settings": user_settings[uid]})


@app.route("/api/posts/<post_id>/favorite", methods=["POST"])
@login_required
def api_toggle_favorite(post_id):
    """Toggle favorite on a post."""
    user = get_current_user()
    if not user:
        return jsonify({"success": False, "message": "Please login"})
    uid = user['user_id']
    if uid not in user_favorites:
        user_favorites[uid] = []
    if post_id in user_favorites[uid]:
        user_favorites[uid].remove(post_id)
        return jsonify({"success": True, "favorited": False, "message": "Removed from favorites"})
    else:
        user_favorites[uid].append(post_id)
        return jsonify({"success": True, "favorited": True, "message": "Added to favorites"})


@app.route("/api/favorites", methods=["GET"])
@login_required
def api_get_favorites():
    """Get user's favorite posts."""
    user = get_current_user()
    if not user:
        return jsonify({"success": False, "posts": []})
    uid = user['user_id']
    fav_ids = user_favorites.get(uid, [])
    fav_posts = [p for p in experience_posts if p["id"] in fav_ids]
    for post in fav_posts:
        post['user_liked'] = uid in post.get('liked_by', [])
        post['user_favorited'] = True
    return jsonify({"success": True, "posts": fav_posts})


@app.route("/api/posts/<post_id>", methods=["DELETE"])
@login_required
def api_delete_post(post_id):
    """Delete a post - only the owner can delete their own posts."""
    user = get_current_user()
    if not user:
        return jsonify({"success": False, "message": "Please login to delete posts"})
    
    uid = user['user_id']
    
    # Find the post
    for i, post in enumerate(experience_posts):
        if post["id"] == post_id:
            # Check ownership
            if post.get("author_id") != uid:
                return jsonify({"success": False, "message": "You can only delete your own posts"})
            
            # Remove the post
            experience_posts.pop(i)
            
            # Also remove from favorites
            for u in user_favorites:
                if post_id in user_favorites[u]:
                    user_favorites[u].remove(post_id)
            
            return jsonify({"success": True, "message": "Post deleted successfully"})
    
    return jsonify({"success": False, "message": "Post not found"})


@app.route("/my-favorites")
@login_required
def my_favorites():
    return render_template("my_favorites.html")


# ============================================================
# ROUTES: Dream Job Ranking
# ============================================================

@app.route("/dream-jobs")
def dream_jobs():
    return render_template("dream_jobs.html")


@app.route("/api/dream-jobs/posts", methods=["GET"])
def api_dream_job_posts():
    """Get dream job posts sorted by votes."""
    dream_posts = [p for p in experience_posts if p.get("is_dream_job")]
    dream_posts.sort(key=lambda x: x.get("votes", 0), reverse=True)

    user = get_current_user()
    if user:
        user_id = user['user_id']
        for post in dream_posts:
            post['user_voted'] = user_id in post.get('voted_by', [])
    else:
        for post in dream_posts:
            post['user_voted'] = False

    return jsonify({"success": True, "posts": dream_posts})


@app.route("/api/dream-jobs/companies", methods=["GET"])
def api_dream_companies():
    """Get dream companies sorted by votes."""
    companies = sorted(dream_companies, key=lambda x: x["votes"], reverse=True)

    user = get_current_user()
    if user:
        user_id = user['user_id']
        for company in companies:
            company['user_voted'] = company["id"] in company_votes and user_id in company_votes[company["id"]]
    else:
        for company in companies:
            company['user_voted'] = False

    return jsonify({"success": True, "companies": companies})


@app.route("/api/dream-jobs/companies/<company_id>/vote", methods=["POST"])
def api_vote_company(company_id):
    """Vote for a dream company."""
    user = get_current_user()
    if not user:
        return jsonify({"success": False, "message": "Please login to vote"})

    user_id = user['user_id']

    # Check if can vote
    can_vote, msg = can_vote_for_company(user_id, company_id)
    if not can_vote:
        return jsonify({"success": False, "message": msg, "already_voted": True})

    for company in dream_companies:
        if company["id"] == company_id:
            company["votes"] += 1

            if company_id not in company_votes:
                company_votes[company_id] = {}
            company_votes[company_id][user_id] = datetime.now().isoformat()

            # Award points and check badges
            award_user_points(user_id, 5, "vote")

            return jsonify({"success": True, "votes": company["votes"]})

    return jsonify({"success": False, "message": "Company not found"})


def award_user_points(user_id, points, action_type):
    """Award points to user and check for new badges."""
    if user_id not in user_achievements:
        user_achievements[user_id] = {
            "badges": [],
            "points": 0,
            "votes_cast": 0,
            "offers_shared": 0
        }
    
    user_achievements[user_id]["points"] += points
    
    if action_type == "vote":
        user_achievements[user_id]["votes_cast"] += 1
        votes = user_achievements[user_id]["votes_cast"]
        
        # Check vote badges
        if votes == 1 and "first_vote" not in user_achievements[user_id]["badges"]:
            user_achievements[user_id]["badges"].append("first_vote")
            user_achievements[user_id]["points"] += ACHIEVEMENT_BADGES["first_vote"]["points"]
        elif votes == 10 and "voter_10" not in user_achievements[user_id]["badges"]:
            user_achievements[user_id]["badges"].append("voter_10")
            user_achievements[user_id]["points"] += ACHIEVEMENT_BADGES["voter_10"]["points"]
        elif votes == 50 and "voter_50" not in user_achievements[user_id]["badges"]:
            user_achievements[user_id]["badges"].append("voter_50")
            user_achievements[user_id]["points"] += ACHIEVEMENT_BADGES["voter_50"]["points"]
    
    elif action_type == "offer":
        user_achievements[user_id]["offers_shared"] += 1
        if "offer_shared" not in user_achievements[user_id]["badges"]:
            user_achievements[user_id]["badges"].append("offer_shared")
            user_achievements[user_id]["points"] += ACHIEVEMENT_BADGES["offer_shared"]["points"]
    
    # Check top contributor
    if user_achievements[user_id]["points"] >= 500 and "top_contributor" not in user_achievements[user_id]["badges"]:
        user_achievements[user_id]["badges"].append("top_contributor")


@app.route("/api/dream-jobs/offers", methods=["GET"])
def api_get_offers():
    """Get offer showcase with optional filters."""
    industry = request.args.get("industry", "")
    sort_by = request.args.get("sort", "recent")  # recent, likes, salary
    
    offers = offer_showcase.copy()
    
    # Filter by industry if specified
    if industry:
        company_ids = [c["id"] for c in dream_companies if c["industry"].lower() == industry.lower()]
        offers = [o for o in offers if o.get("company_id") in company_ids]
    
    # Sort
    if sort_by == "likes":
        offers.sort(key=lambda x: x.get("likes", 0), reverse=True)
    elif sort_by == "recent":
        offers.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    
    return jsonify({"success": True, "offers": offers})


@app.route("/api/dream-jobs/offers", methods=["POST"])
@login_required
def api_submit_offer():
    """Submit a new offer to the showcase."""
    user = get_current_user()
    if not user:
        return jsonify({"success": False, "message": "Please login first"})
    
    data = request.json
    company = data.get("company", "").strip()
    position = data.get("position", "").strip()
    salary = data.get("salary", "").strip()
    location = data.get("location", "Hong Kong").strip()
    offer_date = data.get("offer_date", "")
    anonymous = data.get("anonymous", False)
    
    if not company or not position:
        return jsonify({"success": False, "message": "Company and position are required"})
    
    # Content moderation
    is_valid, msg = check_content_moderation(f"{company} {position} {salary}")
    if not is_valid:
        return jsonify({"success": False, "message": msg})
    
    # Find company_id if exists
    company_id = None
    for c in dream_companies:
        if c["name"].lower() == company.lower():
            company_id = c["id"]
            break
    
    offer_id = str(uuid.uuid4())[:8]
    new_offer = {
        "id": offer_id,
        "user_id": user["user_id"],
        "author_name": "Anonymous" if anonymous else user.get("profile", {}).get("name", "User"),
        "company": company,
        "company_id": company_id,
        "position": position,
        "salary": salary if salary else "Not disclosed",
        "location": location,
        "offer_date": offer_date,
        "anonymous": anonymous,
        "verified": user.get("verified", False),
        "university": user.get("profile", {}).get("institution", "HK University"),
        "likes": 0,
        "created_at": datetime.now().strftime("%Y-%m-%d")
    }
    
    offer_showcase.insert(0, new_offer)
    
    # Award points
    award_user_points(user["user_id"], 50, "offer")
    if user.get("verified", False) and "verified_offer" not in user_achievements.get(user["user_id"], {}).get("badges", []):
        if user["user_id"] not in user_achievements:
            user_achievements[user["user_id"]] = {"badges": [], "points": 0, "votes_cast": 0, "offers_shared": 0}
        user_achievements[user["user_id"]]["badges"].append("verified_offer")
        user_achievements[user["user_id"]]["points"] += ACHIEVEMENT_BADGES["verified_offer"]["points"]
    
    return jsonify({"success": True, "message": "Offer shared successfully!", "offer": new_offer})


@app.route("/api/dream-jobs/offers/<offer_id>/like", methods=["POST"])
@login_required
def api_like_offer(offer_id):
    """Like an offer in the showcase."""
    user = get_current_user()
    if not user:
        return jsonify({"success": False, "message": "Please login first"})
    
    for offer in offer_showcase:
        if offer["id"] == offer_id:
            offer["likes"] = offer.get("likes", 0) + 1
            return jsonify({"success": True, "likes": offer["likes"]})
    
    return jsonify({"success": False, "message": "Offer not found"})


@app.route("/api/dream-jobs/achievements", methods=["GET"])
@login_required
def api_get_achievements():
    """Get current user's achievements and badges."""
    user = get_current_user()
    if not user:
        return jsonify({"success": False})
    
    user_id = user["user_id"]
    achievements = user_achievements.get(user_id, {
        "badges": [],
        "points": 0,
        "votes_cast": 0,
        "offers_shared": 0
    })
    
    # Add badge details
    badge_details = []
    for badge_id in achievements.get("badges", []):
        if badge_id in ACHIEVEMENT_BADGES:
            badge_details.append({
                "id": badge_id,
                **ACHIEVEMENT_BADGES[badge_id]
            })
    
    return jsonify({
        "success": True,
        "achievements": achievements,
        "badge_details": badge_details,
        "all_badges": ACHIEVEMENT_BADGES
    })


@app.route("/api/dream-jobs/leaderboard", methods=["GET"])
def api_get_leaderboard():
    """Get top contributors leaderboard."""
    leaderboard = []
    for user_id, data in user_achievements.items():
        # Get user name from achievements data first, then users_db
        user_name = data.get("name", "Anonymous")
        if user_name == "Anonymous":
            for email, user in users_db.items():
                if user.get("user_id") == user_id:
                    user_name = user.get("profile", {}).get("name", "User")
                    break
        
        leaderboard.append({
            "user_id": user_id,
            "name": user_name,
            "points": data.get("points", 0),
            "badges": len(data.get("badges", [])),
            "votes_cast": data.get("votes_cast", 0),
            "offers_shared": data.get("offers_shared", 0)
        })
    
    leaderboard.sort(key=lambda x: x["points"], reverse=True)
    return jsonify({"success": True, "leaderboard": leaderboard[:20]})


@app.route("/api/dream-jobs/stats", methods=["GET"])
def api_dream_jobs_stats():
    """Get overall dream jobs statistics."""
    total_votes = sum(c["votes"] for c in dream_companies)
    total_offers = len(offer_showcase)
    trending_companies = [c for c in dream_companies if c.get("trending")]
    active_hiring = len([c for c in dream_companies if c.get("hiring_status") == "active"])
    
    # Industry breakdown
    industry_stats = {}
    for company in dream_companies:
        ind = company["industry"]
        if ind not in industry_stats:
            industry_stats[ind] = {"count": 0, "votes": 0}
        industry_stats[ind]["count"] += 1
        industry_stats[ind]["votes"] += company["votes"]
    
    return jsonify({
        "success": True,
        "stats": {
            "total_votes": total_votes,
            "total_offers": total_offers,
            "total_companies": len(dream_companies),
            "active_hiring": active_hiring,
            "trending_count": len(trending_companies),
            "industry_breakdown": industry_stats
        }
    })


# ============================================================
# CONTEXT PROCESSOR
# ============================================================

@app.context_processor
def inject_user():
    """Make user info available in all templates."""
    return {
        'current_user': get_current_user(),
        'is_logged_in': 'user_id' in session,
        'user_name': session.get('name', 'Guest'),
        'is_verified': session.get('verified', False)
    }


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":
    app.run(debug=True, port=5001)
