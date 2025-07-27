import { React, useParams, useNavigate, PlayCircle, Clock, TrendingUp, BarChart, PieChart, Pie, Cell, ResponsiveContainer, BarChart as RechartsBarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend } from "../../deps.ts";

interface SimulationResult {
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

interface SimulationStatus {
  runId: string;
  gameId: string;
  status: string;
  totalRuns: number;
  completedRuns: number;
  progress: number;
  createdAt: string;
}

function SimulationPage() {
  const { gameId } = useParams();
  const navigate = useNavigate();
  
  const [simulationStatus, setSimulationStatus] = React.useState<SimulationStatus | null>(null);
  const [simulationResult, setSimulationResult] = React.useState<SimulationResult | null>(null);
  const [isStarting, setIsStarting] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);

  // Mock game data
  const gameData = {
    gameId: gameId,
    homeTeam: { name: "Red Sox", abbreviation: "BOS", city: "Boston" },
    awayTeam: { name: "Yankees", abbreviation: "NYY", city: "New York" },
    gameDate: "2024-04-15T19:10:00",
    stadium: "Fenway Park"
  };

  const startSimulation = async () => {
    setIsStarting(true);
    setError(null);
    
    try {
      // Mock simulation start
      const mockRunId = `sim_${Date.now()}`;
      setSimulationStatus({
        runId: mockRunId,
        gameId: gameId!,
        status: "running",
        totalRuns: 1000,
        completedRuns: 0,
        progress: 0,
        createdAt: new Date().toISOString()
      });
      
      // Simulate progress updates
      let completed = 0;
      const interval = setInterval(() => {
        completed += Math.floor(Math.random() * 50) + 20;
        if (completed >= 1000) {
          completed = 1000;
          clearInterval(interval);
          
          // Set completion status
          setSimulationStatus(prev => prev ? { ...prev, status: "completed", completedRuns: 1000, progress: 100 } : null);
          
          // Generate mock results
          const mockResults: SimulationResult = {
            runId: mockRunId,
            homeWinProbability: 67.3,
            awayWinProbability: 32.7,
            expectedHomeScore: 5.2,
            expectedAwayScore: 3.8,
            homeScoreDistribution: { 0: 45, 1: 89, 2: 134, 3: 178, 4: 165, 5: 142, 6: 98, 7: 67, 8: 45, 9: 25, 10: 12 },
            awayScoreDistribution: { 0: 67, 1: 123, 2: 187, 3: 189, 4: 156, 5: 119, 6: 78, 7: 48, 8: 23, 9: 8, 10: 2 },
            metadata: {
              totalSimulations: 1000,
              averageGameDuration: 185.4,
              averagePitches: 287.6
            }
          };
          
          setTimeout(() => {
            setSimulationResult(mockResults);
          }, 1000);
        } else {
          setSimulationStatus(prev => prev ? { 
            ...prev, 
            completedRuns: completed, 
            progress: (completed / 1000) * 100 
          } : null);
        }
      }, 200);
      
    } catch (err) {
      setError("Failed to start simulation");
    } finally {
      setIsStarting(false);
    }
  };

  const getScoreDistributionData = (distribution: Record<number, number>) => {
    return Object.entries(distribution).map(([score, count]) => ({
      score: parseInt(score),
      count,
      percentage: ((count / 1000) * 100).toFixed(1)
    }));
  };

  const pieData = simulationResult ? [
    { name: gameData.homeTeam.name, value: simulationResult.homeWinProbability, color: "#3b82f6" },
    { name: gameData.awayTeam.name, value: simulationResult.awayWinProbability, color: "#ef4444" }
  ] : [];

