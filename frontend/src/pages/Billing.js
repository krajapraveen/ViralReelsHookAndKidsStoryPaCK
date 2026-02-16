import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { Button } from '../components/ui/button';
import { paymentAPI, creditAPI } from '../utils/api';
import { toast } from 'sonner';
import { Sparkles, Coins, ArrowLeft, Check } from 'lucide-react';

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
      // API returns { success: true, products: [...] }
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
      
      const options = {
        key: response.data.keyId,
        amount: response.data.amount,
        currency: response.data.currency,
        order_id: response.data.orderId,
        name: 'CreatorStudio AI',
        description: 'Credits Purchase',
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
        theme: { color: '#6366f1' }
      };

      const rzp = new window.Razorpay(options);
      rzp.open();
    } catch (error) {
      toast.error('Failed to create order');
    } finally {
      setLoading({...loading, [productId]: false});
    }
  };

  const subscriptions = products.filter(p => p.type === 'SUBSCRIPTION');
  const packs = products.filter(p => p.type === 'ONE_TIME');

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
        <div className="mb-12"><h2 className="text-3xl font-bold mb-8">Monthly Subscriptions</h2>
          <div className="grid md:grid-cols-3 gap-6">
            {subscriptions.map((product) => (
              <div key={product.id} className="bg-white border-2 border-slate-200 rounded-xl p-6 hover:border-indigo-500 transition-all">
                <h3 className="text-xl font-bold mb-2">{product.name}</h3>
                <div className="flex items-baseline gap-2 mb-4"><span className="text-3xl font-bold">₹{product.price}</span><span className="text-slate-500">/month</span></div>
                <div className="bg-indigo-50 rounded-lg px-4 py-2 mb-4"><p className="text-indigo-700 font-semibold">{product.credits} Credits</p></div>
                <Button onClick={() => handlePurchase(product.id)} disabled={loading[product.id]} className="w-full bg-indigo-500 hover:bg-indigo-600" data-testid={`buy-${product.id}-btn`}>
                  {loading[product.id] ? 'Processing...' : 'Subscribe'}
                </Button>
              </div>
            ))}
          </div>
        </div>

        <div><h2 className="text-3xl font-bold mb-8">Credit Packs</h2>
          <div className="grid md:grid-cols-3 gap-6">
            {packs.map((product) => (
              <div key={product.id} className="bg-white border-2 border-slate-200 rounded-xl p-6 hover:border-purple-500 transition-all">
                <h3 className="text-xl font-bold mb-2">{product.name}</h3>
                <div className="flex items-baseline gap-2 mb-4"><span className="text-3xl font-bold">₹{product.price}</span></div>
                <div className="bg-purple-50 rounded-lg px-4 py-2 mb-4"><p className="text-purple-700 font-semibold">{product.credits} Credits</p></div>
                <Button onClick={() => handlePurchase(product.id)} disabled={loading[product.id]} className="w-full bg-purple-500 hover:bg-purple-600" data-testid={`buy-pack-${product.id}-btn`}>
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