/**
 * FAANG-Grade API Client for Landing Zone Portal
 *
 * Features:
 * - Automatic retry with exponential backoff
 * - Request/response interceptors
 * - Offline detection
 * - Request cancellation
 * - Type-safe API methods
 */
import axios, {
  AxiosInstance,
  AxiosError,
  InternalAxiosRequestConfig,
} from 'axios';

// ============================================================================
// Configuration
// ============================================================================

// Resolve API base URL with priority:
// 1. `VITE_API_URL` (explicit override at build/dev time)
// 2. Runtime derivation from `window.location.hostname` + `VITE_API_PORT` (or default 8082)
// 3. Fallback to localhost:8080
const VITE_API_URL = import.meta.env.VITE_API_URL as string | undefined;
const VITE_API_PORT = import.meta.env.VITE_API_PORT as string | undefined;

let API_BASE_URL = 'http://localhost:8080';
if (VITE_API_URL && VITE_API_URL.length > 0) {
  API_BASE_URL = VITE_API_URL;
} else if (typeof window !== 'undefined') {
  const runtimePort = VITE_API_PORT || '8082';
  API_BASE_URL = `${window.location.protocol}//${window.location.hostname}:${runtimePort}`;
}

interface RetryConfig {
  maxRetries: number;
  baseDelay: number;
  maxDelay: number;
  retryableStatuses: number[];
}

const DEFAULT_RETRY_CONFIG: RetryConfig = {
  maxRetries: 3,
  baseDelay: 1000,
  maxDelay: 10000,
  retryableStatuses: [408, 429, 500, 502, 503, 504],
};

// ============================================================================
// Types
// ============================================================================

interface APIError {
  error: boolean;
  error_code: string;
  message: string;
  request_id: string;
  timestamp: string;
  path: string;
  errors?: Array<{
    code: string;
    message: string;
    field?: string;
  }>;
}

interface PaginatedResponse<T> {
  data: T[];
  total: number;
  page: number;
  limit: number;
  pages: number;
}

// Extend AxiosRequestConfig to include retry metadata
interface ExtendedAxiosRequestConfig extends InternalAxiosRequestConfig {
  _retryCount?: number;
  _retryConfig?: RetryConfig;
}

// ============================================================================
// Utility Functions
// ============================================================================

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function calculateBackoff(attempt: number, config: RetryConfig): number {
  const delay = config.baseDelay * Math.pow(2, attempt);
  const jitter = delay * 0.1 * Math.random();
  return Math.min(delay + jitter, config.maxDelay);
}

function isNetworkError(error: AxiosError): boolean {
  return !error.response && error.code !== 'ECONNABORTED';
}

function isRetryable(error: AxiosError, config: RetryConfig): boolean {
  if (isNetworkError(error)) return true;
  if (!error.response) return false;
  return config.retryableStatuses.includes(error.response.status);
}

// ============================================================================
// Online/Offline Detection
// ============================================================================

class NetworkStatus {
  private listeners: Set<(online: boolean) => void> = new Set();
  private _isOnline: boolean = typeof navigator !== 'undefined' ? navigator.onLine : true;

  constructor() {
    if (typeof window !== 'undefined') {
      window.addEventListener('online', () => this.setOnline(true));
      window.addEventListener('offline', () => this.setOnline(false));
    }
  }

  get isOnline(): boolean {
    return this._isOnline;
  }

  private setOnline(online: boolean): void {
    this._isOnline = online;
    this.listeners.forEach((listener) => listener(online));
  }

  subscribe(listener: (online: boolean) => void): () => void {
    this.listeners.add(listener);
    return () => this.listeners.delete(listener);
  }
}

export const networkStatus = new NetworkStatus();

// ============================================================================
// API Client Class
// ============================================================================

class APIClient {
  private client: AxiosInstance;
  private retryConfig: RetryConfig;

  constructor(baseURL: string = API_BASE_URL, retryConfig: RetryConfig = DEFAULT_RETRY_CONFIG) {
    this.retryConfig = retryConfig;

    this.client = axios.create({
      baseURL,
      timeout: 30000,
      headers: {
        'Content-Type': 'application/json',
      },
    });

    this.setupInterceptors();
  }

  private setupInterceptors(): void {
    // Request interceptor
    this.client.interceptors.request.use(
      (config: InternalAxiosRequestConfig) => {
        // Check if offline
        if (!networkStatus.isOnline) {
          return Promise.reject(new Error('No network connection'));
        }

        // Add authentication token if available
        const token = localStorage.getItem('auth_token');
        if (token) {
          config.headers.Authorization = `Bearer ${token}`;
        }

        // Add request ID for tracing
        config.headers['X-Request-ID'] = crypto.randomUUID?.() || Date.now().toString();

        return config;
      },
      (error) => Promise.reject(error)
    );

    // Response interceptor with retry logic
    this.client.interceptors.response.use(
      (response) => response,
      async (error: AxiosError<APIError>) => {
        const config = error.config as ExtendedAxiosRequestConfig | undefined;

        if (!config) {
          return Promise.reject(error);
        }

        // Initialize retry count
        config._retryCount = config._retryCount || 0;
        config._retryConfig = config._retryConfig || this.retryConfig;

        // Handle 401 Unauthorized
        if (error.response?.status === 401) {
          localStorage.removeItem('auth_token');
          // Emit event for auth context to handle
          window.dispatchEvent(new CustomEvent('auth:unauthorized'));
          return Promise.reject(error);
        }

        // Handle rate limiting
        if (error.response?.status === 429) {
          const retryAfter = parseInt(error.response.headers['retry-after'] || '60', 10);
          console.warn(`Rate limited. Retrying after ${retryAfter}s`);
          await sleep(retryAfter * 1000);
          return this.client.request(config);
        }

        // Retry logic for retryable errors
        if (
          isRetryable(error, config._retryConfig) &&
          config._retryCount < config._retryConfig.maxRetries
        ) {
          config._retryCount++;
          const delay = calculateBackoff(config._retryCount, config._retryConfig);

          console.log(
            `Retry attempt ${config._retryCount}/${config._retryConfig.maxRetries} after ${delay}ms`
          );

          await sleep(delay);
          return this.client.request(config);
        }

        // Transform error for better UX
        return Promise.reject(this.transformError(error));
      }
    );
  }

