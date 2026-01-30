/**
 * Compliance page - Security and compliance monitoring
 */
import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { apiClient } from '../services/api';
import { ShieldCheckIcon, CheckCircleIcon, XCircleIcon } from '@heroicons/react/24/outline';

export default function Compliance() {
  const { data: status } = useQuery({
    queryKey: ['compliance-status'],
    queryFn: () => apiClient.getComplianceStatus(),
  });

  const { data: frameworks } = useQuery({
    queryKey: ['frameworks'],
    queryFn: () => apiClient.listFrameworks(),
  });

  return (
    <div className="p-8 space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-gray-900">Compliance</h1>
        <p className="mt-1 text-sm text-gray-500">
          Security posture and compliance monitoring
        </p>
      </div>

      {/* Compliance score */}
      <div className="bg-gradient-to-r from-green-500 to-emerald-600 rounded-xl shadow-lg p-8 text-white">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm text-green-100">Overall Compliance Score</p>
            <p className="mt-2 text-6xl font-bold">{status?.score?.toFixed(1)}%</p>
            <p className="mt-2 text-green-100">
              {status?.controls_compliant} of {status?.controls_total} controls passing
            </p>
          </div>
          <ShieldCheckIcon className="h-24 w-24 text-green-200" />
        </div>
      </div>

      {/* Frameworks */}
      <div>
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Supported Frameworks</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {frameworks?.frameworks?.map((framework: any) => (
            <div
              key={framework.id}
              className="bg-white rounded-lg shadow-sm border border-gray-200 p-4 hover:shadow-md transition-shadow"
            >
              <h3 className="font-semibold text-gray-900">{framework.name}</h3>
              <p className="text-sm text-gray-600 mt-1">{framework.description}</p>
              <p className="text-xs text-gray-500 mt-2">Version: {framework.version}</p>
            </div>
          ))}
        </div>
      </div>

      {/* Controls */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Control Status</h2>
        <div className="space-y-3">
          {status?.findings?.slice(0, 10).map((control: any) => (
            <div
              key={control.id}
              className="flex items-start justify-between p-4 border border-gray-200 rounded-lg"
            >
              <div className="flex-1">
                <div className="flex items-center space-x-2">
                  <span className="text-sm font-medium text-gray-900">{control.id}</span>
                  <span className={`px-2 py-1 rounded-full text-xs ${
                    control.status === 'compliant'
                      ? 'bg-green-100 text-green-800'
                      : 'bg-red-100 text-red-800'
                  }`}>
                    {control.status}
                  </span>
                  <span className={`px-2 py-1 rounded-full text-xs ${
                    control.severity === 'critical'
                      ? 'bg-red-100 text-red-800'
                      : control.severity === 'high'
                      ? 'bg-orange-100 text-orange-800'
                      : 'bg-yellow-100 text-yellow-800'
                  }`}>
                    {control.severity}
                  </span>
                </div>
                <p className="text-sm text-gray-900 mt-1 font-medium">{control.name}</p>
                <p className="text-sm text-gray-600 mt-1">{control.description}</p>
                {control.remediation && (
                  <p className="text-sm text-indigo-600 mt-2">
                    Remediation: {control.remediation}
                  </p>
                )}
              </div>
              <div>
                {control.status === 'compliant' ? (
                  <CheckCircleIcon className="h-6 w-6 text-green-600" />
                ) : (
                  <XCircleIcon className="h-6 w-6 text-red-600" />
                )}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
