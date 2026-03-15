import React, { useState, useEffect } from 'react'
import { ArrowRight, Brain, Zap, TrendingUp, CheckCircle, AlertCircle } from 'lucide-react'
import axios from 'axios'

export default function JudgesShowcase() {
  const [activeAgent, setActiveAgent] = useState('grievance')
  const [demoRunning, setDemoRunning] = useState(false)
  const [demoResult, setDemoResult] = useState(null)
  const [agentStatus, setAgentStatus] = useState(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    fetchAgentStatus()
  }, [])

  const fetchAgentStatus = async () => {
    try {
      const response = await axios.get('http://localhost:8000/api/agents/agents/status')
      setAgentStatus(response.data)
    } catch (error) {
      console.error('Failed to fetch agent status:', error)
    }
  }

  const runGrievanceDemo = async () => {
    setDemoRunning(true)
    try {
      const response = await axios.post('http://localhost:8000/api/agents/grievance/process', {
        grievance_id: 'DEMO_' + Date.now(),
        description: 'My water pipe burst 5 days ago. No government response. I have kids who are sick.',
        ward: 'Ward 5',
        category: 'water',
        phone: '9876543210',
        credibility_score: 85
      })
      setDemoResult(response.data)
    } catch (error) {
      setDemoResult({ error: error.message })
    }
    setDemoRunning(false)
  }

  const runRoutingDemo = async () => {
    setDemoRunning(true)
    try {
      const response = await axios.post('http://localhost:8000/api/agents/grievance/route', {
        grievance_id: 'DEMO_' + Date.now(),
        category: 'water',
        urgency: 4,
        ward: 'Ward 5',
        credibility_score: 85
      })
      setDemoResult(response.data)
    } catch (error) {
      setDemoResult({ error: error.message })
    }
    setDemoRunning(false)
  }

  const runPolicyDemo = async () => {
    setDemoRunning(true)
    try {
      const response = await axios.get('http://localhost:8000/api/agents/governance/brief?scope=all_wards')
      setDemoResult(response.data)
    } catch (error) {
      setDemoResult({ error: error.message })
    }
    setDemoRunning(false)
  }

  const agents = [
    {
      id: 'grievance',
      name: 'Autonomous Grievance Processor',
      icon: Brain,
      color: 'from-purple-600 to-blue-600',
      description: 'Multi-turn reasoning with ReAct pattern',
      capabilities: [
        'Analyzes complaint context and emotional state',
        'Verifies credibility with multi-factor assessment',
        'Checks compliance with policy rules',
        'Retrieves similar historical cases',
        'Makes autonomous decision with reasoning'
      ],
      demo: runGrievanceDemo,
      input: 'Grievance text describing a problem',
      output: 'Decision (accept/escalate/reject) + full reasoning trace'
    },
    {
      id: 'routing',
      name: 'Intelligent Routing Agent',
      icon: Zap,
      color: 'from-blue-600 to-cyan-600',
      description: 'Multi-factor optimization with explainability',
      capabilities: [
        'Evaluates all available officers',
        'Calculates expertise match score',
        'Considers workload and capacity',
        'Analyzes resolution success history',
        'Makes optimal assignment with alternatives'
      ],
      demo: runRoutingDemo,
      input: 'Grievance category, urgency, location',
      output: 'Assigned officer + fit score + reasoning + alternatives'
    },
    {
      id: 'policy',
      name: 'Policy Recommendation Agent',
      icon: TrendingUp,
      color: 'from-green-600 to-teal-600',
      description: 'Pattern mining + governance insights',
      capabilities: [
        'Analyzes 30-day grievance patterns',
        'Identifies systemic policy failures',
        'Detects emerging crisis areas',
        'Proposes targeted interventions',
        'Generates executive governance brief'
      ],
      demo: runPolicyDemo,
      input: 'Scope (all_wards or specific ward)',
      output: 'Pattern analysis + recommendations + action plan'
    }
  ]

  const selectedAgent = agents.find(a => a.id === activeAgent)
  const Icon = selectedAgent?.icon

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900">
      {/* Header */}
      <div className="text-center py-16 px-6">
        <div className="inline-block mb-4 px-4 py-2 bg-purple-500/20 border border-purple-500/50 rounded-full text-purple-200 text-sm font-semibold">
          🤖 GENAI + AGENTIC AI TRACK
        </div>
        <h1 className="text-5xl font-bold text-white mb-4">NyayaSetu Agents</h1>
        <p className="text-xl text-slate-300 max-w-2xl mx-auto">
          Autonomous AI agents with transparent reasoning, multi-turn logic, and explainable decisions
        </p>
      </div>

      {/* Agent Selection */}
      <div className="max-w-6xl mx-auto px-6 mb-12">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
          {agents.map(agent => {
            const AgentIcon = agent.icon
            const isSelected = activeAgent === agent.id
            return (
              <button
                key={agent.id}
                onClick={() => setActiveAgent(agent.id)}
                className={`p-6 rounded-lg transition-all cursor-pointer border-2 ${
                  isSelected
                    ? 'border-white bg-gradient-to-br ' + agent.color + ' text-white'
                    : 'border-slate-600 bg-slate-800 hover:border-slate-500 text-slate-300'
                }`}
              >
                <AgentIcon className="w-8 h-8 mb-3" />
                <h3 className="font-bold">{agent.name}</h3>
                <p className="text-xs mt-2 opacity-80">{agent.description}</p>
              </button>
            )
          })}
        </div>

        {/* Agent Details */}
        {selectedAgent && (
          <div className={`bg-gradient-to-br ${selectedAgent.color} rounded-lg p-8 text-white mb-8`}>
            <div className="flex items-start justify-between mb-6">
              <div>
                <h2 className="text-3xl font-bold mb-2">{selectedAgent.name}</h2>
                <p className="text-white/80">{selectedAgent.description}</p>
              </div>
              <Icon className="w-12 h-12 opacity-40" />
            </div>

            <div className="grid grid-cols-2 gap-4 mb-6">
              <div>
                <h4 className="font-semibold mb-3">Capabilities</h4>
                <ul className="space-y-2">
                  {selectedAgent.capabilities.map((cap, i) => (
                    <li key={i} className="flex items-start gap-2 text-sm">
                      <CheckCircle className="w-4 h-4 mt-0.5 flex-shrink-0" />
                      <span>{cap}</span>
                    </li>
                  ))}
                </ul>
              </div>
              <div>
                <div className="mb-4">
                  <h4 className="font-semibold mb-2">Input</h4>
                  <p className="text-sm bg-white/10 p-3 rounded">{selectedAgent.input}</p>
                </div>
                <div>
                  <h4 className="font-semibold mb-2">Output</h4>
                  <p className="text-sm bg-white/10 p-3 rounded">{selectedAgent.output}</p>
                </div>
              </div>
            </div>

            <button
              onClick={selectedAgent.demo}
              disabled={demoRunning}
              className="w-full bg-white text-slate-900 font-bold py-3 rounded-lg hover:bg-slate-100 disabled:opacity-50 transition-all flex items-center justify-center gap-2"
            >
              {demoRunning ? (
                <>
                  <div className="animate-spin w-5 h-5 border-2 border-slate-900 border-t-transparent rounded-full" />
                  Running Demo...
                </>
              ) : (
                <>
                  <Zap className="w-5 h-5" />
                  Run Live Demo
                </>
              )}
            </button>
          </div>
        )}

        {/* Demo Result */}
        {demoResult && (
          <div className="bg-slate-800 border-2 border-slate-700 rounded-lg p-6 mb-8">
            <h3 className="text-xl font-bold text-white mb-4">Demo Results</h3>
            
            {demoResult.error ? (
              <div className="bg-red-500/20 border border-red-500/50 rounded p-4 text-red-200">
                <AlertCircle className="w-5 h-5 inline mr-2" />
                {demoResult.error}
              </div>
            ) : (
              <div className="space-y-4">
                {/* Success Indicator */}
                {demoResult.success && (
                  <div className="bg-green-500/20 border border-green-500/50 rounded p-4 text-green-200 flex items-center gap-2">
                    <CheckCircle className="w-5 h-5" />
                    Agent completed successfully
                  </div>
                )}

                {/* Decision/Result */}
                {demoResult.assignment && (
                  <div className="bg-slate-700 rounded p-4">
                    <h4 className="font-semibold text-white mb-2">Assignment</h4>
                    <p className="text-slate-200"><strong>Officer:</strong> {demoResult.assignment.assigned_officer_name}</p>
                    <p className="text-slate-200"><strong>Fit Score:</strong> {(demoResult.assignment.fit_score || 0).toFixed(1)}</p>
                    <p className="text-slate-200"><strong>Confidence:</strong> {((demoResult.assignment.confidence || 0) * 100).toFixed(0)}%</p>
                  </div>
                )}

                {demoResult.decision && (
                  <div className="bg-slate-700 rounded p-4">
                    <h4 className="font-semibold text-white mb-2">Decision</h4>
                    <p className="text-slate-200"><strong>Decision:</strong> {demoResult.decision.decision}</p>
                    <p className="text-slate-200 text-sm mt-2"><strong>Reasoning:</strong> {demoResult.decision.reasoning}</p>
                  </div>
                )}

                {demoResult.brief && (
                  <div className="bg-slate-700 rounded p-4">
                    <h4 className="font-semibold text-white mb-2">Brief</h4>
                    <p className="text-slate-200 text-sm">{demoResult.brief.brief?.substring(0, 200)}...</p>
                  </div>
                )}

                {/* Reasoning Trace */}
                {demoResult.reasoning_trace && (
                  <div className="bg-slate-700 rounded p-4">
                    <h4 className="font-semibold text-white mb-3">Reasoning Trace</h4>
                    <div className="space-y-2 text-sm">
                      <div className="text-slate-300">
                        <strong>Iterations:</strong> {demoResult.iterations}
                      </div>
                      {demoResult.reasoning_trace.thoughts && (
                        <div>
                          <strong className="text-white">Thoughts:</strong>
                          <ul className="mt-1 ml-4 space-y-1">
                            {demoResult.reasoning_trace.thoughts.slice(-3).map((t, i) => (
                              <li key={i} className="text-slate-300">• {t.split('] ')[1]?.substring(0, 60)}...</li>
                            ))}
                          </ul>
                        </div>
                      )}
                      <div className="text-slate-400">
                        Duration: {demoResult.reasoning_trace.duration_seconds?.toFixed(2)}s
                      </div>
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Technical Stack */}
      <div className="max-w-6xl mx-auto px-6 mb-12">
        <div className="bg-slate-800 border-2 border-slate-700 rounded-lg p-8">
          <h2 className="text-2xl font-bold text-white mb-6">🏗️ Technical Architecture</h2>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <h3 className="font-semibold text-white mb-3">ReAct Pattern</h3>
              <div className="space-y-2 text-slate-300 text-sm">
                <div className="flex items-start gap-2">
                  <span className="text-blue-400">→</span>
                  <span><strong>THINK:</strong> Reason about the problem</span>
                </div>
                <div className="flex items-start gap-2">
                  <span className="text-blue-400">→</span>
                  <span><strong>ACT:</strong> Retrieve data, call tools</span>
                </div>
                <div className="flex items-start gap-2">
                  <span className="text-blue-400">→</span>
                  <span><strong>REFLECT:</strong> Interpret observations</span>
                </div>
                <div className="flex items-start gap-2">
                  <span className="text-blue-400">→</span>
                  <span><strong>DECIDE:</strong> Make decision with confidence</span>
                </div>
              </div>
            </div>

            <div>
              <h3 className="font-semibold text-white mb-3">Key Features</h3>
              <div className="space-y-2 text-slate-300 text-sm">
                <div className="flex items-start gap-2">
                  <CheckCircle className="w-4 h-4 mt-0.5 text-green-400" />
                  <span>Transparent reasoning trace</span>
                </div>
                <div className="flex items-start gap-2">
                  <CheckCircle className="w-4 h-4 mt-0.5 text-green-400" />
                  <span>Confidence scoring for each decision</span>
                </div>
                <div className="flex items-start gap-2">
                  <CheckCircle className="w-4 h-4 mt-0.5 text-green-400" />
                  <span>Multi-agent shared memory & learning</span>
                </div>
                <div className="flex items-start gap-2">
                  <CheckCircle className="w-4 h-4 mt-0.5 text-green-400" />
                  <span>Tool use for data retrieval & verification</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Agent Status */}
      {agentStatus && (
        <div className="max-w-6xl mx-auto px-6 mb-12">
          <div className="bg-slate-800 border-2 border-slate-700 rounded-lg p-8">
            <h2 className="text-2xl font-bold text-white mb-6">📊 Agent Status</h2>
            
            <div className="space-y-4">
              {Object.entries(agentStatus.agents || {}).map(([name, status]) => (
                <div key={name} className="flex items-center gap-4 p-4 bg-slate-700 rounded">
                  <div className="w-3 h-3 bg-green-500 rounded-full animate-pulse"></div>
                  <div className="flex-1">
                    <p className="font-semibold text-white">{name}</p>
                    <p className="text-slate-400 text-sm">{status.role}</p>
                  </div>
                  <span className="text-green-400 font-semibold">{status.status}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Footer */}
      <div className="bg-slate-900 border-t border-slate-700 py-12 px-6 my-12">
        <div className="max-w-6xl mx-auto text-center">
          <h3 className="text-2xl font-bold text-white mb-4">Ready for Production</h3>
          <p className="text-slate-400 mb-6">
            These agents demonstrate enterprise-grade agentic AI with transparency, explainability, and measurable impact on governance intelligence.
          </p>
          <div className="flex flex-wrap justify-center gap-4">
            <span className="px-4 py-2 bg-purple-500/20 border border-purple-500/50 rounded-full text-purple-200 text-sm">
              Multi-turn Reasoning
            </span>
            <span className="px-4 py-2 bg-blue-500/20 border border-blue-500/50 rounded-full text-blue-200 text-sm">
              Explainable Decisions
            </span>
            <span className="px-4 py-2 bg-green-500/20 border border-green-500/50 rounded-full text-green-200 text-sm">
              Scalable Architecture
            </span>
            <span className="px-4 py-2 bg-cyan-500/20 border border-cyan-500/50 rounded-full text-cyan-200 text-sm">
              Real-time Processing
            </span>
          </div>
        </div>
      </div>
    </div>
  )
}
