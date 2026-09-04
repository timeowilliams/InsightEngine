# InsightEngine

InsightEngine is an AI conversation intelligence project, nicknamed **Cognitive
Mirror**, for analyzing a user's exported conversations from tools like
ChatGPT, Claude, and similar assistants.

The goal is to turn long-running AI conversation history into measurable,
evidence-backed insight: how someone's questions, topics, language, and
interests change over time. The system should surface behavioral and linguistic
patterns inferred from conversation data, not psychological diagnoses.

## Project Vision

A user imports their AI conversation export. InsightEngine normalizes the raw
data, extracts features, builds embeddings, clusters themes, tracks longitudinal
changes, and lets the user ask questions about their own conversation history.

Example insights:

- "Your technical questions increasingly moved from implementation toward
  architecture and evaluation."
- "Career-related conversations became more planning-oriented after June."
- "Your robotics questions cluster around perception, field testing, and
  deployment reliability."
- "Recent questions are most similar to earlier conversations about backend
  infrastructure and model evaluation."

All insights should be grounded in retrieved conversations, metrics, examples,
or deterministic analysis steps.

## Core Analyses

InsightEngine should model conversation history across several dimensions:

- Question and topic clusters
- Semantic themes over time
- Sentiment and emotional valence
- Question type, such as factual, exploratory, planning, reassurance-seeking,
  debugging, reflective, or argumentative
- Verbosity and linguistic complexity
- Recurring entities and topics
- Changes in interests over time
- Similarity between current and historical questions
- Recurring reasoning patterns
- Conversation depth and branching behavior
- Uncertainty markers, such as "maybe", "I think", and "are you sure"
- Embedding-derived "thinking mode" clusters rather than only predefined labels

## ML Pipeline

The core machine learning flow:

```text
Conversation exports
      |
      v
ETL and normalization
      |
      v
Sentence embeddings
      |
      v
Dimensionality reduction with UMAP or PCA
      |
      v
Clustering with HDBSCAN or K-Means
      |
      v
Cluster labeling
      |
      v
Longitudinal trend analysis
```

This gives the project a real data science center of gravity while still
requiring production-grade backend infrastructure around ingestion, storage,
jobs, APIs, observability, and deployment.

## Collaboration Split

Ryan can own the data science and machine learning path:

- Conversation parsing and normalization
- Feature extraction
- Embedding generation
- Dimensionality reduction
- Clustering
- Classification
- Temporal trend analysis
- Evaluation datasets and metrics

Backend and ML engineering work can focus on:

- FastAPI application structure
- PostgreSQL persistence
- SQLAlchemy models and migrations
- Dockerized local development
- Authentication and user isolation
- Background job orchestration
- Model API integration
- Observability and tracing
- Frontend workflows
- Deployment

The division is clean: data science produces measurable analyses, and the
application turns those analyses into a deployable software system.

## Candidate Data Model

A relational schema might include:

- `users`
- `imports`
- `conversations`
- `messages`
- `embeddings`
- `clusters`
- `analyses`
- `model_runs`
- `evaluations`

This keeps the backend from becoming a generic CRUD exercise. The database
exists to support a real ML product: ingestion, reproducibility, analysis
history, evidence retrieval, and model evaluation.

## Agentic Analysis Layer

The system should support natural-language questions over the user's own
conversation history.

Example:

```text
User: "How has my thinking about my career changed?"

                    Orchestrator
                         |
          +--------------+--------------+
          |              |              |
          v              v              v
  Retrieval Agent   Trend Agent    Statistics Agent
          |              |              |
          +--------------+--------------+
                         |
                         v
                 Synthesis Agent
                         |
                         v
                       Answer
```

Agents should call deterministic tools instead of only relying on free-form
chat:

- `search_conversations()`
- `get_topic_distribution()`
- `calculate_sentiment_trend()`
- `compare_time_periods()`
- `find_similar_questions()`
- `get_cluster_examples()`

The important system pattern is:

```text
LLM -> tool orchestration -> ML pipeline -> database -> evidence -> evaluated response
```

## Evaluation Plan

