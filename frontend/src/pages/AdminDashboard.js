import React, { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Button } from '../components/ui/button';
import api from '../utils/api';
import { toast } from 'sonner';
import { Sparkles, Users, CreditCard, FileText, ArrowLeft, TrendingUp, CheckCircle, XCircle } from 'lucide-react';

export default function AdminDashboard() {
  const [stats, setStats] = useState(null);
  const [users, setUsers] = useState([]);
  const [payments, setPayments] = useState([]);
  const [generations, setGenerations] = useState([]);
  const [activeTab, setActiveTab] = useState('stats');
  const navigate = useNavigate();

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      const [statsRes, usersRes, paymentsRes, generationsRes] = await Promise.all([
        api.get('/api/admin/stats'),
        api.get('/api/admin/users?size=10'),
        api.get('/api/admin/payments?size=10'),
        api.get('/api/admin/generations?size=10')
      ]);
      
      setStats(statsRes.data);
      setUsers(usersRes.data.content || []);
      setPayments(paymentsRes.data.content || []);
      setGenerations(generationsRes.data.content || []);
    } catch (error) {
      if (error.response?.status === 403) {
        toast.error('Admin access required');
        navigate('/app');
      } else {
        toast.error('Failed to load admin data');
      }
    }
  };

  if (!stats) {
    return <div className="min-h-screen flex items-center justify-center">Loading...</div>;
  }

  return (
    <div className="min-h-screen bg-slate-50">
      <header className="bg-white border-b border-slate-200">
        <div className="max-w-7xl mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Link to="/app">
              <Button variant="ghost" size="sm">
                <ArrowLeft className="w-4 h-4 mr-2" />
                Dashboard
              </Button>
            </Link>
            <div className="flex items-center gap-2">
              <Sparkles className="w-6 h-6 text-purple-500" />
              <span className="text-xl font-bold">Admin Panel</span>
            </div>
          </div>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-4 py-8">
        {/* Stats Cards */}
        <div className="grid md:grid-cols-4 gap-6 mb-8">
          <div className="bg-white border border-slate-200 rounded-xl p-6">
            <div className="flex items-center justify-between mb-2">
              <span className="text-slate-600">Total Users</span>
              <Users className="w-5 h-5 text-blue-500" />
            </div>
            <div className="text-3xl font-bold text-slate-900">{stats.totalUsers}</div>
          </div>

          <div className="bg-white border border-slate-200 rounded-xl p-6">
            <div className="flex items-center justify-between mb-2">
              <span className="text-slate-600">Generations</span>
              <FileText className="w-5 h-5 text-indigo-500" />
            </div>
            <div className="text-3xl font-bold text-slate-900">{stats.totalGenerations}</div>
            <div className="text-sm text-green-600 mt-1">
              {stats.successfulGenerations} successful
            </div>
          </div>

          <div className="bg-white border border-slate-200 rounded-xl p-6">
            <div className="flex items-center justify-between mb-2">
              <span className="text-slate-600">Payments</span>
              <CreditCard className="w-5 h-5 text-purple-500" />
            </div>
            <div className="text-3xl font-bold text-slate-900">{stats.totalPayments}</div>
          </div>

          <div className="bg-white border border-slate-200 rounded-xl p-6">
            <div className="flex items-center justify-between mb-2">
              <span className="text-slate-600">Success Rate</span>
              <TrendingUp className="w-5 h-5 text-green-500" />
            </div>
            <div className="text-3xl font-bold text-slate-900">
              {stats.totalGenerations > 0 
                ? Math.round((stats.successfulGenerations / stats.totalGenerations) * 100) 
                : 0}%
            </div>
          </div>
        </div>

        {/* Tabs */}
        <div className="bg-white border border-slate-200 rounded-xl overflow-hidden">
          <div className="border-b border-slate-200 flex">
            <button
              onClick={() => setActiveTab('users')}
              className={`px-6 py-4 font-medium transition-colors ${
                activeTab === 'users' 
                  ? 'border-b-2 border-indigo-500 text-indigo-600' 
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              Users ({users.length})
            </button>
            <button
              onClick={() => setActiveTab('payments')}
              className={`px-6 py-4 font-medium transition-colors ${
                activeTab === 'payments' 
                  ? 'border-b-2 border-indigo-500 text-indigo-600' 
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              Payments ({payments.length})
            </button>
            <button
              onClick={() => setActiveTab('generations')}
              className={`px-6 py-4 font-medium transition-colors ${
                activeTab === 'generations' 
                  ? 'border-b-2 border-indigo-500 text-indigo-600' 
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              Generations ({generations.length})
            </button>
          </div>

          <div className="p-6">
            {activeTab === 'users' && (
              <div className="space-y-4">
                {users.map((user) => (
                  <div key={user.id} className="flex items-center justify-between p-4 bg-slate-50 rounded-lg">
                    <div>
                      <div className="font-medium">{user.name}</div>
                      <div className="text-sm text-slate-500">{user.email}</div>
                    </div>
                    <div className="flex items-center gap-4">
                      <span className={`px-3 py-1 rounded-full text-sm font-medium ${
                        user.role === 'ADMIN' ? 'bg-purple-100 text-purple-700' : 'bg-blue-100 text-blue-700'
                      }`}>
                        {user.role}
                      </span>
                      <span className="text-sm text-slate-500">
                        {new Date(user.createdAt).toLocaleDateString()}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            )}

            {activeTab === 'payments' && (
              <div className="space-y-4">
                {payments.map((payment) => (
                  <div key={payment.id} className="flex items-center justify-between p-4 bg-slate-50 rounded-lg">
                    <div>
                      <div className="font-medium">₹{payment.amountInr}</div>
                      <div className="text-sm text-slate-500">{payment.product?.name}</div>
                    </div>
                    <div className="flex items-center gap-4">
                      <span className={`px-3 py-1 rounded-full text-sm font-medium ${
                        payment.status === 'PAID' ? 'bg-green-100 text-green-700' :
                        payment.status === 'FAILED' ? 'bg-red-100 text-red-700' :
                        'bg-slate-100 text-slate-700'
                      }`}>
                        {payment.status}
                      </span>
                      <span className="text-sm text-slate-500">
                        {new Date(payment.createdAt).toLocaleDateString()}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            )}

            {activeTab === 'generations' && (
              <div className="space-y-4">
                {generations.map((gen) => (
                  <div key={gen.id} className="flex items-center justify-between p-4 bg-slate-50 rounded-lg">
                    <div>
                      <div className="font-medium">{gen.type} Generation</div>
                      <div className="text-sm text-slate-500">
                        Credits: {gen.creditsUsed}
                      </div>
                    </div>
                    <div className="flex items-center gap-4">
                      {gen.status === 'SUCCEEDED' && (
                        <CheckCircle className="w-5 h-5 text-green-500" />
                      )}
                      {gen.status === 'FAILED' && (
                        <XCircle className="w-5 h-5 text-red-500" />
                      )}
                      <span className={`px-3 py-1 rounded-full text-sm font-medium ${
                        gen.status === 'SUCCEEDED' ? 'bg-green-100 text-green-700' :
                        gen.status === 'FAILED' ? 'bg-red-100 text-red-700' :
                        'bg-slate-100 text-slate-700'
                      }`}>
                        {gen.status}
                      </span>
                      <span className="text-sm text-slate-500">
                        {new Date(gen.createdAt).toLocaleString()}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
