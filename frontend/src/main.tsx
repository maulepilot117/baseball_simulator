console.log("main.tsx starting...");

import { createRoot } from "../deps.ts";
import App from "./App.tsx";

const rootElement = document.getElementById("root");
console.log("Root element found:", !!rootElement);

if (!rootElement) {
  console.error("Root element not found!");
} else {
  console.log("Creating React root...");
  
  const root = createRoot(rootElement);
  
  try {
    root.render(<App />);
    console.log("App rendered successfully");
  } catch (error) {
    console.error("Error rendering App:", error);
    
    root.render(
      <div style={{ padding: "20px", backgroundColor: "#f8d7da", border: "2px solid #dc3545", margin: "20px" }}>
        <h1 style={{ color: "#dc3545" }}>❌ Render Error</h1>
        <p>Failed to render the app: {error.message}</p>
        <button 
          onClick={() => window.location.reload()}
          style={{ 
            padding: "10px 20px", 
            backgroundColor: "#007bff", 
            color: "white", 
            border: "none", 
            borderRadius: "4px",
            cursor: "pointer"
          }}
        >
          Reload Page
        </button>
      </div>
    );
  }
}