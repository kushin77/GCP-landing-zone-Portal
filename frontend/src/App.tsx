/**
 * Main App component with routing, layout, and error handling
 */
import React from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { RouterProvider, createRouter, createRootRoute, createRoute, Outlet } from '@tanstack/react-router';
import Dashboard from './pages/Dashboard';
import Projects from './pages/Projects';
import Costs from './pages/Costs';
import Compliance from './pages/Compliance';
import Workflows from './pages/Workflows';
import AIAssistant from './pages/AIAssistant';
import Analysis from './pages/Analysis';
import Layout from './components/Layout';
import { ErrorBoundary, PageErrorBoundary } from './components/ErrorBoundary';
import './index.css';

// Create query client with error handling
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: (failureCount, error: any) => {
        // Don't retry on 401, 403, 404
        if ([401, 403, 404].includes(error?.status)) {
          return false;
        }
        return failureCount < 3;
      },
      staleTime: 30000, // 30 seconds
    },
    mutations: {
      retry: false,
    },
  },
});

// Create root route
const rootRoute = createRootRoute({
  component: () => (
    <PageErrorBoundary>
      <Layout>
        <ErrorBoundary>
          <Outlet />
        </ErrorBoundary>
      </Layout>
    </PageErrorBoundary>
  ),
});

// Create routes
const indexRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/',
  component: Dashboard,
});

const projectsRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/projects',
  component: Projects,
});

const costsRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/costs',
  component: Costs,
});

const complianceRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/compliance',
  component: Compliance,
});

const workflowsRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/workflows',
  component: Workflows,
});

const aiRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/ai',
  component: AIAssistant,
});

const analysisRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/analysis',
  component: Analysis,
});

// Create router
const routeTree = rootRoute.addChildren([
  indexRoute,
  projectsRoute,
  costsRoute,
  complianceRoute,
  workflowsRoute,
  aiRoute,
  analysisRoute,
]);

const router = createRouter({ routeTree });

// TypeScript type for router
declare module '@tanstack/react-router' {
  interface Register {
    router: typeof router;
  }
}

function App() {
  return (
    <ErrorBoundary>
      <QueryClientProvider client={queryClient}>
        <RouterProvider router={router} />
      </QueryClientProvider>
    </ErrorBoundary>
  );
}

export default App;
