> An AI-powered MLB fantasy draft simulator where autonomous agents compete to build the best team

**[Live Demo - mlbdraftoracle.com](http://mlbdraftoracle.com)** | Available daily 2-4 PM EST

[![AWS](https://img.shields.io/badge/AWS-Lambda-orange)](https://aws.amazon.com/lambda/)
[![Python](https://img.shields.io/badge/Python-3.12-blue)](https://www.python.org/)
[![OpenAI](https://img.shields.io/badge/OpenAI-gpt--4o--mini-green)](https://openai.com/)
[![React](https://img.shields.io/badge/React-18-blue)](https://reactjs.org/)
[![S3](https://img.shields.io/badge/AWS-S3%20RAG-yellow)](https://aws.amazon.com/s3/)

---

## 🎯 Overview

MLB Draft Oracle is an autonomous AI draft simulator that pits two AI-powered teams against each other in a fantasy baseball draft. Each team is assigned a unique strategy (e.g., "Power Hitting" vs "Speed & Defense") and uses intelligent agents to research players, analyze statistics, and make strategic picks—complete with detailed rationales for every selection.

Completed drafts are automatically indexed into a vector store on S3, allowing agents in future drafts to learn from historical pick patterns, team strategies, and outcomes via **Retrieval-Augmented Generation (RAG)**.

**Watch as AI teams:**
- 🔍 Research real 2025 MLB player statistics via web search
- 🧠 Query historical draft context via RAG before making picks
- 🤔 Evaluate players based on their team strategy
- 🎯 Draft players with detailed reasoning
- 📊 Build optimized rosters position by position

---

## ✨ Key Features

### 🤖 **Autonomous AI Agents**
- **Researcher Agent**: Searches the web for current MLB player stats and news, and queries historical draft context via RAG
- **Drafter Agent**: Evaluates candidates and executes draft picks with strategic rationale
- Powered by OpenAI's GPT-4o-mini and the OpenAI Agents SDK

### 🧠 **RAG-Powered Draft Memory**
- Completed drafts are saved as structured JSON to S3 and automatically vectorized
- The Researcher Agent queries this vector store before each pick using `search_draft_context` and `get_team_roster_status` tools
- Agents learn from previous drafts: which players were taken early, which strategies succeeded, which positions were scarce
- Vector embeddings generated via OpenAI and stored in S3 (`vectors/draft-insights/`)

### 📋 **Strategic Draft Simulation**
- Two competing AI teams with distinct strategies
- 4-round draft format (configurable)
- 4 roster positions: Catcher (C), First Base (1B), Outfield (OF), Pitcher (P)
- Real-time draft history with AI-generated pick rationales

### 🌐 **Modern Architecture**
- **Serverless AWS Lambda** for scalable, cost-efficient execution
- **Model Context Protocol (MCP)** for agent tool orchestration
- **PostgreSQL RDS** backend for draft state management
- **React + Tailwind CSS** responsive frontend
- **EventBridge Scheduler** for automated daily operation

### 🔍 **Observability**
- **OpenAI Traces**: Full agent execution traces captured in the OpenAI dashboard, showing every tool call, LLM response, and agent decision in sequence
- **AWS CloudWatch Logs**: Detailed structured logging across all Lambda functions, with tagged log lines for each stage of draft execution

### 💰 **Cost-Optimized Design**
- Site active only 2-4 PM EST daily (automatic start/stop)
- Optimized to 2 teams, 4 rounds, 4 positions to manage API costs

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     User Browser (React)                     │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│              API Gateway + S3 Static Hosting                 │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
           ┌─────────────────────────────┐
           │  mlb-draft-oracle-worker    │ ◄── EventBridge (2-4 PM EST)
           │  (Main Orchestrator)        │
           └──────┬──────────────────────┘
                  │
     ┌────────────┼────────────────┐
     │            │                │
     ▼            ▼                ▼
┌─────────┐ ┌──────────────┐ ┌───────────────────────────┐
│mcp-draft│ │mcp-brave-    │ │  RAG Tools (in-process)   │
│(Draft   │ │search        │ │  search_draft_context      │
│ Tool)   │ │(Web Search)  │ │  get_team_roster_status    │
└────┬────┘ └──────┬───────┘ └───────────┬───────────────┘
     │             │                     │
     └──────┬──────┘                     │
            ▼                            ▼
  ┌─────────────────────┐     ┌──────────────────────────┐
  │  PostgreSQL RDS      │     │  S3 RAG Store            │
  │  (Draft Database)    │     │  source_data/            │
  └─────────────────────┘     │    historical_drafts/     │
                               │  vectors/                │
                               │    draft-insights/       │
                               └──────────┬───────────────┘
                                          ▲
                                          │ index after draft
                                          │
                               ┌──────────────────────────┐
                               │ mlb-draft-oracle-         │
                               │ rag-indexer              │
                               │ (Triggered post-draft)   │
                               └──────────────────────────┘
```

### Lambda Functions

1. **`mlb-draft-oracle-worker`** (Main Orchestrator)
   - Manages draft flow and agent coordination
   - Invokes MCP Lambda functions for tools
   - Uses OpenAI Agents SDK with two agents per team
   - Loads RAG tools directly in-process (no subprocess) for low-latency access

2. **`mlb-draft-oracle-mcp-draft`** (MCP Server)
   - Provides `draft_specific_player` tool
   - Handles draft validation and database updates
   - Implements position-filling logic
   - Idempotency guard prevents duplicate picks if the agent calls the tool more than once

3. **`mlb-draft-oracle-mcp-brave-search`** (MCP Server)
   - Provides web search capabilities via Brave Search API
   - Enables agents to research current MLB player stats
   - Returns real 2025 season data

4. **`mlb-draft-oracle-rag-indexer`** (RAG Indexer)
   - Triggered automatically after each completed draft
   - Reads draft JSON from S3 (`source_data/historical_drafts/`)
   - Generates OpenAI vector embeddings for each pick, team strategy, and rationale
   - Writes embeddings to S3 (`vectors/draft-insights/`) for retrieval in future drafts

### Database Schema

**PostgreSQL RDS** stores:
- Draft state (current round, pick)
- Team rosters and strategies
- Player pool (198 MLB players with 2025 stats)
- Draft history with pick rationales

### S3 RAG Store

**S3 bucket `mlbdraftoracle-memory`** stores:
- `source_data/historical_drafts/{draft_id}.json` — full draft results saved after each session
- `source_data/historical_drafts/{draft_id}_current.json` — live snapshot updated after each pick
- `vectors/draft-insights/` — OpenAI vector embeddings, one file per draft, used for cosine similarity search

---

## 🚀 How It Works

### Draft Flow

1. **Initialization**
   - Two teams created with assigned strategies
   - Player pool loaded (198 MLB players with 2025 stats)
   - Draft order determined (snake draft format)

2. **For Each Pick**
   - **Researcher Agent** is given the current roster, needed positions, and available players
   - Agent calls `search_draft_context` to retrieve relevant historical picks and strategies from the RAG store
   - Agent calls `get_team_roster_status` to confirm current roster state from the live S3 snapshot
   - Agent calls `brave_search` to look up current player stats and news
   - Provides recommendations based on team strategy and historical context

3. **Drafter Agent** receives recommendations
   - Evaluates candidates against roster needs
   - Calls `draft_specific_player` tool with selection
   - Includes detailed rationale for the pick

4. **Draft Execution**
   - Validates position availability
   - Updates roster and draft history in PostgreSQL
   - Updates the live S3 snapshot (`_current.json`) for the RAG roster tool
   - Proceeds to next team's pick

5. **Completion**
   - Final rosters displayed with full draft history and rationales
   - Completed draft JSON saved to S3
   - `mlb-draft-oracle-rag-indexer` Lambda triggered to vectorize the draft for future context
   - Database cleaned up before site shutdown

### RAG Detail

The RAG system gives agents a persistent memory of past drafts without requiring an external vector database. After each session, the `rag-indexer` Lambda reads the completed draft JSON, generates an embedding for each pick (player name, position, round, rationale, team strategy) using the OpenAI embeddings API, and writes them to S3 as vector files. During the next draft, the Researcher Agent calls `search_draft_context` with a natural language query (e.g., "best outfielders taken in round 2 with power strategy") and retrieves the most semantically similar historical picks, ranked by cosine similarity—all directly from S3.

```
Draft completes
      │
      ▼
S3: source_data/historical_drafts/{id}.json saved
      │
      ▼
rag-indexer Lambda triggered
      │
      ├── Reads draft JSON
      ├── Generates embeddings per pick (OpenAI)
      └── Writes to S3: vectors/draft-insights/{id}.json
                          │
                          ▼ (next draft)
             Researcher Agent calls:
             search_draft_context("best power hitters round 1")
                          │
                          ▼
             Cosine similarity search across all S3 vector files
                          │
                          ▼
             Top-k historical picks returned as context to agent
```

### Agent Intelligence

Each team employs a **two-agent system**:

**🔬 Researcher Agent**
```
Task: Find best available players for [Strategy]
Tools: brave_search            (web search for current stats)
       search_draft_context    (RAG: historical draft patterns & pick context)
       get_team_roster_status  (RAG: live roster snapshot from S3)
Output: 3-5 player recommendations with stats and historical context
```

**🎯 Drafter Agent**
```
Task: Draft one player from recommendations
Tools: draft_specific_player
Output: Selected player + strategic rationale
```

---

## 🔍 Observability

### OpenAI Traces
Every agent run is captured as a named trace in the OpenAI dashboard (e.g., `baseballerinas-drafting Round: 1 Pick: 1`). Each trace shows the full execution tree: every LLM call, tool invocation, input arguments, output, and latency. This makes it straightforward to diagnose why the agent chose a particular player, how many tool calls were made, and where failures occurred.

### AWS CloudWatch Logs
All Lambda functions emit structured log lines tagged by stage, making it easy to trace a single pick end-to-end across the worker and MCP Lambdas:

| Tag | Lambda | What it covers |
|-----|--------|----------------|
| `[Handler]` | worker | Request routing and HTTP response codes |
| `[Worker]` | worker | Draft/team load, agent invocation |
| `[select_player]` | worker | Player pool loading, tool init, agent output |
| `[draft_specific_player]` | mcp-draft | Pick validation, player lookup, DB write, idempotency check |
| `[LambdaMCPInvoker]` | worker | Tool call payloads and responses between Lambdas |
| `[Tool]` | worker | Individual tool call args and results within the agent |

---

## 🛠️ Technology Stack

### Backend
- **Python 3.12** with FastAPI
- **OpenAI Agents SDK** for autonomous agent orchestration
- **Model Context Protocol (MCP)** for tool integration
- **PostgreSQL** (AWS RDS) for persistent storage
- **AWS Lambda** for serverless compute
- **AWS S3** for RAG vector store and draft history
- **EventBridge Scheduler** for automated operations

### Frontend
- **React 18** with functional components
- **Tailwind CSS** for responsive design
- **AWS S3** for static hosting
- **API Gateway** for backend communication

### External APIs
- **OpenAI API** (GPT-4o-mini) for agent intelligence and vector embeddings
- **Brave Search API** for real-time player research

---

## 📊 Configuration

### Current Limits
- **Teams**: 2 (configurable)
- **Rounds**: 4 (configurable)
- **Positions**: 4 (C, 1B, OF, P)
- **Player Pool**: 198 MLB players
- **Active Hours**: 2-4 PM EST daily

---

## 🔮 Future Work: Expanding the Vector Embeddings

The `vectors/draft-insights/` store currently powers `search_draft_context` — a simple cosine similarity search used by the Researcher Agent. Because every pick, rationale, team strategy, and round is already embedded and persisted in S3, the same vector store can support a range of more sophisticated features without any re-indexing. The following are planned extensions, none of which are implemented today.

### 🏆 Draft Grade & Team Evaluation
After each draft, compare a team's picks against the full vector space to score how well the selections matched the declared strategy. A "Power Hitting" team that drafted four contact hitters would score poorly; one that secured high-HR players in scarce positions would score well. Over many drafts, this produces a historical leaderboard of strategy execution.

```
Team picks → embed each pick
      │
      ▼
Compare to all "Power Hitting" strategy vectors
      │
      ▼
Strategy alignment score (0–100) per team per draft
```

### 📈 ADP Trend Analysis
Embed average draft position (ADP) data alongside each pick. Query the vector store across drafts to surface trends: which players are consistently overdrafted relative to their output, which positions tend to be ignored until late rounds, and how ADP shifts as the season progresses. Agents could use this to find value picks before other teams.

### 🎯 Positional Scarcity Forecasting
Use the historical pick vectors to predict, at any point during a draft, how many players remain at each position and how quickly they are typically exhausted. The Drafter Agent could use this signal to reach for a catcher earlier than its strategy would normally dictate, based on scarcity patterns observed across prior sessions.

### 🤝 Strategy vs. Strategy Win Rate
Because each draft stores both team strategy and final roster, it becomes possible to cluster drafts by strategy matchup and measure outcomes. Which strategies tend to dominate? Does "Speed & Defense" consistently outperform "Power Hitting" in head-to-head matchups? With enough sessions, the vector store becomes a lightweight experiment log for strategy evaluation.

### 🔄 Adaptive Agent Personalization
Rather than giving both agents the same `search_draft_context` tool, future versions could pre-filter the vector search by the team's declared strategy — so a "Pitching-First" team only sees historical context from drafts where similar strategies were employed. This reduces noise in the retrieved context and sharpens the agent's recommendations to be strategy-aware from the first query.

### 💡 Implementation Path
All of the above build directly on the existing S3 vector files with no schema changes:

| Feature | Additional Work Needed |
|---------|----------------------|
| Draft grading | Score function + post-draft Lambda trigger |
| ADP trend analysis | Include ADP field in indexer embeddings |
| Scarcity forecasting | Aggregate pick counts per position across vector files |
| Strategy win rate | Add outcome field to draft JSON before indexing |
| Adaptive personalization | Filter `search_draft_context` by strategy tag at query time |

---

## API
![API](https://github.com/aacister/MLB_Draft_Oracle/blob/main/mlb_draft_oracle_api.PNG)

## 🖼️ Screenshots

### Draft History
