import { React, BarChart3, TrendingUp, Target, Trophy, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, BarChart, Bar, PieChart, Pie, Cell } from "../../deps.ts";

function StatsPage() {
  const [selectedCategory, setSelectedCategory] = React.useState("team");
  const [selectedStat, setSelectedStat] = React.useState("batting");
  const [timeFrame, setTimeFrame] = React.useState("season");

  // Mock statistics data
  const teamBattingStats = [
    { team: "NYY", avg: 0.254, hr: 254, rbi: 807, ops: 0.753 },
    { team: "BOS", avg: 0.267, hr: 213, rbi: 745, ops: 0.742 },
    { team: "CHC", avg: 0.243, hr: 167, rbi: 694, ops: 0.698 },
    { team: "COL", avg: 0.259, hr: 192, rbi: 729, ops: 0.721 }
  ];

  const teamPitchingStats = [
    { team: "NYY", era: 3.30, whip: 1.19, k9: 9.2, hr9: 1.1 },
    { team: "BOS", era: 3.92, whip: 1.31, k9: 8.8, hr9: 1.3 },
    { team: "CHC", era: 4.01, whip: 1.35, k9: 8.5, hr9: 1.4 },
    { team: "COL", era: 5.34, whip: 1.52, k9: 7.9, hr9: 1.8 }
  ];

  const monthlyTrends = [
    { month: "Apr", runs: 4.2, era: 3.8, wins: 15 },
    { month: "May", runs: 4.8, era: 3.6, wins: 18 },
    { month: "Jun", runs: 5.1, era: 3.9, wins: 16 },
    { month: "Jul", runs: 4.9, era: 4.1, wins: 17 },
    { month: "Aug", runs: 4.6, era: 3.7, wins: 19 },
    { month: "Sep", runs: 4.3, era: 3.5, wins: 20 }
  ];

  const simulationAccuracy = [
    { type: "Correct Winner", value: 72, color: "#10b981" },
    { type: "Score Within 1", value: 45, color: "#3b82f6" },
    { type: "Score Within 2", value: 68, color: "#8b5cf6" },
    { type: "Other", value: 15, color: "#ef4444" }
  ];

  const leaderboardData = {
    batting: [
      { rank: 1, player: "Aaron Judge", team: "NYY", stat: 0.311, label: "Batting Average" },
      { rank: 2, player: "Mookie Betts", team: "BOS", stat: 0.295, label: "Batting Average" },
      { rank: 3, player: "Rafael Devers", team: "BOS", stat: 0.279, label: "Batting Average" }
    ],
    pitching: [
      { rank: 1, player: "Chris Sale", team: "BOS", stat: 2.93, label: "ERA" },
      { rank: 2, player: "Gerrit Cole", team: "NYY", stat: 3.20, label: "ERA" },
      { rank: 3, player: "Yu Darvish", team: "CHC", stat: 3.45, label: "ERA" }
    ]
  };

  const categories = [
    { value: "team", label: "Team Statistics" },
    { value: "player", label: "Player Leaderboards" },
    { value: "simulation", label: "Simulation Analytics" }
  ];

  const statTypes = [
    { value: "batting", label: "Batting" },
    { value: "pitching", label: "Pitching" },
    { value: "fielding", label: "Fielding" }
  ];

  const timeFrames = [
    { value: "season", label: "Full Season" },
    { value: "month", label: "Last 30 Days" },
    { value: "week", label: "Last 7 Days" }
  ];

  const getCurrentData = () => {
    if (selectedCategory === "team") {
      return selectedStat === "batting" ? teamBattingStats : teamPitchingStats;
    }
    return leaderboardData[selectedStat as keyof typeof leaderboardData] || [];
  };

  return React.createElement(
    "div",
    { className: "space-y-6" },
    
    // Page header
    React.createElement(
      "div",
      { className: "flex flex-col sm:flex-row sm:items-center sm:justify-between" },
      React.createElement(
        "div",
        {},
        React.createElement(
          "h1",
          { className: "text-2xl font-bold text-gray-900" },
          "Advanced Analytics"
        ),
        React.createElement(
          "p",
          { className: "mt-1 text-sm text-gray-500" },
          "Comprehensive statistics and simulation insights"
        )
      )
    ),

    // Controls
    React.createElement(
      "div",
      { className: "card" },
      React.createElement(
        "div",
        { className: "grid grid-cols-1 md:grid-cols-3 gap-4" },
        React.createElement(
          "select",
          {
            value: selectedCategory,
            onChange: (e: React.ChangeEvent<HTMLSelectElement>) => setSelectedCategory(e.target.value),
            className: "form-input"
          },
          ...categories.map(cat =>
            React.createElement("option", { key: cat.value, value: cat.value }, cat.label)
          )
        ),
        React.createElement(
          "select",
          {
            value: selectedStat,
            onChange: (e: React.ChangeEvent<HTMLSelectElement>) => setSelectedStat(e.target.value),
            className: "form-input",
            disabled: selectedCategory === "simulation"
          },
          ...statTypes.map(stat =>
            React.createElement("option", { key: stat.value, value: stat.value }, stat.label)
          )
        ),
        React.createElement(
          "select",
          {
            value: timeFrame,
            onChange: (e: React.ChangeEvent<HTMLSelectElement>) => setTimeFrame(e.target.value),
            className: "form-input"
          },
          ...timeFrames.map(tf =>
            React.createElement("option", { key: tf.value, value: tf.value }, tf.label)
          )
        )
      )
    ),

    // Summary cards
    React.createElement(
      "div",
      { className: "stats-grid" },
      React.createElement(
        "div",
        { className: "stat-card" },
        React.createElement(
          "div",
          { className: "flex items-center justify-center mb-2" },
          React.createElement(Target, { className: "h-8 w-8 text-blue-600" })
        ),
        React.createElement(
          "div",
          { className: "stat-value text-blue-600" },
          "94.2%"
        ),
        React.createElement(
          "div",
          { className: "stat-label" },
          "Simulation Accuracy"
        )
      ),
      React.createElement(
        "div",
        { className: "stat-card" },
        React.createElement(
          "div",
          { className: "flex items-center justify-center mb-2" },
          React.createElement(TrendingUp, { className: "h-8 w-8 text-green-600" })
        ),
        React.createElement(
          "div",
          { className: "stat-value text-green-600" },
          "1,247"
        ),
        React.createElement(
          "div",
          { className: "stat-label" },
          "Games Simulated"
        )
      ),
      React.createElement(
        "div",
        { className: "stat-card" },
        React.createElement(
          "div",
          { className: "flex items-center justify-center mb-2" },
          React.createElement(BarChart3, { className: "h-8 w-8 text-purple-600" })
        ),
        React.createElement(
          "div",
          { className: "stat-value text-purple-600" },
          "4.7"
        ),
        React.createElement(
          "div",
          { className: "stat-label" },
          "Avg Runs/Game"
        )
      ),
      React.createElement(
        "div",
        { className: "stat-card" },
        React.createElement(
          "div",
          { className: "flex items-center justify-center mb-2" },
          React.createElement(Trophy, { className: "h-8 w-8 text-yellow-600" })
        ),
        React.createElement(
          "div",
          { className: "stat-value text-yellow-600" },
          "0.267"
        ),
        React.createElement(
          "div",
          { className: "stat-label" },
          "League Avg BA"
        )
      )
    ),

    // Main content based on selected category
    selectedCategory === "simulation" ? React.createElement(
      "div",
      { className: "grid grid-cols-1 lg:grid-cols-2 gap-6" },
      
      // Monthly trends
      React.createElement(
        "div",
        { className: "card" },
        React.createElement(
          "div",
          { className: "card-header" },
          React.createElement(
            "h3",
            { className: "card-title flex items-center" },
            React.createElement(TrendingUp, { className: "mr-2 h-5 w-5" }),
            "Monthly Performance Trends"
          )
        ),
        React.createElement(
          "div",
          { className: "chart-container" },
          React.createElement(
            ResponsiveContainer,
            { width: "100%", height: "100%" },
            React.createElement(
              LineChart,
              { data: monthlyTrends },
              React.createElement(CartesianGrid, { strokeDasharray: "3 3" }),
              React.createElement(XAxis, { dataKey: "month" }),
              React.createElement(YAxis),
              React.createElement(Tooltip),
              React.createElement(Legend),
              React.createElement(Line, { type: "monotone", dataKey: "runs", stroke: "#3b82f6", name: "Avg Runs" }),
              React.createElement(Line, { type: "monotone", dataKey: "era", stroke: "#ef4444", name: "Avg ERA" }),
              React.createElement(Line, { type: "monotone", dataKey: "wins", stroke: "#10b981", name: "Team Wins" })
            )
          )
        )
      ),

      // Simulation accuracy
      React.createElement(
        "div",
        { className: "card" },
        React.createElement(
          "div",
          { className: "card-header" },
          React.createElement(
            "h3",
            { className: "card-title flex items-center" },
            React.createElement(Target, { className: "mr-2 h-5 w-5" }),
            "Simulation Accuracy Breakdown"
          )
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
                  data: simulationAccuracy,
                  cx: "50%",
                  cy: "50%",
                  outerRadius: 120,
                  fill: "#8884d8",
                  dataKey: "value",
                  label: ({ name, value }: { name: string; value: number }) => `${name}: ${value}%`
                },
                ...simulationAccuracy.map((entry, index) =>
                  React.createElement(Cell, { key: `cell-${index}`, fill: entry.color })
                )
              ),
              React.createElement(Tooltip, { formatter: (value: number) => `${value}%` })
            )
          )
        )
      )
    ) : React.createElement(
      "div",
      { className: "grid grid-cols-1 lg:grid-cols-2 gap-6" },
      
      // Statistics chart
      React.createElement(
        "div",
        { className: "card" },
        React.createElement(
          "div",
          { className: "card-header" },
          React.createElement(
            "h3",
            { className: "card-title flex items-center" },
            React.createElement(BarChart3, { className: "mr-2 h-5 w-5" }),
            `${selectedCategory === "team" ? "Team" : "Player"} ${selectedStat.charAt(0).toUpperCase() + selectedStat.slice(1)} Statistics`
          )
        ),
        React.createElement(
          "div",
          { className: "chart-container" },
          selectedCategory === "team" ? React.createElement(
            ResponsiveContainer,
            { width: "100%", height: "100%" },
            React.createElement(
              BarChart,
              { data: getCurrentData() },
              React.createElement(CartesianGrid, { strokeDasharray: "3 3" }),
              React.createElement(XAxis, { dataKey: "team" }),
              React.createElement(YAxis),
              React.createElement(Tooltip),
              React.createElement(Legend),
              selectedStat === "batting" ? React.createElement(
                React.Fragment,
                {},
                React.createElement(Bar, { dataKey: "avg", fill: "#3b82f6", name: "Batting Average" }),
                React.createElement(Bar, { dataKey: "ops", fill: "#10b981", name: "OPS" })
              ) : React.createElement(
                React.Fragment,
                {},
                React.createElement(Bar, { dataKey: "era", fill: "#ef4444", name: "ERA" }),
                React.createElement(Bar, { dataKey: "whip", fill: "#8b5cf6", name: "WHIP" })
              )
            )
          ) : React.createElement(
            "div",
            { className: "space-y-4" },
            ...getCurrentData().map((item: any) =>
              React.createElement(
                "div",
                {
                  key: item.rank,
                  className: "flex items-center justify-between p-4 bg-gray-50 rounded-lg"
                },
                React.createElement(
                  "div",
                  { className: "flex items-center" },
                  React.createElement(
                    "div",
                    { 
                      className: `w-8 h-8 rounded-full flex items-center justify-center text-white font-bold text-sm mr-4 ${
                        item.rank === 1 ? "bg-yellow-500" : item.rank === 2 ? "bg-gray-400" : "bg-amber-600"
                      }`
                    },
                    item.rank.toString()
                  ),
                  React.createElement(
                    "div",
                    {},
                    React.createElement(
                      "div",
                      { className: "font-medium" },
                      item.player
                    ),
                    React.createElement(
                      "div",
                      { className: "text-sm text-gray-500" },
                      item.team
                    )
                  )
                ),
                React.createElement(
                  "div",
                  { className: "text-xl font-bold text-blue-600" },
                  selectedStat === "batting" ? item.stat.toFixed(3) : item.stat.toFixed(2)
                )
              )
            )
          )
        )
      ),

      // Statistics table
      React.createElement(
        "div",
        { className: "card" },
        React.createElement(
          "div",
          { className: "card-header" },
          React.createElement(
            "h3",
            { className: "card-title" },
            "Detailed Statistics"
          )
        ),
        React.createElement(
          "div",
          { className: "overflow-x-auto" },
          React.createElement(
            "table",
            { className: "min-w-full divide-y divide-gray-200" },
            React.createElement(
              "thead",
              { className: "bg-gray-50" },
              React.createElement(
                "tr",
                {},
                React.createElement(
                  "th",
                  { className: "px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase" },
                  selectedCategory === "team" ? "Team" : "Player"
                ),
                selectedCategory === "team" && selectedStat === "batting" ? React.createElement(
                  React.Fragment,
                  {},
                  React.createElement(
                    "th",
                    { className: "px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase" },
                    "AVG"
                  ),
                  React.createElement(
                    "th",
                    { className: "px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase" },
                    "HR"
                  ),
                  React.createElement(
                    "th",
                    { className: "px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase" },
                    "RBI"
                  )
                ) : selectedCategory === "team" && selectedStat === "pitching" ? React.createElement(
                  React.Fragment,
                  {},
                  React.createElement(
                    "th",
                    { className: "px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase" },
                    "ERA"
                  ),
                  React.createElement(
                    "th",
                    { className: "px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase" },
                    "WHIP"
                  ),
                  React.createElement(
                    "th",
                    { className: "px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase" },
                    "K/9"
                  )
                ) : React.createElement(
                  React.Fragment,
                  {},
                  React.createElement(
                    "th",
                    { className: "px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase" },
                    "Team"
                  ),
                  React.createElement(
                    "th",
                    { className: "px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase" },
                    "Value"
                  )
                )
              )
            ),
            React.createElement(
              "tbody",
              { className: "bg-white divide-y divide-gray-200" },
              ...getCurrentData().map((item: any, index: number) =>
                React.createElement(
                  "tr",
                  { key: index },
                  React.createElement(
                    "td",
                    { className: "px-4 py-2 whitespace-nowrap text-sm font-medium text-gray-900" },
                    selectedCategory === "team" ? item.team : item.player
                  ),
                  selectedCategory === "team" && selectedStat === "batting" ? React.createElement(
                    React.Fragment,
                    {},
                    React.createElement(
                      "td",
                      { className: "px-4 py-2 whitespace-nowrap text-sm text-gray-900" },
                      item.avg.toFixed(3)
                    ),
                    React.createElement(
                      "td",
                      { className: "px-4 py-2 whitespace-nowrap text-sm text-gray-900" },
                      item.hr
                    ),
                    React.createElement(
                      "td",
                      { className: "px-4 py-2 whitespace-nowrap text-sm text-gray-900" },
                      item.rbi
                    )
                  ) : selectedCategory === "team" && selectedStat === "pitching" ? React.createElement(
                    React.Fragment,
                    {},
                    React.createElement(
                      "td",
                      { className: "px-4 py-2 whitespace-nowrap text-sm text-gray-900" },
                      item.era.toFixed(2)
                    ),
                    React.createElement(
                      "td",
                      { className: "px-4 py-2 whitespace-nowrap text-sm text-gray-900" },
                      item.whip.toFixed(2)
                    ),
                    React.createElement(
                      "td",
                      { className: "px-4 py-2 whitespace-nowrap text-sm text-gray-900" },
                      item.k9.toFixed(1)
                    )
                  ) : React.createElement(
                    React.Fragment,
                    {},
                    React.createElement(
                      "td",
                      { className: "px-4 py-2 whitespace-nowrap text-sm text-gray-900" },
                      item.team
                    ),
                    React.createElement(
                      "td",
                      { className: "px-4 py-2 whitespace-nowrap text-sm font-medium text-blue-600" },
                      selectedStat === "batting" ? item.stat.toFixed(3) : item.stat.toFixed(2)
                    )
                  )
                )
              )
            )
          )
        )
      )
    )
  );
}

export default StatsPage;