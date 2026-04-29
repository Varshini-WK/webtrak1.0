from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import func, select, text

from app.core.database import Base, Database, db
from app.models import AllocationRole, Band, Designation, KpiDefinition, WebknotValue

ALLOCATION_ROLE_ROWS: tuple[tuple[int, str], ...] = (
    (1, "UI Developer"),
    (2, "Associate UI Developer"),
    (3, "Senior UI Developer"),
    (4, "UI Lead"),
    (5, "Cross Platform Developer"),
    (6, "Associate Cross Platform Developer"),
    (7, "Senior Cross platform Developer"),
    (8, "iOS Developer"),
    (9, "Associate IOS Developer"),
    (10, "Senior IOS Developer"),
    (11, "Android Developer"),
    (12, "Associate Android Developer"),
    (13, "Senior Android Developer"),
    (14, "Mobile Lead"),
    (15, "Backend Developer"),
    (16, "Associate Backend Developer"),
    (17, "Senior Backend Developer"),
    (18, "Backend Architect"),
    (19, "Devops Engineer"),
    (20, "Associate Devops Engineer"),
    (21, "Senior Devops Engineer"),
    (22, "Devops Lead"),
    (23, "Scrum Master / APM"),
    (24, "Project Manager"),
    (25, "Delivery Manager"),
    (26, "Fullstack Developer"),
    (27, "Associate Fullstack Developer"),
    (28, "Senior Fullstack Developer"),
    (29, "Manual Tester"),
    (30, "Senior Manual Tester"),
    (31, "Automation Tester"),
    (32, "Senior Automation Tester"),
    (33, "QA Lead"),
    (34, "Business Analyst"),
    (35, "Senior Business Analyst"),
    (36, "Data Engineer"),
    (37, "Associate Data Engineer"),
    (38, "Senior Data Engineer"),
    (39, "Data Engineer Lead"),
    (40, "ML Engineer"),
    (41, "Senior ML Engineer"),
    (42, "ML Lead"),
    (43, "Designer"),
    (44, "Associate designer"),
    (45, "Senior Designer"),
    (46, "Design Lead"),
    (47, "HR"),
    (48, "Senior HR"),
    (49, "Associate PM"),
    (50, "Finance"),
    (51, "Senior Finance"),
)

DESIGNATION_ROWS: tuple[tuple[str, str, str], ...] = (
    ("Developer", "B5", "Principal Engineer"),
    ("Quality Assurance", "B5", "QA Lead"),
    ("UI/UX", "B5", "UI/UX Lead"),
    ("Delivery Manager", "B5", "Delivery Manager"),
    ("AI/ML", "B5", "AM Lead"),
    ("Human Resources", "B5", "Senior HR Manager"),
    ("Finance", "B5", "Senior Finance Manage"),
    ("QA", "B6", "Senior QA"),
    ("UI/UX", "B6", "Senior Designer"),
    ("Project Manager", "B6", "Senior PM"),
    ("Business Analyst", "B6", "Business Analyst"),
    ("Account Manager", "B6", "Senior AM"),
    ("Human Resources", "B6", "HR Manager"),
    ("Finance", "B6", "Finance Manager"),
    ("Developer", "B6H", "Sr. Team Lead - Developer Captain"),
    ("Business Analyst", "B6H", "Product Owner - Management Captain"),
    ("Project Manager", "B6H", "Project Manager"),
    ("Developer", "B6L", "Team Lead"),
    ("AI/ML", "B6L", "AI Team Lead"),
    ("DevOps", "B6L", "DevOps Team Lead"),
    ("Developer", "B7H", "Senior Software Engineer"),
    ("AI/ML", "B7H", "Senior AI/ML Engineer"),
    ("DevOps", "B7H", "Senior DevOps Engineer"),
    ("Quality Assurance", "B7H", "Associate QA"),
    ("UI/UX", "B7H", "Associate Designer"),
    ("Project Manager", "B7H", "Project Manager"),
    ("Business Analyst", "B7H", "Associate BA"),
    ("Account Manager", "B7H", "Account Manager"),
    ("Human Resources", "B7H", "HR Generalist II"),
    ("Finance", "B7H", "Finance Associate"),
    ("Developer", "B7L", "Software Engineer"),
    ("AI/ML", "B7L", "AI/ML Engineer"),
    ("DevOps", "B7L", "DevOps Engineer"),
    ("Quality Assurance", "B7L", "Assistant QA"),
    ("UI/UX", "B7L", "Assistant Designer"),
    ("Project Manager", "B7L", "Assistant Project Manager"),
    ("Account Manager", "B7L", "AM Assistant"),
    ("Human Resources", "B7L", "HR Generalist I"),
    ("Developer", "B8 - Intern", "Software Development Intern"),
    ("AI/ML", "B8 - Intern", "AI/ML Engineer Intern"),
    ("DevOps", "B8 - Intern", "DevOps Engineer Intern"),
    ("Quality Assurance", "B8 - Intern", "QA Intern"),
    ("UI/UX", "B8 - Intern", "Designer Intern"),
    ("Project Manager", "B8 - Intern", "Project Management Intern"),
    ("Business Analyst", "B8 - Intern", "BA Intern"),
    ("Account Manager", "B8 - Intern", "AM Intern"),
    ("Human Resources", "B8 - Intern", "HR Intern"),
    ("Finance", "B8 - Intern", "Finance Intern"),
    ("Executive", "B4", "Senior Technical Architect"),
    ("Executive", "B4", "Senior Delivery Manager"),
    ("Executive", "B3", "Directors"),
    ("Executive", "B2", "Vice Presidents"),
    ("Executive", "B1", "CEO"),
    ("Executive", "B1", "CTO"),
    ("Executive", "B1", "COO"),
    ("Executive", "B1", "CBO"),
    ("Executive", "B1", "Managing Director"),
)

