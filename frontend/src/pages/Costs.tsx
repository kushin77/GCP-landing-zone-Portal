/**
 * Costs page - Cost tracking and optimization
 */
import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { apiClient } from '../services/api';
import { CurrencyDollarIcon, ArrowTrendingUpIcon, LightBulbIcon } from '@heroicons/react/24/outline';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

export default function Costs() {
  const { data: summary } = useQuery({
    queryKey: ['cost-summary'],
    queryFn: () => apiClient.getCostSummary(),
  });

  const { data: optimizations } = useQuery({
    queryKey: ['cost-optimizations'],
    queryFn: () => apiClient.getCostOptimizations(),
  });

  return (
    <div className="p-8 space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-gray-900">Cost Management</h1>
        <p className="mt-1 text-sm text-gray-500">
          Track spending and discover optimization opportunities
        </p>
      </div>

      {/* Summary cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
          <p className="text-sm font-medium text-gray-600">Current Month</p>
          <p className="mt-2 text-3xl font-bold text-gray-900">
            ${summary?.current_month?.toLocaleString() || '0'}
          </p>
          <p className="mt-1 text-sm text-green-600">
            {summary?.trend_percentage > 0 ? '+' : ''}
            {summary?.trend_percentage?.toFixed(1)}% from last month
          </p>
        </div>

        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
          <p className="text-sm font-medium text-gray-600">Forecast (EOM)</p>
          <p className="mt-2 text-3xl font-bold text-gray-900">
            ${summary?.forecast_end_of_month?.toLocaleString() || '0'}
          </p>
          <p className="mt-1 text-sm text-gray-500">
            {summary?.budget_status || 'on-track'}
          </p>
        </div>

        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
          <p className="text-sm font-medium text-gray-600">Potential Savings</p>
          <p className="mt-2 text-3xl font-bold text-green-600">
            ${optimizations?.total_potential_savings?.toLocaleString() || '0'}
          </p>
          <p className="mt-1 text-sm text-gray-500">
            {optimizations?.recommendations?.length || 0} opportunities
          </p>
        </div>
      </div>

      {/* Cost breakdown chart */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Cost Breakdown</h2>
        <ResponsiveContainer width="100%" height={300}>
          <BarChart data={summary?.breakdown || []}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="service" />
            <YAxis />
            <Tooltip formatter={(value: any) => `$${value.toLocaleString()}`} />
            <Bar dataKey="cost" fill="#6366f1" />
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* Optimization recommendations */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
        <div className="flex items-center space-x-2 mb-4">
          <LightBulbIcon className="h-6 w-6 text-yellow-500" />
          <h2 className="text-lg font-semibold text-gray-900">
            Optimization Recommendations
          </h2>
        </div>
        <div className="space-y-4">
          {optimizations?.recommendations?.map((rec: any) => (
            <div
              key={rec.id}
              className="border border-gray-200 rounded-lg p-4 hover:border-indigo-300 transition-colors"
            >
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <h3 className="font-semibold text-gray-900">{rec.title}</h3>
                  <p className="text-sm text-gray-600 mt-1">{rec.description}</p>
                  <p className="text-sm text-indigo-600 mt-2">{rec.action}</p>
                </div>
                <div className="text-right">
                  <p className="text-2xl font-bold text-green-600">
                    ${rec.potential_savings}
                  </p>
                  <p className="text-xs text-gray-500">potential savings</p>
                  <span className={`inline-block mt-2 px-2 py-1 rounded-full text-xs ${
                    rec.priority === 'high'
                      ? 'bg-red-100 text-red-800'
                      : 'bg-yellow-100 text-yellow-800'
                  }`}>
                    {rec.priority}
                  </span>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
