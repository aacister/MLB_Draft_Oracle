# ⚾ MLB Draft Oracle

> An AI-powered MLB fantasy draft simulator where autonomous agents compete to build the best team

**[Live Demo - mlbdraftoracle.com](http://mlbdraftoracle.com)** | Available daily 2-4 PM EST

[![AWS](https://img.shields.io/badge/AWS-Lambda-orange)](https://aws.amazon.com/lambda/)
[![Python](https://img.shields.io/badge/Python-3.12-blue)](https://www.python.org/)
[![OpenAI](https://img.shields.io/badge/OpenAI-gpt--4o--mini-green)](https://openai.com/)
[![React](https://img.shields.io/badge/React-18-blue)](https://reactjs.org/)

---

## 🎯 Overview

MLB Draft Oracle is an autonomous AI draft simulator that pits two AI-powered teams against each other in a fantasy baseball draft. Each team is assigned a unique strategy (e.g., "Power Hitting" vs "Speed & Defense") and uses intelligent agents to research players, analyze statistics, and make strategic picks—complete with detailed rationales for every selection.

**Watch as AI teams:**
- 🔍 Research real 2025 MLB player statistics via web search
- 🤔 Evaluate players based on their team strategy
- 🎯 Draft players with detailed reasoning
- 📊 Build optimized rosters position by position

---

## ✨ Key Features

### 🤖 **Autonomous AI Agents**
- **Researcher Agent**: Searches the web for current MLB player stats and news
- **Drafter Agent**: Evaluates candidates and executes draft picks with strategic rationale
- Powered by OpenAI's GPT-4o-mini and the OpenAI Agents SDK

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

### 💰 **Cost-Optimized Design**
- Site active only 2-4 PM EST daily (automatic start/stop)
- RDS database auto-cleanup after each session
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
           └─────────┬───────────────────┘
                     │
        ┌────────────┴────────────┐
        │                         │
        ▼                         ▼
┌──────────────────┐    ┌──────────────────────┐
│ mcp-draft        │    │ mcp-brave-search     │
│ (Draft Tool)     │    │ (Web Search Tool)    │
└──────────────────┘    └──────────────────────┘
        │                         │
        └────────────┬────────────┘
                     ▼
           ┌─────────────────────┐
           │  PostgreSQL RDS      │
           │  (Draft Database)    │
           └─────────────────────┘
```

### Lambda Functions

1. **`mlb-draft-oracle-worker`** (Main Orchestrator)
   - Manages draft flow and agent coordination
   - Invokes MCP Lambda functions for tools
   - Uses OpenAI Agents SDK with two agents per team

2. **`mlb-draft-oracle-mcp-draft`** (MCP Server)
   - Provides `draft_specific_player` tool
   - Handles draft validation and database updates
   - Implements position-filling logic

3. **`mlb-draft-oracle-mcp-brave-search`** (MCP Server)
   - Provides web search capabilities via Brave Search API
   - Enables agents to research current MLB player stats
   - Returns real 2025 season data

### Database Schema

**PostgreSQL RDS** stores:
- Draft state (current round, pick)
- Team rosters and strategies
- Player pool (198 MLB players with 2025 stats)
- Draft history with pick rationales

---

## 🚀 How It Works

### Draft Flow

1. **Initialization**
   - Two teams created with assigned strategies
   - Player pool loaded (198 MLB players with 2025 stats)
   - Draft order determined (snake draft format)

2. **For Each Pick**
   - **Researcher Agent** searches web for player stats and news
   - Filters results to available players only
   - Provides recommendations based on team strategy
   
3. **Drafter Agent** receives recommendations
   - Evaluates candidates against roster needs
   - Calls `draft_specific_player` tool with selection
   - Includes detailed rationale for the pick
   
4. **Draft Execution**
   - Validates position availability
   - Updates roster and draft history
   - Marks player as drafted
   - Proceeds to next team's pick

5. **Completion**
   - Final rosters displayed
   - Draft history with all rationales shown
   - Database cleaned up before site shutdown

### Agent Intelligence

Each team employs a **two-agent system**:

**🔬 Researcher Agent**
```
Task: Find best available players for [Strategy]
Tools: brave_search (web search)
Output: 3-5 player recommendations with stats
```

**🎯 Drafter Agent**
```
Task: Draft one player from recommendations
Tools: draft_specific_player
Output: Selected player + strategic rationale
```

---

## 🛠️ Technology Stack

### Backend
- **Python 3.12** with FastAPI
- **OpenAI Agents SDK** for autonomous agent orchestration
- **Model Context Protocol (MCP)** for tool integration
- **PostgreSQL** (AWS RDS) for persistent storage
- **AWS Lambda** for serverless compute
- **EventBridge Scheduler** for automated operations

### Frontend
- **React 18** with functional components
- **Tailwind CSS** for responsive design
- **AWS S3** for static hosting
- **API Gateway** for backend communication

### External APIs
- **OpenAI API** (GPT-4o-mini) for agent intelligence
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

## 🖼️ Screenshots

### Draft History
![Draft History showing AI pick rationales](https://github.com/aacister/MLB_Draft_Oracle/blob/main/MlbDraftOracle_snapshot.PNG)

### Team Rosters
![Final team rosters with player stats](https://github.com/aacister/MLB_Draft_Oracle/blob/main/MlbDraftOracle_roster.PNG)

---