KPI_DEFINITION_ROWS: tuple[tuple[str, str, str, str, str], ...] = (
    ("B4", "Developer", "Sr. Architect", "Solution Design Quality (Need to revisit this competency for this role)", "40%"),
    ("B4", "Developer", "Sr. Architect", "Mentorship and Training Impact (Need to revisit this competency for this role)", "20%"),
    ("B4", "Developer", "Sr. Architect", "Innovation and Pre-Sales (Need to revisit this competency for this role)", "20%"),
    ("B4", "Developer", "Sr. Architect", "Cloud and Tech Implementation (Need to revisit this competency for this role)", "20%"),
    ("B5", "Developer", "Principal Engineer / Architect", "Solution DEsign during Pre- sales (p)", "40%"),
    ("B5", "Developer", "Principal Engineer / Architect", "Lead Technial desigm during Project execution (p)", "30%"),
    ("B5", "Developer", "Principal Engineer / Architect", "Anchor inchor technical inciatives (p)", "15%"),
    ("B5", "Developer", "Principal Engineer / Architect", "Customer Satisfaction", "10%"),
    ("B5", "Developer", "Principal Engineer / Architect", "Skill Development of TLs", "5%"),
    ("B6H", "Developer", "Sr. Tech Lead", "Platform / Product Tech Architecure(p)", "40%"),
    ("B6H", "Developer", "Sr. Tech Lead", "Code and Design Quality (p)", "30%"),
    ("B6H", "Developer", "Sr. Tech Lead", "Contributing to Technical discussion with customer (p)", "15%"),
    ("B6H", "Developer", "Sr. Tech Lead", "Contributing to Pre-sales and Discussion with customer", "15%"),
    ("B6L", "Developer", "Tech Lead", "Project Execution", "10%"),
    ("B6L", "Developer", "Tech Lead", "Task Management and Delegation", "10%"),
    ("B6L", "Developer", "Tech Lead", "Code and Design Quality (p)", "40%"),
    ("B6L", "Developer", "Tech Lead", "Guiding the team towards Technical sucesss (p)", "20%"),
    ("B6L", "Developer", "Tech Lead", "Contributing to Technical discussion with customer", "20%"),
    ("B7H", "Developer", "Sr. Software Engineer", "Individual Task Success (p)", "50%"),
    ("B7H", "Developer", "Sr. Software Engineer", "Understanding SDLC Processes  (p)", "10%"),
    ("B7H", "Developer", "Sr. Software Engineer", "Learning Contributions", "10%"),
    ("B7H", "Developer", "Sr. Software Engineer", "Reporting and Documentation (P)", "15%"),
    ("B7H", "Developer", "Sr. Software Engineer", "Guiding Jr. Associates, Interns", "5%"),
    ("B7H", "Developer", "Sr. Software Engineer", "Process Compliance", "5%"),
    ("B7H", "Developer", "Sr. Software Engineer", "Contribution to release", "5%"),
    ("B7L", "Developer", "Software Engineer", "Individual Task Success (p)", "50%"),
    ("B7L", "Developer", "Software Engineer", "Understanding SDLC Processes (p)", "25%"),
    ("B7L", "Developer", "Software Engineer", "Learning Contributions", "10%"),
    ("B7L", "Developer", "Software Engineer", "Reporting and Documentation", "10%"),
    ("B7L", "Developer", "Software Engineer", "Process Compliance", "5%"),
    ("B8", "Developer", "Intern", "Skill Development (p)", "25%"),
    ("B8", "Developer", "Intern", "Task Ownership (p)", "40%"),
    ("B8", "Developer", "Intern", "Collaboration and Communication", "25%"),
    ("B8", "Developer", "Intern", "Cultural Fit and Engagement", "10%"),
    ("B4", "AI/ML", "Sr. Architect", "Solution Design Quality (Need to revisit this competency for this role)", "40%"),
    ("B4", "AI/ML", "Sr. Architect", "Mentorship and Training Impact (Need to revisit this competency for this role)", "20%"),
    ("B4", "AI/ML", "Sr. Architect", "Innovation and Pre-Sales (Need to revisit this competency for this role)", "20%"),
    ("B4", "AI/ML", "Sr. Architect", "Cloud and Tech Implementation (Need to revisit this competency for this role)", "20%"),
    ("B5", "AI/ML", "Principal Engineer / Architect", "Solution DEsign during Pre- sales (p)", "40%"),
    ("B5", "AI/ML", "Principal Engineer / Architect", "Lead Technial desigm during Project execution (p)", "30%"),
    ("B5", "AI/ML", "Principal Engineer / Architect", "Anchor inchor technical inciatives (p)", "15%"),
    ("B5", "AI/ML", "Principal Engineer / Architect", "Customer Satisfaction", "10%"),
    ("B5", "AI/ML", "Principal Engineer / Architect", "Skill Development of TLs", "5%"),
    ("B6H", "AI/ML", "Sr. AI Team Lead", "Platform / Product Tech Architecure(p)", "40%"),
    ("B6H", "AI/ML", "Sr. AI Team Lead", "Code and Design Quality (p)", "30%"),
    ("B6H", "AI/ML", "Sr. AI Team Lead", "Contributing to Technical discussion with customer (p)", "15%"),
    ("B6H", "AI/ML", "Sr. AI Team Lead", "Contributing to Pre-sales and Discussion with customer", "15%"),
    ("B6L", "AI/ML", "AI Team Lead", "Project Execution", "10%"),
    ("B6L", "AI/ML", "AI Team Lead", "Task Management and Delegation", "10%"),
    ("B6L", "AI/ML", "AI Team Lead", "Code and Design Quality (p)", "40%"),
    ("B6L", "AI/ML", "AI Team Lead", "Guiding the team towards Technical sucesss (p)", "20%"),
    ("B6L", "AI/ML", "AI Team Lead", "Contributing to Technical discussion with customer", "20%"),
    ("B7H", "AI/ML", "Sr. AI/ML Engineer", "Individual Task Success (p)", "50%"),
    ("B7H", "AI/ML", "Sr. AI/ML Engineer", "Understanding SDLC Processes  (p)", "10%"),
    ("B7H", "AI/ML", "Sr. AI/ML Engineer", "Learning Contributions", "10%"),
    ("B7H", "AI/ML", "Sr. AI/ML Engineer", "Reporting and Documentation (P)", "15%"),
    ("B7H", "AI/ML", "Sr. AI/ML Engineer", "Guiding Jr. Associates, Interns", "5%"),
    ("B7H", "AI/ML", "Sr. AI/ML Engineer", "Process Compliance", "5%"),
    ("B7H", "AI/ML", "Sr. AI/ML Engineer", "Contribution to release", "5%"),
    ("B7L", "AI/ML", "AI/ML Engineer", "Individual Task Success (p)", "50%"),
    ("B7L", "AI/ML", "AI/ML Engineer", "Understanding SDLC Processes (p)", "25%"),
    ("B7L", "AI/ML", "AI/ML Engineer", "Learning Contributions", "10%"),
    ("B7L", "AI/ML", "AI/ML Engineer", "Reporting and Documentation", "10%"),
    ("B7L", "AI/ML", "AI/ML Engineer", "Process Compliance", "5%"),
    ("B8", "AI/ML", "AI/ML Intern", "Skill Development (p)", "25%"),
    ("B8", "AI/ML", "AI/ML Intern", "Task Ownership (p)", "40%"),
    ("B8", "AI/ML", "AI/ML Intern", "Collaboration and Communication", "25%"),
    ("B8", "AI/ML", "AI/ML Intern", "Cultural Fit and Engagement", "10%"),
    ("B8", "Business Analyst", "BA Intern", "Documentation Accuracy", "35%"),
    ("B8", "Business Analyst", "BA Intern", "Learning Velocity", "25%"),
    ("B8", "Business Analyst", "BA Intern", "Responsiveness", "20%"),
    ("B8", "Business Analyst", "BA Intern", "Process Adherence", "10%"),
    ("B8", "Business Analyst", "BA Intern", "Collaboration", "10%"),
    ("B7", "Business Analyst", "Jr. Business Analyst", "Requirement Clarity", "35%"),
    ("B7", "Business Analyst", "Jr. Business Analyst", "UAT Effectiveness", "25%"),
    ("B7", "Business Analyst", "Jr. Business Analyst", "Stakeholder Satisfaction", "20%"),
    ("B7", "Business Analyst", "Jr. Business Analyst", "Rework Reduction", "10%"),
    ("B7", "Business Analyst", "Jr. Business Analyst", "Ownership", "10%"),
    ("B6", "Business Analyst", "Business Analyst", "Scope Stability", "30%"),
    ("B6", "Business Analyst", "Business Analyst", "Requirement Completeness", "25%"),
    ("B6", "Business Analyst", "Business Analyst", "Delivery Readiness", "20%"),
    ("B6", "Business Analyst", "Business Analyst", "Change Management", "15%"),
    ("B6", "Business Analyst", "Business Analyst", "Solution Thinking", "10%"),
    ("B5", "Business Analyst", "Sr. Business Analyst", "Problem Definition", "30%"),
    ("B5", "Business Analyst", "Sr. Business Analyst", "Solution Effectiveness", "25%"),
    ("B5", "Business Analyst", "Sr. Business Analyst", "Client Trust", "20%"),
    ("B5", "Business Analyst", "Sr. Business Analyst", "Mentorship", "15%"),
    ("B5", "Business Analyst", "Sr. Business Analyst", "Delivery Alignment", "10%"),
    ("B4", "Business Analyst", "Lead Business Analyst", "Program Predictability", "30%"),
    ("B4", "Business Analyst", "Lead Business Analyst", "Cross-Team Alignment", "25%"),
    ("B4", "Business Analyst", "Lead Business Analyst", "Team Performance", "20%"),
    ("B4", "Business Analyst", "Lead Business Analyst", "Client Outcomes", "15%"),
    ("B4", "Business Analyst", "Lead Business Analyst", "Presales Support", "10%"),
    ("B5", "UI/UX", "Design Lead", "Team Management & Design Quality", "20%"),
    ("B5", "UI/UX", "Design Lead", "Strategic Alignment", "20%"),
    ("B5", "UI/UX", "Design Lead", "Process Efficiency", "20%"),
    ("B5", "UI/UX", "Design Lead", "Stakeholder Management", "15%"),
    ("B5", "UI/UX", "Design Lead", "Design Reviews & Direction", "15%"),
    ("B5", "UI/UX", "Design Lead", "Contribution to Presales", "10%"),
    ("B6", "UI/UX", "Sr. UI/UX Designer", "End-to-End Ownership", "25%"),
    ("B6", "UI/UX", "Sr. UI/UX Designer", "Client Communication", "15%"),
    ("B6", "UI/UX", "Sr. UI/UX Designer", "Mentorship & Team Support", "15%"),
    ("B6", "UI/UX", "Sr. UI/UX Designer", "Cross-Functional Collaboration", "20%"),
    ("B6", "UI/UX", "Sr. UI/UX Designer", "Design Impact (First-Pass Acceptance)", "25%"),
    ("B7H", "UI/UX", "UI/UX Designer", "Execution of User Stories", "20%"),
    ("B7H", "UI/UX", "UI/UX Designer", "Business Context Understanding", "25%"),
    ("B7H", "UI/UX", "UI/UX Designer", "Design Iteration Efficiency", "15%"),
    ("B7H", "UI/UX", "UI/UX Designer", "Developer Handoff Quality", "10%"),
    ("B7H", "UI/UX", "UI/UX Designer", "Speed vs Quality Balance", "30%"),
    ("B7L", "UI/UX", "Associate UI/UX Designer", "Execution of UI Tasks & Requirements Understanding", "25%"),
    ("B7L", "UI/UX", "Associate UI/UX Designer", "Design System Usage & Consistency", "25%"),
    ("B7L", "UI/UX", "Associate UI/UX Designer", "Feedback Incorporation & Iteration Speed", "20%"),
    ("B7L", "UI/UX", "Associate UI/UX Designer", "Figma File Hygiene & Handoff Readiness", "15%"),
    ("B7L", "UI/UX", "Associate UI/UX Designer", "Collaboration & Requirement Clarification", "15%"),
    ("B8", "UI/UX", "UI/UX Designer Intern", "Task Completion Rate", "25%"),
    ("B8", "UI/UX", "UI/UX Designer Intern", "Adherence to Design System", "30%"),
    ("B8", "UI/UX", "UI/UX Designer Intern", "Feedback Incorporation", "25%"),
    ("B8", "UI/UX", "UI/UX Designer Intern", "Collaboration & Communication", "20%"),
    ("B6H", "DevOps", "Sr. DevOps Lead", "Infrastructure & Platform Architecture (p)", "40%"),
    ("B6H", "DevOps", "Sr. DevOps Lead", "Infrastructure Quality, Reliability & Automation Standards (p)", "30%"),
    ("B6H", "DevOps", "Sr. DevOps Lead", "Technical Discussions With Customer (p)", "15%"),
    ("B6H", "DevOps", "Sr. DevOps Lead", "Contributing to Pre-sales & Client Solutioning", "15%"),
    ("B6L", "DevOps", "DevOps Lead", "DevOps Project Execution", "10%"),
    ("B6L", "DevOps", "DevOps Lead", "Task Management & Delegation", "10%"),
    ("B6L", "DevOps", "DevOps Lead", "Infrastructure Quality & Automation Standards (p)", "40%"),
    ("B6L", "DevOps", "DevOps Lead", "Guiding Team Toward Technical Success (p)", "20%"),
    ("B6L", "DevOps", "DevOps Lead", "Contributing to Technical Discussions With Customer", "20%"),
    ("B7H", "DevOps", "Sr. DevOps Engineer", "Understanding DevOps & SDLC Processes (p)", "10%"),
    ("B7H", "DevOps", "Sr. DevOps Engineer", "Learning Contributions", "10%"),
    ("B7H", "DevOps", "Sr. DevOps Engineer", "Reporting & Documentation (p)", "15%"),
    ("B7H", "DevOps", "Sr. DevOps Engineer", "Guiding Jr. Associates / Interns", "5%"),
    ("B7H", "DevOps", "Sr. DevOps Engineer", "Process Compliance", "5%"),
    ("B7H", "DevOps", "Sr. DevOps Engineer", "Contribution to Releases", "5%"),
    ("B7L", "DevOps", "DevOps Engineer", "Infrastructure & Task Success (p)", "50%"),
    ("B7L", "DevOps", "DevOps Engineer", "Understanding DevOps & SDLC Processes (p)", "25%"),
    ("B7L", "DevOps", "DevOps Engineer", "Learning Contributions", "10%"),
    ("B7L", "DevOps", "DevOps Engineer", "Reporting & Documentation", "10%"),
    ("B7L", "DevOps", "DevOps Engineer", "Process Compliance", "5%"),
    ("B8", "DevOps", "DevOps Engineer Intern", "Skill Development (p)", "25%"),
    ("B8", "DevOps", "DevOps Engineer Intern", "Task Ownership (p)", "40%"),
    ("B8", "DevOps", "DevOps Engineer Intern", "Collaboration & Communication", "25%"),
    ("B8", "DevOps", "DevOps Engineer Intern", "Cultural Fit & Engagement", "10%"),
    ("B5", "Finance", "Senior Finance Manager", "Strategic Financial Planning & Forecasting", "20%"),
    ("B5", "Finance", "Senior Finance Manager", "Cash Flow & Liquidity Management", "20%"),
    ("B5", "Finance", "Senior Finance Manager", "Profitability & Margin Governance", "20%"),
    ("B5", "Finance", "Senior Finance Manager", "Financial Controls, Audit & Compliance Oversight", "15%"),
    ("B5", "Finance", "Senior Finance Manager", "Finance Process Improvement & Automation", "10%"),
    ("B5", "Finance", "Senior Finance Manager", "Team Leadership & Stakeholder Communication", "15%"),
    ("B6", "Finance", "Finance Manager", "Revenue Collection Efficiency", "10%"),
    ("B6", "Finance", "Finance Manager", "Financial Planning and Utilization", "20%"),
    ("B6", "Finance", "Finance Manager", "Accuracy of Financial Reports", "30%"),
    ("B6", "Finance", "Finance Manager", "Payroll & Invoice Processing Timeliness", "20%"),
    ("B6", "Finance", "Finance Manager", "Compliance Coordination", "10%"),
    ("B6", "Finance", "Finance Manager", "Expense Variance Management", "10%"),
    ("B7", "Finance", "Finance Associate", "Accounts Receivable & Payable Processing", "25%"),
    ("B7", "Finance", "Finance Associate", "Bank & Ledger Reconciliations", "20%"),
    ("B7", "Finance", "Finance Associate", "Support in Financial Reporting & Closures", "20%"),
    ("B7", "Finance", "Finance Associate", "Compliance & Documentation Support", "15%"),
    ("B7", "Finance", "Finance Associate", "Timeliness, Communication & Attention to Detail", "20%"),
    ("B8", "Finance", "Finance Intern", "Zoho Tasks & Financial Data Management", "40%"),
    ("B8", "Finance", "Finance Intern", "Support in Compliance & Banking Procedures", "15%"),
    ("B8", "Finance", "Finance Intern", "Monthly Financial Closures & Reporting", "20%"),
    ("B8", "Finance", "Finance Intern", "Timeliness & Communication", "5%"),
    ("B8", "Finance", "Finance Intern", "Proactivity & Initiative", "10%"),
    ("B8", "Finance", "Finance Intern", "GST Invoice Coordination", "10%"),
    ("B7L", "Project Manager", "Associate PM1", "Execution: Task & Milestone Tracking Accuracy", "20%"),
    ("B7L", "Project Manager", "Associate PM1", "Schedule: On-time Task Completion", "20%"),
    ("B7L", "Project Manager", "Associate PM1", "Quality: Defect Leakage / Rework Due to Misses", "15%"),
    ("B7L", "Project Manager", "Associate PM1", "Communication: Internal Communication Effectiveness", "15%"),
    ("B7L", "Project Manager", "Associate PM1", "Process: Process & Documentation Compliance", "15%"),
    ("B7L", "Project Manager", "Associate PM1", "Learning: Skill Development & Ownership", "15%"),
    ("B7H", "Project Manager", "Associate PM2", "Delivery: On-time Delivery", "30%"),
    ("B7H", "Project Manager", "Associate PM2", "Quality: Defect Leakage & Rework", "20%"),
    ("B7H", "Project Manager", "Associate PM2", "Communication: Client Communication Effectiveness", "15%"),
    ("B7H", "Project Manager", "Associate PM2", "Team Execution: Team Productivity", "15%"),
    ("B7H", "Project Manager", "Associate PM2", "Risk Management: Risk Identification & Mitigation", "15%"),
    ("B7H", "Project Manager", "Associate PM2", "Process: PM Best Practices Adoption", "15%"),
    ("B6L", "Project Manager", "Project Manager", "Delivery: On-time & On-budget Delivery", "25%"),
    ("B6L", "Project Manager", "Project Manager", "Quality: Quality & Stability", "20%"),
    ("B6L", "Project Manager", "Project Manager", "Client Management: Client Satisfaction (CSAT)", "20%"),
    ("B6L", "Project Manager", "Project Manager", "Leadership: Team Engagement & Retention", "15%"),
    ("B6L", "Project Manager", "Project Manager", "Risk & Escalation: Escalation Management", "10%"),
    ("B6L", "Project Manager", "Project Manager", "People Development: Mentoring & Coaching (monthly one on ones)", "10%"),
    ("B6H", "Project Manager", "Sr. Project Manager", "Portfolio Delivery: Multi-project Delivery Health", "25%"),
    ("B6H", "Project Manager", "Sr. Project Manager", "Stakeholder Trust: Client & Stakeholder Satisfaction", "20%"),
    ("B6H", "Project Manager", "Sr. Project Manager", "Delivery Predictability: Estimation & Forecast Accuracy", "15%"),
    ("B6H", "Project Manager", "Sr. Project Manager", "Leadership: Leadership Pipeline & Retention", "15%"),
    ("B6H", "Project Manager", "Sr. Project Manager", "Financial: Margin & Cost Efficiency", "10%"),
    ("B6H", "Project Manager", "Sr. Project Manager", "People Development: Mentoring & Coaching (monthly one on ones)", "5%"),
    ("B6H", "Project Manager", "Sr. Project Manager", "Org Contribution: Capability & Process Building", "10%"),
    ("B6H", "Quality Assurance", "QA Lead", "Test Strategy & Release Planning", "20%"),
    ("B6H", "Quality Assurance", "QA Lead", "Team Productivity & Execution Throughput", "20%"),
    ("B6H", "Quality Assurance", "QA Lead", "Release Quality Metrics (Defect Leakage, Severity Accuracy)", "20%"),
    ("B6H", "Quality Assurance", "QA Lead", "Stakeholder Communication & Release Readiness", "15%"),
    ("B6H", "Quality Assurance", "QA Lead", "Process Improvement & QA Best Practices", "15%"),
    ("B6H", "Quality Assurance", "QA Lead", "People Leadership & Mentoring", "10%"),
    ("B6L", "Quality Assurance", "Senior QA", "Business-Aligned Test Scenario Design", "30%"),
    ("B6L", "Quality Assurance", "Senior QA", "Release Quality Metrics (Leakage, Reopen Rate, Blockers)", "25%"),
    ("B6L", "Quality Assurance", "Senior QA", "Impactful Automation", "20%"),
    ("B6L", "Quality Assurance", "Senior QA", "Cross-Team Quality Leadership", "15%"),
    ("B6L", "Quality Assurance", "Senior QA", "Execution Ownership & Accountability", "10%"),
    ("B7H", "Quality Assurance", "Quality Analyst", "Test Coverage & Prioritization", "30%"),
    ("B7H", "Quality Assurance", "Quality Analyst", "Severity Accuracy & Bug Impact Analysis", "20%"),
    ("B7H", "Quality Assurance", "Quality Analyst", "Release Readiness Contribution", "20%"),
    ("B7H", "Quality Assurance", "Quality Analyst", "Business Flow Understanding", "20%"),
    ("B7H", "Quality Assurance", "Quality Analyst", "Cross-Team Collaboration", "10%"),
    ("B7L", "Quality Assurance", "Associate QA", "Test Case Execution & Reliability", "35%"),
    ("B7L", "Quality Assurance", "Associate QA", "Basic Test Case Writing", "20%"),
    ("B7L", "Quality Assurance", "Associate QA", "Bug Reporting Quality", "20%"),
    ("B7L", "Quality Assurance", "Associate QA", "Understanding of Functionality & Basics of Business Impact", "15%"),
    ("B7L", "Quality Assurance", "Associate QA", "Communication & Responsiveness", "10%"),
    ("B8", "Quality Assurance", "Intern QA", "Test Case Execution Rate", "30%"),
    ("B8", "Quality Assurance", "Intern QA", "Bug Reporting Accuracy", "25%"),
    ("B8", "Quality Assurance", "Intern QA", "Basic Feature Understanding", "25%"),
    ("B8", "Quality Assurance", "Intern QA", "Team Communication", "20%"),
    ("B1", "Executive", "Chief Executive Officer (CEO)", "Strategic Goal Achievement", "50%"),
    ("B1", "Executive", "Chief Executive Officer (CEO)", "Financial Performance", "25%"),
    ("B1", "Executive", "Chief Executive Officer (CEO)", "Leadership Effectiveness", "15%"),
    ("B1", "Executive", "Chief Executive Officer (CEO)", "Stakeholder Engagement", "10%"),
    ("B1", "Executive", "Chief Technology Officer (CTO)", "Technology Strategy Alignment", "40%"),
    ("B1", "Executive", "Chief Technology Officer (CTO)", "Innovation and R&D", "25%"),
    ("B1", "Executive", "Chief Technology Officer (CTO)", "IT Infrastructure Reliability", "20%"),
    ("B1", "Executive", "Chief Technology Officer (CTO)", "Budget Management", "15%"),
    ("B1", "Executive", "Chief Financial Officer (CFO)", "Financial Performance", "40%"),
    ("B1", "Executive", "Chief Financial Officer (CFO)", "Budget Accuracy", "25%"),
    ("B1", "Executive", "Chief Financial Officer (CFO)", "Risk Management", "20%"),
    ("B1", "Executive", "Chief Financial Officer (CFO)", "Investor Relations", "15%"),
    ("B1", "Executive", "Chief Delivery Officer (CDO)", "Project Delivery & Timeliness", "40%"),
    ("B1", "Executive", "Chief Delivery Officer (CDO)", "Budget & Cost Management", "25%"),
    ("B1", "Executive", "Chief Delivery Officer (CDO)", "Quality & Stakeholder Satisfaction", "20%"),
    ("B1", "Executive", "Chief Delivery Officer (CDO)", "Profit & Revenue Panning (Cost Variance (CV))", "10%"),
    ("B1", "Executive", "Chief Delivery Officer (CDO)", "Rework Percentage", "5%"),
    ("B1", "Executive", "Chief Operations Officer (COO)", "Operational Efficiency", "40%"),
    ("B1", "Executive", "Chief Operations Officer (COO)", "Employee & Workforce Management", "25%"),
    ("B1", "Executive", "Chief Operations Officer (COO)", "Customer Satisfaction", "20%"),
    ("B1", "Executive", "Chief Operations Officer (COO)", "NPS (Net Promoter Score)", "15%"),
    ("B2", "Executive", "Vice Presidents", "Business Unit Revenue and Profitability", "40%"),
    ("B2", "Executive", "Chief Operations Officer (COO)", "Operational Efficiency", "30%"),
    ("B2", "Executive", "Chief Operations Officer (COO)", "Employee Development and Retention", "20%"),
    ("B2", "Executive", "Chief Operations Officer (COO)", "Cross-Functional Collaboration", "10%"),
    ("B3", "Executive", "Director- Delivery", "Business Unit Profitability (Revenue & Margin) (p)", "40%"),
    ("B3", "Executive", "Director- Delivery", "Operational Excellence (p)", "30%"),
    ("B3", "Executive", "Director- Delivery", "Team Development (p)", "20%"),
    ("B3", "Executive", "Director- Delivery", "Cross-Department Collaboration", "10%"),
    ("B3", "Executive", "Director- Sales/ Account management", "Revenue (P)", "50%"),
    ("B3", "Executive", "Director- Sales/ Account management", "Margin (P)", "20%"),
    ("B3", "Executive", "Director- Sales/ Account management", "Customer Satisfaction (p)", "15%"),
    ("B3", "Executive", "Director- Sales/ Account management", "Reviewing Attrition Ratios", "15%"),
    ("B3", "Executive", "Director- Tech", "Leadership Impact (Need to revisit this competency for this role)", "30%"),
    ("B3", "Executive", "Director- Tech", "Quality Metrics  (Need to revisit this competency for this role)", "20%"),
    ("B3", "Executive", "Director- Tech", "Cross-Functional Contributions  (Need to revisit this competency for this role)", "10%"),
    ("B3", "Executive", "Director- Tech", "Engineering Roadmap Delivery  (Need to revisit this competency for this role)", "40%"),
    ("B4", "Executive", "Sr Delivery Manager", "Revenue", "20%"),
    ("B4", "Executive", "Sr Delivery Manager", "Margin", "40%"),
    ("B4", "Executive", "Sr Delivery Manager", "Customer Satisfaction", "15%"),
    ("B4", "Executive", "Sr Delivery Manager", "Employee Attrition & employee growth", "15%"),
    ("B4", "Executive", "Sr Delivery Manager", "Process success", "10%"),
    ("B4", "Executive", "Senior Technical Architect - Tech Wizard", "Solution Design Quality (Need to revisit this competency for this role)", "40%"),
    ("B4", "Executive", "Senior Technical Architect - Tech Wizard", "Mentorship and Training Impact (Need to revisit this competency for this role)", "20%"),
    ("B4", "Executive", "Senior Technical Architect - Tech Wizard", "Innovation and Pre-Sales (Need to revisit this competency for this role)", "20%"),
    ("B4", "Executive", "Senior Technical Architect - Tech Wizard", "Cloud and Tech Implementation (Need to revisit this competency for this role)", "20%"),
)

