import { React, NavLink, Home, Calendar, PlayCircle, Users, BarChart3, TrendingUp } from "../../../deps.ts";

interface SidebarProps {
  open: boolean;
  onClose: () => void;
}

const navigation = [
  { name: "Dashboard", href: "/", icon: Home },
  { name: "Games", href: "/games", icon: Calendar },
  { name: "Teams", href: "/teams", icon: Users },
  { name: "Players", href: "/players", icon: Users },
  { name: "Statistics", href: "/stats", icon: BarChart3 },
];

function Sidebar({ open, onClose }: SidebarProps) {
  return React.createElement(
    React.Fragment,
    {},
    // Mobile overlay
    open && React.createElement(
      "div",
      {
        className: "fixed inset-0 z-40 lg:hidden",
        onClick: onClose
      },
      React.createElement("div", { className: "fixed inset-0 bg-gray-600 opacity-75" })
    ),
    
    // Sidebar
    React.createElement(
      "div",
      {
        className: `fixed inset-y-0 left-0 z-50 w-64 bg-white shadow-lg transform transition-transform duration-300 ease-in-out lg:translate-x-0 lg:static lg:inset-0 ${
          open ? "translate-x-0" : "-translate-x-full"
        }`
      },
      React.createElement(
        "div",
        { className: "flex flex-col h-full" },
        
        // Navigation
        React.createElement(
          "nav",
          { className: "flex-1 px-4 py-6 space-y-2" },
          ...navigation.map((item) =>
            React.createElement(
              NavLink,
              {
                key: item.name,
                to: item.href,
                className: ({ isActive }: { isActive: boolean }) =>
                  `flex items-center px-4 py-3 text-sm font-medium rounded-lg transition-colors ${
                    isActive
                      ? "bg-blue-50 text-blue-700 border-r-2 border-blue-700"
                      : "text-gray-700 hover:bg-gray-50 hover:text-blue-600"
                  }`,
                onClick: () => window.innerWidth < 1024 && onClose()
              },
              React.createElement(item.icon, { className: "mr-3 h-5 w-5" }),
              item.name
            )
          )
        ),
        
        // Footer
        React.createElement(
          "div",
          { className: "px-4 py-6 border-t border-gray-200" },
          React.createElement(
            "div",
            { className: "text-xs text-gray-500 text-center" },
            "Baseball Simulation v1.0"
          )
        )
      )
    )
  );
}

export default Sidebar;