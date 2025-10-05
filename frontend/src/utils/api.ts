// API Configuration - Use relative URLs with Vite proxy
const API_BASE_URL = "/api/v1";
const SIMULATION_API_URL = "/sim";
const DATA_FETCHER_URL = "/data";

// WebSocket URL - automatically detect protocol and host
const getWebSocketUrl = (): string => {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const host = window.location.host;
  return `${protocol}//${host}/sim`;
};

// Types for API responses
export interface ApiResponse<T> {
  success: boolean;
  data?: T;
  error?: string;
}

export interface Game {
  id: string;
  gameId: string;
  homeTeam: {
    name: string;
    abbreviation: string;
    city: string;
  };
  awayTeam: {
    name: string;
    abbreviation: string;
    city: string;
  };
  gameDate: string;
  status: string;
  stadium: string;
}

export interface Team {
  id: string;
  name: string;
  abbreviation: string;
  city: string;
  division: string;
  league: string;
  wins: number;
  losses: number;
  runsScored: number;
  runsAllowed: number;
  era: number;
  battingAvg: number;
}

export interface Player {
  id: string;
  name: string;
  team: string;
  position: string;
  battingAvg: number;
  homeRuns: number;
  rbi: number;
  era?: number;
  strikeouts?: number;
  wins?: number;
  losses?: number;
  playerType: "batter" | "pitcher";
}

export interface SimulationRequest {
  gameId: string;
  runs?: number;
  workers?: number;
}

export interface SimulationStatus {
  runId: string;
  gameId: string;
  status: "pending" | "running" | "completed" | "failed";
  totalRuns: number;
  completedRuns: number;
  progress: number;
  createdAt: string;
  completedAt?: string;
}

export interface SimulationResult {
  runId: string;
  homeWinProbability: number;
  awayWinProbability: number;
  expectedHomeScore: number;
  expectedAwayScore: number;
  homeScoreDistribution: Record<number, number>;
  awayScoreDistribution: Record<number, number>;
  metadata: {
    totalSimulations: number;
    averageGameDuration: number;
    averagePitches: number;
  };
}

// Cache implementation for API responses
interface CacheEntry<T> {
  data: T;
  timestamp: number;
  ttl: number;
}

class ApiCache {
  private cache = new Map<string, CacheEntry<any>>();

  set<T>(key: string, data: T, ttlSeconds = 300): void {
    this.cache.set(key, {
      data,
      timestamp: Date.now(),
      ttl: ttlSeconds * 1000,
    });
  }

  get<T>(key: string): T | null {
    const entry = this.cache.get(key);
    if (!entry) return null;

    const age = Date.now() - entry.timestamp;
    if (age > entry.ttl) {
      this.cache.delete(key);
      return null;
    }

    return entry.data as T;
  }

  clear(): void {
    this.cache.clear();
  }

  delete(key: string): void {
    this.cache.delete(key);
  }
}

const apiCache = new ApiCache();

