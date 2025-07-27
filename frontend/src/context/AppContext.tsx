import { React } from "../../deps.ts";
import { useAppState } from "../hooks/useAppState.ts";
import { 
  Game, 
  Team, 
  Player, 
  SimulationStatus, 
  SimulationResult 
} from "../utils/api.ts";

interface AppContextType {
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
  
  // Actions
  fetchGames: (date?: string) => Promise<void>;
  fetchTeams: () => Promise<void>;
  fetchPlayers: () => Promise<void>;
  refreshAll: () => Promise<void>;
  startSimulation: (gameId: string) => Promise<void>;
  stopSimulation: () => void;
  clearSimulation: () => void;
  setSelectedDate: (date: string) => void;
  clearError: () => void;
  testConnections: () => Promise<void>;
}

const AppContext = React.createContext<AppContextType | null>(null);

interface AppProviderProps {
  children?: React.ReactNode;
}

export function AppProvider({ children }: AppProviderProps) {
  const [state, actions] = useAppState();

  const contextValue: AppContextType = {
    ...state,
    ...actions,
  };

  return React.createElement(
    AppContext.Provider,
    { value: contextValue },
    children
  );
}

export function useApp(): AppContextType {
  const context = React.useContext(AppContext);
  
  if (!context) {
    throw new Error('useApp must be used within an AppProvider');
  }
  
  return context;
}

export default AppContext;