Evals should be a first-class feature, not an afterthought.

Build a golden dataset of questions such as:

- "What topic did I ask about most in June?"
- "Did my sentiment toward work improve?"
- "What were my three most common question categories?"
- "Find conversations related to robotics."
- "Did my average question length increase?"

Some questions should have deterministic ground truth from the database. Others
can be graded using code-based evaluators or LLM-as-judge evaluators.

Compare model and system variants across:

- Tool-call accuracy
- Answer correctness
- Citation and evidence correctness
- Hallucination rate
- Latency
- Token usage
- Cost
- Retrieval quality

Phoenix is a strong candidate for experiments, traces, datasets, evaluators,
and OpenTelemetry instrumentation. Langfuse is another good candidate if the
project leans more heavily toward production LLM tracing, token accounting,
tool/retrieval traces, experiments, and self-hosting.

For this project, Phoenix is the preferred starting point because the
experiment and evaluation workflow maps directly to the portfolio story.

## Product Principles

- Be evidence-backed: every generated insight should cite examples, metrics, or
  retrieval results.
- Be humble about inference: describe behavioral and linguistic patterns, not
  clinical or psychological truth.
- Be reproducible: track imports, model runs, prompts, evaluation results, and
  analysis versions.
- Be comparative: make it easy to compare models, retrieval strategies, and
  clustering approaches.
- Be deployable: treat APIs, jobs, database schema, tracing, and frontend UX as
  core project artifacts.

## Roadmap

1. Import and normalize conversation exports.
2. Store users, conversations, messages, and imports in PostgreSQL.
3. Generate embeddings and persist vector metadata.
4. Add clustering and cluster labeling.
5. Build temporal trend analysis.
6. Add deterministic analysis tools.
7. Build the agentic question-answering layer.
8. Add evidence citations and example retrieval.
9. Create a golden evaluation dataset.
10. Compare model variants with Phoenix-backed experiments.
11. Add frontend workflows for import, exploration, and question answering.
12. Dockerize and deploy the full stack.

## Local Ingestion Workflow

Keep raw exports and processed conversation data out of Git. This repo ignores
`data/raw/` and `data/processed/` by default because those folders can contain
private conversation history.

Place a ChatGPT export ZIP under `data/raw/`, then profile it:

```powershell
python scripts\profile_export.py data\raw\chatgpt-export.zip
```

Normalize the export into local JSONL files:

```powershell
python scripts\import_chatgpt_export.py data\raw\chatgpt-export.zip
```

The importer writes:

- `data/processed/conversations.jsonl`
- `data/processed/messages.jsonl`
- `data/processed/summary.json`

Run deterministic local analyses before adding embeddings or LLM synthesis:

```powershell
python scripts\analyze_messages.py
python scripts\analyze_messages.py --search robotics
```

Extract non-text linguistic features for each message:

```powershell
python scripts\build_message_features.py
```

Generate a local Markdown profile report:

```powershell
python scripts\generate_profile_report.py
```

Run tests:

```powershell
python -m unittest discover
```

## Local Postgres Workflow

Use Docker Compose for local Postgres. This gives the project a real backend
database while keeping setup reproducible for collaborators.

Start Postgres:

```powershell
docker compose up -d postgres
```

Create tables:

```powershell
docker compose run --rm app python scripts/postgres_store.py init
```

For a local development rebuild, reset the tables:

```powershell
docker compose run --rm app python scripts/postgres_store.py reset
```

Load the normalized JSONL files into Postgres:

```powershell
docker compose run --rm app python scripts/postgres_store.py load-jsonl
```

Run deterministic database-backed analyses:

```powershell
docker compose run --rm app python scripts/postgres_store.py analyze
docker compose run --rm app python scripts/postgres_store.py analyze --search robotics
```

This first milestone should answer basic questions such as:

- How many conversations and messages are in the export?
- Which months had the most activity?
- How long are user messages on average?
- Which terms recur most often in user messages?
- Which conversations contain a specific keyword or phrase?
- Which heuristic question types are most common?
- How do uncertainty markers and message length change over time?

