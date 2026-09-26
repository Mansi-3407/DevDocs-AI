# DevDocs AI — Intelligent Documentation Ecosystem

> An AI-powered documentation ecosystem that keeps software documentation synchronized with code changes.

## Overview

**DevDocs AI** is an intelligent documentation automation system designed to reduce the gap between a constantly changing codebase and documentation that quickly becomes outdated.

Instead of manually updating README files, API documentation, tutorials, changelogs, and code examples after every code change, DevDocs AI analyzes repository changes and coordinates specialized documentation agents to identify and update the affected documentation.

The system combines **AI agents, code analysis, documentation validation, and IBM Bob 2.0's agentic capabilities** into a unified developer workflow.

---

## Problem

Software documentation frequently becomes outdated as projects evolve.

Developers may forget to:

* Update installation instructions
* Document newly added features
* Synchronize API documentation
* Update code examples
* Maintain changelogs
* Update migration instructions
* Fix broken documentation links
* Remove outdated information

This creates a gap between the actual codebase and the documentation developers depend on.

---

## Solution

DevDocs AI continuously analyzes code changes and determines which documentation needs attention.

Specialized agents handle different documentation tasks while a central orchestrator coordinates their execution.

### Core Workflow

```text
                 Code Changes
                      │
                      ▼
              Change Detection
                      │
                      ▼
              Main Coordinator
                      │
        ┌─────────────┼─────────────┐
        ▼             ▼             ▼
   README Agent    API Agent    Tutorial Agent
        │             │             │
        └─────────────┼─────────────┘
                      ▼
              Changelog Agent
                      │
                      ▼
               Documentation
                  Auditor
                      │
                      ▼
              Final Documentation
```

---

## Core Features

### 1. README Auto-Updater

Automatically identifies documentation affected by code changes.

Capabilities include:

* Updating project/version information
* Detecting new features
* Updating installation instructions
* Synchronizing API usage examples
* Identifying outdated README sections

---

### 2. API Documentation Generator

Analyzes API endpoints and generates structured API documentation.

Planned capabilities include:

* API endpoint detection
* Parameter extraction
* Request/response information
* OpenAPI/Swagger specification generation
* API usage examples

---

### 3. Code-to-Tutorial Generator

Converts significant code changes into developer-friendly documentation.

It can generate:

* Feature tutorials
* Step-by-step usage guides
* Code examples
* Troubleshooting sections
* Migration guides for breaking changes

---

### 4. Documentation Quality Auditor

Reviews documentation against the current codebase.

It can detect:

* Broken links
* Outdated documentation
* Version inconsistencies
* Missing documentation
* Invalid or outdated code examples
* Documentation/code inconsistencies

The auditor reports issues before changes are automatically applied.

---

### 5. Changelog & Migration Generator

Analyzes repository changes and organizes them into meaningful release documentation.

It can identify:

* New features
* Bug fixes
* Breaking changes
* Version changes
* Migration requirements

---

## IBM Bob 2.0 Integration

IBM Bob 2.0 acts as the agentic development and coordination layer of the project.

The system is designed around a main coordinator and specialized tasks that can be delegated to focused agents or subagents.

```text
                     IBM Bob 2.0
                          │
                   Main Coordinator
                          │
          ┌───────────────┼───────────────┐
          ▼               ▼               ▼
       README            API           Tutorial
       Agent             Agent           Agent
          │               │               │
          └───────────────┼───────────────┘
                          ▼
                  Documentation
                     Auditor
```

Independent documentation tasks can be executed separately or in parallel where appropriate.

---

## Technology Stack

### Language

* Python

### Core Technologies

* Python-based AI agents
* Git repository analysis
* Markdown/documentation processing
* API/OpenAPI analysis
* IBM Bob 2.0
* Agent/Subagent orchestration

### Planned Supporting Libraries

Dependencies will be added according to the actual implementation requirements rather than introducing unnecessary packages.

