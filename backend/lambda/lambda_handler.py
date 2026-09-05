"""PathFinder AWS Lambda compute layer (Python 3.12, x86_64).

POST /recommend  ->  { "prompt": "...", "interests": [...], "strengths": [...], "ambitions": [...] }

Resolution order:
1. KNOWLEDGE_BASE_ID set  -> Amazon Bedrock Agent Runtime ``retrieve_and_generate``.
2. BEDROCK_MODEL_ID set   -> Amazon Bedrock ``converse`` with a chosen foundation
                             model (default Claude 3.5 Sonnet / Nova Pro).
3. Otherwise              -> built-in rule-based recommender (recommender.py)
                             so the application works out of the box.
"""

import json
import os

try:
    import boto3
except ImportError:
    boto3 = None

import recommender

REGION = os.environ.get("AWS_REGION", "us-east-1")
KNOWLEDGE_BASE_ID = os.environ.get("KNOWLEDGE_BASE_ID", "TZCHY9CO5N")
BEDROCK_MODEL_ID = os.environ.get(
    "BEDROCK_MODEL_ID", "amazon.nova-pro-v1:0"
)
# Ordered fallback chain: the first listed model is tried first; if it is
# unavailable the next is attempted, and so on. The rule-based recommender
# remains the final fallback when every Bedrock model fails.
BEDROCK_FALLBACK_MODELS = [
    model
    for model in (
        os.environ.get("BEDROCK_MODEL_ID", ""),
        *os.environ.get(
            "BEDROCK_FALLBACK_MODELS",
            "amazon.nova-lite-v1:0,anthropic.claude-3-5-sonnet-20241022-v2:0,meta.llama3-70b-instruct-v1:0",
        ).split(","),
    )
    if model
]


def _has_aws_credentials():
    """No-network check for configured AWS credentials (env, profile, files)."""
    if os.environ.get("AWS_ACCESS_KEY_ID"):
        return True
    if os.environ.get("AWS_PROFILE"):
        return True
    if os.environ.get("AWS_WEB_IDENTITY_TOKEN_FILE"):
        return True
    credentials_path = os.path.expanduser("~/.aws/credentials")
    config_path = os.path.expanduser("~/.aws/config")
    for path in (credentials_path, config_path):
        if os.path.isfile(path):
            return True
    return False

_BOTO_CONFIG = None
if boto3 and hasattr(boto3, "session"):
    try:
        _BOTO_CONFIG = boto3.session.Config(
            connect_timeout=10,
            read_timeout=25,
            retries={"max_attempts": 2, "mode": "standard"},
        )
    except Exception:  # noqa: BLE001 - non-standard boto3 stub, no config needed
        _BOTO_CONFIG = None

bedrock_agent_runtime = (
    boto3.client(
        "bedrock-agent-runtime", region_name=REGION, config=_BOTO_CONFIG
    )
    if boto3
    else None
)
bedrock_runtime = (
    boto3.client("bedrock-runtime", region_name=REGION, config=_BOTO_CONFIG)
    if boto3
    else None
)

MODEL_SCHEMA = {
    "primary_track": "string",
    "primary_summary": "string",
    "core_courses": ["string"],
    "starter_projects": ["string"],
    "career_paths": ["string"],
    "alternative_tracks": [
        {
            "name": "string",
            "summary": "string",
            "core_courses": ["string"],
            "starter_projects": ["string"],
            "career_paths": ["string"],
        }
    ],
    "top_tracks": [
        {
            "id": "string",
            "name": "string",
            "score": "int",
            "summary": "string",
            "core_courses": ["string"],
            "starter_projects": ["string"],
            "career_paths": ["string"],
        }
    ],
    "recommended": "boolean",
}

SYSTEM_PROMPT = f"""You are PathFinder, an academic advisor for freshman Computer Science (CS)
and Computer Technology (CT) students. You recommend academic tracks, core courses and
freshman starter projects based on a student's interests, strengths and ambitions.

Use your knowledge of standard CS/CT curricula. Consider tracks such as:
AI & Machine Learning, Web & Mobile Development, Cybersecurity & Networking,
Cloud & Systems Infrastructure, Data Engineering & Analytics, Game Development & HCI.

Respond with STRICT JSON only, matching this exact schema (no markdown fences, no
commentary). The roadmap must be concrete, grounded and actionable for a first-year student.
Schema:
{json.dumps(MODEL_SCHEMA, indent=2)}"""


def generate_with_model(user_prompt, interests, strengths, ambitions):
    """Query an Amazon Bedrock foundation model via the Converse API.

    Tries each model in ``BEDROCK_FALLBACK_MODELS`` in order. The first model that
    produces a usable response wins; transient/permission/model-unavailable errors
    move on to the next model. Raises the last error if every model fails so the
    caller can fall back to the built-in recommender.
    """
    input_text = user_prompt or (
        "Student profile:\n"
        f"- Interests: {interests or 'not provided'}\n"
        f"- Strengths: {strengths or 'not provided'}\n"
        f"- Ambitions: {ambitions or 'not provided'}"
    )

    last_error = None
    for model_id in BEDROCK_FALLBACK_MODELS:
        try:
            response = bedrock_runtime.converse(
                modelId=model_id,
                system=[{"text": SYSTEM_PROMPT}],
                messages=[{"role": "user", "content": [{"text": input_text}]}],
                inferenceConfig={"maxTokens": 2000, "temperature": 0.3},
            )
            text = response["output"]["message"]["content"][0]["text"]
        except Exception as exc:  # noqa: BLE001 - try next model on any failure
            last_error = exc
            continue

        try:
            roadmap = json.loads(text)
        except (json.JSONDecodeError, TypeError):
            roadmap = text  # fall back to raw model text if not parseable JSON
        return roadmap, text, model_id

    raise last_error if last_error else RuntimeError(
        "No Bedrock models are configured."
    )


