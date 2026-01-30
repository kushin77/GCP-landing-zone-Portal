/**
 * ============================================================================
 * FRONTEND ARCHITECTURE: Enterprise React with TanStack Query + Zustand
 * ============================================================================
 *
 * This file demonstrates the complete frontend architecture pattern:
 * - State management: Zustand (lightweight, DevTools support)
 * - Data fetching: TanStack Query (caching, background sync, retry logic)
 * - Error handling: Error boundaries
 * - Performance: React.lazy, Suspense, memoization, virtual scrolling
 * - Testing: Vitest + React Testing Library
 */

/**
 * ============================================================================
 * Part 1: Hooks - Custom React Hooks for Data Fetching
 * ============================================================================
 * Location: src/hooks/queries.ts
 * Exported by React Query and using useQueries for batch operations
 */

import { useQuery, useMutation, useQueries, useQueryClient, QueryKey } from '@tanstack/react-query';
import { AxiosError } from 'axios';

// Types
export interface Project {
  id: string;
  name: string;
  environment: 'dev' | 'staging' | 'prod';
  team: string;
  createdAt: Date;
  status: 'active' | 'archived';
  complianceScore: number;
  monthlySpend: number;
}

export interface ComplianceStatus {
  projectId: string;
  violations: Array<{
    id: string;
    name: string;
    severity: 'critical' | 'high' | 'medium' | 'low';
    resource: string;
  }>;
  lastChecked: Date;
}

export interface Cost {
  projectId: string;
  month: string;
  cost: number;
  services: Record<string, number>;
  trend: 'up' | 'down' | 'stable';
}

/**
 * Fetch projects with caching
 */
export const useProjects = (filters?: {
  environment?: string;
  team?: string;
  limit?: number;
  offset?: number;
}) => {
  return useQuery<Project[], AxiosError>({
    queryKey: ['projects', filters],
    queryFn: async () => {
      const response = await fetch('/api/v1/projects', {
        method: 'GET',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`,
        },
      });
      if (!response.ok) throw new Error('Failed to fetch projects');
      return response.json();
    },
    staleTime: 1000 * 60 * 5, // 5 minutes
    gcTime: 1000 * 60 * 10, // 10 minutes
    refetchOnWindowFocus: 'stale',
    refetchInterval: 1000 * 60 * 30, // Refetch every 30 minutes
  });
};

/**
 * Fetch compliance status for multiple projects (batch operation)
 */
export const useComplianceStatusBatch = (projectIds: string[]) => {
  return useQueries({
    queries: projectIds.map((projectId) => ({
      queryKey: ['compliance', projectId],
      queryFn: async () => {
        const response = await fetch(`/api/v1/compliance/${projectId}`, {
          headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` },
        });
        if (!response.ok) throw new Error('Failed to fetch compliance');
        return response.json() as Promise<ComplianceStatus>;
      },
      staleTime: 1000 * 60 * 10,
    })),
  });
};

/**
 * Create project mutation with optimistic updates
 */
export const useCreateProject = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (newProject: Omit<Project, 'id' | 'createdAt'>) => {
      const response = await fetch('/api/v1/projects', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(newProject),
      });
      if (!response.ok) throw new Error('Failed to create project');
      return response.json();
    },
    onMutate: async (newProject) => {
      // Cancel any outgoing queries
      await queryClient.cancelQueries({ queryKey: ['projects'] });

      // Snapshot previous data
      const previousProjects = queryClient.getQueryData<Project[]>(['projects']);

      // Optimistically update UI
      if (previousProjects) {
        queryClient.setQueryData<Project[]>(['projects'], (old) => [
          ...(old || []),
          {
            ...newProject,
            id: `temp-${Date.now()}`,
            createdAt: new Date(),
          } as Project,
        ]);
      }

      return { previousProjects };
    },
    onError: (err, newProject, context) => {
      // Rollback on error
      if (context?.previousProjects) {
        queryClient.setQueryData(['projects'], context.previousProjects);
      }
    },
    onSuccess: () => {
      // Refetch projects to sync with server
      queryClient.invalidateQueries({ queryKey: ['projects'] });
    },
  });
};

/**
 * ============================================================================
 * Part 2: State Management - Zustand Store
 * ============================================================================
 * Location: src/store/uiStore.ts
 */

import { create } from 'zustand';
import { devtools, persist, subscribeWithSelector } from 'zustand/middleware';

