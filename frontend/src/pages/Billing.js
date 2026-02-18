import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { Button } from '../components/ui/button';
import { paymentAPI, creditAPI } from '../utils/api';
import { toast } from 'sonner';
import { Sparkles, Coins, ArrowLeft, Check, Star, Zap } from 'lucide-react';

export default function Billing() {
  const [products, setProducts] = useState([]);
  const [credits, setCredits] = useState(0);
  const [loading, setLoading] = useState({});

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      const [productsRes, creditsRes] = await Promise.all([
        paymentAPI.getProducts(),
        creditAPI.getBalance()
      ]);
      
      // Convert products object to array with id and type
      const productsData = productsRes?.data?.products || {};
      const productsArray = Object.entries(productsData).map(([id, product]) => ({
        id,
        ...product,
        type: product.period ? 'SUBSCRIPTION' : 'ONE_TIME',
        interval: product.period === 'quarterly' ? 'quarter' : product.period === 'yearly' ? 'year' : null
      }));
      
      setProducts(productsArray);
      setCredits(creditsRes?.data?.balance || 0);
    } catch (error) {
      console.error('Billing fetch error:', error);
      toast.error('Failed to load billing data');
    }
  };

  const handlePurchase = async (productId) => {
    setLoading({...loading, [productId]: true});
    try {
      // Use Cashfree API
      const response = await api.post('/api/cashfree/create-order', { productId, currency: 'INR' });
      
      if (!response.data.paymentSessionId) {
        toast.error('Payment configuration error. Please contact support.');
        return;
      }
      
      // Load Cashfree checkout
      const cashfree = await loadCashfreeCheckout();
      
      if (cashfree) {
        const checkoutOptions = {
          paymentSessionId: response.data.paymentSessionId,
          redirectTarget: "_modal"
        };
        
        cashfree.checkout(checkoutOptions).then(async (result) => {
          if (result.error) {
            toast.error('Payment failed: ' + result.error.message);
          } else if (result.paymentDetails) {
            // Verify payment
            try {
              const verifyRes = await api.post('/api/cashfree/verify', { order_id: response.data.orderId });
              if (verifyRes.data.success) {
                toast.success(`Payment successful! ${verifyRes.data.creditsAdded} credits added.`);
                fetchData();
              } else {
                toast.info(verifyRes.data.message || 'Payment is being processed');
              }
            } catch (e) {
              toast.error('Payment verification failed');
            }
          }
        });
      }
    } catch (error) {
      console.error('Order creation error:', error);
      toast.error(error.response?.data?.detail || 'Failed to create order');
    } finally {
      setLoading({...loading, [productId]: false});
    }
  };
  
  // Load Cashfree checkout script
  const loadCashfreeCheckout = () => {
    return new Promise((resolve) => {
      if (window.Cashfree) {
        resolve(window.Cashfree({ mode: "production" }));
        return;
      }
      
      const script = document.createElement('script');
      script.src = 'https://sdk.cashfree.com/js/v3/cashfree.js';
      script.onload = () => {
        resolve(window.Cashfree({ mode: "production" }));
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
      case 'month': return '/month';
      case 'quarter': return '/quarter';
      case 'year': return '/year';
      default: return '/month';
    }
  };

  const getBorderColor = (product) => {
    if (product.id === 'yearly') return 'border-amber-400 ring-2 ring-amber-400/30';
    if (product.id === 'quarterly') return 'border-indigo-400';
    return 'border-slate-700';
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-indigo-950 to-slate-900">
      <header className="bg-slate-900/80 backdrop-blur-md border-b border-slate-700/50 sticky top-0 z-40">
        <div className="max-w-7xl mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Link to="/app"><Button variant="ghost" size="sm" className="text-slate-300 hover:text-white hover:bg-slate-800"><ArrowLeft className="w-4 h-4 mr-2" />Dashboard</Button></Link>
            <div className="flex items-center gap-2"><Sparkles className="w-6 h-6 text-indigo-400" /><span className="text-xl font-bold text-white">Billing</span></div>
          </div>
          <div className="flex items-center gap-2 bg-indigo-500/20 border border-indigo-500/30 rounded-full px-4 py-2"><Coins className="w-4 h-4 text-indigo-400" /><span className="font-semibold text-indigo-300">{credits} Credits</span></div>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-4 py-8">
        {/* Subscriptions Section */}
        <div className="mb-12">
          <h2 className="text-3xl font-bold mb-2 text-white">Subscription Plans</h2>
          <p className="text-slate-400 mb-8">Save more with longer commitments</p>
          <div className="grid md:grid-cols-3 gap-6">
            {subscriptions.map((product) => (
              <div key={product.id} className={`bg-slate-800/50 backdrop-blur-sm border-2 ${getBorderColor(product)} rounded-xl p-6 hover:shadow-lg hover:shadow-indigo-500/10 transition-all relative`}>
                {product.savings && (
                  <div className="absolute -top-3 right-4 bg-gradient-to-r from-amber-400 to-orange-500 text-white text-xs font-bold px-3 py-1 rounded-full flex items-center gap-1">
                    <Star className="w-3 h-3" /> Save {product.savings}
                  </div>
                )}
                {product.id === 'yearly' && (
                  <div className="absolute -top-3 left-4 bg-gradient-to-r from-indigo-500 to-purple-600 text-white text-xs font-bold px-3 py-1 rounded-full flex items-center gap-1">
                    <Zap className="w-3 h-3" /> Best Value
                  </div>
                )}
                <h3 className="text-xl font-bold mb-2 text-white">{product.name}</h3>
                <div className="flex items-baseline gap-2 mb-4">
                  <span className="text-3xl font-bold text-white">₹{product.price}</span>
                  <span className="text-slate-400">{getIntervalLabel(product.interval)}</span>
                </div>
                <div className="bg-indigo-500/20 border border-indigo-500/30 rounded-lg px-4 py-2 mb-4">
                  <p className="text-indigo-300 font-semibold">{product.credits} Credits</p>
                  {product.interval === 'quarter' && <p className="text-xs text-indigo-400">~117 credits/month</p>}
                  {product.interval === 'year' && <p className="text-xs text-indigo-400">~125 credits/month</p>}
                </div>
                <ul className="text-sm text-slate-300 mb-4 space-y-2">
                  <li className="flex items-center gap-2"><Check className="w-4 h-4 text-emerald-400" /> Auto-renewal</li>
                  <li className="flex items-center gap-2"><Check className="w-4 h-4 text-emerald-400" /> Priority support</li>
                  {product.id === 'yearly' && <li className="flex items-center gap-2"><Check className="w-4 h-4 text-emerald-400" /> Early feature access</li>}
                </ul>
                <Button 
                  onClick={() => handlePurchase(product.id)} 
                  disabled={loading[product.id]} 
                  className={`w-full ${product.id === 'yearly' ? 'bg-gradient-to-r from-amber-500 to-orange-500 hover:from-amber-600 hover:to-orange-600' : 'bg-indigo-600 hover:bg-indigo-700'}`} 
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
          <div className="grid md:grid-cols-3 gap-6">
            {packs.map((product) => (
              <div key={product.id} className="bg-slate-800/50 backdrop-blur-sm border-2 border-slate-700 rounded-xl p-6 hover:border-purple-500 hover:shadow-lg hover:shadow-purple-500/10 transition-all">
                <h3 className="text-xl font-bold mb-2 text-white">{product.name}</h3>
                <div className="flex items-baseline gap-2 mb-4">
                  <span className="text-3xl font-bold text-white">₹{product.price}</span>
                  <span className="text-slate-400 text-sm">one-time</span>
                </div>
                <div className="bg-purple-500/20 border border-purple-500/30 rounded-lg px-4 py-2 mb-4">
                  <p className="text-purple-300 font-semibold">{product.credits} Credits</p>
                  <p className="text-xs text-purple-400">₹{(product.price / product.credits).toFixed(1)}/credit</p>
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
      </div>
    </div>
  );
}