---

## Project Structure

```text
DevDocs-AI/
│
├── app/
│   ├── agents/
│   │   ├── readme_agent.py
│   │   ├── api_agent.py
│   │   ├── example_validator.py
│   │   ├── tutorial_agent.py
│   │   ├── changelog_agent.py
│   │   └── audit_agent.py
│   │
│   ├── utils/
│   │   ├── git_helper.py
│   │   └── file_helper.py
│   │
│   └── cli/
│       └── main.py
│
├── bob/
│   ├── agents/
│   └── prompts/
│
├── docs/
├── tests/
│
├── .env.example
├── .gitignore
├── CHANGELOG.md
├── PRD.md
├── README.md
├── orchestrator.py
└── requirements.txt
```

---

## How It Works

### Step 1 — Detect Changes

The system analyzes the repository and identifies changed files, features, APIs, and other relevant modifications.

### Step 2 — Analyze Impact

The coordinator determines which documentation areas may be affected.

For example:

```text
New API endpoint
       │
       ├── API documentation
       ├── README usage
       ├── Tutorial
       └── Changelog
```

### Step 3 — Delegate Tasks

Relevant specialized agents are invoked for the affected documentation.

### Step 4 — Generate or Validate Documentation

Agents generate new content, identify inconsistencies, or validate existing documentation.

### Step 5 — Audit

The Documentation Auditor checks the resulting documentation for issues such as broken links, outdated information, and inconsistent examples.

### Step 6 — Produce Final Results

The coordinator combines the agent results and provides a consolidated documentation update/report.

---

## Installation

Clone the repository:

```bash
git clone <repository-url>
cd DevDocs-AI
```

Create a virtual environment:

```bash
python -m venv .venv
```

Activate the environment.

### Windows

```bash
.venv\Scripts\activate
```

### Linux/macOS

```bash
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Create your environment configuration:

```bash
cp .env.example .env
```

Configure the required environment variables in `.env`.

> Never commit `.env` or API keys to the repository.

---

## Usage

The project will expose its core functionality through the Python application and orchestration layer.

Example workflow:

```text
1. Analyze repository changes
2. Detect affected documentation
3. Run relevant documentation agents
4. Validate generated documentation
5. Run documentation audit
6. Produce final results
```

The exact CLI commands will be documented as the CLI implementation is finalized.

---

## Testing

Tests are maintained under:

```text
tests/
```

Run the test suite using:

```bash
pytest
```

The test suite will cover individual agents as well as end-to-end integration scenarios.

---

## Demo Scenario

The project includes a sample repository designed to demonstrate the complete workflow.

A controlled code change can trigger multiple documentation tasks, such as:

```text
Code Change
    │
    ├── New API endpoint
    │       └── API documentation update
    │
    ├── New feature
    │       └── Tutorial generation
    │
    ├── Version change
    │       └── README + Changelog update
    │
    └── Outdated documentation
            └── Audit report
```

This allows the complete DevDocs AI workflow to be demonstrated in a controlled environment.

---

## Project Goals

DevDocs AI aims to make documentation a continuously maintained part of the software development lifecycle rather than a separate task performed after development.

The project focuses on:

* Reducing manual documentation effort
* Keeping documentation synchronized with code
* Improving documentation reliability
* Detecting documentation issues early
* Automating repetitive documentation workflows
* Demonstrating practical multi-agent orchestration with IBM Bob 2.0

---

## Future Scope

Potential future extensions include:

* Interactive documentation playgrounds
* "Try it" functionality for API examples
* Automatic SDK/client generation
* More programming language support
* Pull-request based documentation updates
* Documentation change previews
* Advanced semantic consistency checking

---

## Hackathon

**DevDocs AI — Intelligent Documentation Ecosystem**

Developed as part of the **IBM Bob 2.0 Hackathon**.

The project explores how AI agents and agentic workflows can automate and improve the software documentation lifecycle.