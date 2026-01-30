/**
 * RCA-powered Issue Analysis Dashboard
 *
 * Provides intelligent root cause analysis for issues with automated remediation suggestions
 */
import React, { useState, useEffect } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import { api } from '../services/api';

interface IssueData {
  id: string;
  title: string;
  description: string;
  events?: string[];
  priority?: 'low' | 'medium' | 'high' | 'critical';
}

interface AnalysisResult {
  issue_id: string;
  root_cause: string;
  confidence: number;
  recommendations: string[];
  severity: 'low' | 'medium' | 'high' | 'critical';
  estimated_resolution_time: string;
  automated_actions?: string[];
}

const Analysis: React.FC = () => {
  const [issueData, setIssueData] = useState<IssueData>({
    id: '',
    title: '',
    description: '',
    events: [],
    priority: 'medium'
  });
  const [analysisResult, setAnalysisResult] = useState<AnalysisResult | null>(null);
  const [eventInput, setEventInput] = useState('');

  // Query for available services
  const { data: services, isLoading: servicesLoading } = useQuery({
    queryKey: ['analysis-services'],
    queryFn: () => api.get('/api/v1/analysis/services'),
    staleTime: 5 * 60 * 1000, // 5 minutes
  });

  // Mutation for RCA analysis
  const analysisMutation = useMutation({
    mutationFn: (data: IssueData) => api.post('/api/v1/analysis/rca', data),
    onSuccess: (result: AnalysisResult) => {
      setAnalysisResult(result);
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!issueData.title || !issueData.description) {
      alert('Please provide issue title and description');
      return;
    }
    analysisMutation.mutate(issueData);
  };

  const addEvent = () => {
    if (eventInput.trim()) {
      setIssueData(prev => ({
        ...prev,
        events: [...(prev.events || []), eventInput.trim()]
      }));
      setEventInput('');
    }
  };

  const removeEvent = (index: number) => {
    setIssueData(prev => ({
      ...prev,
      events: prev.events?.filter((_, i) => i !== index) || []
    }));
  };

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'critical': return 'text-red-600 bg-red-50 border-red-200';
      case 'high': return 'text-orange-600 bg-orange-50 border-orange-200';
      case 'medium': return 'text-yellow-600 bg-yellow-50 border-yellow-200';
      case 'low': return 'text-green-600 bg-green-50 border-green-200';
      default: return 'text-gray-600 bg-gray-50 border-gray-200';
    }
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">
          RCA Issue Analysis Dashboard
        </h1>
        <p className="text-gray-600">
          Intelligent root cause analysis powered by AI for automated issue resolution
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Issue Input Form */}
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          <h2 className="text-xl font-semibold text-gray-900 mb-6">Issue Details</h2>

          <form onSubmit={handleSubmit} className="space-y-6">
            <div>
              <label htmlFor="issueId" className="block text-sm font-medium text-gray-700 mb-2">
                Issue ID
              </label>
              <input
                type="text"
                id="issueId"
                value={issueData.id}
                onChange={(e) => setIssueData(prev => ({ ...prev, id: e.target.value }))}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                placeholder="e.g., ISSUE-123"
              />
            </div>

            <div>
              <label htmlFor="title" className="block text-sm font-medium text-gray-700 mb-2">
                Issue Title *
              </label>
              <input
                type="text"
                id="title"
                required
                value={issueData.title}
                onChange={(e) => setIssueData(prev => ({ ...prev, title: e.target.value }))}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                placeholder="Brief description of the issue"
              />
            </div>

            <div>
              <label htmlFor="description" className="block text-sm font-medium text-gray-700 mb-2">
                Issue Description *
              </label>
              <textarea
                id="description"
                required
                rows={4}
                value={issueData.description}
                onChange={(e) => setIssueData(prev => ({ ...prev, description: e.target.value }))}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                placeholder="Detailed description of the issue, symptoms, and impact"
              />
            </div>

            <div>
              <label htmlFor="priority" className="block text-sm font-medium text-gray-700 mb-2">
                Priority
              </label>
              <select
                id="priority"
                value={issueData.priority}
                onChange={(e) => setIssueData(prev => ({ ...prev, priority: e.target.value as IssueData['priority'] }))}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              >
                <option value="low">Low</option>
                <option value="medium">Medium</option>
                <option value="high">High</option>
                <option value="critical">Critical</option>
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Related Events
              </label>
              <div className="flex gap-2 mb-2">
                <input
                  type="text"
                  value={eventInput}
                  onChange={(e) => setEventInput(e.target.value)}
                  onKeyPress={(e) => e.key === 'Enter' && (e.preventDefault(), addEvent())}
                  className="flex-1 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  placeholder="Add event or log entry"
                />
                <button
                  type="button"
                  onClick={addEvent}
                  className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
                >
                  Add
                </button>
              </div>
              {issueData.events && issueData.events.length > 0 && (
                <div className="flex flex-wrap gap-2">
                  {issueData.events.map((event, index) => (
                    <span
                      key={index}
                      className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800"
                    >
                      {event}
                      <button
                        type="button"
                        onClick={() => removeEvent(index)}
                        className="ml-1 inline-flex items-center justify-center w-4 h-4 rounded-full text-blue-400 hover:bg-blue-200 hover:text-blue-500"
                      >
                        ×
                      </button>
                    </span>
                  ))}
                </div>
              )}
            </div>

            <button
              type="submit"
              disabled={analysisMutation.isPending}
              className="w-full px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {analysisMutation.isPending ? 'Analyzing...' : 'Analyze Issue'}
            </button>
          </form>
        </div>

        {/* Analysis Results */}
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          <h2 className="text-xl font-semibold text-gray-900 mb-6">Analysis Results</h2>

          {analysisMutation.isPending && (
            <div className="flex items-center justify-center py-8">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
              <span className="ml-2 text-gray-600">Performing root cause analysis...</span>
            </div>
          )}

          {analysisMutation.isError && (
            <div className="bg-red-50 border border-red-200 rounded-md p-4 mb-4">
              <div className="flex">
                <div className="flex-shrink-0">
                  <svg className="h-5 w-5 text-red-400" viewBox="0 0 20 20" fill="currentColor">
                    <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                  </svg>
                </div>
                <div className="ml-3">
                  <h3 className="text-sm font-medium text-red-800">Analysis Failed</h3>
                  <div className="mt-2 text-sm text-red-700">
                    {analysisMutation.error?.message || 'An error occurred during analysis'}
                  </div>
                </div>
              </div>
            </div>
          )}

          {analysisResult && (
            <div className="space-y-6">
              <div className={`p-4 rounded-lg border ${getSeverityColor(analysisResult.severity)}`}>
                <div className="flex items-center justify-between mb-2">
                  <h3 className="text-lg font-medium">Root Cause Analysis</h3>
                  <span className="text-sm font-medium capitalize">{analysisResult.severity} Priority</span>
                </div>
                <p className="text-sm mb-3">{analysisResult.root_cause}</p>
                <div className="flex items-center text-sm">
                  <span className="font-medium">Confidence:</span>
                  <span className="ml-2">{Math.round(analysisResult.confidence * 100)}%</span>
                </div>
              </div>

              <div>
                <h4 className="text-md font-medium text-gray-900 mb-3">Recommended Actions</h4>
                <ul className="space-y-2">
                  {analysisResult.recommendations.map((rec, index) => (
                    <li key={index} className="flex items-start">
                      <span className="flex-shrink-0 w-5 h-5 bg-blue-100 rounded-full flex items-center justify-center text-xs font-medium text-blue-800 mr-3 mt-0.5">
                        {index + 1}
                      </span>
                      <span className="text-sm text-gray-700">{rec}</span>
                    </li>
                  ))}
                </ul>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="bg-gray-50 p-3 rounded-md">
                  <div className="text-sm font-medium text-gray-500">Estimated Resolution Time</div>
                  <div className="text-lg font-semibold text-gray-900">{analysisResult.estimated_resolution_time}</div>
                </div>
                {analysisResult.automated_actions && analysisResult.automated_actions.length > 0 && (
                  <div className="bg-green-50 p-3 rounded-md">
                    <div className="text-sm font-medium text-green-700">Automated Actions Available</div>
                    <div className="text-lg font-semibold text-green-900">{analysisResult.automated_actions.length}</div>
                  </div>
                )}
              </div>
            </div>
          )}

          {!analysisResult && !analysisMutation.isPending && (
            <div className="text-center py-8 text-gray-500">
              <svg className="mx-auto h-12 w-12 text-gray-400 mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
              <p>Enter issue details and click "Analyze Issue" to get root cause analysis</p>
            </div>
          )}
        </div>
      </div>

      {/* Available Services Info */}
      {services && services.length > 0 && (
        <div className="mt-8 bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          <h3 className="text-lg font-medium text-gray-900 mb-4">Available Analysis Services</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {services.map((service: any, index: number) => (
              <div key={index} className="border border-gray-200 rounded-md p-4">
                <h4 className="font-medium text-gray-900">{service.name}</h4>
                <p className="text-sm text-gray-600 mt-1">{service.description}</p>
                <div className="mt-2 flex flex-wrap gap-1">
                  {service.capabilities?.map((cap: string, capIndex: number) => (
                    <span key={capIndex} className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-blue-100 text-blue-800">
                      {cap}
                    </span>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default Analysis;