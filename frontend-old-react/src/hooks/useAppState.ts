import { React } from "../../deps.ts";
import { 
  ApiGateway, 
  SimulationAPI, 
  DataFetcherAPI,
  Game, 
  Team, 
  Player, 
  SimulationStatus, 
  SimulationResult,
  SimulationPoller,
  isApiError,
  getErrorMessage 
} from "../utils/api.ts";

interface AppState {
  // Data
  games: Game[];
  teams: Team[];
  players: Player[];
  
  // Loading states
  gamesLoading: boolean;
  teamsLoading: boolean;
  playersLoading: boolean;
  
  // Connection status
  connectionStatus: {
    apiGateway: boolean;
    simulationEngine: boolean;
    dataFetcher: boolean;
  };
  
  // Current simulation
  currentSimulation: {
    runId: string | null;
    status: SimulationStatus | null;
    result: SimulationResult | null;
    error: string | null;
  };
  
  // UI state
  selectedDate: string;
  error: string | null;
}

interface AppActions {
  // Data fetching
  fetchGames: (date?: string) => Promise<void>;
  fetchTeams: () => Promise<void>;
  fetchPlayers: () => Promise<void>;
  refreshAll: () => Promise<void>;
  
  // Simulation management
  startSimulation: (gameId: string) => Promise<void>;
  stopSimulation: () => void;
  clearSimulation: () => void;
  
  // UI actions
  setSelectedDate: (date: string) => void;
  clearError: () => void;
  
  // Connection testing
  testConnections: () => Promise<void>;
}

const initialState: AppState = {
  games: [],
  teams: [],
  players: [],
  gamesLoading: false,
  teamsLoading: false,
  playersLoading: false,
  connectionStatus: {
    apiGateway: false,
    simulationEngine: false,
    dataFetcher: false,
  },
  currentSimulation: {
    runId: null,
    status: null,
    result: null,
    error: null,
  },
  selectedDate: new Date().toISOString().split('T')[0],
  error: null,
};

type AppAction = 
  | { type: 'SET_GAMES'; payload: Game[] }
  | { type: 'SET_TEAMS'; payload: Team[] }
  | { type: 'SET_PLAYERS'; payload: Player[] }
  | { type: 'SET_GAMES_LOADING'; payload: boolean }
  | { type: 'SET_TEAMS_LOADING'; payload: boolean }
  | { type: 'SET_PLAYERS_LOADING'; payload: boolean }
  | { type: 'SET_CONNECTION_STATUS'; payload: typeof initialState.connectionStatus }
  | { type: 'SET_SIMULATION_STATUS'; payload: SimulationStatus }
  | { type: 'SET_SIMULATION_RESULT'; payload: SimulationResult }
  | { type: 'SET_SIMULATION_ERROR'; payload: string }
  | { type: 'START_SIMULATION'; payload: string }
  | { type: 'CLEAR_SIMULATION' }
  | { type: 'SET_SELECTED_DATE'; payload: string }
  | { type: 'SET_ERROR'; payload: string }
  | { type: 'CLEAR_ERROR' };

function appReducer(state: AppState, action: AppAction): AppState {
  switch (action.type) {
    case 'SET_GAMES':
      return { ...state, games: action.payload, gamesLoading: false };
    
    case 'SET_TEAMS':
      return { ...state, teams: action.payload, teamsLoading: false };
    
    case 'SET_PLAYERS':
      return { ...state, players: action.payload, playersLoading: false };
    
    case 'SET_GAMES_LOADING':
      return { ...state, gamesLoading: action.payload };
    
    case 'SET_TEAMS_LOADING':
      return { ...state, teamsLoading: action.payload };
    
    case 'SET_PLAYERS_LOADING':
      return { ...state, playersLoading: action.payload };
    
    case 'SET_CONNECTION_STATUS':
      return { ...state, connectionStatus: action.payload };
    
    case 'SET_SIMULATION_STATUS':
      return {
        ...state,
        currentSimulation: {
          ...state.currentSimulation,
          status: action.payload,
          error: null,
        },
      };
    
    case 'SET_SIMULATION_RESULT':
      return {
        ...state,
        currentSimulation: {
          ...state.currentSimulation,
          result: action.payload,
        },
      };
    
    case 'SET_SIMULATION_ERROR':
      return {
        ...state,
        currentSimulation: {
          ...state.currentSimulation,
          error: action.payload,
        },
      };
    
    case 'START_SIMULATION':
      return {
        ...state,
        currentSimulation: {
          runId: action.payload,
          status: null,
          result: null,
          error: null,
        },
      };
    
    case 'CLEAR_SIMULATION':
      return {
        ...state,
        currentSimulation: {
          runId: null,
          status: null,
          result: null,
          error: null,
        },
      };
    
    case 'SET_SELECTED_DATE':
      return { ...state, selectedDate: action.payload };
    
    case 'SET_ERROR':
      return { ...state, error: action.payload };
    
    case 'CLEAR_ERROR':
      return { ...state, error: null };
    
    default:
      return state;
  }
}

