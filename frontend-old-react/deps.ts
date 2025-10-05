// React core with import map compatibility (Classic JSX runtime)
export { default as React, createElement, useState, useEffect, useReducer, useCallback, useRef, useContext, createContext } from "react";
export { createRoot } from "react-dom/client";

// React Router
export { 
  BrowserRouter, 
  Routes, 
  Route, 
  Link, 
  NavLink, 
  useNavigate, 
  useParams, 
  useLocation 
} from "react-router-dom";

// Charts and visualization
export { 
  LineChart, 
  Line, 
  BarChart, 
  Bar, 
  PieChart, 
  Pie, 
  Cell, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  Legend, 
  ResponsiveContainer 
} from "recharts";

// Icons
export { 
  Home, 
  BarChart3, 
  Users, 
  PlayCircle, 
  Settings, 
  TrendingUp, 
  Calendar, 
  Clock, 
  Trophy, 
  Target,
  Activity,
  Zap,
  Database,
  RefreshCw,
  Download,
  ExternalLink,
  Search,
  Filter,
  Menu,
  X
} from "lucide-react";