# Each row: (evaluation_criteria, title) — category name, then the line item shown as title.
WEBKNOT_VALUE_ROWS: tuple[tuple[str, str], ...] = (
    ("Extreme Ownership", "Owns tasks end-to-end without pushing blame"),
    ("Extreme Ownership", "Flags risks early and proposes solutions"),
    ("Extreme Ownership", "Takes accountability for mistakes and corrective actions"),
    ("Extreme Ownership", "Follows through on commitments consistently"),
    ("Extreme Ownership", "Steps in beyond role boundaries when needed"),
    ("Radical Honesty", "Communicates status accurately (no sugar-coating)"),
    ("Radical Honesty", "Raises concerns and disagreements respectfully"),
    ("Radical Honesty", "Shares bad news early with facts"),
    ("Radical Honesty", "Provides constructive feedback to peers and leaders"),
    ("Radical Honesty", "Avoids political or misleading communication"),
    ("Deliver Customer Delight", "Understands customer needs and priorities"),
    ("Deliver Customer Delight", "Delivers quality work with minimal rework"),
    ("Deliver Customer Delight", "Responds promptly to customer queries/issues"),
    ("Deliver Customer Delight", "Takes extra effort to improve customer experience"),
    ("Deliver Customer Delight", "Receives positive feedback from customers or stakeholders"),
    ("Learn and Share", "Actively learns new skills relevant to the role"),
    ("Learn and Share", "Applies learning to improve work outcomes"),
    ("Learn and Share", "Shares knowledge via sessions, docs, mentoring"),
    ("Learn and Share", "Encourages learning culture within the team"),
    ("Learn and Share", "Seeks and acts on feedback"),
    ("Community Participation", "Participates in organisational initiatives"),
    ("Community Participation", "Supports hiring, onboarding, or culture activities"),
    ("Community Participation", "Contributes to internal communities or forums"),
    ("Community Participation", "Represents organisation positively externally"),
    ("Community Participation", "Volunteers for CSR or knowledge initiatives"),
)


