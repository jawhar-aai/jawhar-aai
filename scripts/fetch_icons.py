#!/usr/bin/env python3
"""Fetch monochrome logo paths for the technology badges into scripts/icons.json.

Sources, tried in order for each badge:
  Simple Icons (CC0-1.0)  https://simpleicons.org
  Devicon "plain" set (MIT) https://devicon.dev
Only the viewBox and path data are kept; colours, scripts and other markup are dropped.
Run once when the badge list changes:  python3 scripts/fetch_icons.py
"""
import json
import os
import re
import urllib.request

SIMPLE = "https://cdn.jsdelivr.net/npm/simple-icons@16.33.0/icons/{}.svg"
DEVICON = "https://cdn.jsdelivr.net/npm/devicon@2.17.0/icons/{0}/{0}-{1}.svg"

# badge label -> list of candidates: ("si", slug) or ("dev", name, variant)
ICONS = {
    "Python": [("si", "python")], "TypeScript": [("si", "typescript")], "JavaScript": [("si", "javascript")],
    "Bash": [("si", "gnubash")], "HTML/CSS": [("si", "html5")],
    "React": [("si", "react")], "Next.js": [("si", "nextdotjs")], "Redux Toolkit": [("si", "redux")],
    "Tailwind CSS": [("si", "tailwindcss")], "Vite": [("si", "vite")],
    "FastAPI": [("si", "fastapi")], "NestJS": [("si", "nestjs")], "Node.js": [("si", "nodedotjs")],
    "Express": [("si", "express")], "Pydantic": [("si", "pydantic")],
    "PostgreSQL": [("si", "postgresql")], "SQL Server": [("dev", "microsoftsqlserver", "plain")],
    "MongoDB": [("si", "mongodb")], "Redis": [("si", "redis")], "Kafka": [("si", "apachekafka")],
    "OpenAI": [("si", "openai")], "Azure OpenAI": [("dev", "azure", "plain")],
    "MLflow": [("si", "mlflow")], "Pandas": [("si", "pandas")], "NumPy": [("si", "numpy")],
    "Kubernetes": [("si", "kubernetes")], "Docker": [("si", "docker")], "Helm": [("si", "helm")],
    "Argo CD": [("si", "argo")], "Azure": [("dev", "azure", "plain")],
    "Azure DevOps": [("dev", "azuredevops", "plain")], "AWS S3": [("si", "amazons3"), ("dev", "amazonwebservices", "plain-wordmark")],
    "SQLAlchemy": [("si", "sqlalchemy"), ("dev", "sqlalchemy", "plain")], "RabbitMQ": [("si", "rabbitmq")],
    "Qdrant": [("si", "qdrant")], "Azure AI Search": [("dev", "azure", "plain")],
    "Socket.IO": [("si", "socketdotio")], "Firebase": [("si", "firebase")], "Nginx": [("si", "nginx")],
    "Git": [("si", "git")], "Poetry": [("si", "poetry")],
    "Flowbite": [("si", "flowbite")], "Bootstrap": [("si", "bootstrap")], "Lucide": [("si", "lucide")],
    "Formik": [("si", "formik")],
    "JWT": [("si", "jsonwebtokens")], "Keycloak": [("si", "keycloak")], "Azure AD": [("dev", "azure", "plain")],
    "OpenTelemetry": [("si", "opentelemetry")], "Prometheus": [("si", "prometheus")],
    "Pytest": [("si", "pytest")], "Jest": [("si", "jest")],
    "Stripe": [("si", "stripe")], "Razorpay": [("si", "razorpay")],
    "LinkedIn": [("dev", "linkedin", "plain")], "LeetCode": [("si", "leetcode")],
}

PATH_D = re.compile(r'<path[^>]*?\sd="([^"]+)"', re.S)
VIEWBOX = re.compile(r'viewBox="([0-9.\s-]+)"')
SAFE_D = re.compile(r"^[0-9a-zA-Z.,\s+-]+$")


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "profile-icons"})
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            return resp.read(200_000).decode("utf-8", "replace")
    except Exception:
        return None


def extract(svg):
    if not svg:
        return None
    vb = VIEWBOX.search(svg)
    paths = [d for d in PATH_D.findall(svg) if SAFE_D.match(d)]
    if not vb or not paths or "transform" in svg:
        return None  # skip icons whose geometry depends on transforms
    return {"viewBox": " ".join(vb.group(1).split()), "paths": paths}


def main():
    out, missing = {}, []
    for label, candidates in ICONS.items():
        icon = None
        for cand in candidates:
            url = SIMPLE.format(cand[1]) if cand[0] == "si" else DEVICON.format(cand[1], cand[2])
            icon = extract(fetch(url))
            if icon:
                icon["source"] = url
                break
        if icon:
            out[label] = icon
        else:
            missing.append(label)
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "icons.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1, sort_keys=True)
    print(f"icons: {len(out)} found, missing: {missing}")


if __name__ == "__main__":
    main()
