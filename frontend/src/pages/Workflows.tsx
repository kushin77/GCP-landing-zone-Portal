/**
 * Workflows page - Infrastructure provisioning workflows
 */
import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '../services/api';
import {
  ClipboardDocumentCheckIcon,
  PlusIcon,
  CheckIcon,
  XMarkIcon,
} from '@heroicons/react/24/outline';

export default function Workflows() {
  const queryClient = useQueryClient();
  const [showCreateDialog, setShowCreateDialog] = useState(false);

  const { data: workflows, isLoading } = useQuery({
    queryKey: ['workflows'],
    queryFn: () => apiClient.listWorkflows(),
  });

  const approveMutation = useMutation({
    mutationFn: ({ id, approval }: any) => apiClient.approveWorkflow(id, approval),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['workflows'] });
    },
  });

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed':
        return 'bg-green-100 text-green-800';
      case 'approved':
        return 'bg-blue-100 text-blue-800';
      case 'pending':
        return 'bg-yellow-100 text-yellow-800';
      case 'rejected':
        return 'bg-red-100 text-red-800';
      case 'in_progress':
        return 'bg-purple-100 text-purple-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  return (
    <div className="p-8 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Workflows</h1>
          <p className="mt-1 text-sm text-gray-500">
            Infrastructure provisioning requests and approvals
          </p>
        </div>
        <button
          onClick={() => setShowCreateDialog(true)}
          className="px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 flex items-center space-x-2"
        >
          <PlusIcon className="h-5 w-5" />
          <span>New Request</span>
        </button>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        {['pending', 'approved', 'in_progress', 'completed'].map((status) => {
          const count = workflows?.filter((w: any) => w.status === status).length || 0;
          return (
            <div key={status} className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
              <p className="text-sm text-gray-600 capitalize">{status.replace('_', ' ')}</p>
              <p className="mt-1 text-2xl font-bold text-gray-900">{count}</p>
            </div>
          );
        })}
      </div>

      {/* Workflows list */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-200">
        <div className="p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Recent Requests</h2>
          {isLoading ? (
            <div className="space-y-4">
              {[1, 2, 3].map((i) => (
                <div key={i} className="animate-pulse">
                  <div className="h-20 bg-gray-200 rounded"></div>
                </div>
              ))}
            </div>
          ) : workflows?.length === 0 ? (
            <div className="text-center py-12">
              <ClipboardDocumentCheckIcon className="h-12 w-12 text-gray-400 mx-auto mb-3" />
              <p className="text-gray-600">No workflows yet</p>
              <button
                onClick={() => setShowCreateDialog(true)}
                className="mt-4 px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700"
              >
                Create First Workflow
              </button>
            </div>
          ) : (
            <div className="space-y-4">
              {workflows?.map((workflow: any) => (
                <div
                  key={workflow.id}
                  className="border border-gray-200 rounded-lg p-4 hover:border-indigo-300 transition-colors"
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center space-x-2">
                        <h3 className="font-semibold text-gray-900">{workflow.title}</h3>
                        <span className={`px-2 py-1 rounded-full text-xs ${getStatusColor(workflow.status)}`}>
                          {workflow.status}
                        </span>
                      </div>
                      <p className="text-sm text-gray-600 mt-1">{workflow.description}</p>
                      <div className="flex items-center space-x-4 mt-3 text-xs text-gray-500">
                        <span>Type: {workflow.type}</span>
                        <span>Requester: {workflow.requester}</span>
                        <span>
                          Created: {new Date(workflow.created_at).toLocaleDateString()}
                        </span>
                        {workflow.cost_estimate && (
                          <span>Est. Cost: ${workflow.cost_estimate}/mo</span>
                        )}
                      </div>
                    </div>
                    {workflow.status === 'pending' && (
                      <div className="flex space-x-2">
                        <button
                          onClick={() =>
                            approveMutation.mutate({
                              id: workflow.id,
                              approval: {
                                approved: true,
                                approver: 'admin@example.com',
                                comments: 'Approved via portal',
                              },
                            })
                          }
                          className="p-2 bg-green-100 text-green-700 rounded-lg hover:bg-green-200"
                        >
                          <CheckIcon className="h-5 w-5" />
                        </button>
                        <button
                          onClick={() =>
                            approveMutation.mutate({
                              id: workflow.id,
                              approval: {
                                approved: false,
                                approver: 'admin@example.com',
                                comments: 'Rejected via portal',
                              },
                            })
                          }
                          className="p-2 bg-red-100 text-red-700 rounded-lg hover:bg-red-200"
                        >
                          <XMarkIcon className="h-5 w-5" />
                        </button>
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
