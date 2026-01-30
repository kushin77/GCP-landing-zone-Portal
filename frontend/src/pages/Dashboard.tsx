/**
 * Dashboard page - Main control plane overview
 */
import React, { useState } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import { apiClient } from '../services/api';
import {
  CurrencyDollarIcon,
  ShieldCheckIcon,
  ServerIcon,
  ChartBarIcon,
  ArrowTrendingUpIcon,
  ArrowTrendingDownIcon,
  ExclamationTriangleIcon,
  CheckCircleIcon,
  MagnifyingGlassIcon,
} from '@heroicons/react/24/outline';
import {
  LineChart,
  Line,
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';

const COLORS = ['#6366f1', '#8b5cf6', '#ec4899', '#f59e0b', '#10b981'];

export default function Dashboard() {
  const [rcaResults, setRcaResults] = useState<any>(null);

  const { data: dashboard, isLoading } = useQuery({
    queryKey: ['dashboard'],
    queryFn: () => apiClient.getDashboard(),
  });

  const rcaMutation = useMutation({
    mutationFn: (issueData: any) => apiClient.performRCAAnalysis(issueData),
    onSuccess: (data) => {
      setRcaResults(data);
    },
  });

  const handleAnalyzeIssues = () => {
    // Mock issue data for demonstration - in real app this would come from user input
    const mockIssue = {
      id: "ISSUE-123",
      title: "High CPU usage on production servers",
      description: "Production servers experiencing 90%+ CPU utilization for the past 2 hours",
      severity: "high",
      category: "performance",
      affected_services: ["web-frontend", "api-gateway", "database"],
      timestamp: new Date().toISOString(),
    };

    rcaMutation.mutate(mockIssue);
  };

  if (isLoading) {
    return (
      <div className="p-8">
        <div className="animate-pulse space-y-4">
          <div className="h-8 bg-gray-200 rounded w-1/4"></div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            {[1, 2, 3, 4].map((i) => (
              <div key={i} className="h-32 bg-gray-200 rounded"></div>
            ))}
          </div>
        </div>
      </div>
    );
  }

  const stats = [
    {
      name: 'Monthly Cost',
      value: `$${dashboard?.costs?.current_month?.toLocaleString() || '0'}`,
      change: dashboard?.costs?.trend || '+0%',
      icon: CurrencyDollarIcon,
      color: 'bg-blue-500',
    },
    {
      name: 'Compliance Score',
      value: `${dashboard?.compliance?.score?.toFixed(1) || '0'}%`,
      change: dashboard?.compliance?.status || 'unknown',
      icon: ShieldCheckIcon,
      color: 'bg-green-500',
    },
    {
      name: 'Active Projects',
      value: dashboard?.resources?.projects || 0,
      change: `${dashboard?.resources?.vms || 0} VMs`,
      icon: ServerIcon,
      color: 'bg-purple-500',
    },
    {
      name: 'Storage',
      value: `${dashboard?.resources?.storage_tb || 0} TB`,
      change: `${dashboard?.resources?.clusters || 0} Clusters`,
      icon: ChartBarIcon,
      color: 'bg-orange-500',
    },
  ];

  const costData = dashboard?.costs?.top_services?.map((s: any, i: number) => ({
    name: s.service,
    value: s.cost,
    color: COLORS[i % COLORS.length],
  })) || [];

  return (
    <div className="p-8 space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-gray-900">Dashboard</h1>
        <p className="mt-1 text-sm text-gray-500">
          Real-time overview of your cloud infrastructure
        </p>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {stats.map((stat) => (
          <div
            key={stat.name}
            className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 hover:shadow-md transition-shadow"
          >
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600">{stat.name}</p>
                <p className="mt-2 text-3xl font-bold text-gray-900">{stat.value}</p>
                <p className="mt-1 text-sm text-gray-500">{stat.change}</p>
              </div>
              <div className={`${stat.color} rounded-lg p-3`}>
                <stat.icon className="h-6 w-6 text-white" />
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Cost Breakdown */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">
            Cost Breakdown by Service
          </h2>
          <ResponsiveContainer width="100%" height={300}>
            <PieChart>
              <Pie
                data={costData}
                cx="50%"
                cy="50%"
                labelLine={false}
                label={(entry) => entry.name}
                outerRadius={100}
                fill="#8884d8"
                dataKey="value"
              >
                {costData.map((entry: any, index: number) => (
                  <Cell key={`cell-${index}`} fill={entry.color} />
                ))}
              </Pie>
              <Tooltip formatter={(value: any) => `$${value.toLocaleString()}`} />
            </PieChart>
          </ResponsiveContainer>
        </div>

        {/* Alerts & Activity */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">
            Recent Activity
          </h2>
          <div className="space-y-4">
            {dashboard?.recent_activity?.map((activity: any, index: number) => (
              <div key={index} className="flex items-start space-x-3">
                <div className={`mt-0.5 ${
                  activity.type === 'workflow_approved'
                    ? 'text-green-500'
                    : 'text-orange-500'
                }`}>
                  {activity.type === 'workflow_approved' ? (
                    <CheckCircleIcon className="h-5 w-5" />
                  ) : (
                    <ExclamationTriangleIcon className="h-5 w-5" />
                  )}
                </div>
                <div className="flex-1">
                  <p className="text-sm text-gray-900">{activity.description}</p>
                  <p className="text-xs text-gray-500 mt-1">
                    {new Date(activity.timestamp).toLocaleString()}
                  </p>
                </div>
              </div>
            )) || (
              <p className="text-sm text-gray-500">No recent activity</p>
            )}
          </div>
        </div>
      </div>

      {/* Alerts */}
      {dashboard?.alerts && (
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">
            System Alerts
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="flex items-center space-x-3 p-4 bg-red-50 rounded-lg">
              <ExclamationTriangleIcon className="h-6 w-6 text-red-600" />
              <div>
                <p className="text-sm font-medium text-red-900">Critical</p>
                <p className="text-2xl font-bold text-red-600">
                  {dashboard.alerts.critical}
                </p>
              </div>
            </div>
            <div className="flex items-center space-x-3 p-4 bg-orange-50 rounded-lg">
              <ExclamationTriangleIcon className="h-6 w-6 text-orange-600" />
              <div>
                <p className="text-sm font-medium text-orange-900">Warning</p>
                <p className="text-2xl font-bold text-orange-600">
                  {dashboard.alerts.warning}
                </p>
              </div>
            </div>
            <div className="flex items-center space-x-3 p-4 bg-blue-50 rounded-lg">
              <CheckCircleIcon className="h-6 w-6 text-blue-600" />
              <div>
                <p className="text-sm font-medium text-blue-900">Info</p>
                <p className="text-2xl font-bold text-blue-600">
                  {dashboard.alerts.info}
                </p>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Quick Actions */}
      <div className="bg-gradient-to-r from-indigo-500 to-purple-600 rounded-xl shadow-lg p-8 text-white">
        <h2 className="text-2xl font-bold mb-2">Need something deployed?</h2>
        <p className="text-indigo-100 mb-6">
          Create a workflow request and get it approved in minutes
        </p>
        <div className="flex flex-wrap gap-3">
          <button className="px-4 py-2 bg-white text-indigo-600 rounded-lg font-medium hover:bg-indigo-50 transition-colors">
            Request VM
          </button>
          <button className="px-4 py-2 bg-white text-indigo-600 rounded-lg font-medium hover:bg-indigo-50 transition-colors">
            Create Project
          </button>
          <button className="px-4 py-2 bg-white text-indigo-600 rounded-lg font-medium hover:bg-indigo-50 transition-colors">
            Deploy Database
          </button>
          <button
            onClick={handleAnalyzeIssues}
            disabled={rcaMutation.isPending}
            className="px-4 py-2 bg-white text-indigo-600 rounded-lg font-medium hover:bg-indigo-50 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center space-x-2"
          >
            <MagnifyingGlassIcon className="h-4 w-4" />
            <span>{rcaMutation.isPending ? 'Analyzing...' : 'Analyze Issues'}</span>
          </button>
          <button className="px-4 py-2 bg-indigo-400 text-white rounded-lg font-medium hover:bg-indigo-300 transition-colors">
            Ask AI Assistant
          </button>
        </div>
      </div>

      {/* RCA Analysis Results */}
      {rcaResults && (
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4 flex items-center space-x-2">
            <MagnifyingGlassIcon className="h-5 w-5 text-indigo-600" />
            <span>RCA Analysis Results</span>
          </h2>

          <div className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="bg-indigo-50 rounded-lg p-4">
                <p className="text-sm font-medium text-indigo-900">Issue ID</p>
                <p className="text-lg font-bold text-indigo-600">{rcaResults.issue_id}</p>
              </div>
              <div className="bg-green-50 rounded-lg p-4">
                <p className="text-sm font-medium text-green-900">Services Used</p>
                <p className="text-lg font-bold text-green-600">{rcaResults.services_used}</p>
              </div>
              <div className="bg-orange-50 rounded-lg p-4">
                <p className="text-sm font-medium text-orange-900">Analysis Timestamp</p>
                <p className="text-sm font-bold text-orange-600">{rcaResults.analysis_timestamp}</p>
              </div>
            </div>

            {rcaResults.top_findings && rcaResults.top_findings.length > 0 && (
              <div>
                <h3 className="text-md font-medium text-gray-900 mb-2">Top Findings</h3>
                <div className="space-y-2">
                  {rcaResults.top_findings.map((finding: any, index: number) => (
                    <div key={index} className="bg-gray-50 rounded-lg p-3">
                      <div className="flex items-center justify-between">
                        <span className="font-medium text-gray-900">{finding.service}</span>
                        <span className={`px-2 py-1 rounded text-xs font-medium ${
                          finding.confidence > 0.8 ? 'bg-green-100 text-green-800' :
                          finding.confidence > 0.5 ? 'bg-yellow-100 text-yellow-800' :
                          'bg-red-100 text-red-800'
                        }`}>
                          {(finding.confidence * 100).toFixed(0)}% confidence
                        </span>
                      </div>
                      {finding.result && (
                        <p className="text-sm text-gray-600 mt-1">{finding.result.summary || 'Analysis completed'}</p>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {rcaResults.recommendations && rcaResults.recommendations.length > 0 && (
              <div>
                <h3 className="text-md font-medium text-gray-900 mb-2">Recommendations</h3>
                <div className="space-y-2">
                  {rcaResults.recommendations.map((rec: any, index: number) => (
                    <div key={index} className="bg-blue-50 rounded-lg p-3">
                      <p className="text-sm font-medium text-blue-900">{rec.description}</p>
                      <p className="text-xs text-blue-700 mt-1">Type: {rec.type}</p>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {rcaResults.automated_actions && rcaResults.automated_actions.length > 0 && (
              <div>
                <h3 className="text-md font-medium text-gray-900 mb-2">Automated Actions Available</h3>
                <div className="space-y-2">
                  {rcaResults.automated_actions.map((action: any, index: number) => (
                    <div key={index} className="bg-green-50 rounded-lg p-3 border-l-4 border-green-400">
                      <p className="text-sm font-medium text-green-900">{action.description}</p>
                      <p className="text-xs text-green-700 mt-1">Risk: {action.risk_level}</p>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