def _parse_weightage(weightage: str) -> Decimal:
    cleaned = weightage.strip()
    if cleaned.endswith("%"):
        cleaned = cleaned[:-1]
    return Decimal(cleaned)

async def _seed_allocation_roles(database: Database) -> None:
    async with database.tx() as session:
        total_existing = await session.scalar(select(func.count()).select_from(AllocationRole))
        if int(total_existing or 0) > 0:
            return

        role_ids = [role_id for role_id, _ in ALLOCATION_ROLE_ROWS]
        existing_rows = (
            await session.scalars(select(AllocationRole).where(AllocationRole.id.in_(role_ids)))
        ).all()
        existing_by_id = {row.id: row for row in existing_rows}
        for role_id, role_name in ALLOCATION_ROLE_ROWS:
            existing = existing_by_id.get(role_id)
            if existing is None:
                session.add(AllocationRole(id=role_id, name=role_name))
            elif existing.name != role_name:
                existing.name = role_name


async def _seed_designations(database: Database) -> None:
    now = datetime.now(UTC)
    band_names = sorted({band_name for _, band_name, _ in DESIGNATION_ROWS})
    normalized_band_names = {name.lower() for name in band_names}
    async with database.tx() as session:
        total_existing_designations = await session.scalar(select(func.count()).select_from(Designation))
        if int(total_existing_designations or 0) > 0:
            return

        sequence_name = await session.scalar(text("SELECT pg_get_serial_sequence('bands', 'id')"))
        max_band_id = await session.scalar(select(func.max(Band.id)))
        if sequence_name:
            if max_band_id is not None:
                await session.execute(
                    text(f"SELECT setval('{sequence_name}', :set_to, true)"),
                    {"set_to": int(max_band_id)},
                )
        existing_bands = (
            await session.scalars(select(Band).where(func.lower(Band.name).in_(normalized_band_names)))
        ).all()
        bands_by_name = {band.name.lower(): band for band in existing_bands}

        for band_name in band_names:
            if band_name.lower() in bands_by_name:
                continue
            created = Band(name=band_name)
            session.add(created)
            await session.flush()
            bands_by_name[band_name.lower()] = created

        band_ids = [band.id for band in bands_by_name.values()]
        existing_designations = (
            await session.scalars(select(Designation).where(Designation.band_id.in_(band_ids)))
        ).all()
        existing_keys = {
            (
                int(designation.band_id),
                (designation.department or "").strip().lower(),
                (designation.name or "").strip().lower(),
            )
            for designation in existing_designations
            if designation.band_id is not None
        }

        for stream, band_name, designation_name in DESIGNATION_ROWS:
            band = bands_by_name.get(band_name.lower())
            if not band:
                continue
            key = (band.id, stream.strip().lower(), designation_name.strip().lower())
            if key in existing_keys:
                continue
            session.add(
                Designation(
                    name=designation_name,
                    band_id=band.id,
                    department=stream,
                    created_at=now,
                    updated_at=now,
                )
            )
            existing_keys.add(key)