  return React.createElement(
    "div",
    { className: "space-y-6" },
    
    // Header
    React.createElement(
      "div",
      { className: "flex items-center justify-between" },
      React.createElement(
        "div",
        {},
        React.createElement(
          "button",
          {
            onClick: () => navigate("/games"),
            className: "text-blue-600 hover:text-blue-800 mb-2"
          },
          "← Back to Games"
        ),
        React.createElement(
          "h1",
          { className: "text-2xl font-bold text-gray-900" },
          "Monte Carlo Simulation"
        ),
        React.createElement(
          "p",
          { className: "text-gray-500" },
          `${gameData.awayTeam.city} ${gameData.awayTeam.name} @ ${gameData.homeTeam.city} ${gameData.homeTeam.name}`
        )
      )
    ),

    // Game info card
    React.createElement(
      "div",
      { className: "card" },
      React.createElement(
        "div",
        { className: "flex items-center justify-between" },
        React.createElement(
          "div",
          { className: "flex items-center space-x-8" },
          React.createElement(
            "div",
            { className: "text-center" },
            React.createElement(
              "div",
              { className: "text-2xl font-bold text-gray-900" },
              gameData.awayTeam.abbreviation
            ),
            React.createElement(
              "div",
              { className: "text-sm text-gray-500" },
              gameData.awayTeam.name
            )
          ),
          React.createElement(
            "div",
            { className: "text-gray-400 text-xl font-bold" },
            "VS"
          ),
          React.createElement(
            "div",
            { className: "text-center" },
            React.createElement(
              "div",
              { className: "text-2xl font-bold text-gray-900" },
              gameData.homeTeam.abbreviation
            ),
            React.createElement(
              "div",
              { className: "text-sm text-gray-500" },
              gameData.homeTeam.name
            )
          )
        ),
        React.createElement(
          "div",
          { className: "text-right" },
          React.createElement(
            "div",
            { className: "text-sm text-gray-500 mb-1" },
            gameData.stadium
          ),
          React.createElement(
            "div",
            { className: "text-sm text-gray-500" },
            new Date(gameData.gameDate).toLocaleString()
          )
        )
      )
    ),

    // Simulation controls and status
    !simulationStatus ? React.createElement(
      "div",
      { className: "card text-center py-12" },
      React.createElement(
        "div",
        { className: "mb-6" },
        React.createElement(PlayCircle, { className: "mx-auto h-16 w-16 text-blue-600" })
      ),
      React.createElement(
        "h2",
        { className: "text-xl font-semibold mb-2" },
        "Ready to Simulate"
      ),
      React.createElement(
        "p",
        { className: "text-gray-500 mb-6" },
        "Run 1,000 Monte Carlo simulations to predict game outcomes"
      ),
      React.createElement(
        "button",
        {
          onClick: startSimulation,
          disabled: isStarting,
          className: "btn btn-primary btn-lg"
        },
        isStarting ? React.createElement(
          React.Fragment,
          {},
          React.createElement("div", { className: "spinner mr-2" }),
          "Starting..."
        ) : React.createElement(
          React.Fragment,
          {},
          React.createElement(PlayCircle, { className: "mr-2 h-5 w-5" }),
          "Start Simulation"
        )
      )
    ) : React.createElement(
      "div",
      { className: "card" },
      React.createElement(
        "div",
        { className: "flex items-center justify-between mb-4" },
        React.createElement(
          "h2",
          { className: "text-lg font-semibold flex items-center" },
          React.createElement(Clock, { className: "mr-2 h-5 w-5" }),
          simulationStatus.status === "completed" ? "Simulation Complete" : "Simulation Running"
        ),
        React.createElement(
          "div",
          { className: "text-sm text-gray-500" },
          `${simulationStatus.completedRuns} / ${simulationStatus.totalRuns} runs`
        )
      ),
      React.createElement(
        "div",
        { className: "progress-bar mb-2" },
        React.createElement(
          "div",
          { 
            className: "progress-bar-fill",
            style: { width: `${simulationStatus.progress}%` }
          }
        )
      ),
      React.createElement(
        "div",
        { className: "text-sm text-gray-600" },
        `${simulationStatus.progress.toFixed(1)}% complete`
      )
    ),

    // Results
    simulationResult && React.createElement(
      React.Fragment,
      {},
      
      // Win probability
      React.createElement(
        "div",
        { className: "grid grid-cols-1 lg:grid-cols-2 gap-6" },
        React.createElement(
          "div",
          { className: "card" },
          React.createElement(
            "h3",
            { className: "text-lg font-semibold mb-4 flex items-center" },
            React.createElement(TrendingUp, { className: "mr-2 h-5 w-5" }),
            "Win Probability"
          ),
          React.createElement(
            "div",
            { className: "chart-container" },
            React.createElement(
              ResponsiveContainer,
              { width: "100%", height: "100%" },
              React.createElement(
                PieChart,
                {},
                React.createElement(
                  Pie,
                  {
                    data: pieData,
                    cx: "50%",
                    cy: "50%",
                    innerRadius: 60,
                    outerRadius: 120,
                    paddingAngle: 5,
                    dataKey: "value"
                  },
                  ...pieData.map((entry, index) =>
                    React.createElement(Cell, { key: `cell-${index}`, fill: entry.color })
                  )
                ),
                React.createElement(Tooltip, { formatter: (value: number) => `${value}%` }),
                React.createElement(Legend)
              )
            )
          )
        ),
        
        React.createElement(
          "div",
          { className: "card" },
          React.createElement(
            "h3",
            { className: "text-lg font-semibold mb-4" },
            "Expected Scores"
          ),
          React.createElement(
            "div",
            { className: "space-y-4" },
            React.createElement(
              "div",
              { className: "flex items-center justify-between p-4 bg-blue-50 rounded-lg" },
              React.createElement(
                "div",
                {},
                React.createElement(
                  "div",
                  { className: "font-semibold text-blue-900" },
                  `${gameData.homeTeam.name} (Home)`
                ),
                React.createElement(
                  "div",
                  { className: "text-sm text-blue-700" },
                  `${simulationResult.homeWinProbability}% win probability`
                )
              ),
              React.createElement(
                "div",
                { className: "text-2xl font-bold text-blue-600" },
                simulationResult.expectedHomeScore.toFixed(1)
              )
            ),
            React.createElement(
              "div",
              { className: "flex items-center justify-between p-4 bg-red-50 rounded-lg" },
              React.createElement(
                "div",
                {},
                React.createElement(
                  "div",
                  { className: "font-semibold text-red-900" },
                  `${gameData.awayTeam.name} (Away)`
                ),
                React.createElement(
                  "div",
                  { className: "text-sm text-red-700" },
                  `${simulationResult.awayWinProbability}% win probability`
                )
              ),
              React.createElement(
                "div",
                { className: "text-2xl font-bold text-red-600" },
                simulationResult.expectedAwayScore.toFixed(1)
              )
            )
          )
        )
      ),

      // Score distributions
      React.createElement(
        "div",
        { className: "card" },
        React.createElement(
          "h3",
          { className: "text-lg font-semibold mb-4 flex items-center" },
          React.createElement(BarChart, { className: "mr-2 h-5 w-5" }),
          "Score Distribution"
        ),
        React.createElement(
          "div",
          { className: "chart-container" },
          React.createElement(
            ResponsiveContainer,
            { width: "100%", height: "100%" },
            React.createElement(
              RechartsBarChart,
              { 
                data: getScoreDistributionData(simulationResult.homeScoreDistribution).slice(0, 11) 
              },
              React.createElement(CartesianGrid, { strokeDasharray: "3 3" }),
              React.createElement(XAxis, { dataKey: "score" }),
              React.createElement(YAxis),
              React.createElement(Tooltip, { 
                formatter: (value: number, name: string) => [
                  `${value} games (${((value / 1000) * 100).toFixed(1)}%)`, 
                  "Frequency"
                ]
              }),
              React.createElement(Bar, { dataKey: "count", fill: "#3b82f6", name: `${gameData.homeTeam.name} Score Distribution` })
            )
          )
        )
      ),

      // Simulation metadata
      React.createElement(
        "div",
        { className: "stats-grid" },
        React.createElement(
          "div",
          { className: "stat-card" },
          React.createElement(
            "div",
            { className: "stat-value text-blue-600" },
            simulationResult.metadata.totalSimulations.toLocaleString()
          ),
          React.createElement(
            "div",
            { className: "stat-label" },
            "Total Simulations"
          )
        ),
        React.createElement(
          "div",
          { className: "stat-card" },
          React.createElement(
            "div",
            { className: "stat-value text-green-600" },
            `${simulationResult.metadata.averageGameDuration.toFixed(1)} min`
          ),
          React.createElement(
            "div",
            { className: "stat-label" },
            "Avg Game Duration"
          )
        ),
        React.createElement(
          "div",
          { className: "stat-card" },
          React.createElement(
            "div",
            { className: "stat-value text-purple-600" },
            simulationResult.metadata.averagePitches.toFixed(0)
          ),
          React.createElement(
            "div",
            { className: "stat-label" },
            "Avg Total Pitches"
          )
        )
      )
    ),

    error && React.createElement(
      "div",
      { className: "bg-red-50 border border-red-200 rounded-lg p-4" },
      React.createElement(
        "div",
        { className: "text-red-800" },
        error
      )
    )
  );
}

export default SimulationPage;