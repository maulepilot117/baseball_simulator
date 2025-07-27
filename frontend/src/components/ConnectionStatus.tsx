import { React, Database, Activity, Zap, RefreshCw } from "../../deps.ts";
import { useApp } from "../context/AppContext.tsx";

function ConnectionStatus() {
  const { connectionStatus, testConnections } = useApp();
  const [isRefreshing, setIsRefreshing] = React.useState(false);

  const handleRefresh = async () => {
    setIsRefreshing(true);
    await testConnections();
    setIsRefreshing(false);
  };

  const getStatusColor = (isConnected: boolean) => {
    return isConnected ? "text-green-600" : "text-red-600";
  };

  const getStatusText = (isConnected: boolean) => {
    return isConnected ? "Online" : "Offline";
  };

  const services = [
    {
      name: "API Gateway",
      key: "apiGateway" as keyof typeof connectionStatus,
      icon: Database,
      port: "8080"
    },
    {
      name: "Simulation Engine",
      key: "simulationEngine" as keyof typeof connectionStatus,
      icon: Zap,
      port: "8081"
    },
    {
      name: "Data Fetcher",
      key: "dataFetcher" as keyof typeof connectionStatus,
      icon: Activity,
      port: "8082"
    }
  ];

  const allConnected = Object.values(connectionStatus).every(status => status);

  return React.createElement(
    "div",
    { className: "card" },
    React.createElement(
      "div",
      { className: "flex items-center justify-between mb-4" },
      React.createElement(
        "h3",
        { className: "text-lg font-semibold text-gray-900" },
        "System Status"
      ),
      React.createElement(
        "button",
        {
          onClick: handleRefresh,
          disabled: isRefreshing,
          className: "btn btn-secondary text-sm",
          title: "Refresh connection status"
        },
        React.createElement(RefreshCw, { 
          className: `h-4 w-4 mr-2 ${isRefreshing ? "animate-spin" : ""}` 
        }),
        "Refresh"
      )
    ),
    React.createElement(
      "div",
      { className: "space-y-3" },
      ...services.map(service =>
        React.createElement(
          "div",
          {
            key: service.key,
            className: "flex items-center justify-between p-3 bg-gray-50 rounded-lg"
          },
          React.createElement(
            "div",
            { className: "flex items-center" },
            React.createElement(service.icon, { 
              className: `h-5 w-5 mr-3 ${getStatusColor(connectionStatus[service.key])}` 
            }),
            React.createElement(
              "div",
              {},
              React.createElement(
                "div",
                { className: "font-medium text-gray-900" },
                service.name
              ),
              React.createElement(
                "div",
                { className: "text-sm text-gray-500" },
                `Port ${service.port}`
              )
            )
          ),
          React.createElement(
            "div",
            { className: "flex items-center" },
            React.createElement(
              "div",
              { 
                className: `w-2 h-2 rounded-full mr-2 ${
                  connectionStatus[service.key] ? "bg-green-400" : "bg-red-400"
                }` 
              }
            ),
            React.createElement(
              "span",
              { 
                className: `text-sm font-medium ${getStatusColor(connectionStatus[service.key])}` 
              },
              getStatusText(connectionStatus[service.key])
            )
          )
        )
      )
    ),
    React.createElement(
      "div",
      { className: "mt-4 pt-4 border-t border-gray-200" },
      React.createElement(
        "div",
        { className: "flex items-center justify-between" },
        React.createElement(
          "div",
          { className: "text-sm text-gray-600" },
          "Overall System Health"
        ),
        React.createElement(
          "div",
          { className: "flex items-center" },
          React.createElement(
            "div",
            { 
              className: `w-3 h-3 rounded-full mr-2 ${
                allConnected ? "bg-green-400" : "bg-red-400"
              }` 
            }
          ),
          React.createElement(
            "span",
            { 
              className: `text-sm font-semibold ${
                allConnected ? "text-green-600" : "text-red-600"
              }` 
            },
            allConnected ? "All Systems Operational" : "System Issues Detected"
          )
        )
      )
    )
  );
}

export default ConnectionStatus;