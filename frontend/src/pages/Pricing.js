import React, { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Button } from '../components/ui/button';
import { paymentAPI } from '../utils/api';
import { toast } from 'sonner';
import { Check, Sparkles, ArrowLeft, Loader2, RefreshCw } from 'lucide-react';

export default function Pricing() {
  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState({});
  const [selectedCurrency, setSelectedCurrency] = useState('INR');
  const [exchangeRates, setExchangeRates] = useState({ INR: 1, USD: 0.012, EUR: 0.011, GBP: 0.0095 });
  const [isLiveRate, setIsLiveRate] = useState(false);
  const navigate = useNavigate();

  const currencySymbols = {
    INR: '₹',
    USD: '$',
    EUR: '€',
    GBP: '£'
  };

  const getConvertedPrice = (priceInr) => {
    const rate = exchangeRates[selectedCurrency] || 1;
    const converted = Math.ceil(priceInr * rate);
    return converted;
  };

  useEffect(() => {
    fetchProducts();
    fetchExchangeRates();
  }, []);

  const fetchProducts = async () => {
    try {
      const response = await paymentAPI.getProducts();
      // Handle both array and object formats from API
      const productsData = response.data.products;
      if (Array.isArray(productsData)) {
        setProducts(productsData);
      } else if (productsData && typeof productsData === 'object') {
        // Convert object to array with id from key
        const productsArray = Object.entries(productsData).map(([id, product]) => ({
          id,
          ...product,
          priceInr: product.price || product.priceInr,
          type: product.period ? 'SUBSCRIPTION' : 'CREDIT_PACK'
        }));
        setProducts(productsArray);
      } else {
        setProducts([]);
      }
    } catch (error) {
      console.log('Not authenticated, showing empty products');
      setProducts([]);
    }
  };

  const fetchExchangeRates = async () => {
    try {
      const response = await paymentAPI.getCurrencies();
      if (response.data.success && response.data.currencies) {
        const { rates, isLiveRate } = response.data.currencies;
        if (rates) {
          setExchangeRates(rates);
          setIsLiveRate(isLiveRate);
        }
      }
    } catch (error) {
      console.log('Using fallback exchange rates');
    }
  };

  const handlePurchase = async (productId) => {
    const token = localStorage.getItem('token');
    if (!token) {
      toast.error('Please login to purchase');
      navigate('/login');
      return;
    }

    setLoading({...loading, [productId]: true});
    try {
      const response = await paymentAPI.createOrder(productId, selectedCurrency);
      
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
            toast.success('Payment successful! Credits added to your account.');
            // Store that user has purchased
            localStorage.setItem('has_purchased', 'true');
            navigate('/app');
          } catch (error) {
            toast.error('Payment verification failed');
          }
        },
        prefill: {
          email: localStorage.getItem('userEmail') || ''
        },
        theme: { color: '#6366f1' }
      };

      const rzp = new window.Razorpay(options);
      rzp.on('payment.failed', function (response) {
        toast.error('Payment failed: ' + response.error.description);
      });
      rzp.open();
    } catch (error) {
      toast.error('Failed to create order. Please login first.');
    } finally {
      setLoading({...loading, [productId]: false});
    }
  };

  const subscriptions = products.filter(p => p.type === 'SUBSCRIPTION');
  const packs = products.filter(p => p.type === 'CREDIT_PACK');

  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-950 via-indigo-950 to-slate-950">
      <div className="max-w-7xl mx-auto px-4 py-12">
        <Link to="/">
          <Button variant="ghost" className="text-white hover:bg-white/10 mb-8">
            <ArrowLeft className="w-4 h-4 mr-2" />
            Back to Home
          </Button>
        </Link>

        <div className="text-center mb-16">
          <div className="inline-flex items-center gap-2 bg-indigo-500/10 border border-indigo-500/20 rounded-full px-6 py-2 mb-6">
            <Sparkles className="w-4 h-4 text-indigo-400" />
            <span className="text-indigo-400 text-sm font-medium">Simple, Transparent Pricing</span>
          </div>
          <h1 className="text-5xl font-bold text-white mb-4">Choose Your Plan</h1>
          <p className="text-xl text-slate-300 max-w-2xl mx-auto mb-6">
            Start with 100 free credits. Buy more as you need or subscribe for better value.
          </p>
          
          {/* Currency Selector */}
          <div className="flex items-center justify-center gap-4">
            <span className="text-slate-400 text-sm">Select Currency:</span>
            <div className="flex gap-2 bg-white/10 rounded-full p-1">
              {['INR', 'USD', 'EUR', 'GBP'].map((currency) => (
                <button
                  key={currency}
                  onClick={() => setSelectedCurrency(currency)}
                  className={`px-4 py-2 rounded-full text-sm font-medium transition-all ${
                    selectedCurrency === currency 
                      ? 'bg-indigo-500 text-white' 
                      : 'text-slate-300 hover:text-white'
                  }`}
                  data-testid={`currency-${currency}-btn`}
                >
                  {currencySymbols[currency]} {currency}
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Subscriptions */}
        <div className="mb-16">
          <h2 className="text-3xl font-bold text-white text-center mb-8">Monthly Subscriptions</h2>
          <div className="grid md:grid-cols-3 gap-6">
            {subscriptions.map((product) => (
              <div key={product.id} className="bg-white/10 backdrop-blur-lg border border-white/20 rounded-2xl p-8 hover:border-indigo-500/50 transition-all">
                <h3 className="text-2xl font-bold text-white mb-2">{product.name}</h3>
                <div className="flex items-baseline gap-2 mb-6">
                  <span className="text-4xl font-bold text-white">
                    {currencySymbols[selectedCurrency]}{selectedCurrency === 'INR' ? product.priceInr : getConvertedPrice(product.priceInr)}
                  </span>
                  <span className="text-slate-400">/month</span>
                </div>
                <div className="bg-indigo-500/20 rounded-lg px-4 py-2 mb-6">
                  <p className="text-indigo-300 font-semibold">{product.credits} Credits</p>
                </div>
                <Button 
                  onClick={() => handlePurchase(product.id)} 
                  disabled={loading[product.id]}
                  className="w-full bg-indigo-500 hover:bg-indigo-600 rounded-full" 
                  data-testid={`subscribe-${product.id}-btn`}
                >
                  {loading[product.id] ? (
                    <><Loader2 className="w-4 h-4 mr-2 animate-spin" />Processing...</>
                  ) : 'Subscribe Now'}
                </Button>
              </div>
            ))}
          </div>
        </div>

        {/* Credit Packs */}
        <div>
          <h2 className="text-3xl font-bold text-white text-center mb-8">One-Time Credit Packs</h2>
          <div className="grid md:grid-cols-3 gap-6">
            {packs.map((product) => (
              <div key={product.id} className="bg-white/10 backdrop-blur-lg border border-white/20 rounded-2xl p-8 hover:border-purple-500/50 transition-all">
                <h3 className="text-2xl font-bold text-white mb-2">{product.name}</h3>
                <div className="flex items-baseline gap-2 mb-6">
                  <span className="text-4xl font-bold text-white">
                    {currencySymbols[selectedCurrency]}{selectedCurrency === 'INR' ? product.priceInr : getConvertedPrice(product.priceInr)}
                  </span>
                </div>
                <div className="bg-purple-500/20 rounded-lg px-4 py-2 mb-6">
                  <p className="text-purple-300 font-semibold">{product.credits} Credits</p>
                </div>
                <Button 
                  onClick={() => handlePurchase(product.id)} 
                  disabled={loading[product.id]}
                  className="w-full bg-purple-500 hover:bg-purple-600 rounded-full" 
                  data-testid={`buy-pack-${product.id}-btn`}
                >
                  {loading[product.id] ? (
                    <><Loader2 className="w-4 h-4 mr-2 animate-spin" />Processing...</>
                  ) : 'Buy Now'}
                </Button>
              </div>
            ))}
          </div>
        </div>

        {/* Credit Usage */}
        <div className="mt-16 bg-white/5 backdrop-blur-lg border border-white/10 rounded-2xl p-8">
          <h3 className="text-2xl font-bold text-white mb-6 text-center">How Credits Work</h3>
          <div className="grid md:grid-cols-2 gap-6">
            <div className="flex gap-4">
              <div className="w-12 h-12 bg-indigo-500/20 rounded-lg flex items-center justify-center flex-shrink-0">
                <Check className="w-6 h-6 text-indigo-400" />
              </div>
              <div>
                <h4 className="text-white font-semibold mb-2">Reel Generation</h4>
                <p className="text-slate-400">10 credits per full reel script with hooks, captions, and hashtags</p>
              </div>
            </div>
            <div className="flex gap-4">
              <div className="w-12 h-12 bg-purple-500/20 rounded-lg flex items-center justify-center flex-shrink-0">
                <Check className="w-6 h-6 text-purple-400" />
              </div>
              <div>
                <h4 className="text-white font-semibold mb-2">Story Pack</h4>
                <p className="text-slate-400">10 credits per story (any scene count)</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}