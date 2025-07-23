// src/App.js
// Main application component that serves as the entry point for the React application
// Wraps the entire application with the AuthWrapper component for authentication
import React from 'react';
import AuthWrapper from './components/AuthWrapper';

function App() {
  return <AuthWrapper />;
}

export default App;