async def _ensure_bands(database: Database, band_names: set[str]) -> None:
    normalized = {name.lower() for name in band_names}
    async with database.tx() as session:
        existing = (
            await session.scalars(select(Band).where(func.lower(Band.name).in_(normalized)))
        ).all()
        bands_by_name = {band.name.lower(): band for band in existing}
        for band_name in sorted(band_names):
            if band_name.lower() in bands_by_name:
                continue
            created = Band(name=band_name)
            session.add(created)
            await session.flush()
            bands_by_name[band_name.lower()] = created


async def _seed_kpi_definitions(database: Database) -> None:
    now = datetime.now(UTC)
    async with database.tx() as session:
        total_existing = await session.scalar(select(func.count()).select_from(KpiDefinition))
        if int(total_existing or 0) > 0:
            return

    await _ensure_bands(database, {band for band, _, _, _, _ in KPI_DEFINITION_ROWS})

    async with database.tx() as session:
        bands = (await session.scalars(select(Band))).all()
        bands_by_name = {band.name.strip().lower(): band for band in bands}
        for band_name, department, designation, kpi_name, weightage in KPI_DEFINITION_ROWS:
            band = bands_by_name.get(band_name.strip().lower())
            if not band:
                continue
            session.add(
                KpiDefinition(
                    band_id=band.id,
                    department=department,
                    designation=designation,
                    kpi_name=kpi_name,
                    weightage=_parse_weightage(weightage),
                    active=True,
                    created_at=now,
                    updated_at=now,
                )
            )


async def _seed_webknot_values(database: Database) -> None:
    now = datetime.now(UTC)
    async with database.tx() as session:
        total_existing = await session.scalar(select(func.count()).select_from(WebknotValue))
        if int(total_existing or 0) > 0:
            return

        for evaluation_criteria, title in WEBKNOT_VALUE_ROWS:
            session.add(
                WebknotValue(
                    title=title,
                    evaluation_criteria=evaluation_criteria,
                    active=True,
                    created_at=now,
                    updated_at=now,
                )
            )


async def seed_master_data(database: Database = db) -> None:
    await _seed_allocation_roles(database)
    await _seed_designations(database)
    await _seed_kpi_definitions(database)
    await _seed_webknot_values(database)


async def run_db_insert() -> None:
    await db.connect()
    async with db.engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await seed_master_data(db)
    await db.disconnect()


if __name__ == "__main__":
    asyncio.run(run_db_insert())