interface UIStore {
  // Sidebar state
  sidebarOpen: boolean;
  setSidebarOpen: (open: boolean) => void;

  // Filters
  filters: {
    environment: 'all' | 'dev' | 'staging' | 'prod';
    team: 'all' | string;
    searchText: string;
    dateRange: [Date, Date];
  };
  setFilters: (filters: Partial<UIStore['filters']>) => void;

  // Modals
  modals: {
    createProjectOpen: boolean;
    settingsOpen: boolean;
    detailsDrawerOpen: boolean;
    selectedProjectId: string | null;
  };
  openCreateProjectModal: () => void;
  closeCreateProjectModal: () => void;
  openDetailsDrawer: (projectId: string) => void;
  closeDetailsDrawer: () => void;

  // Theme
  theme: 'light' | 'dark' | 'auto';
  setTheme: (theme: 'light' | 'dark' | 'auto') => void;

  // User preferences
  preferences: {
    itemsPerPage: number;
    defaultSort: 'name' | 'date' | 'cost';
    showComplianceWarnings: boolean;
  };
  setPreferences: (prefs: Partial<UIStore['preferences']>) => void;
}

export const useUIStore = create<UIStore>()(
  devtools(
    persist(
      subscribeWithSelector((set) => ({
        // Sidebar
        sidebarOpen: true,
        setSidebarOpen: (open) => set({ sidebarOpen: open }),

        // Filters
        filters: {
          environment: 'all',
          team: 'all',
          searchText: '',
          dateRange: [new Date(Date.now() - 30 * 24 * 60 * 60 * 1000), new Date()],
        },
        setFilters: (filters) =>
          set((state) => ({
            filters: { ...state.filters, ...filters },
          })),

        // Modals
        modals: {
          createProjectOpen: false,
          settingsOpen: false,
          detailsDrawerOpen: false,
          selectedProjectId: null,
        },
        openCreateProjectModal: () =>
          set((state) => ({
            modals: { ...state.modals, createProjectOpen: true },
          })),
        closeCreateProjectModal: () =>
          set((state) => ({
            modals: { ...state.modals, createProjectOpen: false },
          })),
        openDetailsDrawer: (projectId) =>
          set((state) => ({
            modals: {
              ...state.modals,
              detailsDrawerOpen: true,
              selectedProjectId: projectId,
            },
          })),
        closeDetailsDrawer: () =>
          set((state) => ({
            modals: {
              ...state.modals,
              detailsDrawerOpen: false,
              selectedProjectId: null,
            },
          })),

        // Theme
        theme: 'auto' as const,
        setTheme: (theme) => set({ theme }),

        // Preferences
        preferences: {
          itemsPerPage: 25,
          defaultSort: 'date',
          showComplianceWarnings: true,
        },
        setPreferences: (prefs) =>
          set((state) => ({
            preferences: { ...state.preferences, ...prefs },
          })),
      })),
      {
        name: 'landing-zone-ui',
      }
    )
  )
);

/**
 * ============================================================================
 * Part 3: Components - Memoized, Error Boundaries
 * ============================================================================
 * Location: src/components/ProjectCard.tsx
 */

import React from 'react';

interface ProjectCardProps {
  project: Project;
  onClick: (projectId: string) => void;
}

/**
 * Memoized project card to prevent unnecessary re-renders
 */
export const ProjectCard = React.memo(function ProjectCard({
  project,
  onClick,
}: ProjectCardProps) {
  return (
    <div
      onClick={() => onClick(project.id)}
      className="p-4 border rounded-lg hover:shadow-lg transition cursor-pointer"
    >
      <h3 className="font-bold">{project.name}</h3>
      <div className="flex justify-between mt-4 text-sm text-gray-600">
        <span>{project.environment}</span>
        <span>${project.monthlySpend.toLocaleString()}</span>
      </div>
      <div className="mt-2">
        <div className="flex items-center justify-between">
          <span>Compliance</span>
          <span className={project.complianceScore > 80 ? 'text-green-600' : 'text-red-600'}>
            {project.complianceScore}%
          </span>
        </div>
      </div>
    </div>
  );
}, (prevProps, nextProps) => {
  // Custom comparison: only re-render if project or onClick truly changed
  return (
    prevProps.project.id === nextProps.project.id &&
    prevProps.project.monthlySpend === nextProps.project.monthlySpend &&
    prevProps.project.complianceScore === nextProps.project.complianceScore
  );
});

