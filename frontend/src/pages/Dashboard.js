import React, { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Button } from '../components/ui/button';
import { creditAPI, authAPI, generationAPI } from '../utils/api';
import { toast } from 'sonner';
import { Sparkles, Video, BookOpen, Clock, LogOut, CreditCard, History as HistoryIcon, Coins, Shield, Lightbulb } from 'lucide-react';

export default function Dashboard() {
  const [credits, setCredits] = useState(0);
  const [user, setUser] = useState(null);
  const [recentGenerations, setRecentGenerations] = useState([]);
  const navigate = useNavigate();

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      const [creditsRes, userRes, generationsRes] = await Promise.all([
        creditAPI.getBalance(),
        authAPI.getCurrentUser(),
        generationAPI.getGenerations(null, 0, 5)
      ]);
      setCredits(creditsRes.data.balance);
      setUser(userRes.data);
      setRecentGenerations(generationsRes.data.content || []);
    } catch (error) {
      toast.error('Failed to load dashboard data');
    }
  };

  const handleLogout = () => {
    localStorage.removeItem('token');
    navigate('/login');
  };

  const isAdmin = user?.role === 'ADMIN';

  return (
    <div className="min-h-screen bg-slate-50">
      <header className="bg-white border-b border-slate-200">
        <div className="max-w-7xl mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Sparkles className="w-6 h-6 text-indigo-500" />
            <span className="text-xl font-bold">CreatorStudio AI</span>
          </div>
          
          <div className="flex items-center gap-4">
            {isAdmin && (
              <Link to="/app/admin">
                <Button variant="outline" size="sm" className="border-purple-300 text-purple-600 hover:bg-purple-50" data-testid="admin-dashboard-btn">
                  <Shield className="w-4 h-4 mr-2" />
                  Admin Panel
                </Button>
              </Link>
            )}
            
            <div className="flex items-center gap-2 bg-slate-100 rounded-full px-4 py-2" data-testid="credit-balance">
              <Coins className="w-4 h-4 text-purple-500" />
              <span className="font-semibold">{credits} Credits</span>
            </div>
            
            <Button variant="ghost" onClick={handleLogout} data-testid="logout-btn">
              <LogOut className="w-4 h-4 mr-2" />
              Logout
            </Button>
          </div>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-4 py-12">
        <div className="mb-12">
          <h1 className="text-4xl font-bold mb-2" data-testid="dashboard-welcome">Welcome back, {user?.name}!</h1>
          <p className="text-slate-600 text-lg">What would you like to create today?</p>
        </div>

        <div className="grid md:grid-cols-2 gap-6 mb-12">
          <Link to="/app/reels">
            <div className="bg-gradient-to-br from-indigo-500 to-indigo-600 rounded-2xl p-8 text-white hover:scale-105 transition-transform cursor-pointer" data-testid="quick-action-reel">
              <Video className="w-12 h-12 mb-4" />
              <h2 className="text-2xl font-bold mb-2">Generate Reel Script</h2>
              <p className="text-indigo-100 mb-4">Create viral reel scripts in 5-10 seconds</p>
              <div className="inline-flex items-center gap-2 bg-white/20 rounded-full px-4 py-2 text-sm">
                <Coins className="w-4 h-4" />
                <span>1 credit per generation</span>
              </div>
            </div>
          </Link>

          <Link to="/app/stories">
            <div className="bg-gradient-to-br from-purple-500 to-purple-600 rounded-2xl p-8 text-white hover:scale-105 transition-transform cursor-pointer" data-testid="quick-action-story">
              <BookOpen className="w-12 h-12 mb-4" />
              <h2 className="text-2xl font-bold mb-2">Create Kids Story Pack</h2>
              <p className="text-purple-100 mb-4">Complete video production packages</p>
              <div className="inline-flex items-center gap-2 bg-white/20 rounded-full px-4 py-2 text-sm">
                <Coins className="w-4 h-4" />
                <span>6-8 credits per pack</span>
              </div>
            </div>
          </Link>
        </div>

        <div className="grid md:grid-cols-4 gap-6 mb-12">
          <div className="bg-white border border-slate-200 rounded-xl p-6">
            <div className="flex items-center justify-between mb-2">
              <span className="text-slate-600">Available Credits</span>
              <Coins className="w-5 h-5 text-purple-500" />
            </div>
            <div className="text-3xl font-bold text-slate-900">{credits}</div>
          </div>

          <Link to="/app/history" className="bg-white border border-slate-200 rounded-xl p-6 hover:shadow-md transition-shadow">
            <div className="flex items-center justify-between mb-2">
              <span className="text-slate-600">Total Generations</span>
              <Clock className="w-5 h-5 text-indigo-500" />
            </div>
            <div className="text-3xl font-bold text-slate-900">{recentGenerations.length}</div>
          </Link>

          <Link to="/app/billing" className="bg-white border border-slate-200 rounded-xl p-6 hover:shadow-md transition-shadow">
            <div className="flex items-center justify-between mb-2">
              <span className="text-slate-600">Buy More Credits</span>
              <CreditCard className="w-5 h-5 text-green-500" />
            </div>
            <div className="text-lg font-semibold text-indigo-600">View Plans →</div>
          </Link>

          <Link to="/app/feature-requests" className="bg-gradient-to-br from-yellow-50 to-amber-50 border border-yellow-200 rounded-xl p-6 hover:shadow-md transition-shadow">
            <div className="flex items-center justify-between mb-2">
              <span className="text-slate-600">Feature Requests</span>
              <Lightbulb className="w-5 h-5 text-yellow-500" />
            </div>
            <div className="text-lg font-semibold text-yellow-700">Vote & Request →</div>
          </Link>
        </div>

        <div className="bg-white border border-slate-200 rounded-xl p-6">
          <div className="flex items-center justify-between mb-6">
            <h3 className="text-xl font-bold">Recent Generations</h3>
            <Link to="/app/history">
              <Button variant="outline" size="sm" data-testid="view-all-history-btn">
                <HistoryIcon className="w-4 h-4 mr-2" />
                View All
              </Button>
            </Link>
          </div>

          {recentGenerations.length === 0 ? (
            <div className="text-center py-12 text-slate-500">
              <p>No generations yet. Start creating!</p>
            </div>
          ) : (
            <div className="space-y-4" data-testid="recent-generations-list">
              {recentGenerations.map((gen) => (
                <div key={gen.id} className="flex items-center justify-between p-4 bg-slate-50 rounded-lg">
                  <div className="flex items-center gap-4">
                    {gen.type === 'REEL' ? (
                      <div className="w-10 h-10 bg-indigo-100 rounded-lg flex items-center justify-center">
                        <Video className="w-5 h-5 text-indigo-600" />
                      </div>
                    ) : (
                      <div className="w-10 h-10 bg-purple-100 rounded-lg flex items-center justify-center">
                        <BookOpen className="w-5 h-5 text-purple-600" />
                      </div>
                    )}
                    <div>
                      <div className="font-medium">{gen.type} Generation</div>
                      <div className="text-sm text-slate-500">{new Date(gen.createdAt).toLocaleString()}</div>
                    </div>
                  </div>
                  <div className={`px-3 py-1 rounded-full text-sm font-medium ${
                    gen.status === 'SUCCEEDED' ? 'bg-green-100 text-green-700' :
                    gen.status === 'FAILED' ? 'bg-red-100 text-red-700' :
                    'bg-slate-100 text-slate-700'
                  }`}>
                    {gen.status}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
