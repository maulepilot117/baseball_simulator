import { React, Users, Target, TrendingUp, Trophy, Search, Filter } from "../../deps.ts";

interface Player {
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

function PlayersPage() {
  const [players, setPlayers] = React.useState<Player[]>([]);
  const [loading, setLoading] = React.useState(true);
  const [selectedPosition, setSelectedPosition] = React.useState("all");
  const [playerType, setPlayerType] = React.useState<"all" | "batter" | "pitcher">("all");
  const [searchTerm, setSearchTerm] = React.useState("");

  // Mock players data - will be replaced with API call
  React.useEffect(() => {
    const mockPlayers: Player[] = [
      {
        id: "1",
        name: "Mookie Betts",
        team: "BOS",
        position: "RF",
        battingAvg: 0.295,
        homeRuns: 29,
        rbi: 80,
        playerType: "batter"
      },
      {
        id: "2",
        name: "Aaron Judge",
        team: "NYY",
        position: "RF",
        battingAvg: 0.311,
        homeRuns: 62,
        rbi: 131,
        playerType: "batter"
      },
      {
        id: "3",
        name: "Rafael Devers",
        team: "BOS",
        position: "3B",
        battingAvg: 0.279,
        homeRuns: 27,
        rbi: 88,
        playerType: "batter"
      },
      {
        id: "4",
        name: "Gerrit Cole",
        team: "NYY",
        position: "SP",
        era: 3.20,
        strikeouts: 257,
        wins: 13,
        losses: 8,
        battingAvg: 0,
        homeRuns: 0,
        rbi: 0,
        playerType: "pitcher"
      },
      {
        id: "5",
        name: "Chris Sale",
        team: "BOS",
        position: "SP",
        era: 2.93,
        strikeouts: 226,
        wins: 11,
        losses: 4,
        battingAvg: 0,
        homeRuns: 0,
        rbi: 0,
        playerType: "pitcher"
      },
      {
        id: "6",
        name: "Nico Hoerner",
        team: "CHC",
        position: "2B",
        battingAvg: 0.273,
        homeRuns: 5,
        rbi: 51,
        playerType: "batter"
      }
    ];

    setTimeout(() => {
      setPlayers(mockPlayers);
      setLoading(false);
    }, 1000);
  }, []);

  const positions = [
    "all", "C", "1B", "2B", "3B", "SS", "LF", "CF", "RF", "DH", "SP", "RP", "CP"
  ];

  const filteredPlayers = players.filter(player => {
    const matchesSearch = player.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         player.team.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesPosition = selectedPosition === "all" || player.position === selectedPosition;
    const matchesType = playerType === "all" || player.playerType === playerType;
    
    return matchesSearch && matchesPosition && matchesType;
  });

  const getTopBatters = () => {
    return players
      .filter(p => p.playerType === "batter")
      .sort((a, b) => b.battingAvg - a.battingAvg)
      .slice(0, 3);
  };

  const getTopPitchers = () => {
    return players
      .filter(p => p.playerType === "pitcher")
      .sort((a, b) => (a.era || 999) - (b.era || 999))
      .slice(0, 3);
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
          "Players & Performance"
        ),
        React.createElement(
          "p",
          { className: "mt-1 text-sm text-gray-500" },
          "Track player statistics and performance metrics"
        )
      )
    ),

    // Search and filters
    React.createElement(
      "div",
      { className: "card" },
      React.createElement(
        "div",
        { className: "grid grid-cols-1 md:grid-cols-4 gap-4" },
        React.createElement(
          "div",
          { className: "relative" },
          React.createElement(
            "div",
            { className: "absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none" },
            React.createElement(Search, { className: "h-5 w-5 text-gray-400" })
          ),
          React.createElement(
            "input",
            {
              type: "text",
              placeholder: "Search players or teams...",
              value: searchTerm,
              onChange: (e: React.ChangeEvent<HTMLInputElement>) => setSearchTerm(e.target.value),
              className: "form-input pl-10"
            }
          )
        ),
        React.createElement(
          "select",
          {
            value: playerType,
            onChange: (e: React.ChangeEvent<HTMLSelectElement>) => setPlayerType(e.target.value as "all" | "batter" | "pitcher"),
            className: "form-input"
          },
          React.createElement("option", { value: "all" }, "All Players"),
          React.createElement("option", { value: "batter" }, "Batters"),
          React.createElement("option", { value: "pitcher" }, "Pitchers")
        ),
        React.createElement(
          "select",
          {
            value: selectedPosition,
            onChange: (e: React.ChangeEvent<HTMLSelectElement>) => setSelectedPosition(e.target.value),
            className: "form-input"
          },
          ...positions.map(pos =>
            React.createElement(
              "option",
              { key: pos, value: pos },
              pos === "all" ? "All Positions" : pos
            )
          )
        ),
        React.createElement(
          "button",
          { className: "btn btn-secondary flex items-center" },
          React.createElement(Filter, { className: "mr-2 h-4 w-4" }),
          "Advanced Filters"
        )
      )
    ),

    // Top performers
    React.createElement(
      "div",
      { className: "grid grid-cols-1 lg:grid-cols-2 gap-6" },
      
      // Top batters
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
            "Top Batting Averages"
          )
        ),
        React.createElement(
          "div",
          { className: "space-y-3" },
          ...getTopBatters().map((player, index) =>
            React.createElement(
              "div",
              {
                key: player.id,
                className: "flex items-center justify-between p-3 bg-gray-50 rounded-lg"
              },
              React.createElement(
                "div",
                { className: "flex items-center" },
                React.createElement(
                  "div",
                  { 
                    className: `w-8 h-8 rounded-full flex items-center justify-center text-white font-bold text-xs mr-3 ${
                      index === 0 ? "bg-yellow-500" : index === 1 ? "bg-gray-400" : "bg-amber-600"
                    }`
                  },
                  (index + 1).toString()
                ),
                React.createElement(
                  "div",
                  {},
                  React.createElement(
                    "div",
                    { className: "font-medium" },
                    player.name
                  ),
                  React.createElement(
                    "div",
                    { className: "text-sm text-gray-500" },
                    `${player.team} - ${player.position}`
                  )
                )
              ),
              React.createElement(
                "div",
                { className: "text-right" },
                React.createElement(
                  "div",
                  { className: "font-bold text-green-600" },
                  player.battingAvg.toFixed(3)
                ),
                React.createElement(
                  "div",
                  { className: "text-sm text-gray-500" },
                  `${player.homeRuns} HR, ${player.rbi} RBI`
                )
              )
            )
          )
        )
      ),

      // Top pitchers
      React.createElement(
        "div",
        { className: "card" },
        React.createElement(
          "div",
          { className: "card-header" },
          React.createElement(
            "h3",
            { className: "card-title flex items-center" },
            React.createElement(Trophy, { className: "mr-2 h-5 w-5" }),
            "Top Pitchers (ERA)"
          )
        ),
        React.createElement(
          "div",
          { className: "space-y-3" },
          ...getTopPitchers().map((player, index) =>
            React.createElement(
              "div",
              {
                key: player.id,
                className: "flex items-center justify-between p-3 bg-gray-50 rounded-lg"
              },
              React.createElement(
                "div",
                { className: "flex items-center" },
                React.createElement(
                  "div",
                  { 
                    className: `w-8 h-8 rounded-full flex items-center justify-center text-white font-bold text-xs mr-3 ${
                      index === 0 ? "bg-yellow-500" : index === 1 ? "bg-gray-400" : "bg-amber-600"
                    }`
                  },
                  (index + 1).toString()
                ),
                React.createElement(
                  "div",
                  {},
                  React.createElement(
                    "div",
                    { className: "font-medium" },
                    player.name
                  ),
                  React.createElement(
                    "div",
                    { className: "text-sm text-gray-500" },
                    `${player.team} - ${player.position}`
                  )
                )
              ),
              React.createElement(
                "div",
                { className: "text-right" },
                React.createElement(
                  "div",
                  { className: "font-bold text-blue-600" },
                  player.era?.toFixed(2) || "N/A"
                ),
                React.createElement(
                  "div",
                  { className: "text-sm text-gray-500" },
                  `${player.wins}-${player.losses}, ${player.strikeouts} K`
                )
              )
            )
          )
        )
      )
    ),

    // Players table
    React.createElement(
      "div",
      { className: "card" },
      React.createElement(
        "div",
        { className: "card-header" },
        React.createElement(
          "h2",
          { className: "card-title flex items-center" },
          React.createElement(Users, { className: "mr-2 h-5 w-5" }),
          `Player Statistics (${filteredPlayers.length} players)`
        )
      ),
      
      loading ? React.createElement(
        "div",
        { className: "flex items-center justify-center py-12" },
        React.createElement("div", { className: "spinner mr-3" }),
        "Loading players..."
      ) : React.createElement(
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
                { className: "px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider" },
                "Player"
              ),
              React.createElement(
                "th",
                { className: "px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider" },
                "Team"
              ),
              React.createElement(
                "th",
                { className: "px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider" },
                "Position"
              ),
              React.createElement(
                "th",
                { className: "px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider" },
                playerType === "pitcher" ? "ERA" : "AVG"
              ),
              React.createElement(
                "th",
                { className: "px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider" },
                playerType === "pitcher" ? "K" : "HR"
              ),
              React.createElement(
                "th",
                { className: "px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider" },
                playerType === "pitcher" ? "W-L" : "RBI"
              )
            )
          ),
          React.createElement(
            "tbody",
            { className: "bg-white divide-y divide-gray-200" },
            ...filteredPlayers.map((player, index) =>
              React.createElement(
                "tr",
                { 
                  key: player.id,
                  className: index % 2 === 0 ? "bg-white" : "bg-gray-50"
                },
                React.createElement(
                  "td",
                  { className: "px-6 py-4 whitespace-nowrap" },
                  React.createElement(
                    "div",
                    { className: "flex items-center" },
                    React.createElement(
                      "div",
                      { className: "w-10 h-10 rounded-full bg-blue-600 flex items-center justify-center text-white font-bold text-sm mr-4" },
                      player.name.split(' ').map(n => n[0]).join('')
                    ),
                    React.createElement(
                      "div",
                      { className: "text-sm font-medium text-gray-900" },
                      player.name
                    )
                  )
                ),
                React.createElement(
                  "td",
                  { className: "px-6 py-4 whitespace-nowrap text-sm text-gray-900" },
                  player.team
                ),
                React.createElement(
                  "td",
                  { className: "px-6 py-4 whitespace-nowrap text-sm text-gray-900" },
                  player.position
                ),
                React.createElement(
                  "td",
                  { className: "px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900" },
                  player.playerType === "pitcher" 
                    ? player.era?.toFixed(2) || "N/A"
                    : player.battingAvg.toFixed(3)
                ),
                React.createElement(
                  "td",
                  { className: "px-6 py-4 whitespace-nowrap text-sm text-gray-900" },
                  player.playerType === "pitcher" 
                    ? player.strikeouts?.toString() || "0"
                    : player.homeRuns.toString()
                ),
                React.createElement(
                  "td",
                  { className: "px-6 py-4 whitespace-nowrap text-sm text-gray-900" },
                  player.playerType === "pitcher" 
                    ? `${player.wins || 0}-${player.losses || 0}`
                    : player.rbi.toString()
                )
              )
            )
          )
        )
      )
    )
  );
}

export default PlayersPage;