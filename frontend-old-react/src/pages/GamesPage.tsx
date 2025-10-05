import { React, Link, Calendar, Clock, PlayCircle, Users, TrendingUp } from "../../deps.ts";

function GamesPage() {
  const [selectedDate, setSelectedDate] = React.useState(new Date().toISOString().split('T')[0]);
  const [games, setGames] = React.useState([]);
  const [loading, setLoading] = React.useState(true);

  // Mock games data - will be replaced with API call
  React.useEffect(() => {
    const mockGames = [
      {
        id: "BOS_NYY_20240415",
        gameId: "BOS_NYY_20240415",
        homeTeam: { name: "Red Sox", abbreviation: "BOS", city: "Boston" },
        awayTeam: { name: "Yankees", abbreviation: "NYY", city: "New York" },
        gameDate: "2024-04-15T19:10:00",
        status: "scheduled",
        stadium: "Fenway Park"
      },
      {
        id: "CHC_COL_20240416", 
        gameId: "CHC_COL_20240416",
        homeTeam: { name: "Cubs", abbreviation: "CHC", city: "Chicago" },
        awayTeam: { name: "Rockies", abbreviation: "COL", city: "Colorado" },
        gameDate: "2024-04-16T20:10:00",
        status: "scheduled", 
        stadium: "Wrigley Field"
      }
    ];
    
    setTimeout(() => {
      setGames(mockGames);
      setLoading(false);
    }, 1000);
  }, [selectedDate]);

  const formatGameTime = (dateString: string) => {
    return new Date(dateString).toLocaleTimeString('en-US', {
      hour: 'numeric',
      minute: '2-digit',
      hour12: true
    });
  };

  const getStatusBadge = (status: string) => {
    const statusConfig = {
      scheduled: { color: "bg-blue-100 text-blue-800", text: "Scheduled" },
      live: { color: "bg-green-100 text-green-800", text: "Live" },
      final: { color: "bg-gray-100 text-gray-800", text: "Final" },
      postponed: { color: "bg-yellow-100 text-yellow-800", text: "Postponed" }
    };
    
    const config = statusConfig[status as keyof typeof statusConfig] || statusConfig.scheduled;
    
    return React.createElement(
      "span",
      { className: `inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${config.color}` },
      config.text
    );
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
          "Games & Simulations"
        ),
        React.createElement(
          "p",
          { className: "mt-1 text-sm text-gray-500" },
          "Select games to run Monte Carlo simulations"
        )
      ),
      React.createElement(
        "div",
        { className: "mt-4 sm:mt-0 flex items-center space-x-3" },
        React.createElement(
          "input",
          {
            type: "date",
            value: selectedDate,
            onChange: (e: React.ChangeEvent<HTMLInputElement>) => setSelectedDate(e.target.value),
            className: "form-input"
          }
        )
      )
    ),

    // Statistics cards
    React.createElement(
      "div",
      { className: "grid grid-cols-1 md:grid-cols-3 gap-6" },
      React.createElement(
        "div",
        { className: "stat-card" },
        React.createElement(
          "div",
          { className: "flex items-center" },
          React.createElement(Calendar, { className: "h-8 w-8 text-blue-600" }),
          React.createElement(
            "div",
            { className: "ml-4" },
            React.createElement(
              "div",
              { className: "stat-value text-blue-600" },
              games.length
            ),
            React.createElement(
              "div",
              { className: "stat-label" },
              "Games Today"
            )
          )
        )
      ),
      React.createElement(
        "div",
        { className: "stat-card" },
        React.createElement(
          "div",
          { className: "flex items-center" },
          React.createElement(PlayCircle, { className: "h-8 w-8 text-green-600" }),
          React.createElement(
            "div",
            { className: "ml-4" },
            React.createElement(
              "div",
              { className: "stat-value text-green-600" },
              "0"
            ),
            React.createElement(
              "div",
              { className: "stat-label" },
              "Active Simulations"
            )
          )
        )
      ),
      React.createElement(
        "div",
        { className: "stat-card" },
        React.createElement(
          "div",
          { className: "flex items-center" },
          React.createElement(TrendingUp, { className: "h-8 w-8 text-purple-600" }),
          React.createElement(
            "div",
            { className: "ml-4" },
            React.createElement(
              "div",
              { className: "stat-value text-purple-600" },
              "94.2%"
            ),
            React.createElement(
              "div",
              { className: "stat-label" },
              "Avg Accuracy"
            )
          )
        )
      )
    ),

    // Games list
    React.createElement(
      "div",
      { className: "card" },
      React.createElement(
        "div",
        { className: "card-header" },
        React.createElement(
          "h2",
          { className: "card-title flex items-center" },
          React.createElement(Calendar, { className: "mr-2 h-5 w-5" }),
          `Games for ${new Date(selectedDate).toLocaleDateString('en-US', { 
            weekday: 'long',
            year: 'numeric', 
            month: 'long', 
            day: 'numeric' 
          })}`
        )
      ),
      
      loading ? React.createElement(
        "div",
        { className: "flex items-center justify-center py-12" },
        React.createElement("div", { className: "spinner mr-3" }),
        "Loading games..."
      ) : games.length === 0 ? React.createElement(
        "div",
        { className: "text-center py-12" },
        React.createElement(
          "div",
          { className: "text-gray-500 mb-4" },
          "No games scheduled for this date"
        ),
        React.createElement(
          "button",
          { 
            className: "btn btn-secondary",
            onClick: () => setSelectedDate(new Date().toISOString().split('T')[0])
          },
          "View Today's Games"
        )
      ) : React.createElement(
        "div",
        { className: "space-y-4" },
        ...games.map((game: any) =>
          React.createElement(
            "div",
            { 
              key: game.id,
              className: "border border-gray-200 rounded-lg p-6 hover:shadow-md transition-shadow"
            },
            React.createElement(
              "div",
              { className: "flex flex-col sm:flex-row sm:items-center sm:justify-between" },
              
              // Game info
              React.createElement(
                "div",
                { className: "flex items-center space-x-6" },
                
                // Teams
                React.createElement(
                  "div",
                  { className: "flex items-center space-x-4" },
                  React.createElement(
                    "div",
                    { className: "text-center" },
                    React.createElement(
                      "div",
                      { className: "font-semibold text-gray-900" },
                      game.awayTeam.abbreviation
                    ),
                    React.createElement(
                      "div",
                      { className: "text-sm text-gray-500" },
                      game.awayTeam.city
                    )
                  ),
                  React.createElement(
                    "div",
                    { className: "text-gray-400 font-bold" },
                    "@"
                  ),
                  React.createElement(
                    "div",
                    { className: "text-center" },
                    React.createElement(
                      "div",
                      { className: "font-semibold text-gray-900" },
                      game.homeTeam.abbreviation
                    ),
                    React.createElement(
                      "div",
                      { className: "text-sm text-gray-500" },
                      game.homeTeam.city
                    )
                  )
                ),
                
                // Game details
                React.createElement(
                  "div",
                  { className: "text-center sm:text-left" },
                  React.createElement(
                    "div",
                    { className: "flex items-center text-sm text-gray-500 mb-1" },
                    React.createElement(Clock, { className: "mr-1 h-4 w-4" }),
                    formatGameTime(game.gameDate)
                  ),
                  React.createElement(
                    "div",
                    { className: "text-sm text-gray-500" },
                    game.stadium
                  ),
                  React.createElement(
                    "div",
                    { className: "mt-2" },
                    getStatusBadge(game.status)
                  )
                )
              ),
              
              // Actions
              React.createElement(
                "div",
                { className: "mt-4 sm:mt-0 flex space-x-3" },
                React.createElement(
                  Link,
                  { 
                    to: `/simulation/${game.gameId}`,
                    className: "btn btn-primary"
                  },
                  React.createElement(PlayCircle, { className: "mr-2 h-4 w-4" }),
                  "Simulate Game"
                ),
                React.createElement(
                  "button",
                  { className: "btn btn-secondary" },
                  React.createElement(TrendingUp, { className: "mr-2 h-4 w-4" }),
                  "View Stats"
                )
              )
            )
          )
        )
      )
    )
  );
}

export default GamesPage;