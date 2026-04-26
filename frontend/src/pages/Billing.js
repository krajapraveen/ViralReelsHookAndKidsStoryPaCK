import React, { useState, useEffect, useCallback } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { Button } from '../components/ui/button';
import { Coins, Sparkles, Check, Star, Zap, ArrowLeft, Loader2, AlertCircle, RefreshCw } from 'lucide-react';
import { toast } from 'sonner';
import api, { paymentAPI, creditAPI } from '../utils/api';
import HelpGuide from '../components/HelpGuide';
import analytics from '../utils/analytics';
import { trackFunnel } from '../utils/funnelTracker';
import { triggerPurchaseSurvey } from './PurchaseSurvey';

export default function Billing() {
  const [products, setProducts] = useState([]);
  const [credits, setCredits] = useState(0);
  const [loading, setLoading] = useState({});
  const [pageLoading, setPageLoading] = useState(true);
  const [pageError, setPageError] = useState(false);
  const [verifyingReturn, setVerifyingReturn] = useState(false);
  const [searchParams, setSearchParams] = useSearchParams();

  const fetchData = useCallback(async () => {
    setPageLoading(true);
    setPageError(false);
    try {
      const [productsRes, creditsRes] = await Promise.all([
        paymentAPI.getProducts(),
        creditAPI.getBalance()
      ]);
      
      const productsData = productsRes?.data?.products || {};
      const productsArray = Object.entries(productsData).map(([id, product]) => ({
        id,
        ...product,
        type: product.period ? 'SUBSCRIPTION' : 'ONE_TIME',
        interval: product.period === 'weekly' ? 'week' : 
                  product.period === 'monthly' ? 'month' : 
                  product.period === 'quarterly' ? 'quarter' : 
                  product.period === 'yearly' ? 'year' : null
      }));
      
      setProducts(productsArray);
      setCredits(creditsRes?.data?.credits || creditsRes?.data?.balance || 0);
    } catch (error) {
      console.error('Billing fetch error:', error);
      setPageError(true);
      toast.error('Failed to load billing data');
    } finally {
      setPageLoading(false);
    }
  }, []);

  // Auto-verify payment on return from Cashfree redirect (mobile/popup-blocked fallback)
  useEffect(() => {
    const orderId = searchParams.get('order_id');
    const gateway = searchParams.get('gateway');
    if (orderId && gateway === 'cashfree') {
      setVerifyingReturn(true);
      api.post('/api/cashfree/verify', { order_id: orderId })
        .then(res => {
          if (res.data.success) {
            toast.success(`Payment successful! ${res.data.creditsAdded} credits added.`);
            trackFunnel('payment_success', { source_page: 'billing_return', meta: { order_id: orderId } });
            // P1.6 — fire post-payment micro-survey (one-question, one-tap).
            triggerPurchaseSurvey({ orderId, plan: null });
          } else {
            toast.info(res.data.message || 'Payment is being processed.');
          }
        })
        .catch(() => {
          toast.warning('Could not verify payment status. Your credits will appear shortly if payment was successful.');
        })
        .finally(() => {
          setVerifyingReturn(false);
          // Clean URL params
          setSearchParams({}, { replace: true });
          fetchData();
        });
    } else {
      fetchData();
    }
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const handlePurchase = async (productId) => {
    if (loading[productId]) return; // prevent double-click
    setLoading(prev => ({...prev, [productId]: true}));
    
    // Find product details for analytics
    const product = products.find(p => p.id === productId);
    const productName = product?.name || productId;
    const productPrice = product?.displayPrice || product?.price || 0;
    
    // Create item object for enhanced e-commerce
    const item = {
      id: productId,
      name: productName,
      price: productPrice,
      category: product?.type === 'SUBSCRIPTION' ? 'subscription' : 'credit_pack'
    };
    
    // Track checkout start with enhanced e-commerce and funnel
    analytics.trackBeginCheckout(item, 'INR');
    analytics.trackFunnelStep('checkout_start', { product_id: productId, product_name: productName });
    trackFunnel('payment_started', { source_page: 'billing', plan_selected: productId });
    
    try {
      // Use Cashfree API
      const response = await api.post('/api/cashfree/create-order', { productId, currency: 'INR' });
      
      if (!response.data.paymentSessionId) {
        toast.error('Payment configuration error. Please contact support.');
        setLoading(prev => ({...prev, [productId]: false}));
        return;
      }
      
      // Track add_payment_info when payment modal opens
      analytics.trackAddPaymentInfo(item, 'cashfree', 'INR');
      
      // Get the environment from backend response to ensure frontend matches
      const cashfreeEnv = response.data.environment === 'production' ? 'production' : 'sandbox';
      
      // Load Cashfree checkout with matching environment
      const cashfree = await loadCashfreeCheckout(cashfreeEnv);
      
      if (cashfree) {
        const checkoutOptions = {
          paymentSessionId: response.data.paymentSessionId,
          redirectTarget: "_modal"
        };
        
        cashfree.checkout(checkoutOptions).then(async (result) => {
          if (result.error) {
            // Detect cancel vs actual failure
            const msg = result.error.message || '';
            if (msg.includes('cancel') || msg.includes('closed') || msg.includes('dismiss')) {
              trackFunnel('payment_abandoned', { source_page: 'billing', plan_selected: productId });
              toast.info('Payment was cancelled. No charges were made.');
            } else {
              trackFunnel('payment_abandoned', { source_page: 'billing', plan_selected: productId, meta: { error: msg } });
              toast.error(`Payment did not complete: ${msg}. Please try again.`);
              analytics.trackError('payment_failed', msg, 'billing');
            }
          } else if (result.paymentDetails) {
            // Verify payment
            try {
              const verifyRes = await api.post('/api/cashfree/verify', { order_id: response.data.orderId });
              if (verifyRes.data.success) {
                analytics.trackPurchase(response.data.orderId, item, 'INR');
                analytics.trackFunnelStep('purchase_complete', { 
                  order_id: response.data.orderId, 
                  product_name: productName,
                  amount: productPrice 
                });
                analytics.trackFunnelComplete('main_conversion');
                trackFunnel('payment_success', { source_page: 'billing', plan_selected: productId, meta: { order_id: response.data.orderId } });
                // P1.6 — fire post-payment micro-survey (one-question, one-tap).
                triggerPurchaseSurvey({ orderId: response.data.orderId, plan: productId });
                toast.success(`Payment successful! ${verifyRes.data.creditsAdded} credits added to your account.`);
                fetchData();
              } else {
                toast.info(verifyRes.data.message || 'Payment is being processed. Credits will appear shortly.');
              }
            } catch (e) {
              toast.warning('Payment succeeded, but credits are still syncing. Please refresh in a moment.');
            }
          } else {
            // No error, no paymentDetails — user closed/cancelled
            toast.info('Payment window was closed. No charges were made.');
          }
        }).catch(() => {
          toast.info('Payment window was closed. No charges were made.');
        }).finally(() => {
          setLoading(prev => ({...prev, [productId]: false}));
        });
        return; // Don't reset loading in outer finally — the checkout promise handles it
      } else {
        toast.error('Unable to load payment gateway. Please try again in a few minutes.');
      }
    } catch (error) {
      const status = error.response?.status;
      const detail = error.response?.data?.detail;
      if (status === 503) {
        toast.error('Payment service is temporarily unavailable. Please try again in a few minutes.');
      } else if (status === 429) {
        toast.error('Too many payment attempts. Please wait a moment before trying again.');
      } else {
        toast.error(detail || 'Could not initiate payment. Please check your connection and try again.');
      }
      analytics.trackError('order_creation_failed', error.message, 'billing');
    }
    setLoading(prev => ({...prev, [productId]: false}));
  };
  
  // Load Cashfree checkout script with dynamic environment
  const loadCashfreeCheckout = (env = 'production') => {
    return new Promise((resolve) => {
      if (window.Cashfree) {
        resolve(window.Cashfree({ mode: env }));
        return;
      }
      
      const script = document.createElement('script');
      script.src = 'https://sdk.cashfree.com/js/v3/cashfree.js';
      script.onload = () => {
        resolve(window.Cashfree({ mode: env }));
      };
      script.onerror = () => {
        toast.error('Failed to load payment gateway');
        resolve(null);
      };
      document.body.appendChild(script);
    });
  };

  const subscriptions = Array.isArray(products) ? products.filter(p => p.type === 'SUBSCRIPTION') : [];
  const packs = Array.isArray(products) ? products.filter(p => p.type === 'ONE_TIME') : [];

  const getIntervalLabel = (interval) => {
    switch(interval) {
      case 'week': return '/week';
      case 'month': return '/month';
      case 'quarter': return '/quarter';
      case 'year': return '/year';
      default: return '';
    }
  };

  const getBorderColor = (product) => {
    if (product.id === 'yearly') return 'border-amber-400 ring-2 ring-amber-400/30';
    if (product.id === 'quarterly') return 'border-indigo-400';
    if (product.id === 'monthly') return 'border-purple-400';
    if (product.id === 'weekly') return 'border-blue-400';
    return 'border-slate-700';
  };

  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-950 via-indigo-950 to-slate-950">
      <header className="bg-slate-900/80 backdrop-blur-md border-b border-slate-700/50 sticky top-0 z-40 vs-page-header">
        <div className="max-w-7xl mx-auto px-3 sm:px-4 py-2.5 sm:py-4 flex items-center justify-between">
          <div className="flex items-center gap-2 sm:gap-4 min-w-0 vs-header-left">
            <Link to="/app"><Button variant="ghost" size="sm" className="text-slate-300 hover:text-white hover:bg-slate-800 flex-shrink-0"><ArrowLeft className="w-4 h-4 sm:mr-2" /><span className="hidden sm:inline">Dashboard</span></Button></Link>
            <div className="flex items-center gap-2 min-w-0"><Sparkles className="w-5 h-5 sm:w-6 sm:h-6 text-indigo-400 flex-shrink-0" /><span className="text-base sm:text-xl font-bold text-white truncate vs-header-title">Billing</span></div>
          </div>
          <div className="hidden sm:flex items-center gap-2 bg-indigo-500/20 border border-indigo-500/30 rounded-full px-4 py-2"><Coins className="w-4 h-4 text-indigo-400" /><span className="font-semibold text-indigo-300">{credits} Credits</span></div>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-4 py-8">
        {/* Return-from-payment verification */}
        {verifyingReturn && (
          <div className="flex items-center justify-center gap-3 py-12 mb-8 rounded-2xl border border-indigo-500/20 bg-indigo-500/[0.04]" data-testid="billing-verify-return">
            <Loader2 className="w-6 h-6 animate-spin text-indigo-400" />
            <span className="text-indigo-300 font-medium">Verifying your payment...</span>
          </div>
        )}

        {/* Page loading */}
        {pageLoading && !verifyingReturn && (
          <div className="flex items-center justify-center py-24" data-testid="billing-loading">
            <Loader2 className="w-8 h-8 animate-spin text-indigo-400" />
          </div>
        )}

        {/* Page error */}
        {pageError && !pageLoading && (
          <div className="text-center py-16 rounded-2xl border border-red-500/20 bg-red-500/[0.04] mb-8" data-testid="billing-error">
            <AlertCircle className="w-10 h-10 mx-auto mb-3 text-red-400" />
            <p className="text-sm text-slate-300 mb-1">Failed to load billing data</p>
            <p className="text-xs text-slate-500 mb-4">Check your connection and try again</p>
            <Button onClick={fetchData} variant="outline" className="border-red-500/30 text-red-300 hover:bg-red-500/10" data-testid="billing-retry-btn">
              <RefreshCw className="w-4 h-4 mr-2" /> Retry
            </Button>
          </div>
        )}

        {!pageLoading && !pageError && !verifyingReturn && (<>
        {/* Subscriptions Section */}
        <div className="mb-12">
          <h2 className="text-3xl font-bold mb-2 text-white">Subscription Plans</h2>
          <p className="text-slate-400 mb-8">Save more with longer commitments</p>
          <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {subscriptions.map((product) => (
              <div key={product.id} className={`bg-slate-800/50 backdrop-blur-sm border-2 ${getBorderColor(product)} rounded-xl p-5 hover:shadow-lg hover:shadow-indigo-500/10 transition-all relative`}>
                {product.savings && (
                  <div className="absolute -top-3 right-2 bg-gradient-to-r from-amber-400 to-orange-500 text-white text-xs font-bold px-2 py-1 rounded-full flex items-center gap-1">
                    <Star className="w-3 h-3" /> {product.savings}
                  </div>
                )}
                {product.id === 'yearly' && (
                  <div className="absolute -top-3 left-2 bg-gradient-to-r from-indigo-500 to-purple-600 text-white text-xs font-bold px-2 py-1 rounded-full flex items-center gap-1">
                    <Zap className="w-3 h-3" /> Best
                  </div>
                )}
                <h3 className="text-lg font-bold mb-2 text-white">{product.name}</h3>
                <div className="flex items-baseline gap-1 mb-3">
                  <span className="text-2xl font-bold text-white">₹{product.displayPrice || product.price}</span>
                  <span className="text-slate-400 text-sm">{getIntervalLabel(product.interval)}</span>
                </div>
                <div className="bg-indigo-500/20 border border-indigo-500/30 rounded-lg px-3 py-2 mb-3">
                  <p className="text-indigo-300 font-semibold text-sm">{product.credits} Credits</p>
                </div>
                <ul className="text-xs text-slate-300 mb-3 space-y-1">
                  <li className="flex items-center gap-1"><Check className="w-3 h-3 text-emerald-400" /> Auto-renewal</li>
                  <li className="flex items-center gap-1"><Check className="w-3 h-3 text-emerald-400" /> Priority support</li>
                </ul>
                <Button 
                  onClick={() => handlePurchase(product.id)} 
                  disabled={loading[product.id]} 
                  className={`w-full text-sm ${product.id === 'yearly' ? 'bg-gradient-to-r from-amber-500 to-orange-500 hover:from-amber-600 hover:to-orange-600' : 'bg-indigo-600 hover:bg-indigo-700'}`} 
                  data-testid={`buy-${product.id}-btn`}
                >
                  {loading[product.id] ? 'Processing...' : 'Subscribe'}
                </Button>
              </div>
            ))}
          </div>
        </div>

        {/* Credit Packs Section */}
        <div>
          <h2 className="text-3xl font-bold mb-2 text-white">Credit Packs</h2>
          <p className="text-slate-400 mb-8">One-time purchase, no commitment</p>
          <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {packs.map((product) => (
              <div key={product.id} className="bg-slate-800/50 backdrop-blur-sm border-2 border-slate-700 rounded-xl p-6 hover:border-purple-500 hover:shadow-lg hover:shadow-purple-500/10 transition-all">
                <h3 className="text-xl font-bold mb-2 text-white">{product.name}</h3>
                <div className="flex items-baseline gap-2 mb-4">
                  <span className="text-3xl font-bold text-white">₹{product.displayPrice || product.price}</span>
                  <span className="text-slate-400 text-sm">one-time</span>
                </div>
                <div className="bg-purple-500/20 border border-purple-500/30 rounded-lg px-4 py-2 mb-4">
                  <p className="text-purple-300 font-semibold">{product.credits} Credits</p>
                  <p className="text-xs text-purple-400">₹{((product.displayPrice || product.price || 0) / (product.credits || 1)).toFixed(1)}/credit</p>
                </div>
                <Button 
                  onClick={() => handlePurchase(product.id)} 
                  disabled={loading[product.id]} 
                  className="w-full bg-purple-600 hover:bg-purple-700" 
                  data-testid={`buy-pack-${product.id}-btn`}
                >
                  {loading[product.id] ? 'Processing...' : 'Buy Now'}
                </Button>
              </div>
            ))}
          </div>
        </div>
        </>)}
      </div>
      
      {/* Help Guide */}
      <HelpGuide pageId="billing" />
    </div>
  );
}
