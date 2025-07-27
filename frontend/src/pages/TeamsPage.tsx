import { React, Link, Users, TrendingUp, BarChart3, Trophy, Target, Activity } from "../../deps.ts";

interface Team {
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

function TeamsPage() {
  const [teams, setTeams] = React.useState<Team[]>([]);
  const [loading, setLoading] = React.useState(true);
  const [selectedDivision, setSelectedDivision] = React.useState("all");

  // Mock teams data - will be replaced with API call
  React.useEffect(() => {
    const mockTeams: Team[] = [
      {
        id: "BOS",
        name: "Red Sox",
        abbreviation: "BOS",
        city: "Boston",
        division: "AL East",
        league: "American League",
        wins: 89,
        losses: 73,
        runsScored: 745,
        runsAllowed: 678,
        era: 3.92,
        battingAvg: 0.267
      },
      {
        id: "NYY",
        name: "Yankees",
        abbreviation: "NYY",
        city: "New York",
        division: "AL East",
        league: "American League",
        wins: 102,
        losses: 60,
        runsScored: 807,
        runsAllowed: 601,
        era: 3.30,
        battingAvg: 0.254
      },
      {
        id: "CHC",
        name: "Cubs",
        abbreviation: "CHC",
        city: "Chicago",
        division: "NL Central",
        league: "National League",
        wins: 83,
        losses: 79,
        runsScored: 694,
        runsAllowed: 705,
        era: 4.01,
        battingAvg: 0.243
      },
      {
        id: "COL",
        name: "Rockies",
        abbreviation: "COL",
        city: "Colorado",
        division: "NL West",
        league: "National League",
        wins: 68,
        losses: 94,
        runsScored: 729,
        runsAllowed: 865,
        era: 5.34,
        battingAvg: 0.259
      }
    ];

    setTimeout(() => {
      setTeams(mockTeams);
      setLoading(false);
    }, 1000);
  }, []);

  const divisions = ["all", "AL East", "AL Central", "AL West", "NL East", "NL Central", "NL West"];
  
  const filteredTeams = selectedDivision === "all" 
    ? teams 
    : teams.filter(team => team.division === selectedDivision);

  const getWinPercentage = (wins: number, losses: number) => {
    return ((wins / (wins + losses)) * 100).toFixed(1);
  };

  const getRunDifferential = (scored: number, allowed: number) => {
    const diff = scored - allowed;
    return diff > 0 ? `+${diff}` : diff.toString();
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
          "Teams & Statistics"
        ),
        React.createElement(
          "p",
          { className: "mt-1 text-sm text-gray-500" },
          "Compare team performance and statistics"
        )
      ),
      React.createElement(
        "div",
        { className: "mt-4 sm:mt-0" },
        React.createElement(
          "select",
          {
            value: selectedDivision,
            onChange: (e: React.ChangeEvent<HTMLSelectElement>) => setSelectedDivision(e.target.value),
            className: "form-input"
          },
          ...divisions.map(division =>
            React.createElement(
              "option",
              { key: division, value: division },
              division === "all" ? "All Divisions" : division
            )
          )
        )
      )
    ),

    // League overview stats
    React.createElement(
      "div",
      { className: "stats-grid" },
      React.createElement(
        "div",
        { className: "stat-card" },
        React.createElement(
          "div",
          { className: "flex items-center justify-center mb-2" },
          React.createElement(Users, { className: "h-8 w-8 text-blue-600" })
        ),
        React.createElement(
          "div",
          { className: "stat-value text-blue-600" },
          filteredTeams.length
        ),
        React.createElement(
          "div",
          { className: "stat-label" },
          "Teams"
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
          filteredTeams.length > 0 ? Math.max(...filteredTeams.map(t => t.wins)) : "0"
        ),
        React.createElement(
          "div",
          { className: "stat-label" },
          "Most Wins"
        )
      ),
      React.createElement(
        "div",
        { className: "stat-card" },
        React.createElement(
          "div",
          { className: "flex items-center justify-center mb-2" },
          React.createElement(Target, { className: "h-8 w-8 text-green-600" })
        ),
        React.createElement(
          "div",
          { className: "stat-value text-green-600" },
          filteredTeams.length > 0 ? Math.max(...filteredTeams.map(t => t.runsScored)).toLocaleString() : "0"
        ),
        React.createElement(
          "div",
          { className: "stat-label" },
          "Highest Runs Scored"
        )
      ),
      React.createElement(
        "div",
        { className: "stat-card" },
        React.createElement(
          "div",
          { className: "flex items-center justify-center mb-2" },
          React.createElement(Activity, { className: "h-8 w-8 text-purple-600" })
        ),
        React.createElement(
          "div",
          { className: "stat-value text-purple-600" },
          filteredTeams.length > 0 ? Math.min(...filteredTeams.map(t => t.era)).toFixed(2) : "0.00"
        ),
        React.createElement(
          "div",
          { className: "stat-label" },
          "Best ERA"
        )
      )
    ),

    // Teams table
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
          selectedDivision === "all" ? "All Teams" : selectedDivision
        )
      ),
      
      loading ? React.createElement(
        "div",
        { className: "flex items-center justify-center py-12" },
        React.createElement("div", { className: "spinner mr-3" }),
        "Loading teams..."
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
                "Team"
              ),
              React.createElement(
                "th",
                { className: "px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider" },
                "Record"
              ),
              React.createElement(
                "th",
                { className: "px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider" },
                "Win %"
              ),
              React.createElement(
                "th",
                { className: "px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider" },
                "Run Diff"
              ),
              React.createElement(
                "th",
                { className: "px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider" },
                "ERA"
              ),
              React.createElement(
                "th",
                { className: "px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider" },
                "Batting Avg"
              ),
              React.createElement(
                "th",
                { className: "px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider" },
                "Actions"
              )
            )
          ),
          React.createElement(
            "tbody",
            { className: "bg-white divide-y divide-gray-200" },
            ...filteredTeams.map((team, index) =>
              React.createElement(
                "tr",
                { 
                  key: team.id,
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
                      { className: `w-10 h-10 rounded-full bg-blue-600 flex items-center justify-center text-white font-bold text-sm mr-4` },
                      team.abbreviation
                    ),
                    React.createElement(
                      "div",
                      {},
                      React.createElement(
                        "div",
                        { className: "text-sm font-medium text-gray-900" },
                        `${team.city} ${team.name}`
                      ),
                      React.createElement(
                        "div",
                        { className: "text-sm text-gray-500" },
                        team.division
                      )
                    )
                  )
                ),
                React.createElement(
                  "td",
                  { className: "px-6 py-4 whitespace-nowrap text-sm text-gray-900" },
                  `${team.wins}-${team.losses}`
                ),
                React.createElement(
                  "td",
                  { className: "px-6 py-4 whitespace-nowrap text-sm text-gray-900" },
                  `${getWinPercentage(team.wins, team.losses)}%`
                ),
                React.createElement(
                  "td",
                  { 
                    className: `px-6 py-4 whitespace-nowrap text-sm font-medium ${
                      team.runsScored > team.runsAllowed ? "text-green-600" : "text-red-600"
                    }`
                  },
                  getRunDifferential(team.runsScored, team.runsAllowed)
                ),
                React.createElement(
                  "td",
                  { className: "px-6 py-4 whitespace-nowrap text-sm text-gray-900" },
                  team.era.toFixed(2)
                ),
                React.createElement(
                  "td",
                  { className: "px-6 py-4 whitespace-nowrap text-sm text-gray-900" },
                  team.battingAvg.toFixed(3)
                ),
                React.createElement(
                  "td",
                  { className: "px-6 py-4 whitespace-nowrap text-sm font-medium" },
                  React.createElement(
                    "div",
                    { className: "flex space-x-2" },
                    React.createElement(
                      Link,
                      { 
                        to: `/teams/${team.id}`,
                        className: "text-blue-600 hover:text-blue-900"
                      },
                      "View Details"
                    ),
                    React.createElement(
                      "button",
                      { className: "text-green-600 hover:text-green-900" },
                      "Compare"
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

export default TeamsPage;