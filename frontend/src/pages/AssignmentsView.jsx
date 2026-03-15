import React, { useState, useEffect } from 'react'
import { getMyAssignments, updateGrievanceStatus } from '../api'
import AssignmentCard from '../components/AssignmentCard'
import Toast from '../components/Toast'
import LoadingSpinner from '../components/LoadingSpinner'
import ErrorCard from '../components/ErrorCard'
import StatusUpdateForm from '../components/StatusUpdateForm'

export default function AssignmentsView() {
  const [assignments, setAssignments] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [toast, setToast] = useState(null)
  const [selectedGrievance, setSelectedGrievance] = useState(null)
  const [statusUpdateLoading, setStatusUpdateLoading] = useState(false)
  const [filterStatus, setFilterStatus] = useState(null)

  useEffect(() => {
    fetchAssignments()
  }, [filterStatus])

  const fetchAssignments = async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await getMyAssignments(filterStatus)
      setAssignments(res?.data?.data || [])
    } catch (err) {
      console.error('Fetch assignments error:', err)
      setError(err?.message || 'Failed to load assignments')
    } finally {
      setLoading(false)
    }
  }

  const handleStatusUpdate = async (grievanceId, status, notes = '') => {
    setStatusUpdateLoading(true)
    try {
      await updateGrievanceStatus(grievanceId, {
        status,
        notes,
      })
      setToast({ message: `Grievance marked as ${status}`, type: 'success' })
      setSelectedGrievance(null)
      fetchAssignments()
    } catch (err) {
      console.error('Status update error:', err)
      setToast({ message: err?.message || 'Failed to update status', type: 'error' })
    } finally {
      setStatusUpdateLoading(false)
    }
  }

  const handleQuickStatusUpdate = async (grievanceId, status) => {
    setStatusUpdateLoading(true)
    try {
      await updateGrievanceStatus(grievanceId, {
        status,
        notes: `Quick update to ${status}`,
      })
      setToast({ message: `Grievance marked as ${status}`, type: 'success' })
      fetchAssignments()
    } catch (err) {
      console.error('Status update error:', err)
      setToast({ message: err?.message || 'Failed to update status', type: 'error' })
    } finally {
      setStatusUpdateLoading(false)
    }
  }

  if (loading) return <LoadingSpinner />
  if (error) return <ErrorCard error={error} onRetry={fetchAssignments} />

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-3xl font-bold text-gray-800 dark:text-white">
          My Assignments
        </h1>
        <button
          onClick={fetchAssignments}
          className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg font-semibold transition"
        >
          🔄 Refresh
        </button>
      </div>

      {/* Filter Buttons */}
      <div className="flex gap-2 flex-wrap">
        <button
          onClick={() => setFilterStatus(null)}
          className={`px-4 py-2 rounded-lg font-semibold transition ${
            filterStatus === null
              ? 'bg-indigo-600 text-white'
              : 'bg-gray-200 dark:bg-gray-700 text-gray-800 dark:text-white hover:bg-gray-300 dark:hover:bg-gray-600'
          }`}
        >
          All ({assignments.length})
        </button>
        <button
          onClick={() => setFilterStatus('assigned')}
          className={`px-4 py-2 rounded-lg font-semibold transition ${
            filterStatus === 'assigned'
              ? 'bg-blue-600 text-white'
              : 'bg-gray-200 dark:bg-gray-700 text-gray-800 dark:text-white hover:bg-gray-300 dark:hover:bg-gray-600'
          }`}
        >
          New
        </button>
        <button
          onClick={() => setFilterStatus('in_progress')}
          className={`px-4 py-2 rounded-lg font-semibold transition ${
            filterStatus === 'in_progress'
              ? 'bg-purple-600 text-white'
              : 'bg-gray-200 dark:bg-gray-700 text-gray-800 dark:text-white hover:bg-gray-300 dark:hover:bg-gray-600'
          }`}
        >
          In Progress
        </button>
      </div>

      {/* Assignments Grid */}
      {assignments.length === 0 ? (
        <div className="text-center p-12 bg-gray-50 dark:bg-gray-800 rounded-lg">
          <p className="text-gray-600 dark:text-gray-400 text-lg">
            No assignments found
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-4">
          {assignments.map((assignment) => (
            <AssignmentCard
              key={assignment.assignment_id}
              assignment={assignment}
              onStatusUpdate={handleQuickStatusUpdate}
              loading={statusUpdateLoading}
            />
          ))}
        </div>
      )}

      {/* Status Update Modal */}
      {selectedGrievance && (
        <StatusUpdateForm
          grievanceId={selectedGrievance}
          onSubmit={handleStatusUpdate}
          onCancel={() => setSelectedGrievance(null)}
          loading={statusUpdateLoading}
        />
      )}

      {/* Toast */}
      {toast && (
        <Toast
          message={toast.message}
          type={toast.type}
          onClose={() => setToast(null)}
        />
      )}
    </div>
  )
}
