import { React, Link, BarChart3, PlayCircle, Users, TrendingUp, Calendar, Activity } from "../../deps.ts";
import { useApp } from "../context/AppContext.tsx";
import ConnectionStatus from "../components/ConnectionStatus.tsx";

function HomePage() {
  const { teams, players, games, fetchTeams, fetchPlayers, testConnections } = useApp();

  React.useEffect(() => {
    // Load initial data and test connections
    fetchTeams();
    fetchPlayers();
    testConnections();
  }, []);

  const stats = [
    { label: "Total Games Simulated", value: "1,247", icon: PlayCircle, color: "text-blue-600" },
    { label: "Active Teams", value: teams.length.toString(), icon: Users, color: "text-green-600" },
    { label: "Players Tracked", value: players.length.toString(), icon: Users, color: "text-purple-600" },
    { label: "Simulation Accuracy", value: "94.2%", icon: TrendingUp, color: "text-orange-600" },
  ];

  const recentSimulations = [
    { id: 1, homeTeam: "Red Sox", awayTeam: "Yankees", date: "2024-07-27", status: "completed", homeWin: 67.3 },
    { id: 2, homeTeam: "Cubs", awayTeam: "Rockies", date: "2024-07-26", status: "completed", homeWin: 58.9 },
    { id: 3, homeTeam: "Yankees", awayTeam: "Red Sox", date: "2024-07-25", status: "running", homeWin: null },
  ];

  return React.createElement(
    "div",
    { className: "space-y-6" },
    
    // Welcome section
    React.createElement(
      "div",
      { className: "bg-gradient-to-r from-blue-600 to-blue-800 rounded-lg p-8 text-white" },
      React.createElement(
        "h1",
        { className: "text-3xl font-bold mb-2" },
        "Welcome to Baseball Simulation"
      ),
      React.createElement(
        "p",
        { className: "text-blue-100 text-lg" },
        "Advanced Monte Carlo simulations for baseball game predictions and analytics"
      ),
      React.createElement(
        "div",
        { className: "mt-6 flex flex-wrap gap-4" },
        React.createElement(
          Link,
          { 
            to: "/games",
            className: "btn btn-primary bg-white text-blue-600 hover:bg-gray-100"
          },
          React.createElement(Calendar, { className: "mr-2 h-4 w-4" }),
          "View Games"
        ),
        React.createElement(
          Link,
          { 
            to: "/teams",
            className: "btn btn-secondary bg-blue-700 text-white hover:bg-blue-600"
          },
          React.createElement(Users, { className: "mr-2 h-4 w-4" }),
          "Browse Teams"
        )
      )
    ),

    // Statistics overview
    React.createElement(
      "div",
      { className: "stats-grid" },
      ...stats.map((stat, index) =>
        React.createElement(
          "div",
          { key: index, className: "stat-card" },
          React.createElement(
            "div",
            { className: "flex items-center justify-center mb-2" },
            React.createElement(stat.icon, { className: `h-8 w-8 ${stat.color}` })
          ),
          React.createElement(
            "div",
            { className: `stat-value ${stat.color}` },
            stat.value
          ),
          React.createElement(
            "div",
            { className: "stat-label" },
            stat.label
          )
        )
      )
    ),

    React.createElement(
      "div",
      { className: "grid grid-cols-1 lg:grid-cols-3 gap-6" },

      // Recent simulations
      React.createElement(
        "div",
        { className: "card" },
        React.createElement(
          "div",
          { className: "card-header" },
          React.createElement(
            "h2",
            { className: "card-title flex items-center" },
            React.createElement(Activity, { className: "mr-2 h-5 w-5" }),
            "Recent Simulations"
          )
        ),
        React.createElement(
          "div",
          { className: "space-y-3" },
          ...recentSimulations.map((sim) =>
            React.createElement(
              "div",
              { 
                key: sim.id,
                className: "flex items-center justify-between p-3 bg-gray-50 rounded-lg"
              },
              React.createElement(
                "div",
                {},
                React.createElement(
                  "div",
                  { className: "font-medium" },
                  `${sim.awayTeam} @ ${sim.homeTeam}`
                ),
                React.createElement(
                  "div",
                  { className: "text-sm text-gray-500" },
                  sim.date
                )
              ),
              React.createElement(
                "div",
                { className: "text-right" },
                sim.status === "completed" 
                  ? React.createElement(
                      "div",
                      { className: "text-sm font-medium text-green-600" },
                      `${sim.homeWin}% home win`
                    )
                  : React.createElement(
                      "div",
                      { className: "text-sm text-orange-600 flex items-center" },
                      React.createElement("div", { className: "spinner mr-2" }),
                      "Running..."
                    )
              )
            )
          )
        ),
        React.createElement(
          "div",
          { className: "mt-4 text-center" },
          React.createElement(
            Link,
            { 
              to: "/games",
              className: "text-blue-600 hover:text-blue-800 text-sm font-medium"
            },
            "View all simulations →"
          )
        )
      ),

      // Quick actions
      React.createElement(
        "div",
        { className: "card" },
        React.createElement(
          "div",
          { className: "card-header" },
          React.createElement(
            "h2",
            { className: "card-title" },
            "Quick Actions"
          )
        ),
        React.createElement(
          "div",
          { className: "space-y-3" },
          React.createElement(
            Link,
            { 
              to: "/games",
              className: "flex items-center p-3 bg-blue-50 rounded-lg hover:bg-blue-100 transition-colors"
            },
            React.createElement(PlayCircle, { className: "mr-3 h-6 w-6 text-blue-600" }),
            React.createElement(
              "div",
              {},
              React.createElement(
                "div",
                { className: "font-medium" },
                "Start New Simulation"
              ),
              React.createElement(
                "div",
                { className: "text-sm text-gray-500" },
                "Run Monte Carlo analysis on upcoming games"
              )
            )
          ),
          React.createElement(
            Link,
            { 
              to: "/stats",
              className: "flex items-center p-3 bg-green-50 rounded-lg hover:bg-green-100 transition-colors"
            },
            React.createElement(BarChart3, { className: "mr-3 h-6 w-6 text-green-600" }),
            React.createElement(
              "div",
              {},
              React.createElement(
                "div",
                { className: "font-medium" },
                "View Analytics"
              ),
              React.createElement(
                "div",
                { className: "text-sm text-gray-500" },
                "Explore team and player statistics"
              )
            )
          ),
          React.createElement(
            Link,
            { 
              to: "/teams",
              className: "flex items-center p-3 bg-purple-50 rounded-lg hover:bg-purple-100 transition-colors"
            },
            React.createElement(Users, { className: "mr-3 h-6 w-6 text-purple-600" }),
            React.createElement(
              "div",
              {},
              React.createElement(
                "div",
                { className: "font-medium" },
                "Team Comparison"
              ),
              React.createElement(
                "div",
                { className: "text-sm text-gray-500" },
                "Compare team statistics and performance"
              )
            )
          )
        )
      ),

      // Connection status
      React.createElement(ConnectionStatus)
    )
  );
}

export default HomePage;