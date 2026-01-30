/**
 * Projects page - List and manage GCP projects
 */
import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { apiClient } from '../services/api';
import { CubeIcon, MagnifyingGlassIcon } from '@heroicons/react/24/outline';

export default function Projects() {
  const { data, isLoading } = useQuery({
    queryKey: ['projects'],
    queryFn: () => apiClient.listProjects(),
  });

  return (
    <div className="p-8 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Projects</h1>
          <p className="mt-1 text-sm text-gray-500">
            Manage and monitor your GCP projects
          </p>
        </div>
        <button className="px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700">
          Request New Project
        </button>
      </div>

      {/* Search and filters */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
        <div className="relative">
          <MagnifyingGlassIcon className="absolute left-3 top-1/2 transform -translate-y-1/2 h-5 w-5 text-gray-400" />
          <input
            type="text"
            placeholder="Search projects..."
            className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500"
          />
        </div>
      </div>

      {/* Projects list */}
      {isLoading ? (
        <div className="space-y-4">
          {[1, 2, 3].map((i) => (
            <div key={i} className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 animate-pulse">
              <div className="h-6 bg-gray-200 rounded w-1/3 mb-2"></div>
              <div className="h-4 bg-gray-200 rounded w-1/2"></div>
            </div>
          ))}
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {data?.data?.map((project: any) => (
            <div
              key={project.id}
              className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 hover:shadow-md transition-shadow"
            >
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <h3 className="text-lg font-semibold text-gray-900">
                    {project.name}
                  </h3>
                  <p className="text-sm text-gray-500 mt-1">{project.project_id}</p>
                  <div className="mt-4 space-y-2">
                    <div className="flex items-center text-sm">
                      <span className="text-gray-600">State:</span>
                      <span className="ml-2 px-2 py-1 bg-green-100 text-green-800 rounded-full text-xs">
                        {project.state}
                      </span>
                    </div>
                    {project.labels && Object.keys(project.labels).length > 0 && (
                      <div className="flex flex-wrap gap-1 mt-2">
                        {Object.entries(project.labels).slice(0, 3).map(([key, value]) => (
                          <span
                            key={key}
                            className="px-2 py-1 bg-gray-100 text-gray-700 rounded text-xs"
                          >
                            {key}: {value as string}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
                <CubeIcon className="h-8 w-8 text-indigo-600" />
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
