import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../../utils/api';
import { toast } from 'sonner';
import {
  DollarSign, AlertTriangle, CheckCircle2, XCircle, Clock,
  RefreshCw, Search, ChevronRight, Shield, ArrowLeft, Eye,
  Webhook, FileText, Scale, BarChart3, Activity, Ban,
  ExternalLink, Copy, RotateCcw
} from 'lucide-react';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';

// ─── ENVIRONMENT BADGE ──────────────────────────────────
function EnvBadge({ env }) {
  const isProd = env === 'PRODUCTION';
  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider ${
      isProd ? 'bg-red-500/20 text-red-400 border border-red-500/30' : 'bg-amber-500/20 text-amber-400 border border-amber-500/30'
    }`} data-testid="env-badge">
      <Shield className="w-3 h-3" />
      {env}
    </span>
  );
}

// ─── STATUS BADGE ───────────────────────────────────────
function StatusBadge({ status }) {
  const colors = {
    CREATED: 'bg-slate-500/20 text-slate-400',
    INITIATED: 'bg-blue-500/20 text-blue-400',
    SUCCESS: 'bg-emerald-500/20 text-emerald-400',
    CREDIT_APPLIED: 'bg-emerald-500/20 text-emerald-400',
    SUBSCRIPTION_ACTIVATED: 'bg-emerald-500/20 text-emerald-400',
    PAID: 'bg-emerald-500/20 text-emerald-400',
    FAILED: 'bg-red-500/20 text-red-400',
    PROCESSING: 'bg-amber-500/20 text-amber-400',
    PENDING: 'bg-amber-500/20 text-amber-400',
    RECOVERY_REQUIRED: 'bg-red-500/20 text-red-400',
    REFUNDED: 'bg-purple-500/20 text-purple-400',
    PROCESSED: 'bg-emerald-500/20 text-emerald-400',
    ERROR: 'bg-red-500/20 text-red-400',
  };
  return (
    <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${colors[status] || 'bg-slate-500/20 text-slate-400'}`}>
      {status || 'UNKNOWN'}
    </span>
  );
}

// ─── STAT CARD ──────────────────────────────────────────
function StatCard({ label, value, icon: Icon, color = 'text-slate-400', alert }) {
  return (
    <div className={`bg-slate-800/50 border rounded-xl p-3 ${alert ? 'border-red-500/40' : 'border-slate-700/50'}`}>
      <div className="flex items-center justify-between mb-1">
        <span className="text-[10px] text-slate-500 uppercase tracking-wider font-medium">{label}</span>
        <Icon className={`w-3.5 h-3.5 ${color}`} />
      </div>
      <p className={`text-xl font-bold ${alert ? 'text-red-400' : 'text-white'}`}>{value}</p>
    </div>
  );
}

