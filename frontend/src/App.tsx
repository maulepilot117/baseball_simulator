import { React, BrowserRouter, Routes, Route } from "../deps.ts";
import { AppProvider } from "./context/AppContext.tsx";
import Layout from "./components/layout/Layout.tsx";
import HomePage from "./pages/HomePage.tsx";
import GamesPage from "./pages/GamesPage.tsx";
import SimulationPage from "./pages/SimulationPage.tsx";
import TeamsPage from "./pages/TeamsPage.tsx";
import PlayersPage from "./pages/PlayersPage.tsx";
import StatsPage from "./pages/StatsPage.tsx";

// Load CSS dynamically to avoid module import issues
const loadCSS = () => {
  const link = document.createElement('link');
  link.rel = 'stylesheet';
  link.href = '/src/styles/globals.css';
  document.head.appendChild(link);
};

// Load CSS when the module loads
loadCSS();

function App() {
  return React.createElement(
    AppProvider,
    { children: 
      React.createElement(
        BrowserRouter,
        { children:
          React.createElement(
            Layout,
            { children:
              React.createElement(
                Routes,
                { children: [
                  React.createElement(Route, { key: "home", path: "/", element: React.createElement(HomePage) }),
                  React.createElement(Route, { key: "games", path: "/games", element: React.createElement(GamesPage) }),
                  React.createElement(Route, { key: "simulation", path: "/simulation/:gameId", element: React.createElement(SimulationPage) }),
                  React.createElement(Route, { key: "teams", path: "/teams", element: React.createElement(TeamsPage) }),
                  React.createElement(Route, { key: "players", path: "/players", element: React.createElement(PlayersPage) }),
                  React.createElement(Route, { key: "stats", path: "/stats", element: React.createElement(StatsPage) })
                ]}
              )
            }
          )
        }
      )
    }
  );
}

export default App;