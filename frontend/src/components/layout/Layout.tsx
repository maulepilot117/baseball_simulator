import { React } from "../../../deps.ts";
import Header from "./Header.tsx";
import Sidebar from "./Sidebar.tsx";

interface LayoutProps {
  children?: React.ReactNode;
}

function Layout({ children }: LayoutProps) {
  const [sidebarOpen, setSidebarOpen] = React.useState(false);

  return React.createElement(
    "div",
    { className: "min-h-screen bg-gray-50" },
    React.createElement(Header, { 
      onMenuClick: () => setSidebarOpen(!sidebarOpen) 
    }),
    React.createElement(
      "div",
      { className: "flex" },
      React.createElement(Sidebar, { 
        open: sidebarOpen,
        onClose: () => setSidebarOpen(false)
      }),
      React.createElement(
        "main",
        { 
          className: "flex-1 p-6 lg:ml-64 transition-all duration-300",
          style: { marginLeft: sidebarOpen ? "16rem" : "0" }
        },
        children
      )
    )
  );
}

export default Layout;