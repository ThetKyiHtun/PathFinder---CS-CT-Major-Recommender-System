# PathFinder

This project was developed by Master Students (Thet Kyi Htun,Thiha Oo,Ye Htut Naung,Khoon Sett Naing,Hein Myat Paing,Htet Myat Aung,Nan La Min You,Phue Pyae Pyae San,Su Myat Noe Oo,Theint Theint Lwim,Khin Nadi Kyaw) from University Of Computer Studies,Yangon (UCSY).

**CS & CT Major Recommender System**

A full-stack, serverless web application that recommends academic tracks, core
courses, and freshman starter projects to first-year Computer Science (CS) and
Computer Technology (CT) students based on their interests, strengths, and
career ambitions.

PathFinder runs on Amazon Web Services (AWS): a React client talks to an
API Gateway endpoint backed by an AWS Lambda function that queries **Amazon
Bedrock** foundation models — with a built-in rule engine as a guaranteed
offline fallback.

```
React Web Client → API Gateway (POST /recommend, CORS *)
                → AWS Lambda (Python 3.12, x86_64)
                   ├─ Amazon Bedrock foundation model (primary)
                   │    └─ multi-model fallback chain
                   └─ built-in rule-based recommender (final fallback)
```

---



## Table of Contents

- [Features](#features)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [API](#api)
- [Preprocessing](#preprocessing)
- [Workflow](#workflow)
- [System Flow](#system-flow)
- [Getting Started](#getting-started)
- [Deployment](#deployment)
- [Configuration](#configuration)

---



## Features

- **Blueprint-styled UI** — navy grid-lined canvas with cyan/amber accents and a
plan-drawing aesthetic.
- **Student profile form** — multi-select chips for Interests, Strengths, and
Ambitions, plus custom ambition input.
- **Career roadmap** — primary track, summary, core courses, freshman starter
projects, career paths, match-strength bars, and alternative tracks.
- **Serverless & resilient** — API Gateway → Lambda → Bedrock, with automatic
fallback so the app always returns a usable roadmap.
- **Model fallback chain** — tries the primary Bedrock model, steps through
alternative Bedrock models, then the built-in recommender.
- **Six CS/CT tracks** — AI & ML, Web & Mobile, Cybersecurity & Networking,
Cloud & Systems, Data Engineering, Game Dev & HCI.

---



## Tech Stack

**Frontend**


| Technology      | Purpose                         |
| --------------- | ------------------------------- |
| React 18 + Vite | UI framework and build tool     |
| Node.js 18+     | Development / build environment |


**Backend & Cloud**


| Technology               | Purpose                                        |
| ------------------------ | ---------------------------------------------- |
| Python 3.12              | Lambda runtime                                 |
| AWS Lambda               | Serverless compute — `POST /recommend` handler |
| Amazon API Gateway       | HTTP API with CORS for `/recommend`            |
| Amazon Bedrock           | Foundation-model reasoning (Converse API)      |
| boto3                    | AWS SDK for Python                             |
| AWS SAM / CloudFormation | Infrastructure as code and deployment          |


**Optional**


| Technology                    | Purpose                      |
| ----------------------------- | ---------------------------- |
| Amazon Bedrock Knowledge Base | RAG-style grounded retrieval |


---



## Project Structure

```
PathFinder/
├── frontend/                     # React (Vite) web client
│   ├── src/
│   │   ├── App.jsx               # layout, state, API orchestration
│   │   ├── api.js                # POST /recommend client
│   │   ├── main.jsx              # React entry point
│   │   ├── styles.css            # blueprint theme
│   │   └── components/
│   │       ├── RecommenderForm.jsx
│   │       └── RoadmapResult.jsx
│   ├── vite.config.js            # dev proxy → local_server (port 3001)
│   ├── .env.example              # VITE_API_BASE_URL template
│   └── package.json
├── backend/
│   ├── lambda/
│   │   ├── lambda_handler.py     # Lambda entry point + Bedrock fallback
│   │   └── recommender.py        # deterministic CS/CT scoring engine
│   ├── templates/template.yaml   # SAM: API Gateway + Lambda + CORS + Bedrock IAM
│   ├── knowledge-base/           # seed documents for a Bedrock Knowledge Base
│   ├── events/sample_request.json
│   ├── tests/test_local.py       # offline unit tests (stubs boto3)
│   └── local_server.py           # stdlib-only local API stand-in
└── README.md
```

---



## API



### `POST /recommend`

**Request**

```json
{
  "prompt": "",
  "interests": ["AI", "Web Development"],
  "strengths": ["Mathematics", "Logic"],
  "ambitions": ["AI Researcher", "Technical Architect"]
}
```

**Response** — `200 OK` with CORS headers (`Access-Control-Allow-Origin: `*):

```json
{
  "recommendation": {
    "roadmap": {
      "primary_track": "AI & Machine Learning",
      "primary_summary": "Build systems that learn from data…",
      "core_courses": ["Data Structures & Algorithms", "…"],
      "starter_projects": ["Spam Classifier with Naive Bayes", "…"],
      "career_paths": ["AI Engineer", "…"],
      "alternative_tracks": [{ "name": "…", "summary": "…" }],
      "top_tracks": [{ "id": "ai-ml", "name": "…", "score": 5 }]
    },
    "source": "bedrock:amazon.nova-pro-v1:0",
    "model_error": "…"
  }
}
```

The `source` field reports which system produced the result:


| `source`               | Meaning                                                |
| ---------------------- | ------------------------------------------------------ |
| `bedrock:<model-id>`   | Generated by a Bedrock foundation model (primary path) |
| `built-in-recommender` | Generated by the deterministic rule engine (fallback)  |


`model_error` appears only when every Bedrock model was unavailable.

---



## Preprocessing

Raw student input is normalized before a recommendation is produced:

1. **Extraction** — the Lambda reads `prompt`, `interests`, `strengths`, and
  `ambitions` from the JSON request body.
2. **Normalization** — selections are lower-cased and whitespace-stripped by the
  `_tokens()` helper, so keyword matching is case-insensitive.
3. **Prompt composition** — when no free-text prompt is given, the handler builds
  a structured "Student profile" block and sends it with a strict-JSON system
   prompt and output schema to the Bedrock model.
4. **Feature matching (fallback)** — the rule engine scores each track by weighted
  keyword overlap: interests ×3, strengths ×2, ambitions ×3.
5. **Ranking** — tracks are sorted by score, yielding the top track, alternatives,
  and support scores for the UI.

---



## Workflow

1. **Submit** — the user selects Interests, Strengths, and Ambitions and submits.
2. **Request** — `api.js` sends `POST /recommend` to the backend.
3. **Route** — the Lambda selects the resolution path:
  - Bedrock Knowledge Base (optional) → `retrieve_and_generate`, or
  - Bedrock model chain (primary) → `converse`, or
  - Built-in recommender (final) → deterministic scoring.
4. **Model fallback** — if a Bedrock model errors (permission / model disabled /
  quota / timeout), the next model in the chain is tried; if all fail, the
   built-in recommender runs.
5. **Parse** — the winning model's output is parsed as JSON against the roadmap
  schema; unparseable output is returned raw.
6. **Render** — `RoadmapResult.jsx` displays the roadmap.

---



## System Flow

```
                ┌────────────────────────────────────────┐
                │  React Web Client (frontend)           │
                │  RecommenderForm → api.js → fetch      │
                └───────────────────┬────────────────────┘
                                    │ POST /recommend (JSON)
                                    ▼
                ┌────────────────────────────────────────┐
                │  Amazon API Gateway (CORS *)           │
                └───────────────────┬────────────────────┘
                                    │ invoke
                                    ▼
                ┌────────────────────────────────────────┐
                │  AWS Lambda (lambda_handler.py)        │
                │  resolve path:                         │
                │   1) Bedrock Knowledge Base ──┐        │
                │   2) Bedrock model chain ─────┼─► model│
                │   3) Built-in recommender ◄────┘       │
                └──────────────┬─────────────────────────┘
              ┌────────────────┼──────────────────────────┐
              ▼                ▼                          ▼
     ┌──────────────┐ ┌──────────────────────┐ ┌───────────────────┐
     │ Bedrock KB   │ │ Bedrock Converse     │ │ recommender.py    │
     │ retrieve_and │ │ nova-pro ▸ nova-lite │ │ weighted keyword  │
     │ _generate    │ │ ▸ claude ▸ llama     │ │ scoring + roadmap │
     └──────────────┘ └──────────────────────┘ └───────────────────┘
              └────────────────┼──────────────────────────┘
                               ▼
                ┌────────────────────────────────────────┐
                │  JSON roadmap + source → RoadmapResult  │
                └────────────────────────────────────────┘
```

**Fallback order** (when the Knowledge Base is unset):

1. `amazon.nova-pro-v1:0` — primary model (`BEDROCK_MODEL_ID`)
2. `amazon.nova-lite-v1:0`
3. `anthropic.claude-3-5-sonnet-20241022-v2:0`
4. `meta.llama3-70b-instruct-v1:0`
5. Built-in recommender (works offline, always available)

Override the chain with `BEDROCK_FALLBACK_MODELS` (comma-separated). Each Bedrock
model is usable only if it is **enabled in your account/region**.

---



## Getting Started

Requirements: **Python 3.12+** and **Node.js 18+**.

Run the project from a terminal in **two separate terminals** — one for the
backend and one for the frontend.

### 1. Backend (terminal 1)

```bash
cd backend

# Load AWS credentials (needed for the Bedrock path)
export AWS_ACCESS_KEY_ID="$(grep aws_access_key_id ~/.aws/credentials | awk '{print $3}')"
export AWS_SECRET_ACCESS_KEY="$(grep aws_secret_access_key ~/.aws/credentials | awk '{print $3}')"
export AWS_DEFAULT_REGION=us-east-1

# Knowledge Base is off by default; set the ID to enable the KB path
export KNOWLEDGE_BASE_ID=""

python3 -m venv .venv
.venv/bin/pip install boto3          # first time only (optional — needed for Bedrock)
.venv/bin/python local_server.py 3001
```

`local_server.py` is a stdlib-only API Gateway stand-in serving
`http://localhost:3001/recommend`.

### 2. Frontend (terminal 2)

```bash
cd frontend
npm install                          # first time only
npm r un dev                         # http://localhost:5173
```

The Vite dev server proxies `/recommend` to `localhost:3001`. To force the
frontend to use your **local** backend (instead of the endpoint in
`frontend/.env`), launch with the variable emptied:

```bash
VITE_API_BASE_URL="" npm run dev
```

To target a **deployed** endpoint instead, set `VITE_API_BASE_URL` in
`frontend/.env`:

```bash
echo "VITE_API_BASE_URL=https://<api-id>.execute-api.us-east-1.amazonaws.com/prod/recommend" > frontend/.env
```

Then open **[http://localhost:5173](http://localhost:5173)** in your browser.

### 3. Verify offline

```bash
python3 backend/tests/test_local.py
python3 backend/lambda/lambda_handler.py backend/events/sample_request.json

curl -X POST http://localhost:3001/recommend \
  -H "Content-Type: application/json" \
  -d '{"interests":["AI"],"strengths":["Mathematics"],"ambitions":["Data Scientist"]}'
```



### 4. Stop the running processes

```
Ctrl+C   # in each terminal
```

or, from anywhere:

```bash
pkill -f local_server.py     # stop backend
pkill -f vite                # stop frontend
```

---



## Deployment

Requirements: AWS CLI, SAM CLI, and credentials for `us-east-1`.

```bash
cd backend
sam build -t templates/template.yaml

sam deploy \
  --stack-name pathfinder-backend \
  --region us-east-1 \
  --capabilities CAPABILITY_IAM CAPABILITY_AUTO_EXPAND \
  --resolve-s3 \
  --no-confirm-changeset \
  --parameter-overrides "BedrockModelId=amazon.nova-pro-v1:0"
```

Or interactively: `sam deploy --guided -t templates/template.yaml`.

The stack outputs the endpoint URL:

```
https://<api-id>.execute-api.us-east-1.amazonaws.com/prod/recommend
```

Deploy without the Knowledge Base path:

```bash
sam deploy --guided --parameter-overrides KnowledgeBaseId=
```

**Optional — Bedrock Knowledge Base:** create a Knowledge Base in the Bedrock
console, upload `backend/knowledge-base/pathfinder-track-guide.md` as a source
document, and pass its ID through `KnowledgeBaseId`. The Lambda IAM role already
grants `bedrock:RetrieveAndGenerate` and `bedrock:InvokeModel` on the primary and
fallback foundation models.

---



## Configuration


| Variable                  | Default                                                                                         | Purpose                                |
| ------------------------- | ----------------------------------------------------------------------------------------------- | -------------------------------------- |
| `AWS_REGION`              | `us-east-1`                                                                                     | AWS region for Bedrock clients         |
| `KNOWLEDGE_BASE_ID`       | *(empty)*                                                                                       | Enable the Bedrock Knowledge Base path |
| `BEDROCK_MODEL_ID`        | `amazon.nova-pro-v1:0`                                                                          | Primary Bedrock model                  |
| `BEDROCK_FALLBACK_MODELS` | `amazon.nova-lite-v1:0,anthropic.claude-3-5-sonnet-20241022-v2:0,meta.llama3-70b-instruct-v1:0` | Comma-separated fallback chain         |
| `VITE_API_BASE_URL`       | `http://localhost:3001/recommend`                                                               | Frontend → backend endpoint            |


---



## AWS Credentials

Configure credentials either via the CLI:

```bash
aws configure
# Access Key ID:     <your-key-id>
# Secret Access Key: <your-secret-key>
# Region:            us-east-1
# Output format:     json
```

or with environment variables:

```bash
export AWS_ACCESS_KEY_ID=...
export AWS_SECRET_ACCESS_KEY=...
export AWS_DEFAULT_REGION=us-east-1
```

Verify with `aws sts get-caller-identity`.

> **Security:** never commit credentials. Rotate any keys that may have been
> exposed via IAM → Users → Security credentials.
