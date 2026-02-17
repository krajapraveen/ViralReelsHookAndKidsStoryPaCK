import React, { useState, useEffect } from 'react';
import api from '../../utils/api';
import { toast } from 'sonner';
import { 
  CheckCircle, XCircle, RefreshCw, DollarSign, 
  AlertTriangle, Clock, TrendingUp, Filter
} from 'lucide-react';
import { Button } from '../ui/button';

export default function PaymentMonitoringTab() {
  const [activeView, setActiveView] = useState('successful');
  const [payments, setPayments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState({ successful: 0, failed: 0, refunded: 0 });
  const [page, setPage] = useState(0);
  const [total, setTotal] = useState(0);

  useEffect(() => {
    fetchPayments();
  }, [activeView, page]);

  const fetchPayments = async () => {
    setLoading(true);
    try {
      const endpoint = activeView === 'successful' 
        ? '/api/admin/payments/successful'
        : activeView === 'failed'
        ? '/api/admin/payments/failed'
        : '/api/admin/payments/refunded';
      
      const response = await api.get(`${endpoint}?page=${page}&size=20&days=30`);
      setPayments(response.data.payments || []);
      setTotal(response.data.total || 0);
      
      // Also fetch summary stats
      const dashboardRes = await api.get('/api/admin/analytics/dashboard?days=30');
      if (dashboardRes.data) {
        const p = dashboardRes.data.payments || {};
        setStats({
          successful: p.successful || 0,
          failed: p.failed || 0,
          refunded: p.refunded || 0
        });
      }
    } catch (error) {
      console.error('Failed to fetch payments:', error);
      toast.error('Failed to load payment data');
    } finally {
      setLoading(false);
    }
  };

  const formatDate = (dateStr) => {
    if (!dateStr) return 'N/A';
    return new Date(dateStr).toLocaleString();
  };

  const formatAmount = (amount, currency = 'INR') => {
    if (currency === 'INR') {
      return `₹${(amount / 100).toFixed(2)}`;
    }
    return `${currency} ${(amount / 100).toFixed(2)}`;
  };

  const views = [
    { id: 'successful', label: 'Successful', icon: <CheckCircle className="w-4 h-4" />, color: 'text-green-400' },
    { id: 'failed', label: 'Failed', icon: <XCircle className="w-4 h-4" />, color: 'text-red-400' },
    { id: 'refunded', label: 'Refunded', icon: <RefreshCw className="w-4 h-4" />, color: 'text-yellow-400' },
  ];

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <RefreshCw className="w-6 h-6 animate-spin text-purple-500" />
        <span className="ml-2 text-slate-400">Loading payment data...</span>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Stats Summary */}
      <div className="grid grid-cols-3 gap-4">
        <div className="bg-green-500/10 border border-green-500/20 rounded-lg p-4">
          <div className="flex items-center gap-2 text-green-400 mb-2">
            <CheckCircle className="w-5 h-5" />
            <span className="font-medium">Successful</span>
          </div>
          <p className="text-2xl font-bold text-white">{stats.successful}</p>
          <p className="text-xs text-slate-400">Last 30 days</p>
        </div>
        <div className="bg-red-500/10 border border-red-500/20 rounded-lg p-4">
          <div className="flex items-center gap-2 text-red-400 mb-2">
            <XCircle className="w-5 h-5" />
            <span className="font-medium">Failed</span>
          </div>
          <p className="text-2xl font-bold text-white">{stats.failed}</p>
          <p className="text-xs text-slate-400">Last 30 days</p>
        </div>
        <div className="bg-yellow-500/10 border border-yellow-500/20 rounded-lg p-4">
          <div className="flex items-center gap-2 text-yellow-400 mb-2">
            <RefreshCw className="w-5 h-5" />
            <span className="font-medium">Refunded</span>
          </div>
          <p className="text-2xl font-bold text-white">{stats.refunded}</p>
          <p className="text-xs text-slate-400">Last 30 days</p>
        </div>
      </div>

      {/* View Selector */}
      <div className="flex gap-2">
        {views.map((view) => (
          <Button
            key={view.id}
            variant={activeView === view.id ? 'default' : 'outline'}
            size="sm"
            onClick={() => { setActiveView(view.id); setPage(0); }}
            className={activeView === view.id ? 'bg-purple-600' : 'border-slate-600'}
          >
            <span className={view.color}>{view.icon}</span>
            <span className="ml-2">{view.label}</span>
          </Button>
        ))}
        <Button variant="outline" size="sm" onClick={fetchPayments} className="ml-auto border-slate-600">
          <RefreshCw className="w-4 h-4 mr-2" />
          Refresh
        </Button>
      </div>

      {/* Payment List */}
      <div className="bg-slate-700/50 rounded-lg overflow-hidden">
        <table className="w-full">
          <thead className="bg-slate-800">
            <tr>
              <th className="px-4 py-3 text-left text-xs font-medium text-slate-400 uppercase">User</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-slate-400 uppercase">Order ID</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-slate-400 uppercase">Amount</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-slate-400 uppercase">Product</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-slate-400 uppercase">Credits</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-slate-400 uppercase">Date</th>
              {activeView === 'failed' && (
                <th className="px-4 py-3 text-left text-xs font-medium text-slate-400 uppercase">Reason</th>
              )}
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-600">
            {payments.length === 0 ? (
              <tr>
                <td colSpan={activeView === 'failed' ? 7 : 6} className="px-4 py-8 text-center text-slate-400">
                  No {activeView} payments found
                </td>
              </tr>
            ) : (
              payments.map((payment, index) => (
                <tr key={payment.id || index} className="hover:bg-slate-700/30">
                  <td className="px-4 py-3 text-sm text-white">
                    {payment.user_email || payment.userEmail || 'N/A'}
                  </td>
                  <td className="px-4 py-3 text-sm text-slate-300 font-mono">
                    {(payment.order_id || payment.razorpay_order_id || '').substring(0, 20)}...
                  </td>
                  <td className="px-4 py-3 text-sm text-white font-medium">
                    {formatAmount(payment.amount, payment.currency)}
                  </td>
                  <td className="px-4 py-3 text-sm text-slate-300">
                    {payment.product_id || payment.productId || 'N/A'}
                  </td>
                  <td className="px-4 py-3 text-sm text-purple-400">
                    {payment.credits || 0}
                  </td>
                  <td className="px-4 py-3 text-sm text-slate-400">
                    {formatDate(payment.created_at || payment.createdAt)}
                  </td>
                  {activeView === 'failed' && (
                    <td className="px-4 py-3 text-sm text-red-400">
                      {payment.failure_reason || 'Unknown'}
                    </td>
                  )}
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      {total > 20 && (
        <div className="flex items-center justify-between">
          <p className="text-sm text-slate-400">
            Showing {page * 20 + 1} - {Math.min((page + 1) * 20, total)} of {total}
          </p>
          <div className="flex gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setPage(p => Math.max(0, p - 1))}
              disabled={page === 0}
              className="border-slate-600"
            >
              Previous
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setPage(p => p + 1)}
              disabled={(page + 1) * 20 >= total}
              className="border-slate-600"
            >
              Next
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
