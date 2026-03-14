import React, { useState, useEffect, useCallback } from 'react'
import {
  getRailwayDashboardStats,
  getRailwayDashboardClusters,
  getRailwayDashboardTrends,
  getRailwayGrievances,
  resolveRailwayGrievance,
  generateRailwayBrief,
} from '../api'
import StatCard from '../components/StatCard'
import ClusterCard from '../components/ClusterCard'
import LoadingSpinner from '../components/LoadingSpinner'
import ErrorCard from '../components/ErrorCard'
import Toast from '../components/Toast'
import UrgencyBadge from '../components/UrgencyBadge'
import { BarChart, Bar, PieChart, Pie, Cell, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from 'recharts'

const TABS = ['Dashboard', 'Complaints', 'Clusters', 'Generate Brief']
const PIE_COLORS = ['#3B82F6', '#10B981', '#EF4444', '#F59E0B', '#8B5CF6', '#6B7280']

export default function RailwayDashboard() {
  const [activeTab, setActiveTab] = useState('Dashboard')
  const [toast, setToast] = useState(null)

  const [stats, setStats] = useState(null)
  const [trends, setTrends] = useState(null)
  const [statsLoading, setStatsLoading] = useState(true)
  const [statsError, setStatsError] = useState(null)

  const [grievances, setGrievances] = useState([])
  const [grievancesLoading, setGrievancesLoading] = useState(false)
  const [grievancesError, setGrievancesError] = useState(null)

  const [clusters, setClusters] = useState([])
  const [clustersLoading, setClustersLoading] = useState(false)
  const [clustersError, setClustersError] = useState(null)

  const [brief, setBrief] = useState('')
  const [briefLoading, setBriefLoading] = useState(false)
  const [briefError, setBriefError] = useState(null)

  const fetchDashboard = useCallback(async () => {
    setStatsLoading(true)
    setStatsError(null)
    try {
      const [statsRes, trendsRes] = await Promise.all([
        getRailwayDashboardStats(),
        getRailwayDashboardTrends(),
      ])
      setStats(statsRes?.data?.data || statsRes?.data || null)
      setTrends(trendsRes?.data?.data || trendsRes?.data || null)
    } catch (err) {
      setStatsError(err?.message || 'Failed to load dashboard')
    } finally {
      setStatsLoading(false)
    }
  }, [])

  const fetchGrievances = useCallback(async () => {
    setGrievancesLoading(true)
    setGrievancesError(null)
    try {
      const res = await getRailwayGrievances({ limit: 100 })
      setGrievances(res?.data?.data || res?.data || [])
    } catch (err) {
      setGrievancesError(err?.message || 'Failed to load complaints')
    } finally {
      setGrievancesLoading(false)
    }
  }, [])

  const fetchClusters = useCallback(async () => {
    setClustersLoading(true)
    setClustersError(null)
    try {
      const res = await getRailwayDashboardClusters()
      setClusters(res?.data?.data || res?.data || [])
    } catch (err) {
      setClustersError(err?.message || 'Failed to load clusters')
    } finally {
      setClustersLoading(false)
    }
  }, [])

  useEffect(() => {
    try {
      if (activeTab === 'Dashboard') fetchDashboard()
      else if (activeTab === 'Complaints') fetchGrievances()
      else if (activeTab === 'Clusters') fetchClusters()
    } catch (err) {
      console.error('Tab load error:', err)
    }
  }, [activeTab, fetchDashboard, fetchGrievances, fetchClusters])

  const handleResolve = async (id) => {
    try {
      const res = await resolveRailwayGrievance(id)
      const msg = res?.data?.data?.message || 'Railway grievance resolved'
      setToast({ message: msg, type: 'success' })
      fetchGrievances()
      fetchDashboard()
    } catch (err) {
      setToast({ message: err?.message || 'Failed to resolve', type: 'error' })
    }
  }

  const handleGenerateBrief = async () => {
    setBriefLoading(true)
    setBriefError(null)
    try {
      const res = await generateRailwayBrief()
      setBrief(res?.data?.data?.brief || res?.data?.brief || 'No brief generated.')
    } catch (err) {
      setBriefError(err?.message || 'Failed to generate brief')
    } finally {
      setBriefLoading(false)
    }
  }

  return (
    <div className="flex min-h-[calc(100vh-64px)]">
      {toast && (
        <Toast message={toast.message} type={toast.type} onClose={() => setToast(null)} />
      )}

      {/* Sidebar */}
      <aside className="hidden w-56 shrink-0 border-r border-gray-200 bg-white lg:block">
        <div className="p-4">
          <h2 className="mb-4 font-heading text-lg font-bold text-navy">Railway Officer</h2>
          <nav className="space-y-1">
            {TABS.map((tab) => (
              <button
                key={tab}
                onClick={() => setActiveTab(tab)}
                className={`w-full rounded-lg px-3 py-2 text-left text-sm font-medium font-body transition-colors ${
                  activeTab === tab
                    ? 'bg-accent/10 text-accent'
                    : 'text-gray-600 hover:bg-gray-50 hover:text-navy'
                }`}
              >
                {tab}
              </button>
            ))}
          </nav>
        </div>
      </aside>

      {/* Mobile tab bar */}
      <div className="fixed bottom-0 left-0 right-0 z-40 flex border-t border-gray-200 bg-white lg:hidden">
        {TABS.map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`flex-1 py-3 text-xs font-bold font-body transition-colors ${
              activeTab === tab ? 'text-accent bg-accent/5' : 'text-gray-500'
            }`}
          >
            {tab.split(' ')[0]}
          </button>
        ))}
      </div>

      {/* Main content */}
      <main className="flex-1 overflow-auto p-4 pb-20 sm:p-6 lg:p-8 lg:pb-8">
        {/* DASHBOARD TAB */}
        {activeTab === 'Dashboard' && (
          <div>
            <h1 className="mb-6 font-heading text-2xl font-bold text-navy">Railway Dashboard</h1>
            {statsError && <ErrorCard message={statsError} onRetry={fetchDashboard} />}
            {statsLoading ? (
              <LoadingSpinner message="Loading railway dashboard..." />
            ) : (
              <>
                <div className="mb-8 grid grid-cols-2 gap-4 lg:grid-cols-4">
                  <StatCard title="Total Complaints" value={stats?.total ?? 0} color="border-navy" icon="🚂" />
                  <StatCard title="Open" value={stats?.open ?? 0} color="border-blue-500" icon="📂" />
                  <StatCard title="Critical" value={stats?.critical ?? 0} color="border-critical" icon="🚨" />
                  <StatCard title="Active Clusters" value={stats?.clusters_active ?? 0} color="border-accent" icon="🔗" />
                </div>

                {trends && (
                  <div className="mb-8 grid gap-4 lg:grid-cols-2">
                    <div className="rounded-lg border border-gray-200 bg-white p-4 shadow-sm">
                      <h3 className="mb-3 font-heading text-sm font-semibold text-navy">Complaints by Category</h3>
                      <ResponsiveContainer width="100%" height={250}>
                        <BarChart data={trends.by_category || []}>
                          <CartesianGrid strokeDasharray="3 3" />
                          <XAxis dataKey="name" tick={{ fontSize: 11 }} />
                          <YAxis allowDecimals={false} />
                          <Tooltip />
                          <Bar dataKey="count" fill="#10B981" radius={[4, 4, 0, 0]} />
                        </BarChart>
                      </ResponsiveContainer>
                    </div>

                    <div className="rounded-lg border border-gray-200 bg-white p-4 shadow-sm">
                      <h3 className="mb-3 font-heading text-sm font-semibold text-navy">Status Distribution</h3>
                      <ResponsiveContainer width="100%" height={250}>
                        <PieChart>
                          <Pie
                            data={trends.by_status || []}
                            dataKey="count"
                            nameKey="name"
                            cx="50%"
                            cy="50%"
                            outerRadius={90}
                            label={({ name, count }) => `${name} (${count})`}
                          >
                            {(trends.by_status || []).map((_, i) => (
                              <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />
                            ))}
                          </Pie>
                          <Tooltip />
                          <Legend />
                        </PieChart>
                      </ResponsiveContainer>
                    </div>
                  </div>
                )}

                {/* By Zone chart */}
                {trends?.by_zone && (
                  <div className="mb-8 rounded-lg border border-gray-200 bg-white p-4 shadow-sm">
                    <h3 className="mb-3 font-heading text-sm font-semibold text-navy">Complaints by Railway Zone</h3>
                    <ResponsiveContainer width="100%" height={250}>
                      <BarChart data={trends.by_zone || []} layout="vertical">
                        <CartesianGrid strokeDasharray="3 3" />
                        <XAxis type="number" allowDecimals={false} />
                        <YAxis dataKey="name" type="category" tick={{ fontSize: 10 }} width={120} />
                        <Tooltip />
                        <Bar dataKey="count" fill="#3B82F6" radius={[0, 4, 4, 0]} />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                )}
              </>
            )}
          </div>
        )}

        {/* COMPLAINTS TAB */}
        {activeTab === 'Complaints' && (
          <div>
            <div className="mb-6 flex items-center justify-between">
              <h1 className="font-heading text-2xl font-bold text-navy">Railway Complaints</h1>
              <button
                onClick={fetchGrievances}
                className="rounded-lg bg-gray-100 px-4 py-2 text-sm font-medium font-body text-gray-700 hover:bg-gray-200 transition-colors"
              >
                Refresh
              </button>
            </div>

            {grievancesError && <ErrorCard message={grievancesError} onRetry={fetchGrievances} />}

            {grievancesLoading ? (
              <LoadingSpinner message="Loading complaints..." />
            ) : grievances.length === 0 ? (
              <div className="rounded-lg border border-gray-200 bg-white p-12 text-center text-gray-400 font-body">
                No railway complaints yet.
              </div>
            ) : (
              <div className="overflow-x-auto rounded-lg border border-gray-200 bg-white shadow-sm">
                <table className="min-w-full divide-y divide-gray-200">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 font-body">Train</th>
                      <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 font-body">Zone</th>
                      <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 font-body">Passenger</th>
                      <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 font-body">Summary</th>
                      <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 font-body">Urgency</th>
                      <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 font-body">Status</th>
                      <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 font-body">Action</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100">
                    {grievances.map((g, idx) => (
                      <tr key={g?.id || idx} className="hover:bg-gray-50">
                        <td className="px-4 py-3 text-sm font-body font-medium text-gray-900">{g.train_number}</td>
                        <td className="px-4 py-3 text-sm font-body text-gray-600">{g.railway_zone?.replace(' Railway', '')}</td>
                        <td className="px-4 py-3 text-sm font-body text-gray-600">{g.passenger_name}</td>
                        <td className="max-w-xs truncate px-4 py-3 text-sm font-body text-gray-600">{g.ai_summary || g.description?.slice(0, 60)}</td>
                        <td className="px-4 py-3"><UrgencyBadge level={g.urgency} /></td>
                        <td className="px-4 py-3">
                          <span className={`inline-flex rounded-full px-2 py-0.5 text-xs font-semibold ${
                            g.status === 'open' ? 'bg-blue-100 text-blue-700' :
                            g.status === 'resolved' ? 'bg-green-100 text-green-700' :
                            g.status === 'closed' ? 'bg-gray-100 text-gray-700' :
                            'bg-red-100 text-red-700'
                          }`}>
                            {g.status}
                          </span>
                        </td>
                        <td className="px-4 py-3">
                          {g.status === 'open' && (
                            <button
                              onClick={() => handleResolve(g.id)}
                              className="rounded bg-green-500 px-3 py-1 text-xs font-semibold text-white hover:bg-green-600"
                            >
                              Resolve
                            </button>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}

        {/* CLUSTERS TAB */}
        {activeTab === 'Clusters' && (
          <div>
            <div className="mb-6 flex items-center justify-between">
              <h1 className="font-heading text-2xl font-bold text-navy">Railway Complaint Clusters</h1>
              <button
                onClick={fetchClusters}
                className="rounded-lg bg-gray-100 px-4 py-2 text-sm font-medium font-body text-gray-700 hover:bg-gray-200 transition-colors"
              >
                Refresh
              </button>
            </div>
            {clustersError && <ErrorCard message={clustersError} onRetry={fetchClusters} />}
            {clustersLoading ? (
              <LoadingSpinner message="Loading clusters..." />
            ) : clusters.length === 0 ? (
              <div className="rounded-lg border border-gray-200 bg-white p-12 text-center text-gray-400 font-body">
                No active railway clusters. Clusters are detected automatically every 10 minutes.
              </div>
            ) : (
              <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
                {clusters.map((cluster, idx) => (
                  <ClusterCard key={cluster?.id || idx} cluster={cluster} />
                ))}
              </div>
            )}
          </div>
        )}

        {/* GENERATE BRIEF TAB */}
        {activeTab === 'Generate Brief' && (
          <div className="print-full">
            <h1 className="mb-6 font-heading text-2xl font-bold text-navy no-print">
              Railway Intelligence Brief
            </h1>
            {!brief && !briefLoading && !briefError && (
              <div className="text-center py-12">
                <button
                  onClick={handleGenerateBrief}
                  disabled={briefLoading}
                  className="rounded-lg bg-accent px-8 py-3 text-base font-semibold text-white shadow-sm transition-all hover:bg-accent/90 focus:outline-none focus:ring-2 focus:ring-accent focus:ring-offset-2 disabled:opacity-50"
                >
                  Generate Railway Intelligence Brief
                </button>
                <p className="mt-3 text-sm text-gray-400 font-body">
                  AI will analyse all active railway clusters and generate a report
                </p>
              </div>
            )}
            {briefLoading && <LoadingSpinner message="AI is analysing railway patterns..." />}
            {briefError && <ErrorCard message={briefError} onRetry={handleGenerateBrief} />}
            {brief && !briefLoading && (
              <div>
                <div className="no-print mb-4 flex gap-3">
                  <button onClick={handleGenerateBrief} className="rounded-lg bg-gray-100 px-4 py-2 text-sm font-medium font-body text-gray-700 hover:bg-gray-200 transition-colors">
                    Regenerate
                  </button>
                  <button onClick={() => window.print()} className="rounded-lg bg-navy px-4 py-2 text-sm font-medium font-body text-white hover:bg-navy/90 transition-colors">
                    Export as PDF
                  </button>
                </div>
                <div className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm prose prose-sm max-w-none font-body">
                  {brief.split('\n').map((line, i) => {
                    if (!line.trim()) return <br key={i} />
                    if (line.startsWith('# ')) return <h1 key={i} className="font-heading text-xl font-bold text-navy mt-4 mb-2">{line.slice(2)}</h1>
                    if (line.startsWith('## ')) return <h2 key={i} className="font-heading text-lg font-semibold text-navy mt-4 mb-2">{line.slice(3)}</h2>
                    if (line.startsWith('### ')) return <h3 key={i} className="font-heading text-base font-semibold text-navy mt-3 mb-1">{line.slice(4)}</h3>
                    if (line.startsWith('- ')) return <li key={i} className="ml-4 text-gray-700">{line.slice(2)}</li>
                    if (line.startsWith('**') && line.endsWith('**')) return <p key={i} className="font-bold text-gray-800">{line.slice(2, -2)}</p>
                    return <p key={i} className="text-gray-700 leading-relaxed">{line}</p>
                  })}
                </div>
              </div>
            )}
          </div>
        )}
      </main>
    </div>
  )
}