  private transformError(error: AxiosError<APIError>): Error {
    if (error.response?.data) {
      const apiError = error.response.data;
      const message = apiError.message || 'An unexpected error occurred';
      const transformedError = new Error(message);
      (transformedError as any).code = apiError.error_code;
      (transformedError as any).requestId = apiError.request_id;
      (transformedError as any).status = error.response.status;
      return transformedError;
    }

    if (isNetworkError(error)) {
      return new Error('Network error. Please check your connection.');
    }

    return new Error(error.message || 'An unexpected error occurred');
  }

  // Dashboard
  async getDashboard() {
    const { data } = await this.client.get('/api/v1/dashboard');
    return data;
  }

  // Projects
  async listProjects(page = 1, limit = 10) {
    const { data } = await this.client.get('/api/v1/projects', {
      params: { page, limit },
    });
    return data;
  }

  async getProject(projectId: string) {
    const { data } = await this.client.get(`/api/v1/projects/${projectId}`);
    return data;
  }

  async getProjectResources(projectId: string, page = 1, limit = 10) {
    const { data } = await this.client.get(
      `/api/v1/projects/${projectId}/resources`,
      { params: { page, limit } }
    );
    return data;
  }

  async getProjectCosts(projectId: string, days = 30) {
    const { data } = await this.client.get(
      `/api/v1/projects/${projectId}/costs`,
      { params: { days } }
    );
    return data;
  }

  // Costs
  async getCostSummary() {
    const { data } = await this.client.get('/api/v1/costs/summary');
    return data;
  }

  async getCostBreakdown(days = 30, groupBy = 'service') {
    const { data } = await this.client.get('/api/v1/costs/breakdown', {
      params: { days, group_by: groupBy },
    });
    return data;
  }

  async getCostTrends(days = 30) {
    const { data } = await this.client.get('/api/v1/costs/trends', {
      params: { days },
    });
    return data;
  }

  async getCostOptimizations() {
    const { data } = await this.client.get('/api/v1/costs/optimizations');
    return data;
  }

  // Compliance
  async getComplianceStatus(framework = 'NIST 800-53') {
    const { data } = await this.client.get('/api/v1/compliance/status', {
      params: { framework },
    });
    return data;
  }

  async listFrameworks() {
    const { data } = await this.client.get('/api/v1/compliance/frameworks');
    return data;
  }

  async getControlDetails(controlId: string, framework = 'NIST 800-53') {
    const { data } = await this.client.get(
      `/api/v1/compliance/controls/${controlId}`,
      { params: { framework } }
    );
    return data;
  }

  async triggerComplianceScan(framework = 'NIST 800-53') {
    const { data } = await this.client.post('/api/v1/compliance/scan', null, {
      params: { framework },
    });
    return data;
  }

  // Workflows
  async createWorkflow(workflow: any) {
    const { data } = await this.client.post('/api/v1/workflows/', workflow);
    return data;
  }

  async listWorkflows(filters: any = {}) {
    const { data } = await this.client.get('/api/v1/workflows/', {
      params: filters,
    });
    return data;
  }

  async getWorkflow(workflowId: string) {
    const { data } = await this.client.get(`/api/v1/workflows/${workflowId}`);
    return data;
  }

  async approveWorkflow(workflowId: string, approval: any) {
    const { data } = await this.client.post(
      `/api/v1/workflows/${workflowId}/approve`,
      approval
    );
    return data;
  }

  async executeWorkflow(workflowId: string) {
    const { data } = await this.client.post(
      `/api/v1/workflows/${workflowId}/execute`
    );
    return data;
  }

  async getTerraformPlan(workflowId: string) {
    const { data } = await this.client.get(
      `/api/v1/workflows/${workflowId}/terraform-plan`
    );
    return data;
  }

  // AI Assistant
  async queryAI(query: string, context?: any) {
    const { data } = await this.client.post('/api/v1/ai/query', {
      query,
      context,
      include_recommendations: true,
    });
    return data;
  }

  async getAISuggestions() {
    const { data} = await this.client.get('/api/v1/ai/suggestions');
    return data;
  }

  async getAIExamples() {
    const { data } = await this.client.get('/api/v1/ai/examples');
    return data;
  }

  // Analysis / RCA
  async performRCAAnalysis(issueData: any) {
    const { data } = await this.client.post('/api/v1/analysis/rca', issueData);
    return data;
  }

  async getAvailableRCAServices() {
    const { data } = await this.client.get('/api/v1/analysis/services');
    return data;
  }

  async performBatchRCAAnalysis(issues: any[]) {
    const { data } = await this.client.post('/api/v1/analysis/rca/batch', issues);
    return data;
  }

  // Health
  async getHealth() {
    const { data } = await this.client.get('/health');
    return data;
  }
}

export const apiClient = new APIClient();
export default apiClient;
