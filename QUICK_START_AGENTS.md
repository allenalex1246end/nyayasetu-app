# 🚀 QUICK START - NyayaSetu Agentic AI

Run the complete demo in **5 minutes**.

---

## ⚡ 60-Second Setup

### 1️⃣ Backend Setup (Ctrl+C to stop anytime)

```bash
# Terminal 1: Backend
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy environment template
cp .env.template .env

# Edit .env and add your API keys:
# - GROQ_API_KEY (from https://console.groq.com)
# - SUPABASE_URL & SUPABASE_KEY (from https://supabase.com)
# - GOOGLE_API_KEY (from https://aistudio.google.com/apikey)

# Run backend
python -m uvicorn main:app --reload --port 8000
```

**✅ Backend ready:** http://localhost:8000

### 2️⃣ Frontend Setup (new terminal)

```bash
# Terminal 2: Frontend
cd frontend

# Install dependencies
npm install

# Start dev server
npm run dev
```

**✅ Frontend ready:** http://localhost:5173

---

## 🎯 JUDGES DEMO (3 clicks)

### View the Showcase

1. Open: **http://localhost:5173/showcase**
2. You'll see three agent cards (Grievance Processor, Router, Policy)
3. Click **"Run Live Demo"** on each card

### Watch Agents in Action

Each demo shows:
- ✅ Agent reasoning step-by-step
- ✅ Data retrieval from database
- ✅ Decision logic with confidence score
- ✅ Complete audit trail for compliance

---

## 🖥️ API Testing (For Advanced Users)

### Test Autonomous Grievance Processing

```bash
curl -X POST http://localhost:8000/api/agents/grievance/process \
  -H "Content-Type: application/json" \
  -d '{
    "grievance_id": "DEMO_001",
    "description": "My water pipe burst 5 days ago. No government response. I have kids who are sick.",
    "ward": "Ward 5",
    "category": "water",
    "phone": "9876543210",
    "credibility_score": 85
  }'
```

**Response:** Complete agent decision with reasoning trace

### Test Intelligent Officer Routing

```bash
curl -X POST http://localhost:8000/api/agents/grievance/route \
  -H "Content-Type: application/json" \
  -d '{
    "grievance_id": "DEMO_002",
    "category": "water",
    "urgency": 4,
    "ward": "Ward 5",
    "credibility_score": 85
  }'
```

**Response:** Optimal officer assignment with alternatives

### Test Governance Intelligence

```bash
curl -X GET http://localhost:8000/api/agents/governance/brief
```

**Response:** Governance analysis with recommendations

### Check Agent Status

```bash
curl -X GET http://localhost:8000/api/agents/agents/status
```

**Response:** All agents active + collective memory insights

---

## 📚 KEY FILES FOR JUDGES

### Backend Agents
- `backend/agents/base_agent.py` - ReAct pattern framework
- `backend/agents/grievance_processor_agent.py` - Autonomous processing
- `backend/agents/routing_agent.py` - Intelligent assignment
- `backend/agents/policy_agent.py` - Governance intelligence
- `backend/agents/agent_memory.py` - Learning system
- `backend/routers/agents.py` - API endpoints

### Frontend Demo
- `frontend/src/pages/JudgesShowcase.jsx` - Interactive showcase
- `frontend/src/App.jsx` - Route registration

### Documentation
- `AGENTS_README.md` - Complete technical documentation
- `README.md` - Project overview

---

## 🆘 TROUBLESHOOTING

### "Groq API not configured"
```
Solution: Add GROQ_API_KEY to .env file
Get key: https://console.groq.com → API Keys
```

### "Supabase connection failed"
```
Solution: Add SUPABASE_URL and SUPABASE_KEY to .env
Test: Each endpoint shows {"success": false} with appropriate error
```

### "Port 8000/5173 already in use"
```
Solution: Use different ports
python -m uvicorn main:app --port 8001
npm run dev -- --port 5174
```

### "Module not found" errors
```
Solution: Ensure you activated venv before pip install
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt
```

---

## ✨ WHAT YOU'LL SEE

### Live Agent Showcase
```
┌────────────────────────────────────────────┐
│  NyayaSetu Agents - Judges Showcase        │
├────────────────────────────────────────────┤
│                                            │
│  [🧠 Processor] [⚡ Router] [📈 Policy]   │
│                                            │
│  Click any agent → Run Live Demo           │
│  ↓                                         │
│  Agent starts reasoning...                 │
│  Fetches data from database...             │
│  Calculates decisions...                   │
│  Shows confidence & alternatives...        │
│  ↓                                         │
│  Full reasoning trace visible below        │
│  (Auditable for compliance)                │
│                                            │
└────────────────────────────────────────────┘
```

### Agent Reasoning Flow
```
INPUT: Grievance text
  ↓
THINK: Analyze problem context
  ↓
ACT: Retrieve data, verify credibility
  ↓
REFLECT: Interpret observations
  ↓
DECIDE: Make decision with confidence
  ↓
OUTPUT: Decision + Reasoning + Audit Trail
```

---

## 🎓 FOR JUDGES EVALUATING

### Check These Features:

✅ **Reasoning Transparency**
- Every step logged
- Thoughts visible in trace
- Observations recorded
- Decisions explained

✅ **Multi-Factor Analysis**
- Considers multiple factors
- Weights each appropriately
- Shows trade-offs

✅ **Confidence Scoring**
- Each decision has 0-100% confidence
- Acknowledges uncertainty
- Officers know when to verify

✅ **Scalability**
- Agents work independently
- Can run in parallel
- Shared memory for learning

✅ **Real-world Impact**
- Actually makes governance decisions
- Autonomous (doesn't need human approval for simple cases)
- Transparent to citizens

---

## 📞 LIVE SUPPORT

If agents crash or show errors:

1. Check backend console for error messages
2. Verify API keys in .env file
3. Check database connection in Supabase dashboard
4. Frontend console (F12) may show axios errors

**Backend logs show:**
```
[INFO] GrievanceProcessor iteration 1
[INFO] Grievance analysis: {...}
[INFO] Compliance check: {...}
[INFO] Agent decision made with confidence 0.94
```

---

## 🎬 RECORDING THE DEMO

For judges who want to record:

1. Open `/showcase` page
2. Screen record (OBS Studio / ScreenFlow)
3. Click "Run Live Demo" for each agent
4. Let demos complete (shows full reasoning)
5. Stop recording (~2 min per agent = 6 min total)

**Pro tip:** Show the reasoning trace - that's what impresses judges! 💡

---

## ✨ Next Steps After Demo

To extend the system:
- Add more agents for other tasks
- Implement multi-agent collaboration
- Add real-time WebSocket updates
- Deploy to production (Railway/Render)
- Integrate mobile app

See `AGENTS_README.md` for more details.

---

**Status:** ✅ Ready to Impress  
**Track:** GenAI + Agentic AI  
**Time to Awesome:** 5 minutes ⚡

Good luck! 🚀
