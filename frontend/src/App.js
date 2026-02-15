import React, { useState, useEffect } from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import Landing from './pages/Landing';
import Login from './pages/Login';
import Signup from './pages/Signup';
import Dashboard from './pages/Dashboard';
import ReelGenerator from './pages/ReelGenerator';
import StoryGenerator from './pages/StoryGenerator';
import History from './pages/History';
import Billing from './pages/Billing';
import Pricing from './pages/Pricing';
import AdminDashboard from './pages/AdminDashboard';
import FeatureRequests from './pages/FeatureRequests';
import AuthCallback from './pages/AuthCallback';
import Contact from './pages/Contact';
import Reviews from './pages/Reviews';
import './App.css';

function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = localStorage.getItem('token');
    if (token) {
      setIsAuthenticated(true);
    }
    setLoading(false);
  }, []);

  if (loading) {
    return <div className="flex items-center justify-center min-h-screen">Loading...</div>;
  }

  return (
    <Routes>
      <Route path="/" element={<Landing />} />
      <Route path="/pricing" element={<Pricing />} />
      <Route path="/contact" element={<Contact />} />
      <Route path="/reviews" element={<Reviews />} />
      <Route path="/login" element={<Login setAuth={setIsAuthenticated} />} />
      <Route path="/signup" element={<Signup setAuth={setIsAuthenticated} />} />
      <Route path="/auth/callback" element={<AuthCallback setAuth={setIsAuthenticated} />} />
      
      {/* Protected routes */}
      <Route path="/app" element={isAuthenticated ? <Dashboard /> : <Navigate to="/login" />} />
      <Route path="/app/reels" element={isAuthenticated ? <ReelGenerator /> : <Navigate to="/login" />} />
      <Route path="/app/stories" element={isAuthenticated ? <StoryGenerator /> : <Navigate to="/login" />} />
      <Route path="/app/history" element={isAuthenticated ? <History /> : <Navigate to="/login" />} />
      <Route path="/app/billing" element={isAuthenticated ? <Billing /> : <Navigate to="/login" />} />
      <Route path="/app/admin" element={isAuthenticated ? <AdminDashboard /> : <Navigate to="/login" />} />
      <Route path="/app/feature-requests" element={isAuthenticated ? <FeatureRequests /> : <Navigate to="/login" />} />
    </Routes>
  );
}

export default App;