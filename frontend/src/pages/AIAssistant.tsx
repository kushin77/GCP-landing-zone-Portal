/**
 * AI Assistant page - Intelligent infrastructure queries
 */
import React, { useState } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import { apiClient } from '../services/api';
import {
  SparklesIcon,
  PaperAirplaneIcon,
  LightBulbIcon,
  DocumentTextIcon,
} from '@heroicons/react/24/outline';

export default function AIAssistant() {
  const [query, setQuery] = useState('');
  const [chatHistory, setChatHistory] = useState<any[]>([]);

  const { data: suggestions } = useQuery({
    queryKey: ['ai-suggestions'],
    queryFn: () => apiClient.getAISuggestions(),
  });

  const { data: examples } = useQuery({
    queryKey: ['ai-examples'],
    queryFn: () => apiClient.getAIExamples(),
  });

  const queryMutation = useMutation({
    mutationFn: (q: string) => apiClient.queryAI(q),
    onSuccess: (data, variables) => {
      setChatHistory((prev) => [
        ...prev,
        { type: 'user', message: variables },
        { type: 'ai', data },
      ]);
      setQuery('');
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (query.trim()) {
      queryMutation.mutate(query);
    }
  };

  const handleExampleClick = (exampleQuery: string) => {
    setQuery(exampleQuery);
  };

  return (
    <div className="h-screen flex flex-col bg-gray-50">
      {/* Header */}
      <div className="bg-white border-b border-gray-200 p-6">
        <div className="flex items-center space-x-3">
          <div className="h-10 w-10 rounded-lg bg-gradient-to-br from-purple-500 to-pink-500 flex items-center justify-center">
            <SparklesIcon className="h-6 w-6 text-white" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-gray-900">AI Assistant</h1>
            <p className="text-sm text-gray-500">
              Intelligent infrastructure queries and recommendations
            </p>
          </div>
        </div>
      </div>

      <div className="flex-1 overflow-hidden flex">
        {/* Sidebar with suggestions */}
        <div className="w-80 bg-white border-r border-gray-200 overflow-y-auto p-6">
          <div className="space-y-6">
            {/* Quick Suggestions */}
            <div>
              <h3 className="text-sm font-semibold text-gray-900 mb-3 flex items-center">
                <LightBulbIcon className="h-4 w-4 mr-2" />
                AI Suggestions
              </h3>
              <div className="space-y-2">
                {suggestions?.suggestions?.slice(0, 2).map((cat: any, idx: number) => (
                  <div key={idx} className="bg-amber-50 rounded-lg p-3">
                    <p className="text-xs font-medium text-amber-900 mb-1">
                      {cat.category}
                    </p>
                    {cat.items?.slice(0, 2).map((item: string, i: number) => (
                      <p key={i} className="text-xs text-amber-700 mt-1">
                        • {item}
                      </p>
                    ))}
                  </div>
                ))}
              </div>
            </div>

            {/* Example Queries */}
            <div>
              <h3 className="text-sm font-semibold text-gray-900 mb-3 flex items-center">
                <DocumentTextIcon className="h-4 w-4 mr-2" />
                Example Queries
              </h3>
              <div className="space-y-2">
                {examples?.examples?.[0]?.queries?.slice(0, 5).map((q: string, idx: number) => (
                  <button
                    key={idx}
                    onClick={() => handleExampleClick(q)}
                    className="w-full text-left text-xs text-gray-700 hover:text-indigo-600 hover:bg-indigo-50 rounded-lg p-2 transition-colors"
                  >
                    {q}
                  </button>
                ))}
              </div>
            </div>
          </div>
        </div>

        {/* Main chat area */}
        <div className="flex-1 flex flex-col">
          {/* Messages */}
          <div className="flex-1 overflow-y-auto p-6 space-y-4">
            {chatHistory.length === 0 ? (
              <div className="h-full flex items-center justify-center">
                <div className="text-center max-w-2xl">
                  <SparklesIcon className="h-16 w-16 text-indigo-600 mx-auto mb-4" />
                  <h2 className="text-2xl font-bold text-gray-900 mb-2">
                    Welcome to AI Assistant
                  </h2>
                  <p className="text-gray-600 mb-6">
                    Ask me anything about your infrastructure, costs, security, or compliance.
                    I can help you optimize, troubleshoot, and make informed decisions.
                  </p>
                  <div className="grid grid-cols-2 gap-3 text-left">
                    <div className="bg-white rounded-lg p-4 border border-gray-200">
                      <p className="text-sm font-medium text-gray-900 mb-1">
                        💰 Cost Management
                      </p>
                      <p className="text-xs text-gray-500">
                        Get insights on spending and optimization opportunities
                      </p>
                    </div>
                    <div className="bg-white rounded-lg p-4 border border-gray-200">
                      <p className="text-sm font-medium text-gray-900 mb-1">
                        🔒 Security & Compliance
                      </p>
                      <p className="text-xs text-gray-500">
                        Check compliance status and security findings
                      </p>
                    </div>
                    <div className="bg-white rounded-lg p-4 border border-gray-200">
                      <p className="text-sm font-medium text-gray-900 mb-1">
                        📦 Resource Management
                      </p>
                      <p className="text-xs text-gray-500">
                        Search and manage your cloud resources
                      </p>
                    </div>
                    <div className="bg-white rounded-lg p-4 border border-gray-200">
                      <p className="text-sm font-medium text-gray-900 mb-1">
                        🔧 Troubleshooting
                      </p>
                      <p className="text-xs text-gray-500">
                        Debug issues and get step-by-step solutions
                      </p>
                    </div>
                  </div>
                </div>
              </div>
            ) : (
              chatHistory.map((msg, idx) => (
                <div key={idx}>
                  {msg.type === 'user' ? (
                    <div className="flex justify-end">
                      <div className="bg-indigo-600 text-white rounded-lg px-4 py-2 max-w-2xl">
                        {msg.message}
                      </div>
                    </div>
                  ) : (
                    <div className="flex justify-start">
                      <div className="bg-white border border-gray-200 rounded-lg px-4 py-3 max-w-3xl">
                        <div className="prose prose-sm max-w-none">
                          <div className="whitespace-pre-wrap">{msg.data.answer}</div>
                        </div>
                        {msg.data.recommendations?.length > 0 && (
                          <div className="mt-4 space-y-2">
                            <p className="text-xs font-semibold text-gray-700">
                              Recommendations:
                            </p>
                            {msg.data.recommendations.map((rec: any, i: number) => (
                              <div
                                key={i}
                                className="bg-blue-50 rounded-lg p-3 text-sm"
                              >
                                <p className="font-medium text-blue-900">
                                  {rec.title}
                                </p>
                                {rec.savings && (
                                  <p className="text-xs text-blue-700 mt-1">
                                    💰 Save {rec.savings}
                                  </p>
                                )}
                                {rec.action && (
                                  <p className="text-xs text-blue-600 mt-1">
                                    {rec.action}
                                  </p>
                                )}
                              </div>
                            ))}
                          </div>
                        )}
                        {msg.data.follow_up_questions?.length > 0 && (
                          <div className="mt-4">
                            <p className="text-xs font-semibold text-gray-700 mb-2">
                              Follow-up questions:
                            </p>
                            <div className="flex flex-wrap gap-2">
                              {msg.data.follow_up_questions.map((q: string, i: number) => (
                                <button
                                  key={i}
                                  onClick={() => handleExampleClick(q)}
                                  className="text-xs text-indigo-600 hover:text-indigo-700 bg-indigo-50 hover:bg-indigo-100 rounded-full px-3 py-1 transition-colors"
                                >
                                  {q}
                                </button>
                              ))}
                            </div>
                          </div>
                        )}
                      </div>
                    </div>
                  )}
                </div>
              ))
            )}
            {queryMutation.isPending && (
              <div className="flex justify-start">
                <div className="bg-white border border-gray-200 rounded-lg px-4 py-3">
                  <div className="flex items-center space-x-2">
                    <div className="animate-spin h-4 w-4 border-2 border-indigo-600 border-t-transparent rounded-full" />
                    <span className="text-sm text-gray-600">Thinking...</span>
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Input */}
          <div className="border-t border-gray-200 bg-white p-4">
            <form onSubmit={handleSubmit} className="flex space-x-3">
              <input
                type="text"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Ask me anything about your infrastructure..."
                className="flex-1 rounded-lg border border-gray-300 px-4 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                disabled={queryMutation.isPending}
              />
              <button
                type="submit"
                disabled={!query.trim() || queryMutation.isPending}
                className="px-6 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors flex items-center space-x-2"
              >
                <PaperAirplaneIcon className="h-4 w-4" />
                <span>Send</span>
              </button>
            </form>
          </div>
        </div>
      </div>
    </div>
  );
}