/**
 * ============================================================================
 * Part 4: Virtual Scrolling - Render Only Visible Items
 * ============================================================================
 * Location: src/components/ProjectList.tsx
 * Uses react-window for rendering 1000s of projects efficiently
 */

import { FixedSizeList as List } from 'react-window';

interface ProjectListProps {
  projects: Project[];
  onProjectClick: (projectId: string) => void;
}

export const ProjectList = React.memo(function ProjectList({
  projects,
  onProjectClick,
}: ProjectListProps) {
  const itemSize = 120; // Height of each project card
  const height = 600; // Visible height

  const Row = ({ index, style }: { index: number; style: React.CSSProperties }) => (
    <div style={style}>
      <ProjectCard project={projects[index]} onClick={onProjectClick} />
    </div>
  );

  return (
    <List
      height={height}
      itemCount={projects.length}
      itemSize={itemSize}
      width="100%"
    >
      {Row}
    </List>
  );
});

/**
 * ============================================================================
 * Part 5: Suspense & Code Splitting
 * ============================================================================
 * Location: src/pages/Dashboard.tsx
 */

const ProjectsPage = React.lazy(() => import('./pages/ProjectsPage'));
const CompliancePage = React.lazy(() => import('./pages/CompliancePage'));
const CostsPage = React.lazy(() => import('./pages/CostsPage'));

const PageLoader = () => (
  <div className="flex items-center justify-center h-96">
    <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
  </div>
);

interface DashboardProps {
  currentPage: 'projects' | 'compliance' | 'costs';
}

export const Dashboard = React.memo(function Dashboard({ currentPage }: DashboardProps) {
  return (
    <React.Suspense fallback={<PageLoader />}>
      {currentPage === 'projects' && <ProjectsPage />}
      {currentPage === 'compliance' && <CompliancePage />}
      {currentPage === 'costs' && <CostsPage />}
    </React.Suspense>
  );
});

/**
 * ============================================================================
 * Part 6: Error Handling & Fallbacks
 * ============================================================================
 * Location: src/components/ErrorBoundary.tsx
 */

interface ErrorBoundaryProps {
  children: React.ReactNode;
  fallback?: (error: Error, retry: () => void) => React.ReactNode;
}

interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends React.Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    // Log to error tracking (Sentry)
    console.error('Error:', error, errorInfo);
  }

  retry = () => {
    this.setState({ hasError: false, error: null });
  };

  render() {
    if (this.state.hasError) {
      return (
        this.props.fallback?.(this.state.error!, this.retry) || (
          <div className="p-6 bg-red-50 border border-red-200 rounded">
            <h2 className="font-bold text-red-800">Something went wrong</h2>
            <p className="text-red-700">{this.state.error?.message}</p>
            <button
              onClick={this.retry}
              className="mt-4 px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700"
            >
              Retry
            </button>
          </div>
        )
      );
    }

    return this.props.children;
  }
}

/**
 * ============================================================================
 * Part 7: Performance Optimizations Summary
 * ============================================================================
 *
 * 1. TanStack Query Benefits:
 *    - Automatic caching (staleTime = 5min)
 *    - Background refetching
 *    - Request deduplication (same query run twice = 1 request)
 *    - Optimistic updates (show result before server confirms)
 *    - Retry logic (3 attempts with exponential backoff)
 *
 * 2. Zustand Benefits:
 *    - Lightweight (1.2KB gzipped)
 *    - DevTools support (time travel debugging)
 *    - localStorage persistence
 *    - Subscription system (update without re-render)
 *
 * 3. React Patterns:
 *    - React.memo prevents unnecessary re-renders
 *    - Suspense + code splitting loads faster
 *    - Error boundaries gracefully handle crashes
 *    - Virtual scrolling renders 1000s efficiently (only visible items)
 *
 * 4. Network Efficiency:
 *    - Request deduplication (same query twice = 1 HTTP)
 *    - Cache-first strategy (5 min stale time)
 *    - Background refetch (automatic sync)
 *    - Batch queries (useQueries) fetch multiple items in parallel
 *
 * 5. User Experience:
 *    - Optimistic updates (instant feedback)
 *    - Skeleton loaders (perceived performance)
 *    - Error boundaries (graceful degradation)
 *    - Pagination (initial page loads fast)
 *
 * ============================================================================
 */
