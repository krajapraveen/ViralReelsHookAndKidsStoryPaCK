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
      setProducts(productsRes.data.products || []);
      setCredits(creditsRes.data.balance);
    } catch (error) {
      toast.error('Failed to load billing data');
    }
  };

  const handlePurchase = async (productId) => {
    setLoading({...loading, [productId]: true});
    try {
      const response = await paymentAPI.createOrder(productId);
      
      if (!response.data.keyId) {
        toast.error('Payment configuration error. Please contact support.');
        return;
      }
      
      const options = {
        key: response.data.keyId,
        amount: response.data.amount,
        currency: response.data.currency,
        order_id: response.data.orderId,
        name: 'CreatorStudio AI',
        description: response.data.productName,
        handler: async (paymentResponse) => {
          try {
            await paymentAPI.verifyPayment({
              razorpayOrderId: paymentResponse.razorpay_order_id,
              razorpayPaymentId: paymentResponse.razorpay_payment_id,
              razorpaySignature: paymentResponse.razorpay_signature
            });
            toast.success('Payment successful! Credits added.');
            fetchData();
          } catch (error) {
            toast.error('Payment verification failed');
          }
        },
        prefill: {
          name: '',
          email: '',
        },
        theme: { color: '#6366f1' }
      };

      const rzp = new window.Razorpay(options);
      rzp.on('payment.failed', function (response) {
        toast.error('Payment failed. Please try again.');
      });
      rzp.open();
    } catch (error) {
      console.error('Order creation error:', error);
      toast.error('Failed to create order');
    } finally {
      setLoading({...loading, [productId]: false});
    }
  };

  const subscriptions = products.filter(p => p.type === 'SUBSCRIPTION');
  const packs = products.filter(p => p.type === 'ONE_TIME');

  const getIntervalLabel = (interval) => {
    switch(interval) {
      case 'month': return '/month';
      case 'quarter': return '/quarter';
      case 'year': return '/year';
      default: return '/month';
    }
  };

  const getBorderColor = (product) => {
    if (product.id === 'yearly') return 'border-amber-400 ring-2 ring-amber-200';
    if (product.id === 'quarterly') return 'border-indigo-400';
    return 'border-slate-200';
  };

  return (
    <div className="min-h-screen bg-slate-50">
      <header className="bg-white border-b border-slate-200">
        <div className="max-w-7xl mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Link to="/app"><Button variant="ghost" size="sm"><ArrowLeft className="w-4 h-4 mr-2" />Dashboard</Button></Link>
            <div className="flex items-center gap-2"><Sparkles className="w-6 h-6 text-indigo-500" /><span className="text-xl font-bold">Billing</span></div>
          </div>
          <div className="flex items-center gap-2 bg-slate-100 rounded-full px-4 py-2"><Coins className="w-4 h-4 text-purple-500" /><span className="font-semibold">{credits} Credits</span></div>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-4 py-8">
        {/* Subscriptions Section */}
        <div className="mb-12">
          <h2 className="text-3xl font-bold mb-2">Subscription Plans</h2>
          <p className="text-slate-500 mb-8">Save more with longer commitments</p>
          <div className="grid md:grid-cols-3 gap-6">
            {subscriptions.map((product) => (
              <div key={product.id} className={`bg-white border-2 ${getBorderColor(product)} rounded-xl p-6 hover:shadow-lg transition-all relative`}>
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
                <h3 className="text-xl font-bold mb-2">{product.name}</h3>
                <div className="flex items-baseline gap-2 mb-4">
                  <span className="text-3xl font-bold">₹{product.price}</span>
                  <span className="text-slate-500">{getIntervalLabel(product.interval)}</span>
                </div>
                <div className="bg-indigo-50 rounded-lg px-4 py-2 mb-4">
                  <p className="text-indigo-700 font-semibold">{product.credits} Credits</p>
                  {product.interval === 'quarter' && <p className="text-xs text-indigo-500">~117 credits/month</p>}
                  {product.interval === 'year' && <p className="text-xs text-indigo-500">~125 credits/month</p>}
                </div>
                <ul className="text-sm text-slate-600 mb-4 space-y-2">
                  <li className="flex items-center gap-2"><Check className="w-4 h-4 text-green-500" /> Auto-renewal</li>
                  <li className="flex items-center gap-2"><Check className="w-4 h-4 text-green-500" /> Priority support</li>
                  {product.id === 'yearly' && <li className="flex items-center gap-2"><Check className="w-4 h-4 text-green-500" /> Early feature access</li>}
                </ul>
                <Button 
                  onClick={() => handlePurchase(product.id)} 
                  disabled={loading[product.id]} 
                  className={`w-full ${product.id === 'yearly' ? 'bg-gradient-to-r from-amber-500 to-orange-500 hover:from-amber-600 hover:to-orange-600' : 'bg-indigo-500 hover:bg-indigo-600'}`} 
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
          <h2 className="text-3xl font-bold mb-2">Credit Packs</h2>
          <p className="text-slate-500 mb-8">One-time purchase, no commitment</p>
          <div className="grid md:grid-cols-3 gap-6">
            {packs.map((product) => (
              <div key={product.id} className="bg-white border-2 border-slate-200 rounded-xl p-6 hover:border-purple-500 hover:shadow-lg transition-all">
                <h3 className="text-xl font-bold mb-2">{product.name}</h3>
                <div className="flex items-baseline gap-2 mb-4">
                  <span className="text-3xl font-bold">₹{product.price}</span>
                  <span className="text-slate-400 text-sm">one-time</span>
                </div>
                <div className="bg-purple-50 rounded-lg px-4 py-2 mb-4">
                  <p className="text-purple-700 font-semibold">{product.credits} Credits</p>
                  <p className="text-xs text-purple-500">₹{(product.price / product.credits).toFixed(1)}/credit</p>
                </div>
                <Button 
                  onClick={() => handlePurchase(product.id)} 
                  disabled={loading[product.id]} 
                  className="w-full bg-purple-500 hover:bg-purple-600" 
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