def lambda_handler(event, context):
    headers = {
        "Access-Control-Allow-Origin": "*",
        "Content-Type": "application/json",
    }

    body = json.loads(event.get("body", "{}")) if event.get("body") else {}
    user_prompt = body.get("prompt", "")
    interests = body.get("interests", [])
    strengths = body.get("strengths", [])
    ambitions = body.get("ambitions", [])

    if KNOWLEDGE_BASE_ID and bedrock_agent_runtime:
        # Resolve full Model ARN required by Knowledge Base retrieve_and_generate API
        model_arn = os.environ.get(
            "BEDROCK_MODEL_ARN",
            BEDROCK_MODEL_ID if BEDROCK_MODEL_ID.startswith("arn:") 
            else f"arn:aws:bedrock:{REGION}::foundation-model/{BEDROCK_MODEL_ID}"
        )

        prompt_text = user_prompt or (
            f"Recommend academic tracks and starter projects for a freshman student with "
            f"Interests: {interests}, Strengths: {strengths}, Ambitions: {ambitions}"
        )

        try:
            response = bedrock_agent_runtime.retrieve_and_generate(
                input={"text": prompt_text},
                retrieveAndGenerateConfiguration={
                    "type": "KNOWLEDGE_BASE",
                    "knowledgeBaseConfiguration": {
                        "knowledgeBaseId": KNOWLEDGE_BASE_ID,
                        "modelArn": model_arn,
                    },
                },
            )
            recommendation = response["output"]["text"]
        except Exception as exc:
            prompt = user_prompt or recommender.build_prompt(interests, strengths, ambitions)
            roadmap = recommender.build_roadmap(interests, strengths, ambitions)
            recommendation = {
                "roadmap": roadmap,
                "source": "built-in-recommender",
                "prompt": prompt,
                "model_error": f"{type(exc).__name__}: {exc}",
            }
    elif KNOWLEDGE_BASE_ID:
        prompt = user_prompt or recommender.build_prompt(interests, strengths, ambitions)
        roadmap = recommender.build_roadmap(interests, strengths, ambitions)
        recommendation = {
            "roadmap": roadmap,
            "source": "built-in-recommender",
            "prompt": prompt,
            "model_error": "AWS SDK (boto3) not available in this environment.",
        }
    elif bedrock_runtime and _has_aws_credentials():
        try:
            roadmap, raw, model_id = generate_with_model(
                user_prompt, interests, strengths, ambitions
            )
            recommendation = {
                "roadmap": roadmap,
                "source": f"bedrock:{model_id}",
                "raw": raw,
            }
        except Exception as exc:  # noqa: BLE001 - fall back on any Bedrock failure
            prompt = user_prompt or recommender.build_prompt(interests, strengths, ambitions)
            roadmap = recommender.build_roadmap(interests, strengths, ambitions)
            recommendation = {
                "roadmap": roadmap,
                "source": "built-in-recommender",
                "prompt": prompt,
                "model_error": f"{type(exc).__name__}: {exc}",
            }
    elif bedrock_runtime:
        recommendation = {
            "roadmap": recommender.build_roadmap(interests, strengths, ambitions),
            "source": "built-in-recommender",
            "model_error": "No AWS credentials configured. Set AWS_ACCESS_KEY_ID/AWS_SECRET_ACCESS_KEY or AWS_PROFILE to use Amazon Bedrock.",
        }
    else:
        prompt = user_prompt or recommender.build_prompt(interests, strengths, ambitions)
        roadmap = recommender.build_roadmap(interests, strengths, ambitions)
        recommendation = {
            "roadmap": roadmap,
            "source": "built-in-recommender",
            "prompt": prompt,
        }

    return {
        "statusCode": 200,
        "headers": headers,
        "body": json.dumps({"recommendation": recommendation}),
    }


def run_local(event_path=None):
    """Small harness for running the handler without AWS infrastructure."""
    if event_path:
        with open(event_path, "r", encoding="utf-8") as fh:
            event = json.load(fh)
    else:
        event = {
            "body": json.dumps(
                {
                    "interests": ["AI", "web development"],
                    "strengths": ["mathematics", "logic"],
                    "ambitions": ["AI Researcher", "Full-Stack Developer"],
                }
            )
        }
    response = lambda_handler(event, {})
    print(json.dumps(response, indent=2, default=str))


if __name__ == "__main__":
    import sys

    run_local(sys.argv[1] if len(sys.argv) > 1 else None)