export function useAppState(): [AppState, AppActions] {
  const [state, dispatch] = React.useReducer(appReducer, initialState);
  const simulationPollerRef = React.useRef<SimulationPoller | null>(null);

  // Actions
  const actions: AppActions = {
    fetchGames: React.useCallback(async (date?: string) => {
      dispatch({ type: 'SET_GAMES_LOADING', payload: true });
      dispatch({ type: 'CLEAR_ERROR' });
      
      try {
        const response = date 
          ? await ApiGateway.getGamesByDate(date)
          : await ApiGateway.getGames();
        
        if (isApiError(response)) {
          throw new Error(getErrorMessage(response));
        }
        
        dispatch({ type: 'SET_GAMES', payload: response.data || [] });
      } catch (error) {
        const errorMessage = error instanceof Error ? error.message : 'Failed to fetch games';
        dispatch({ type: 'SET_ERROR', payload: errorMessage });
        dispatch({ type: 'SET_GAMES_LOADING', payload: false });
      }
    }, []),

    fetchTeams: React.useCallback(async () => {
      dispatch({ type: 'SET_TEAMS_LOADING', payload: true });
      dispatch({ type: 'CLEAR_ERROR' });
      
      try {
        const response = await ApiGateway.getTeams();
        
        if (isApiError(response)) {
          throw new Error(getErrorMessage(response));
        }
        
        dispatch({ type: 'SET_TEAMS', payload: response.data || [] });
      } catch (error) {
        const errorMessage = error instanceof Error ? error.message : 'Failed to fetch teams';
        dispatch({ type: 'SET_ERROR', payload: errorMessage });
        dispatch({ type: 'SET_TEAMS_LOADING', payload: false });
      }
    }, []),

    fetchPlayers: React.useCallback(async () => {
      dispatch({ type: 'SET_PLAYERS_LOADING', payload: true });
      dispatch({ type: 'CLEAR_ERROR' });
      
      try {
        const response = await ApiGateway.getPlayers();
        
        if (isApiError(response)) {
          throw new Error(getErrorMessage(response));
        }
        
        dispatch({ type: 'SET_PLAYERS', payload: response.data || [] });
      } catch (error) {
        const errorMessage = error instanceof Error ? error.message : 'Failed to fetch players';
        dispatch({ type: 'SET_ERROR', payload: errorMessage });
        dispatch({ type: 'SET_PLAYERS_LOADING', payload: false });
      }
    }, []),

    refreshAll: React.useCallback(async () => {
      await Promise.all([
        actions.fetchGames(state.selectedDate),
        actions.fetchTeams(),
        actions.fetchPlayers(),
      ]);
    }, [state.selectedDate]),

    startSimulation: React.useCallback(async (gameId: string) => {
      dispatch({ type: 'CLEAR_ERROR' });
      
      try {
        const response = await SimulationAPI.startSimulation({
          gameId,
          runs: 1000,
          workers: 4,
        });
        
        if (isApiError(response)) {
          throw new Error(getErrorMessage(response));
        }
        
        const runId = response.data?.runId;
        if (!runId) {
          throw new Error('No run ID returned from simulation start');
        }
        
        dispatch({ type: 'START_SIMULATION', payload: runId });
        
        // Start polling for simulation updates
        if (simulationPollerRef.current) {
          simulationPollerRef.current.stop();
        }
        
        simulationPollerRef.current = new SimulationPoller();
        simulationPollerRef.current.start(
          runId,
          (status: SimulationStatus) => {
            dispatch({ type: 'SET_SIMULATION_STATUS', payload: status });
          },
          (result: SimulationResult) => {
            dispatch({ type: 'SET_SIMULATION_RESULT', payload: result });
          },
          (error: string) => {
            dispatch({ type: 'SET_SIMULATION_ERROR', payload: error });
          }
        );
        
      } catch (error) {
        const errorMessage = error instanceof Error ? error.message : 'Failed to start simulation';
        dispatch({ type: 'SET_SIMULATION_ERROR', payload: errorMessage });
      }
    }, []),

    stopSimulation: React.useCallback(() => {
      if (simulationPollerRef.current) {
        simulationPollerRef.current.stop();
        simulationPollerRef.current = null;
      }
    }, []),

    clearSimulation: React.useCallback(() => {
      if (simulationPollerRef.current) {
        simulationPollerRef.current.stop();
        simulationPollerRef.current = null;
      }
      dispatch({ type: 'CLEAR_SIMULATION' });
    }, []),

    setSelectedDate: React.useCallback((date: string) => {
      dispatch({ type: 'SET_SELECTED_DATE', payload: date });
    }, []),

    clearError: React.useCallback(() => {
      dispatch({ type: 'CLEAR_ERROR' });
    }, []),

    testConnections: React.useCallback(async () => {
      try {
        const connectionTests = await Promise.allSettled([
          ApiGateway.getHealth(),
          DataFetcherAPI.getHealth(),
          fetch('http://localhost:8081/health').then(r => r.ok),
        ]);

        const connectionStatus = {
          apiGateway: connectionTests[0].status === 'fulfilled' && connectionTests[0].value.success,
          dataFetcher: connectionTests[1].status === 'fulfilled' && connectionTests[1].value.success,
          simulationEngine: connectionTests[2].status === 'fulfilled' && connectionTests[2].value === true,
        };

        dispatch({ type: 'SET_CONNECTION_STATUS', payload: connectionStatus });
      } catch (error) {
        console.error('Connection test failed:', error);
        dispatch({ 
          type: 'SET_CONNECTION_STATUS', 
          payload: { apiGateway: false, simulationEngine: false, dataFetcher: false } 
        });
      }
    }, []),
  };

  // Cleanup effect
  React.useEffect(() => {
    return () => {
      if (simulationPollerRef.current) {
        simulationPollerRef.current.stop();
      }
    };
  }, []);

  // Auto-refresh games when date changes
  React.useEffect(() => {
    actions.fetchGames(state.selectedDate);
  }, [state.selectedDate, actions.fetchGames]);

  return [state, actions];
}

export default useAppState;