// ─── ORDERS TAB ─────────────────────────────────────────
function OrdersTab({ token, onDrilldown }) {
  const [orders, setOrders] = useState([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [filters, setFilters] = useState({ email: '', order_id: '', status: '', days: 7, unreconciled_only: false });

  const fetchOrders = useCallback(async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (filters.email) params.append('email', filters.email);
      if (filters.order_id) params.append('order_id', filters.order_id);
      if (filters.status) params.append('status', filters.status);
      if (filters.unreconciled_only) params.append('unreconciled_only', 'true');
      params.append('days', filters.days);
      params.append('limit', '50');
      const { data } = await api.get(`/api/admin/payments/orders?${params}`);
      setOrders(data.orders || []);
      setTotal(data.total || 0);
    } catch (e) {
      toast.error('Failed to fetch orders');
    }
    setLoading(false);
  }, [filters]);

  useEffect(() => { fetchOrders(); }, [fetchOrders]);

  return (
    <div className="space-y-3">
      {/* Filters */}
      <div className="flex flex-wrap gap-2 items-center">
        <Input placeholder="Search email..." value={filters.email} onChange={e => setFilters(f => ({...f, email: e.target.value}))}
          className="w-44 h-8 text-xs bg-slate-800 border-slate-700 text-white" data-testid="filter-email" />
        <Input placeholder="Order ID..." value={filters.order_id} onChange={e => setFilters(f => ({...f, order_id: e.target.value}))}
          className="w-44 h-8 text-xs bg-slate-800 border-slate-700 text-white" data-testid="filter-order-id" />
        <select value={filters.status} onChange={e => setFilters(f => ({...f, status: e.target.value}))}
          className="h-8 text-xs bg-slate-800 border border-slate-700 text-white rounded-md px-2" data-testid="filter-status">
          <option value="">All Status</option>
          <option value="CREATED">CREATED</option>
          <option value="SUCCESS">SUCCESS</option>
          <option value="CREDIT_APPLIED">CREDIT_APPLIED</option>
          <option value="SUBSCRIPTION_ACTIVATED">SUBSCRIPTION_ACTIVATED</option>
          <option value="FAILED">FAILED</option>
          <option value="RECOVERY_REQUIRED">RECOVERY_REQUIRED</option>
        </select>
        <select value={filters.days} onChange={e => setFilters(f => ({...f, days: parseInt(e.target.value)}))}
          className="h-8 text-xs bg-slate-800 border border-slate-700 text-white rounded-md px-2">
          <option value="1">Today</option>
          <option value="7">7 days</option>
          <option value="30">30 days</option>
          <option value="90">90 days</option>
        </select>
        <label className="flex items-center gap-1 text-xs text-slate-400 cursor-pointer">
          <input type="checkbox" checked={filters.unreconciled_only}
            onChange={e => setFilters(f => ({...f, unreconciled_only: e.target.checked}))}
            className="rounded bg-slate-700 border-slate-600" data-testid="filter-unreconciled" />
          Unreconciled only
        </label>
        <Button size="sm" variant="outline" onClick={fetchOrders} className="h-8 text-xs" data-testid="orders-refresh">
          <RefreshCw className={`w-3 h-3 mr-1 ${loading ? 'animate-spin' : ''}`} /> Refresh
        </Button>
        <span className="text-xs text-slate-500 ml-auto">{total} orders</span>
      </div>

      {/* Table */}
      <div className="overflow-x-auto rounded-xl border border-slate-700/50">
        <table className="w-full text-xs" data-testid="orders-table">
          <thead>
            <tr className="bg-slate-800/80 text-slate-400 text-left">
              <th className="px-3 py-2 font-medium">Time</th>
              <th className="px-3 py-2 font-medium">Order ID</th>
              <th className="px-3 py-2 font-medium">Email</th>
              <th className="px-3 py-2 font-medium">Product</th>
              <th className="px-3 py-2 font-medium">Amount</th>
              <th className="px-3 py-2 font-medium">Order Status</th>
              <th className="px-3 py-2 font-medium">Webhook</th>
              <th className="px-3 py-2 font-medium">Entitlement</th>
              <th className="px-3 py-2 font-medium">Settlement</th>
              <th className="px-3 py-2 font-medium">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800">
            {orders.map(o => (
              <tr key={o.order_id} className="hover:bg-slate-800/40 transition-colors">
                <td className="px-3 py-2 text-slate-400 whitespace-nowrap">{(o.createdAt || '').slice(0, 16).replace('T', ' ')}</td>
                <td className="px-3 py-2 text-indigo-400 font-mono text-[10px]">{(o.order_id || '').slice(-20)}</td>
                <td className="px-3 py-2 text-white">{o.userEmail || '?'}</td>
                <td className="px-3 py-2 text-slate-300">{o.productName}</td>
                <td className="px-3 py-2 text-white font-medium">{o.displayAmount} {o.currency}</td>
                <td className="px-3 py-2"><StatusBadge status={o.status} /></td>
                <td className="px-3 py-2">
                  {o.webhook_received
                    ? <span className="flex items-center gap-1"><CheckCircle2 className="w-3 h-3 text-emerald-400" /> <StatusBadge status={o.webhook_status} /></span>
                    : <span className="text-slate-600">-</span>}
                </td>
                <td className="px-3 py-2">
                  {o.entitlementApplied
                    ? <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                    : <XCircle className="w-3.5 h-3.5 text-slate-600" />}
                </td>
                <td className="px-3 py-2"><StatusBadge status={o.settlementStatus || 'PENDING'} /></td>
                <td className="px-3 py-2">
                  <button onClick={() => onDrilldown(o.order_id)} className="text-indigo-400 hover:text-indigo-300" data-testid={`drilldown-${o.order_id}`}>
                    <Eye className="w-3.5 h-3.5" />
                  </button>
                </td>
              </tr>
            ))}
            {!orders.length && (
              <tr><td colSpan={10} className="px-4 py-8 text-center text-slate-500">No orders found</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// ─── WEBHOOKS TAB ───────────────────────────────────────
function WebhooksTab() {
  const [webhooks, setWebhooks] = useState([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [orderFilter, setOrderFilter] = useState('');
  const [expanded, setExpanded] = useState(null);

  const fetchWebhooks = useCallback(async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams({ days: '30', limit: '50' });
      if (orderFilter) params.append('order_id', orderFilter);
      const { data } = await api.get(`/api/admin/payments/webhooks?${params}`);
      setWebhooks(data.webhooks || []);
      setTotal(data.total || 0);
    } catch (e) {
      toast.error('Failed to fetch webhooks');
    }
    setLoading(false);
  }, [orderFilter]);

  useEffect(() => { fetchWebhooks(); }, [fetchWebhooks]);

  return (
    <div className="space-y-3">
      <div className="flex gap-2 items-center">
        <Input placeholder="Filter by order ID..." value={orderFilter} onChange={e => setOrderFilter(e.target.value)}
          className="w-60 h-8 text-xs bg-slate-800 border-slate-700 text-white" data-testid="webhook-filter" />
        <Button size="sm" variant="outline" onClick={fetchWebhooks} className="h-8 text-xs">
          <RefreshCw className={`w-3 h-3 mr-1 ${loading ? 'animate-spin' : ''}`} /> Refresh
        </Button>
        <span className="text-xs text-slate-500 ml-auto">{total} events</span>
      </div>

      <div className="space-y-2">
        {webhooks.map((w, i) => (
          <div key={w.eventId || i} className="bg-slate-800/50 border border-slate-700/50 rounded-xl overflow-hidden">
            <div className="flex items-center gap-2 px-3 py-2 cursor-pointer hover:bg-slate-800/80" onClick={() => setExpanded(expanded === i ? null : i)}>
              <StatusBadge status={w.status} />
              <span className="text-[10px] font-mono text-slate-400">{w.eventType}</span>
              <span className="text-[10px] text-indigo-400 font-mono">{(w.orderId || '').slice(-20)}</span>
              <span className="text-[10px] text-slate-500 ml-auto">{(w.receivedAt || '').slice(0, 19)}</span>
              {w.signatureVerified === true && <CheckCircle2 className="w-3 h-3 text-emerald-400" title="Signature verified" />}
              {w.signatureVerified === false && <XCircle className="w-3 h-3 text-red-400" title="Signature FAILED" />}
              {w.payloadHash && <span className="text-[8px] text-slate-600 font-mono">#{(w.payloadHash || '').slice(0, 8)}</span>}
              <ChevronRight className={`w-3 h-3 text-slate-500 transition-transform ${expanded === i ? 'rotate-90' : ''}`} />
            </div>
            {expanded === i && (
              <div className="px-3 py-2 border-t border-slate-700/40 bg-slate-900/50">
                <pre className="text-[10px] text-slate-400 overflow-x-auto max-h-48 whitespace-pre-wrap">
                  {JSON.stringify(w.payload, null, 2)}
                </pre>
              </div>
            )}
          </div>
        ))}
        {!webhooks.length && <p className="text-center text-slate-500 text-sm py-8">No webhook events found</p>}
      </div>
    </div>
  );
}

// ─── RECONCILIATION TAB ─────────────────────────────────
function ReconciliationTab({ onDrilldown }) {
  const [orders, setOrders] = useState([]);
  const [loading, setLoading] = useState(false);
  const [reconciling, setReconciling] = useState(null);

  const fetchUnreconciled = useCallback(async () => {
    setLoading(true);
    try {
      const { data } = await api.get('/api/admin/payments/orders?unreconciled_only=true&days=30');
      setOrders(data.orders || []);
    } catch (e) {
      toast.error('Failed to fetch unreconciled orders');
    }
    setLoading(false);
  }, []);

  useEffect(() => { fetchUnreconciled(); }, [fetchUnreconciled]);

  const handleReconcile = async (orderId) => {
    setReconciling(orderId);
    try {
      const { data } = await api.post(`/api/admin/payments/reconcile/${orderId}`);
      toast.success(`Reconciled: ${data.actions_taken?.join(', ') || 'Done'}`);
      fetchUnreconciled();
    } catch (e) {
      toast.error(`Reconciliation failed: ${e.response?.data?.detail || e.message}`);
    }
    setReconciling(null);
  };

  const handleReplay = async (orderId) => {
    try {
      const { data } = await api.post(`/api/admin/payments/replay-webhook/${orderId}`);
      toast.success(`Replay: ${data.result?.message || data.status}`);
      fetchUnreconciled();
    } catch (e) {
      toast.error(`Replay failed: ${e.response?.data?.detail || e.message}`);
    }
  };

  const handleFetch = async (orderId) => {
    try {
      const { data } = await api.post(`/api/admin/payments/fetch-cashfree/${orderId}`);
      const cfStatus = data.order?.order_status || 'UNKNOWN';
      const payments = data.payments?.length || 0;
      const settlements = data.settlements?.length || 0;
      toast.info(`Cashfree: ${cfStatus} | ${payments} payments | ${settlements} settlements`);
    } catch (e) {
      toast.error(`Fetch failed: ${e.response?.data?.detail || e.message}`);
    }
  };

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-sm font-semibold text-white">Reconciliation Queue</h3>
          <p className="text-[10px] text-slate-500">Orders that need attention — paid in Cashfree but not reflected in your system</p>
        </div>
        <Button size="sm" variant="outline" onClick={fetchUnreconciled} className="h-8 text-xs" data-testid="reconcile-refresh">
          <RefreshCw className={`w-3 h-3 mr-1 ${loading ? 'animate-spin' : ''}`} /> Refresh
        </Button>
      </div>

      {!orders.length && !loading && (
        <div className="bg-emerald-500/10 border border-emerald-500/30 rounded-xl p-6 text-center">
          <CheckCircle2 className="w-8 h-8 text-emerald-400 mx-auto mb-2" />
          <p className="text-sm text-emerald-400 font-medium">All orders reconciled</p>
          <p className="text-xs text-slate-500 mt-1">No mismatches detected in the last 30 days</p>
        </div>
      )}

      {orders.map(o => (
        <div key={o.order_id} className="bg-slate-800/50 border border-red-500/20 rounded-xl p-3" data-testid={`recon-${o.order_id}`}>
          <div className="flex items-start justify-between mb-2">
            <div>
              <p className="text-xs font-mono text-indigo-400">{o.order_id}</p>
              <p className="text-xs text-slate-400">{o.userEmail} — {o.productName} — {o.displayAmount} INR</p>
            </div>
            <div className="flex items-center gap-1">
              <StatusBadge status={o.status} />
              {!o.webhook_received && <span className="text-[10px] text-red-400 flex items-center gap-0.5"><Ban className="w-3 h-3" /> No webhook</span>}
            </div>
          </div>
          <div className="flex gap-2">
            <Button size="sm" className="h-7 text-[10px] bg-indigo-600 hover:bg-indigo-700" onClick={() => handleFetch(o.order_id)}>
              <Search className="w-3 h-3 mr-1" /> Fetch from Cashfree
            </Button>
            <Button size="sm" className="h-7 text-[10px] bg-emerald-600 hover:bg-emerald-700"
              onClick={() => handleReconcile(o.order_id)} disabled={reconciling === o.order_id}>
              <Scale className="w-3 h-3 mr-1" /> {reconciling === o.order_id ? 'Reconciling...' : 'Reconcile'}
            </Button>
            <Button size="sm" className="h-7 text-[10px] bg-amber-600 hover:bg-amber-700" onClick={() => handleReplay(o.order_id)}>
              <RotateCcw className="w-3 h-3 mr-1" /> Replay Webhook
            </Button>
            <Button size="sm" variant="outline" className="h-7 text-[10px]" onClick={() => onDrilldown(o.order_id)}>
              <Eye className="w-3 h-3 mr-1" /> Inspect
            </Button>
          </div>
        </div>
      ))}
    </div>
  );
}

// ─── SETTLEMENTS TAB ────────────────────────────────────
function SettlementsTab() {
  const [settlements, setSettlements] = useState([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    (async () => {
      setLoading(true);
      try {
        const { data } = await api.get('/api/admin/payments/settlements?days=30');
        setSettlements(data.settlements || []);
        setTotal(data.total || 0);
      } catch { /* ignore */ }
      setLoading(false);
    })();
  }, []);

  return (
    <div className="space-y-3">
      <p className="text-xs text-slate-500">{total} successful orders in last 30 days</p>
      <div className="overflow-x-auto rounded-xl border border-slate-700/50">
        <table className="w-full text-xs" data-testid="settlements-table">
          <thead>
            <tr className="bg-slate-800/80 text-slate-400 text-left">
              <th className="px-3 py-2 font-medium">Order ID</th>
              <th className="px-3 py-2 font-medium">Email</th>
              <th className="px-3 py-2 font-medium">Product</th>
              <th className="px-3 py-2 font-medium">Amount</th>
              <th className="px-3 py-2 font-medium">Paid At</th>
              <th className="px-3 py-2 font-medium">Settlement</th>
              <th className="px-3 py-2 font-medium">UTR</th>
              <th className="px-3 py-2 font-medium">Settled At</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800">
            {settlements.map(o => (
              <tr key={o.order_id} className="hover:bg-slate-800/40">
                <td className="px-3 py-2 font-mono text-[10px] text-indigo-400">{(o.order_id || '').slice(-20)}</td>
                <td className="px-3 py-2 text-white">{o.userEmail}</td>
                <td className="px-3 py-2 text-slate-300">{o.productName}</td>
                <td className="px-3 py-2 text-white font-medium">{o.displayAmount}</td>
                <td className="px-3 py-2 text-slate-400">{(o.paidAt || '').slice(0, 16)}</td>
                <td className="px-3 py-2"><StatusBadge status={o.settlementStatus || 'PENDING'} /></td>
                <td className="px-3 py-2 text-[10px] font-mono text-slate-400">{o.settlementUTR || '-'}</td>
                <td className="px-3 py-2 text-slate-400">{(o.settledAt || '-').slice(0, 16)}</td>
              </tr>
            ))}
            {!settlements.length && <tr><td colSpan={8} className="px-4 py-8 text-center text-slate-500">No settlements</td></tr>}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// ─── ORDER DRILLDOWN ────────────────────────────────────
function OrderDrilldown({ orderId, onBack }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    (async () => {
      try {
        const { data: d } = await api.get(`/api/admin/payments/orders/${orderId}`);
        setData(d);
      } catch (e) {
        toast.error('Failed to load order');
      }
      setLoading(false);
    })();
  }, [orderId]);

  if (loading) return <div className="text-slate-400 text-center py-8">Loading...</div>;
  if (!data) return <div className="text-red-400 text-center py-8">Order not found</div>;

  const { order, user: u, cashfree: cf, webhooks, credit_transactions: txns, mismatches } = data;

  return (
    <div className="space-y-4" data-testid="order-drilldown">
      <div className="flex items-center gap-3">
        <button onClick={onBack} className="text-slate-400 hover:text-white"><ArrowLeft className="w-4 h-4" /></button>
        <h3 className="text-sm font-bold text-white">Order: {orderId}</h3>
        <EnvBadge env={data.environment} />
      </div>

      {/* Mismatches */}
      {mismatches.length > 0 && (
        <div className="bg-red-500/10 border border-red-500/30 rounded-xl p-3" data-testid="mismatch-alert">
          <div className="flex items-center gap-2 mb-2">
            <AlertTriangle className="w-4 h-4 text-red-400" />
            <span className="text-xs font-bold text-red-400">{mismatches.length} Mismatch(es) Detected</span>
          </div>
          {mismatches.map((m, i) => (
            <span key={i} className="inline-block mr-2 mb-1 px-2 py-0.5 bg-red-500/20 text-red-300 text-[10px] font-mono rounded">{m}</span>
          ))}
        </div>
      )}

      {/* 4 Panels */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
        {/* Panel 1: Business View */}
        <div className="bg-slate-800/50 border border-slate-700/50 rounded-xl p-3">
          <h4 className="text-xs font-semibold text-indigo-400 mb-2 flex items-center gap-1"><FileText className="w-3 h-3" /> Business View</h4>
          <div className="space-y-1 text-xs">
            <Row label="User" value={u?.email || order?.userEmail} />
            <Row label="Product" value={`${order?.productName} (${order?.productType})`} />
            <Row label="Amount" value={`${order?.displayAmount} ${order?.currency}`} />
            <Row label="DB Status" value={order?.status} badge />
            <Row label="Entitlement" value={order?.entitlementApplied ? 'GRANTED' : 'NOT GRANTED'} color={order?.entitlementApplied ? 'text-emerald-400' : 'text-red-400'} />
            <Row label="User Credits" value={u?.credits} />
            <Row label="Subscription" value={u?.subscription ? `${u.subscription.planName} (${u.subscription.status})` : 'None'} />
            <Row label="Created" value={(order?.createdAt || '').slice(0, 19)} />
          </div>
        </div>

        {/* Panel 2: Cashfree Truth */}
        <div className="bg-slate-800/50 border border-slate-700/50 rounded-xl p-3">
          <h4 className="text-xs font-semibold text-amber-400 mb-2 flex items-center gap-1"><ExternalLink className="w-3 h-3" /> Cashfree Truth (Live)</h4>
          {cf?.error && <p className="text-[10px] text-red-400 mb-2">{cf.error}</p>}
          {cf?.order ? (
            <div className="space-y-1 text-xs">
              <Row label="CF Status" value={cf.order.order_status} badge />
              <Row label="CF Order ID" value={cf.order.cf_order_id} mono />
              <Row label="Amount" value={`${cf.order.order_amount} ${cf.order.order_currency}`} />
              <Row label="Created" value={(cf.order.created_at || '').slice(0, 19)} />
            </div>
          ) : <p className="text-xs text-slate-500">Could not fetch from Cashfree</p>}

          {cf?.payments?.length > 0 && (
            <div className="mt-2 border-t border-slate-700/40 pt-2">
              <p className="text-[10px] text-slate-400 font-medium mb-1">Payment Attempts ({cf.payments.length})</p>
              {cf.payments.map((p, i) => (
                <div key={i} className="flex items-center gap-2 text-[10px] mb-1">
                  <StatusBadge status={p.payment_status} />
                  <span className="text-slate-400">{p.payment_amount}</span>
                  <span className="text-slate-500">{(p.payment_time || '').slice(0, 19)}</span>
                  <span className="text-slate-600 font-mono">{(p.cf_payment_id || '').slice(-10)}</span>
                </div>
              ))}
            </div>
          )}

          {cf?.settlements?.length > 0 && (
            <div className="mt-2 border-t border-slate-700/40 pt-2">
              <p className="text-[10px] text-slate-400 font-medium mb-1">Settlements</p>
              {cf.settlements.map((s, i) => (
                <div key={i} className="text-[10px] text-slate-300 mb-1">
                  <span className="text-emerald-400">{s.settlement_amount}</span>
                  <span className="text-slate-500 mx-1">UTR: {s.transfer_utr || 'pending'}</span>
                  <span className="text-slate-600">{(s.transfer_time || '').slice(0, 19)}</span>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Panel 3: Webhook Trace */}
        <div className="bg-slate-800/50 border border-slate-700/50 rounded-xl p-3">
          <h4 className="text-xs font-semibold text-purple-400 mb-2 flex items-center gap-1"><Webhook className="w-3 h-3" /> Webhook Trace</h4>
          {webhooks?.length ? webhooks.map((w, i) => (
            <div key={i} className="mb-2 border-b border-slate-700/30 pb-2 last:border-0 text-[10px]">
              <div className="flex items-center gap-2 mb-1">
                <StatusBadge status={w.status} />
                <span className="text-slate-400">{w.eventType}</span>
                {w.signatureVerified === true && <CheckCircle2 className="w-3 h-3 text-emerald-400" />}
                {w.signatureVerified === false && <XCircle className="w-3 h-3 text-red-400" />}
              </div>
              <Row label="Event ID" value={w.eventId} mono />
              <Row label="Received" value={(w.receivedAt || '').slice(0, 19)} />
              {w.payloadHash && <Row label="Hash" value={(w.payloadHash || '').slice(0, 16) + '...'} mono />}
            </div>
          )) : <p className="text-xs text-slate-500">No webhooks received for this order</p>}
        </div>

        {/* Panel 4: Credit Transactions */}
        <div className="bg-slate-800/50 border border-slate-700/50 rounded-xl p-3">
          <h4 className="text-xs font-semibold text-emerald-400 mb-2 flex items-center gap-1"><DollarSign className="w-3 h-3" /> Credit Transactions</h4>
          {txns?.length ? txns.map((t, i) => (
            <div key={i} className="flex items-center gap-2 text-[10px] mb-1.5">
              <span className="text-emerald-400 font-medium">+{t.amount}</span>
              <span className="text-slate-400 flex-1">{t.description}</span>
              <span className="text-slate-500">{(t.created_at || '').slice(0, 16)}</span>
            </div>
          )) : <p className="text-xs text-slate-500">No credit transactions for this order</p>}
        </div>
      </div>
    </div>
  );
}

function Row({ label, value, badge, color, mono }) {
  return (
    <div className="flex items-center justify-between">
      <span className="text-slate-500">{label}</span>
      {badge ? <StatusBadge status={value} /> :
        <span className={`${mono ? 'font-mono text-[10px]' : ''} ${color || 'text-white'}`}>{value ?? '-'}</span>}
    </div>
  );
}

// ─── MAIN DASHBOARD ─────────────────────────────────────
export default function PaymentsDashboard() {
  const [tab, setTab] = useState('orders');
  const [stats, setStats] = useState(null);
  const [drilldownId, setDrilldownId] = useState(null);
  const navigate = useNavigate();

  useEffect(() => {
    (async () => {
      try {
        const { data } = await api.get('/api/admin/payments/stats');
        setStats(data);
      } catch { /* ignore */ }
    })();
  }, []);

  const TABS = [
    { id: 'orders', label: 'Orders', icon: FileText },
    { id: 'webhooks', label: 'Webhooks', icon: Webhook },
    { id: 'reconciliation', label: 'Reconciliation', icon: Scale },
    { id: 'settlements', label: 'Settlements', icon: DollarSign },
    { id: 'health', label: 'Health', icon: Activity },
  ];

  if (drilldownId) {
    return (
      <div className="min-h-screen bg-slate-950 p-4 lg:p-6">
        <OrderDrilldown orderId={drilldownId} onBack={() => setDrilldownId(null)} />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-950 p-4 lg:p-6" data-testid="payments-dashboard">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <button onClick={() => navigate('/app/admin')} className="text-slate-400 hover:text-white">
            <ArrowLeft className="w-4 h-4" />
          </button>
          <h1 className="text-lg font-bold text-white">Payment Verification</h1>
          {stats && <EnvBadge env={stats.environment} />}
        </div>
        <div className="flex items-center gap-2">
          {stats && !stats.cashfree_configured && (
            <span className="text-[10px] text-red-400 flex items-center gap-1"><AlertTriangle className="w-3 h-3" /> Cashfree NOT configured</span>
          )}
        </div>
      </div>

      {/* Stats Strip */}
      {stats && (
        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-8 gap-2 mb-4" data-testid="stats-strip">
          <StatCard label="Orders Today" value={stats.orders_today} icon={FileText} />
          <StatCard label="Succeeded" value={stats.succeeded_today} icon={CheckCircle2} color="text-emerald-400" />
          <StatCard label="Failed" value={stats.failed_today} icon={XCircle} color="text-red-400" alert={stats.failed_today > 0} />
          <StatCard label="Webhooks" value={stats.webhook_events_today} icon={Webhook} />
          <StatCard label="WH Failures" value={stats.webhook_failures_today} icon={AlertTriangle} color="text-red-400" alert={stats.webhook_failures_today > 0} />
          <StatCard label="Unreconciled" value={stats.unreconciled_orders} icon={Scale} color="text-amber-400" alert={stats.unreconciled_orders > 0} />
          <StatCard label="Settle Pending" value={stats.settlements_pending} icon={Clock} color="text-amber-400" />
          <StatCard label="Revenue Today" value={`${stats.revenue_today}`} icon={DollarSign} color="text-emerald-400" />
        </div>
      )}

      {/* Tabs */}
      <div className="flex gap-1 mb-4 bg-slate-900/60 rounded-xl p-1 overflow-x-auto">
        {TABS.map(t => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            className={`flex items-center gap-1.5 px-3 py-2 rounded-lg text-xs font-medium transition-colors whitespace-nowrap ${
              tab === t.id ? 'bg-indigo-500/20 text-indigo-300' : 'text-slate-500 hover:text-slate-300'
            }`}
            data-testid={`tab-${t.id}`}
          >
            <t.icon className="w-3.5 h-3.5" />
            {t.label}
            {t.id === 'reconciliation' && stats?.unreconciled_orders > 0 && (
              <span className="w-4 h-4 rounded-full bg-red-500 text-[8px] text-white flex items-center justify-center font-bold">{stats.unreconciled_orders}</span>
            )}
          </button>
        ))}
      </div>

      {/* Tab Content */}
      <div>
        {tab === 'orders' && <OrdersTab onDrilldown={setDrilldownId} />}
        {tab === 'webhooks' && <WebhooksTab />}
        {tab === 'reconciliation' && <ReconciliationTab onDrilldown={setDrilldownId} />}
        {tab === 'settlements' && <SettlementsTab />}
        {tab === 'health' && (
          <div className="bg-slate-800/50 border border-slate-700/50 rounded-xl p-4 text-center">
            <BarChart3 className="w-8 h-8 text-slate-500 mx-auto mb-2" />
            <p className="text-sm text-slate-400">Health charts will populate with real transaction volume</p>
            <p className="text-xs text-slate-600 mt-1">Current: {stats?.orders_today || 0} orders today, {stats?.succeeded_today || 0} succeeded</p>
          </div>
        )}
      </div>
    </div>
  );
}
