import { React, Menu } from "../../../deps.ts";

interface HeaderProps {
  onMenuClick: () => void;
}

function Header({ onMenuClick }: HeaderProps) {
  return React.createElement(
    "header",
    { className: "bg-blue-600 text-white shadow-lg" },
    React.createElement(
      "div",
      { className: "px-4 sm:px-6 lg:px-8" },
      React.createElement(
        "div",
        { className: "flex items-center justify-between h-16" },
        React.createElement(
          "div",
          { className: "flex items-center" },
          React.createElement(
            "button",
            {
              onClick: onMenuClick,
              className: "lg:hidden p-2 rounded-md hover:bg-blue-700 focus:outline-none"
            },
            React.createElement(Menu, { className: "h-6 w-6" })
          ),
          React.createElement(
            "div",
            { className: "flex-shrink-0 ml-4 lg:ml-0" },
            React.createElement(
              "h1",
              { className: "text-xl font-bold" },
              "⚾ Baseball Simulation"
            )
          )
        ),
        React.createElement(
          "div",
          { className: "hidden md:block" },
          React.createElement(
            "div",
            { className: "ml-10 flex items-baseline space-x-4" },
            React.createElement(
              "div",
              { className: "text-sm text-blue-100" },
              "Monte Carlo Baseball Analytics"
            )
          )
        ),
        React.createElement(
          "div",
          { className: "flex items-center space-x-4" },
          React.createElement(
            "div",
            { className: "hidden sm:flex items-center space-x-2" },
            React.createElement(
              "div",
              { className: "h-2 w-2 bg-green-400 rounded-full" }
            ),
            React.createElement(
              "span",
              { className: "text-sm text-blue-100" },
              "System Online"
            )
          )
        )
      )
    )
  );
}

export default Header;