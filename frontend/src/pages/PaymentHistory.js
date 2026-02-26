import React, { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Button } from '../components/ui/button';
import { toast } from 'sonner';
import { 
  Sparkles, ArrowLeft, Coins, LogOut, Receipt, CreditCard,
  Calendar, CheckCircle, XCircle, Clock, Download, Filter,
  ChevronLeft, ChevronRight, IndianRupee, DollarSign, FileText
} from 'lucide-react';
import api from '../utils/api';

export default function PaymentHistory() {
  const [payments, setPayments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [credits, setCredits] = useState(0);
  const [page, setPage] = useState(0);
  const [totalPages, setTotalPages] = useState(1);
  const [stats, setStats] = useState({ total: 0, successful: 0, totalAmount: 0 });
  const [downloadingInvoice, setDownloadingInvoice] = useState(null);
  const navigate = useNavigate();

  useEffect(() => {
    fetchPayments();
  }, [page]);

  const fetchPayments = async () => {
    try {
      setLoading(true);
      const [creditsRes, paymentsRes] = await Promise.all([
        api.get('/api/credits/balance'),
        api.get(`/api/payments/history?page=${page}&size=10`)
      ]);
      
      setCredits(creditsRes.data.balance);
      setPayments(paymentsRes.data.payments || []);
      setTotalPages(paymentsRes.data.totalPages || 1);
      setStats({
        total: paymentsRes.data.total || 0,
        successful: paymentsRes.data.successful || 0,
        totalAmount: paymentsRes.data.totalAmount || 0
      });
    } catch (error) {
      toast.error('Failed to load payment history');
    } finally {
      setLoading(false);
    }
  };

  const handleDownloadInvoice = async (orderId) => {
    try {
      setDownloadingInvoice(orderId);
      const response = await fetch(`${process.env.REACT_APP_BACKEND_URL}/api/cashfree/invoice/${orderId}`, {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        }
      });
      
      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to download invoice');
      }
      
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `invoice_${orderId}.pdf`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
      
      toast.success('Invoice downloaded successfully');
    } catch (error) {
      toast.error(error.message || 'Failed to download invoice');
    } finally {
      setDownloadingInvoice(null);
    }
  };

  const getStatusIcon = (status) => {
    switch (status?.toUpperCase()) {
      case 'PAID':
      case 'SUCCESS':
      case 'COMPLETED':
        return <CheckCircle className="w-5 h-5 text-green-500" />;
      case 'FAILED':
      case 'CANCELLED':
        return <XCircle className="w-5 h-5 text-red-500" />;
      case 'PENDING':
      case 'CREATED':
        return <Clock className="w-5 h-5 text-amber-500" />;
      default:
        return <Clock className="w-5 h-5 text-slate-400" />;
    }
  };

  const getStatusColor = (status) => {
    switch (status?.toUpperCase()) {
      case 'PAID':
      case 'SUCCESS':
      case 'COMPLETED':
        return 'bg-green-500/20 text-green-400';
      case 'FAILED':
      case 'CANCELLED':
        return 'bg-red-500/20 text-red-400';
      case 'PENDING':
      case 'CREATED':
        return 'bg-amber-500/20 text-amber-400';
      default:
        return 'bg-slate-500/20 text-slate-400';
    }
  };

  const formatDate = (dateString) => {
    if (!dateString) return 'N/A';
    return new Date(dateString).toLocaleDateString('en-IN', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const formatCurrency = (amount, currency = 'INR') => {
    if (currency === 'INR') {
      return `₹${(amount || 0).toLocaleString('en-IN')}`;
    }
    return `$${(amount || 0).toLocaleString('en-US')}`;
  };

  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-950 via-indigo-950 to-slate-950 text-white">
      {/* Header */}
      <header className="bg-slate-900/80 backdrop-blur-sm border-b border-slate-700/50">
        <div className="max-w-6xl mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Link to="/app">
              <Button variant="ghost" size="sm" className="text-slate-300 hover:text-white hover:bg-white/10">
                <ArrowLeft className="w-4 h-4 mr-2" />
                Dashboard
              </Button>
            </Link>
            <div className="flex items-center gap-2">
              <Receipt className="w-6 h-6 text-purple-400" />
              <span className="text-xl font-bold text-white">Payment History</span>
            </div>
          </div>
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2 bg-purple-500/20 border border-purple-500/30 rounded-full px-4 py-2">
              <Coins className="w-4 h-4 text-purple-400" />
              <span className="font-semibold text-purple-300">{credits} Credits</span>
            </div>
            <Button variant="ghost" size="sm" onClick={() => { localStorage.removeItem('token'); navigate('/login'); }} className="text-slate-300 hover:text-white hover:bg-white/10">
              <LogOut className="w-4 h-4 mr-2" />
              Logout
            </Button>
          </div>
        </div>
      </header>

      <div className="max-w-6xl mx-auto px-4 py-8">
        {/* Stats Cards */}
        <div className="grid md:grid-cols-3 gap-6 mb-8">
          <div className="bg-slate-800/50 backdrop-blur-sm rounded-xl border border-slate-700/50 p-6">
            <div className="flex items-center gap-3 mb-2">
              <div className="p-2 bg-purple-500/20 rounded-lg">
                <CreditCard className="w-5 h-5 text-purple-400" />
              </div>
              <span className="text-slate-400 text-sm">Total Transactions</span>
            </div>
            <p className="text-3xl font-bold text-white">{stats.total}</p>
          </div>
          
          <div className="bg-slate-800/50 backdrop-blur-sm rounded-xl border border-slate-700/50 p-6">
            <div className="flex items-center gap-3 mb-2">
              <div className="p-2 bg-green-500/20 rounded-lg">
                <CheckCircle className="w-5 h-5 text-green-400" />
              </div>
              <span className="text-slate-400 text-sm">Successful Payments</span>
            </div>
            <p className="text-3xl font-bold text-green-400">{stats.successful}</p>
          </div>
          
          <div className="bg-slate-800/50 backdrop-blur-sm rounded-xl border border-slate-700/50 p-6">
            <div className="flex items-center gap-3 mb-2">
              <div className="p-2 bg-amber-500/20 rounded-lg">
                <IndianRupee className="w-5 h-5 text-amber-400" />
              </div>
              <span className="text-slate-400 text-sm">Total Spent</span>
            </div>
            <p className="text-3xl font-bold text-white">{formatCurrency(stats.totalAmount)}</p>
          </div>
        </div>

        {/* Payment List */}
        <div className="bg-slate-800/50 backdrop-blur-sm rounded-xl border border-slate-700/50">
          <div className="p-6 border-b border-slate-700">
            <h2 className="text-lg font-bold text-white">Transaction History</h2>
            <p className="text-slate-500 text-sm">View all your past transactions and purchases</p>
          </div>

          {loading ? (
            <div className="p-12 text-center">
              <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-purple-400 mx-auto"></div>
              <p className="mt-4 text-slate-400">Loading transactions...</p>
            </div>
          ) : payments.length === 0 ? (
            <div className="p-12 text-center">
              <Receipt className="w-16 h-16 text-slate-500 mx-auto mb-4" />
              <h3 className="text-lg font-semibold text-white mb-2">No transactions yet</h3>
              <p className="text-slate-400 mb-4">Your payment history will appear here once you make a purchase.</p>
              <Link to="/app/billing">
                <Button className="bg-purple-600 hover:bg-purple-700">
                  <Coins className="w-4 h-4 mr-2" />
                  Buy Credits
                </Button>
              </Link>
            </div>
          ) : (
            <>
              <div className="divide-y divide-slate-700">
                {payments.map((payment, index) => (
                  <div key={payment.id || index} className="p-4 hover:bg-slate-700/30 transition-colors" data-testid={`payment-${payment.id}`}>
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-4">
                        {getStatusIcon(payment.status)}
                        <div>
                          <p className="font-semibold text-white">
                            {payment.product?.name || payment.description || 'Credit Purchase'}
                          </p>
                          <div className="flex items-center gap-2 text-sm text-slate-400">
                            <Calendar className="w-3 h-3" />
                            {formatDate(payment.createdAt || payment.paidAt)}
                            {payment.orderId && (
                              <>
                                <span className="text-slate-600">•</span>
                                <span className="font-mono text-xs">{payment.orderId.slice(-8)}</span>
                              </>
                            )}
                          </div>
                        </div>
                      </div>
                      
                      <div className="flex items-center gap-4">
                        <div className="text-right">
                          <p className="font-bold text-white">
                            {formatCurrency(payment.amount, payment.currency)}
                          </p>
                          {payment.credits && (
                            <p className="text-sm text-purple-400">+{payment.credits} credits</p>
                          )}
                        </div>
                        <span className={`px-3 py-1 rounded-full text-xs font-medium ${getStatusColor(payment.status)}`}>
                          {payment.status || 'Unknown'}
                        </span>
                        {/* Invoice Download Button */}
                        {(payment.status === 'PAID' || payment.status === 'SUCCESS' || payment.status === 'COMPLETED') && payment.orderId && (
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => handleDownloadInvoice(payment.orderId)}
                            disabled={downloadingInvoice === payment.orderId}
                            className="border-purple-200 text-purple-600 hover:bg-purple-50"
                            data-testid={`invoice-${payment.orderId}`}
                          >
                            {downloadingInvoice === payment.orderId ? (
                              <Clock className="w-4 h-4 animate-spin" />
                            ) : (
                              <>
                                <FileText className="w-4 h-4 mr-1" />
                                Invoice
                              </>
                            )}
                          </Button>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
              </div>

              {/* Pagination */}
              {totalPages > 1 && (
                <div className="p-4 border-t border-slate-200 flex items-center justify-between">
                  <p className="text-sm text-slate-500">
                    Page {page + 1} of {totalPages}
                  </p>
                  <div className="flex items-center gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setPage(Math.max(0, page - 1))}
                      disabled={page === 0}
                    >
                      <ChevronLeft className="w-4 h-4" />
                      Previous
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setPage(Math.min(totalPages - 1, page + 1))}
                      disabled={page >= totalPages - 1}
                    >
                      Next
                      <ChevronRight className="w-4 h-4" />
                    </Button>
                  </div>
                </div>
              )}
            </>
          )}
        </div>

        {/* Quick Actions */}
        <div className="mt-8 grid md:grid-cols-2 gap-6">
          <Link to="/app/billing" className="block">
            <div className="bg-gradient-to-r from-purple-500 to-indigo-600 rounded-xl p-6 text-white hover:shadow-lg transition-shadow">
              <h3 className="text-lg font-bold mb-2">Need More Credits?</h3>
              <p className="text-purple-100 text-sm mb-4">Top up your account and continue creating amazing content.</p>
              <Button variant="secondary" size="sm">
                <Coins className="w-4 h-4 mr-2" />
                Buy Credits
              </Button>
            </div>
          </Link>
          
          <Link to="/app/profile" className="block">
            <div className="bg-gradient-to-r from-emerald-500 to-teal-600 rounded-xl p-6 text-white hover:shadow-lg transition-shadow">
              <h3 className="text-lg font-bold mb-2">Manage Subscription</h3>
              <p className="text-emerald-100 text-sm mb-4">View and manage your subscription plan and billing details.</p>
              <Button variant="secondary" size="sm">
                View Profile
              </Button>
            </div>
          </Link>
        </div>
      </div>
    </div>
  );
}