// Utility function for making HTTP requests with caching
async function apiRequest<T>(
  url: string,
  options: RequestInit = {},
  cacheTTL?: number
): Promise<ApiResponse<T>> {
  // Only cache GET requests
  const cacheKey = options.method === "GET" || !options.method ? url : null;

  // Check cache for GET requests
  if (cacheKey && cacheTTL !== undefined) {
    const cached = apiCache.get<T>(cacheKey);
    if (cached) {
      return { success: true, data: cached };
    }
  }

  try {
    const response = await fetch(url, {
      headers: {
        "Content-Type": "application/json",
        ...options.headers,
      },
      ...options,
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const data = await response.json();

    // Cache successful GET responses
    if (cacheKey && cacheTTL !== undefined) {
      apiCache.set(cacheKey, data, cacheTTL);
    }

    return { success: true, data };
  } catch (error) {
    console.error("API request failed:", error);
    return {
      success: false,
      error: error instanceof Error ? error.message : "Unknown error"
    };
  }
}

// API Gateway endpoints with caching
export class ApiGateway {
  static async getHealth(): Promise<ApiResponse<{ status: string }>> {
    return apiRequest(`${API_BASE_URL}/health`, {}, 30); // 30s cache
  }

  static async getTeams(): Promise<ApiResponse<Team[]>> {
    return apiRequest(`${API_BASE_URL}/teams`, {}, 600); // 10min cache - teams rarely change
  }

  static async getPlayers(): Promise<ApiResponse<Player[]>> {
    return apiRequest(`${API_BASE_URL}/players`, {}, 300); // 5min cache
  }

  static async getGames(): Promise<ApiResponse<Game[]>> {
    return apiRequest(`${API_BASE_URL}/games`, {}, 60); // 1min cache
  }

  static async getGamesByDate(date: string): Promise<ApiResponse<Game[]>> {
    return apiRequest(`${API_BASE_URL}/games/date/${date}`, {}, 120); // 2min cache
  }

  // Cache control methods
  static clearCache(): void {
    apiCache.clear();
  }
}

// Simulation Engine endpoints
export class SimulationAPI {
  static async startSimulation(
    request: SimulationRequest
  ): Promise<ApiResponse<{ runId: string }>> {
    return apiRequest(`${SIMULATION_API_URL}/simulate`, {
      method: "POST",
      body: JSON.stringify(request),
    });
  }

  static async getSimulationStatus(
    runId: string
  ): Promise<ApiResponse<SimulationStatus>> {
    return apiRequest(`${SIMULATION_API_URL}/simulation/${runId}/status`);
  }

  static async getSimulationResult(
    runId: string
  ): Promise<ApiResponse<SimulationResult>> {
    return apiRequest(`${SIMULATION_API_URL}/simulation/${runId}/result`);
  }
}

// Data Fetcher endpoints
export class DataFetcherAPI {
  static async getHealth(): Promise<ApiResponse<{ status: string }>> {
    return apiRequest(`${DATA_FETCHER_URL}/health`);
  }

  static async getStatus(): Promise<ApiResponse<{
    last_fetch: string;
    total_games: number;
    total_players: number;
    total_teams: number;
  }>> {
    return apiRequest(`${DATA_FETCHER_URL}/status`);
  }

  static async triggerDataFetch(): Promise<ApiResponse<{ message: string }>> {
    return apiRequest(`${DATA_FETCHER_URL}/fetch`, {
      method: "POST",
    });
  }
}

// WebSocket connection for real-time simulation updates
export class SimulationWebSocket {
  private ws: WebSocket | null = null;
  private callbacks: {
    onStatus?: (status: SimulationStatus) => void;
    onResult?: (result: SimulationResult) => void;
    onError?: (error: string) => void;
  } = {};

  connect(runId: string, callbacks: typeof this.callbacks) {
    this.callbacks = callbacks;

    try {
      const wsUrl = getWebSocketUrl();
      this.ws = new WebSocket(`${wsUrl}/simulation/${runId}/ws`);
      
      this.ws.onopen = () => {
        console.log("WebSocket connected for simulation:", runId);
      };
      
      this.ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          
          if (data.type === "status" && this.callbacks.onStatus) {
            this.callbacks.onStatus(data.payload);
          } else if (data.type === "result" && this.callbacks.onResult) {
            this.callbacks.onResult(data.payload);
          }
        } catch (error) {
          console.error("Error parsing WebSocket message:", error);
          this.callbacks.onError?.(error instanceof Error ? error.message : "Unknown error");
        }
      };
      
      this.ws.onerror = (error) => {
        console.error("WebSocket error:", error);
        this.callbacks.onError?.("WebSocket connection error");
      };
      
      this.ws.onclose = () => {
        console.log("WebSocket connection closed");
        this.ws = null;
      };
    } catch (error) {
      console.error("Failed to connect WebSocket:", error);
      this.callbacks.onError?.(error instanceof Error ? error.message : "Connection failed");
    }
  }

  disconnect() {
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }
}

// Polling utility for simulation status when WebSocket is not available
export class SimulationPoller {
  private intervalId: number | null = null;
  private isPolling = false;

  start(
    runId: string,
    onUpdate: (status: SimulationStatus) => void,
    onComplete: (result: SimulationResult) => void,
    onError: (error: string) => void,
    intervalMs = 2000
  ) {
    if (this.isPolling) {
      this.stop();
    }

    this.isPolling = true;
    
    const poll = async () => {
      if (!this.isPolling) return;

      try {
        const statusResponse = await SimulationAPI.getSimulationStatus(runId);
        
        if (!statusResponse.success || !statusResponse.data) {
          onError(statusResponse.error || "Failed to get simulation status");
          this.stop();
          return;
        }

        const status = statusResponse.data;
        onUpdate(status);

        if (status.status === "completed") {
          const resultResponse = await SimulationAPI.getSimulationResult(runId);
          
          if (resultResponse.success && resultResponse.data) {
            onComplete(resultResponse.data);
          } else {
            onError(resultResponse.error || "Failed to get simulation result");
          }
          
          this.stop();
        } else if (status.status === "failed") {
          onError("Simulation failed");
          this.stop();
        }
      } catch (error) {
        onError(error instanceof Error ? error.message : "Polling error");
        this.stop();
      }
    };

    // Initial poll
    poll();
    
    // Set up interval polling
    this.intervalId = window.setInterval(poll, intervalMs);
  }

  stop() {
    this.isPolling = false;
    
    if (this.intervalId) {
      clearInterval(this.intervalId);
      this.intervalId = null;
    }
  }
}

// Error handling utilities
export function isApiError(response: ApiResponse<any>): response is ApiResponse<never> {
  return !response.success;
}

export function getErrorMessage(response: ApiResponse<any>): string {
  return response.error || "An unknown error occurred";
}

// Connection testing utility
export async function testConnections(): Promise<{
  apiGateway: boolean;
  simulationEngine: boolean;
  dataFetcher: boolean;
}> {
  const [apiGatewayResponse, dataFetcherResponse] = await Promise.allSettled([
    ApiGateway.getHealth(),
    DataFetcherAPI.getHealth(),
  ]);

  // For simulation engine, we'll test a different endpoint since it might not have a health check
  const simulationEngineTest = await fetch(`${SIMULATION_API_URL}/health`).catch(() => null);

  return {
    apiGateway: apiGatewayResponse.status === "fulfilled" && apiGatewayResponse.value.success,
    simulationEngine: simulationEngineTest?.ok === true,
    dataFetcher: dataFetcherResponse.status === "fulfilled" && dataFetcherResponse.value.success,
  };
}

export default {
  ApiGateway,
  SimulationAPI,
  DataFetcherAPI,
  SimulationWebSocket,
  SimulationPoller,
  testConnections,
  isApiError,
  getErrorMessage,
  apiCache,
};