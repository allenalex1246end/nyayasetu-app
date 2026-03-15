import React, { useState, useEffect } from 'react'
import { motion } from 'framer-motion'

const container = {
  hidden: { opacity: 0 },
  show: {
    opacity: 1,
    transition: { staggerChildren: 0.1 }
  }
}

const item = {
  hidden: { opacity: 0, y: 20 },
  show: { opacity: 1, y: 0 }
}

export default function MLInsightsPanel({ refresh }) {
  const [insights, setInsights] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    fetchInsights()
  }, [refresh])

  const fetchInsights = async () => {
    try {
      setLoading(true)
      setError(null)
      
      const response = await fetch('http://localhost:8000/api/dashboard/ml-insights', {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('authToken')}`
        }
      })
      
      const data = await response.json()
      if (data.success) {
        setInsights(data.data)
      } else {
        setError(data.error || 'Failed to fetch insights')
      }
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="p-6 bg-white dark:bg-gray-800 rounded-lg shadow-md">
        <div className="animate-pulse space-y-4">
          <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-1/4"></div>
          <div className="space-y-3">
            {[1, 2, 3].map(i => (
              <div key={i} className="h-3 bg-gray-200 dark:bg-gray-700 rounded"></div>
            ))}
          </div>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="p-6 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
        <p className="text-sm text-red-700 dark:text-red-200">Error: {error}</p>
      </div>
    )
  }

  if (!insights) {
    return <div className="p-6 text-center text-gray-500">No insights available</div>
  }

  return (
    <motion.div
      variants={container}
      initial="hidden"
      animate="show"
      className="space-y-4"
    >
      {/* Header */}
      <motion.div variants={item} className="flex items-center justify-between mb-6">
        <h2 className="text-2xl font-bold text-gray-900 dark:text-white">🤖 ML Predictions</h2>
        <button
          onClick={fetchInsights}
          className="text-sm px-3 py-1 bg-blue-500 text-white rounded hover:bg-blue-600 transition"
        >
          Refresh
        </button>
      </motion.div>

      {/* Key Metrics Grid */}
      <motion.div variants={item} className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[
          { label: 'Total Grievances', value: insights.total_grievances, icon: '📋', color: 'blue' },
          { label: 'Avg Resolution', value: `${insights.average_resolution_days?.toFixed(1)}d`, icon: '⏱️', color: 'green' },
          { label: 'At Risk', value: insights.high_risk_count, icon: '⚠️', color: 'orange' },
          { label: 'Top Issue', value: insights.top_issue, icon: '🔝', color: 'purple' },
        ].map((metric, idx) => (
          <motion.div
            key={idx}
            variants={item}
            className={`p-4 bg-gradient-to-br from-${metric.color}-50 to-${metric.color}-100 dark:from-${metric.color}-900/20 dark:to-${metric.color}-800/20 rounded-lg border border-${metric.color}-200 dark:border-${metric.color}-700`}
          >
            <div className="text-2xl mb-1">{metric.icon}</div>
            <div className="text-sm text-gray-600 dark:text-gray-300">{metric.label}</div>
            <div className="text-lg font-bold text-gray-900 dark:text-white">{metric.value}</div>
          </motion.div>
        ))}
      </motion.div>

      {/* High Risk Grievances */}
      {insights.high_risk_grievances && insights.high_risk_grievances.length > 0 && (
        <motion.div variants={item} className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6">
          <h3 className="text-lg font-bold text-red-600 dark:text-red-400 mb-4">🔴 High Risk Grievances</h3>
          <div className="space-y-3 max-h-64 overflow-y-auto">
            {insights.high_risk_grievances.map((g) => (
              <motion.div
                key={g.grievance_id}
                variants={item}
                className="p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-700 rounded-lg"
              >
                <div className="flex items-start justify-between">
                  <div>
                    <p className="font-semibold text-gray-900 dark:text-white text-sm">{g.citizen_name}</p>
                    <p className="text-xs text-gray-600 dark:text-gray-400">{g.category} • {g.ward}</p>
                  </div>
                  <span className={`text-xs font-bold px-2 py-1 rounded ${
                    g.risk_data.risk_level === 'critical' 
                      ? 'bg-red-600 text-white'
                      : g.risk_data.risk_level === 'high'
                      ? 'bg-orange-500 text-white'
                      : 'bg-yellow-500 text-white'
                  }`}>
                    {g.risk_data.risk_level.toUpperCase()}
                  </span>
                </div>
                <p className="text-xs text-gray-700 dark:text-gray-300 mt-2">
                  {g.risk_data.recommendation}
                </p>
              </motion.div>
            ))}
          </div>
        </motion.div>
      )}

      {/* Recommendations */}
      <motion.div variants={item} className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-700 rounded-lg p-6">
        <h3 className="text-lg font-bold text-blue-900 dark:text-blue-200 mb-3">💡 Actionable Insights</h3>
        <ul className="space-y-2 text-sm text-blue-800 dark:text-blue-100">
          {insights.high_risk_count > 0 && (
            <li>• Focus on {insights.high_risk_count} high-risk grievances to prevent SLA breaches</li>
          )}
          {insights.average_resolution_days && (
            <li>• Current avg resolution: {insights.average_resolution_days.toFixed(1)} days (target: 3 days)</li>
          )}
          {insights.top_issue && (
            <li>• {insights.top_issue.toUpperCase()} is the most common issue type</li>
          )}
          {insights.critical_ward && (
            <li>• {insights.critical_ward} requires additional resources</li>
          )}
        </ul>
      </motion.div>
    </motion.div>
  )
}
