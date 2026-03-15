import React from 'react'
import { formatDistanceToNow } from 'date-fns'

export default function AssignmentCard({ assignment, onStatusUpdate, loading }) {
  const { grievance, status, assigned_at } = assignment

  const getUrgencyColor = (urgency) => {
    if (urgency >= 4) return 'text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-900'
    if (urgency === 3) return 'text-yellow-600 dark:text-yellow-400 bg-yellow-50 dark:bg-yellow-900'
    return 'text-green-600 dark:text-green-400 bg-green-50 dark:bg-green-900'
  }

  const getStatusBadge = (status) => {
    switch (status) {
      case 'assigned':
        return 'bg-blue-100 dark:bg-blue-900 text-blue-800 dark:text-blue-200'
      case 'in_progress':
        return 'bg-purple-100 dark:bg-purple-900 text-purple-800 dark:text-purple-200'
      case 'completed':
        return 'bg-green-100 dark:bg-green-900 text-green-800 dark:text-green-200'
      default:
        return 'bg-gray-100 dark:bg-gray-700 text-gray-800 dark:text-gray-200'
    }
  }

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-5 hover:shadow-md transition-shadow">
      {/* Header */}
      <div className="flex items-start justify-between mb-4">
        <div className="flex-1">
          <h3 className="text-lg font-semibold text-gray-800 dark:text-white mb-1">
            {grievance.category ? grievance.category.toUpperCase() : 'OTHER'}
          </h3>
          <p className="text-sm text-gray-600 dark:text-gray-400">
            From: {grievance.citizen_name}
          </p>
        </div>
        <div className="text-right">
          <div className={`inline-block px-3 py-1 rounded-full text-xs font-semibold ${getStatusBadge(status)}`}>
            {status.replace('_', ' ').toUpperCase()}
          </div>
        </div>
      </div>

      {/* Details Grid */}
      <div className="grid grid-cols-2 gap-4 mb-4 text-sm">
        <div>
          <p className="text-gray-600 dark:text-gray-400">Ward</p>
          <p className="font-medium text-gray-800 dark:text-white">{grievance.ward}</p>
        </div>
        <div>
          <p className="text-gray-600 dark:text-gray-400">Urgency</p>
          <div className={`inline-block px-2 py-1 rounded font-semibold text-xs ${getUrgencyColor(grievance.urgency)}`}>
            {'⚠️'.repeat(grievance.urgency || 1)} Level {grievance.urgency || 1}
          </div>
        </div>
        <div>
          <p className="text-gray-600 dark:text-gray-400">Phone</p>
          <p className="font-medium text-gray-800 dark:text-white">{grievance.phone || 'N/A'}</p>
        </div>
        <div>
          <p className="text-gray-600 dark:text-gray-400">Assigned</p>
          <p className="font-medium text-gray-800 dark:text-white">
            {formatDistanceToNow(new Date(assigned_at), { addSuffix: true })}
          </p>
        </div>
      </div>

      {/* Description */}
      <div className="mb-4 p-3 bg-gray-50 dark:bg-gray-700 rounded-lg">
        <p className="text-sm text-gray-700 dark:text-gray-300">{grievance.description}</p>
      </div>

      {/* AI Summary */}
      {grievance.ai_summary && (
        <div className="mb-4 p-3 bg-blue-50 dark:bg-blue-900 border border-blue-200 dark:border-blue-700 rounded-lg">
          <p className="text-xs font-semibold text-blue-800 dark:text-blue-300 mb-1">AI Summary</p>
          <p className="text-sm text-blue-900 dark:text-blue-200">{grievance.ai_summary}</p>
        </div>
      )}

      {/* Status Update Form */}
      {status !== 'completed' && (
        <div className="border-t border-gray-200 dark:border-gray-700 pt-4">
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
            Mark As
          </label>
          <div className="flex gap-2">
            <button
              onClick={() => onStatusUpdate(grievance.id, 'in_progress')}
              disabled={loading || status === 'in_progress'}
              className="flex-1 px-3 py-2 bg-purple-600 hover:bg-purple-700 disabled:bg-gray-400 text-white text-sm font-semibold rounded-lg transition"
            >
              In Progress
            </button>
            <button
              onClick={() => onStatusUpdate(grievance.id, 'resolved')}
              disabled={loading}
              className="flex-1 px-3 py-2 bg-green-600 hover:bg-green-700 disabled:bg-gray-400 text-white text-sm font-semibold rounded-lg transition"
            >
              Resolved
            </button>
            <button
              onClick={() => onStatusUpdate(grievance.id, 'rejected')}
              disabled={loading}
              className="flex-1 px-3 py-2 bg-red-600 hover:bg-red-700 disabled:bg-gray-400 text-white text-sm font-semibold rounded-lg transition"
            >
              Reject
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
