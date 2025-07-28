console.log("main.tsx starting...");

// Try direct CDN imports first to test
let React, createRoot;

try {
  const reactModule = await import("https://esm.sh/react@18.2.0");
  const reactDomModule = await import("https://esm.sh/react-dom@18.2.0/client");
  
  React = reactModule.default;
  createRoot = reactDomModule.createRoot;
  
  console.log("React imported:", !!React);
  console.log("createRoot imported:", !!createRoot);

  const rootElement = document.getElementById("root");
  console.log("Root element found:", !!rootElement);

  if (!rootElement) {
    console.error("Root element not found!");
  } else if (React && createRoot) {
    console.log("Creating React root...");
    
    const root = createRoot(rootElement);
    
    // Load the full App component
    try {
      const AppModule = await import("./App.tsx");
      console.log("App module loaded:", !!AppModule.default);
      
      root.render(React.createElement(AppModule.default));
      console.log("Full app rendered successfully");
      
    } catch (appError) {
      console.error("Error loading App component:", appError);
      
      // Fallback to simple test component if App fails
      const ErrorComponent = React.createElement("div", 
        { style: { padding: "20px", backgroundColor: "#fff3cd", border: "2px solid #ffc107", margin: "20px" } }, 
        React.createElement("h1", { style: { color: "#856404" } }, "⚠️ App Loading Error"),
        React.createElement("p", null, "Failed to load the full app. Error: " + appError.message),
        React.createElement("div", { style: { marginTop: "20px" } },
          React.createElement("button", 
            { 
              onClick: () => window.location.reload(),
              style: { 
                padding: "10px 20px", 
                backgroundColor: "#007bff", 
                color: "white", 
                border: "none", 
                borderRadius: "4px",
                cursor: "pointer"
              }
            }, 
            "Reload Page"
          )
        ),
        React.createElement("details", 
          { style: { marginTop: "20px" } },
          React.createElement("summary", null, "Technical Details"),
          React.createElement("pre", 
            { style: { fontSize: "12px", backgroundColor: "#f8f9fa", padding: "10px", marginTop: "10px" } },
            appError.stack || appError.message
          )
        )
      );
      
      root.render(ErrorComponent);
    }
  } else {
    console.error("React dependencies not available");
    if (rootElement) {
      rootElement.innerHTML = `
        <div style="padding: 20px; background-color: #fff3cd; border: 2px solid #ffc107; margin: 20px;">
          <h1 style="color: #856404;">⚠️ Warning</h1>
          <p>React dependencies not loaded. React: ${!!React}, createRoot: ${!!createRoot}</p>
        </div>
      `;
    }
  }
} catch (error) {
  console.error("Error importing React modules:", error);
  const rootElement = document.getElementById("root");
  if (rootElement) {
    rootElement.innerHTML = `
      <div style="padding: 20px; background-color: #f8d7da; border: 2px solid #dc3545; margin: 20px;">
        <h1 style="color: #dc3545;">❌ Import Error</h1>
        <p>Failed to load React modules: ${error.message}</p>
        <p>Check browser console for details.</p>
      </div>
    `;
  }
}