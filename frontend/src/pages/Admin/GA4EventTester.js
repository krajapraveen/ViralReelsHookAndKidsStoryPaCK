import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { Button } from '../../components/ui/button';
import { 
  ArrowLeft, Send, CheckCircle, XCircle, RefreshCw, 
  Activity, BarChart3, Users, ShoppingCart, Download, 
  UserPlus, LogIn, Eye, MousePointer, FileText
} from 'lucide-react';
import analytics from '../../utils/analytics';

export default function GA4EventTester() {
  const [testResults, setTestResults] = useState([]);
  const [gaStatus, setGaStatus] = useState(null);

  const checkGAStatus = () => {
    const isLoaded = analytics.verifyGALoaded();
    setGaStatus(isLoaded);
    addResult('GA4 Status Check', isLoaded ? 'Google Analytics is loaded and ready' : 'Google Analytics is NOT loaded', isLoaded);
  };

  const addResult = (event, details, success) => {
    setTestResults(prev => [{
      id: Date.now(),
      event,
      details,
      success,
      timestamp: new Date().toLocaleTimeString()
    }, ...prev.slice(0, 19)]);
  };

  const testEvents = [
    {
      name: 'sign_up',
      icon: UserPlus,
      description: 'User registration event',
      action: () => {
        analytics.trackSignup('test');
        addResult('sign_up', 'Method: test', true);
      }
    },
    {
      name: 'login',
      icon: LogIn,
      description: 'User login event',
      action: () => {
        analytics.trackLogin('test');
        addResult('login', 'Method: test', true);
      }
    },
    {
      name: 'view_item_list',
      icon: Eye,
      description: 'View pricing/product list',
      action: () => {
        analytics.trackViewItemList('Test Products', [
          { id: 'test-1', name: 'Test Plan', price: 499, category: 'subscription' },
          { id: 'test-2', name: 'Credit Pack', price: 299, category: 'credit_pack' }
        ]);
        addResult('view_item_list', 'List: Test Products (2 items)', true);
      }
    },
    {
      name: 'view_item',
      icon: Eye,
      description: 'View single product',
      action: () => {
        analytics.trackViewItem({ id: 'test-1', name: 'Pro Plan', price: 999, currency: 'INR' });
        addResult('view_item', 'Item: Pro Plan (₹999)', true);
      }
    },
    {
      name: 'select_item',
      icon: MousePointer,
      description: 'Select/click product',
      action: () => {
        analytics.trackSelectItem('Pricing', { id: 'test-1', name: 'Pro Plan', price: 999 });
        addResult('select_item', 'Selected: Pro Plan from Pricing', true);
      }
    },
    {
      name: 'add_to_cart',
      icon: ShoppingCart,
      description: 'Add product to cart',
      action: () => {
        analytics.trackAddToCart({ id: 'test-1', name: 'Pro Plan', price: 999 }, 'INR');
        addResult('add_to_cart', 'Added: Pro Plan (₹999)', true);
      }
    },
    {
      name: 'begin_checkout',
      icon: ShoppingCart,
      description: 'Start checkout process',
      action: () => {
        analytics.trackBeginCheckout({ id: 'test-1', name: 'Pro Plan', price: 999 }, 'INR');
        addResult('begin_checkout', 'Checkout started: Pro Plan (₹999)', true);
      }
    },
    {
      name: 'add_payment_info',
      icon: ShoppingCart,
      description: 'Enter payment details',
      action: () => {
        analytics.trackAddPaymentInfo({ id: 'test-1', name: 'Pro Plan', price: 999 }, 'cashfree', 'INR');
        addResult('add_payment_info', 'Payment method: Cashfree', true);
      }
    },
    {
      name: 'purchase',
      icon: CheckCircle,
      description: 'Complete purchase',
      action: () => {
        analytics.trackPurchase('TEST-ORDER-123', { id: 'test-1', name: 'Pro Plan', price: 999 }, 'INR');
        addResult('purchase', 'Transaction: TEST-ORDER-123 (₹999)', true);
      }
    },
    {
      name: 'generate_content',
      icon: Activity,
      description: 'Content generation',
      action: () => {
        analytics.trackGeneration('gif_maker', 10);
        addResult('generate_content', 'Feature: gif_maker (10 credits)', true);
      }
    },
    {
      name: 'download',
      icon: Download,
      description: 'Content download',
      action: () => {
        analytics.trackDownload('gif', 'gif_maker');
        addResult('download', 'Type: gif from gif_maker', true);
      }
    },
    {
      name: 'blog_view',
      icon: FileText,
      description: 'Blog article view',
      action: () => {
        analytics.trackBlogView('test-article', 'Test Article Title', 'Test Category');
        addResult('blog_view', 'Article: test-article', true);
      }
    }
  ];

  const sendTestEvent = () => {
    const testId = analytics.sendTestEvent();
    addResult('test_event', `Test ID: ${testId}`, true);
  };

  const runAllTests = () => {
    checkGAStatus();
    setTimeout(() => {
      testEvents.forEach((test, index) => {
        setTimeout(() => test.action(), index * 200);
      });
    }, 500);
  };

  const clearResults = () => {
    setTestResults([]);
    setGaStatus(null);
  };

  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-950 via-indigo-950 to-slate-950 p-6">
      <div className="max-w-6xl mx-auto">
        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <div className="flex items-center gap-4">
            <Link to="/app/admin">
              <Button variant="ghost" className="text-white hover:bg-white/10">
                <ArrowLeft className="w-4 h-4 mr-2" />
                Back to Admin
              </Button>
            </Link>
            <div>
              <h1 className="text-2xl font-bold text-white">GA4 Event Tester</h1>
              <p className="text-slate-400 text-sm">Test and verify Google Analytics 4 event tracking</p>
            </div>
          </div>
          <div className="flex gap-3">
            <Button onClick={clearResults} variant="outline" className="border-slate-600">
              <RefreshCw className="w-4 h-4 mr-2" />
              Clear
            </Button>
            <Button onClick={runAllTests} className="bg-gradient-to-r from-indigo-500 to-purple-500">
              <Send className="w-4 h-4 mr-2" />
              Run All Tests
            </Button>
          </div>
        </div>

        {/* GA Status */}
        <div className="bg-slate-800/50 rounded-xl border border-slate-700/50 p-6 mb-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <div className={`w-12 h-12 rounded-full flex items-center justify-center ${
                gaStatus === null ? 'bg-slate-700' : gaStatus ? 'bg-green-500/20' : 'bg-red-500/20'
              }`}>
                {gaStatus === null ? (
                  <BarChart3 className="w-6 h-6 text-slate-400" />
                ) : gaStatus ? (
                  <CheckCircle className="w-6 h-6 text-green-400" />
                ) : (
                  <XCircle className="w-6 h-6 text-red-400" />
                )}
              </div>
              <div>
                <h3 className="text-lg font-semibold text-white">Google Analytics Status</h3>
                <p className="text-slate-400 text-sm">
                  {gaStatus === null ? 'Click "Check Status" to verify GA4 is loaded' : 
                   gaStatus ? 'GA4 is loaded and ready to track events' : 
                   'GA4 is NOT loaded - check your configuration'}
                </p>
              </div>
            </div>
            <Button onClick={checkGAStatus} variant="outline" className="border-slate-600">
              Check Status
            </Button>
          </div>
        </div>

        <div className="grid lg:grid-cols-2 gap-6">
          {/* Event Buttons */}
          <div className="bg-slate-800/50 rounded-xl border border-slate-700/50 p-6">
            <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
              <Activity className="w-5 h-5 text-indigo-400" />
              Event Triggers
            </h2>
            <p className="text-slate-400 text-sm mb-4">
              Click each button to fire the corresponding GA4 event. Check GA4 Realtime to verify receipt.
            </p>
            <div className="grid grid-cols-2 gap-3">
              {testEvents.map((test) => (
                <Button
                  key={test.name}
                  onClick={test.action}
                  variant="outline"
                  className="border-slate-600 hover:bg-slate-700 justify-start h-auto py-3"
                >
                  <test.icon className="w-4 h-4 mr-2 text-indigo-400" />
                  <div className="text-left">
                    <div className="text-white font-medium">{test.name}</div>
                    <div className="text-slate-500 text-xs">{test.description}</div>
                  </div>
                </Button>
              ))}
            </div>
            <div className="mt-4 pt-4 border-t border-slate-700">
              <Button
                onClick={sendTestEvent}
                className="w-full bg-gradient-to-r from-green-500 to-emerald-500"
              >
                <Send className="w-4 h-4 mr-2" />
                Send Test Event (Unique ID)
              </Button>
            </div>
          </div>

          {/* Results Log */}
          <div className="bg-slate-800/50 rounded-xl border border-slate-700/50 p-6">
            <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
              <FileText className="w-5 h-5 text-indigo-400" />
              Event Log
            </h2>
            <p className="text-slate-400 text-sm mb-4">
              Events fired from this page. Open GA4 Realtime to verify events are received.
            </p>
            <div className="space-y-2 max-h-[500px] overflow-y-auto">
              {testResults.length === 0 ? (
                <div className="text-center py-8 text-slate-500">
                  No events fired yet. Click an event button to start testing.
                </div>
              ) : (
                testResults.map((result) => (
                  <div
                    key={result.id}
                    className={`p-3 rounded-lg border ${
                      result.success 
                        ? 'bg-green-500/10 border-green-500/30' 
                        : 'bg-red-500/10 border-red-500/30'
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        {result.success ? (
                          <CheckCircle className="w-4 h-4 text-green-400" />
                        ) : (
                          <XCircle className="w-4 h-4 text-red-400" />
                        )}
                        <span className="text-white font-medium">{result.event}</span>
                      </div>
                      <span className="text-slate-500 text-xs">{result.timestamp}</span>
                    </div>
                    <p className="text-slate-400 text-sm mt-1 ml-6">{result.details}</p>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>

        {/* Instructions */}
        <div className="mt-6 bg-slate-800/50 rounded-xl border border-slate-700/50 p-6">
          <h2 className="text-lg font-semibold text-white mb-4">How to Verify Events in GA4</h2>
          <ol className="space-y-3 text-slate-300">
            <li className="flex gap-3">
              <span className="flex-shrink-0 w-6 h-6 rounded-full bg-indigo-500/20 text-indigo-400 flex items-center justify-center text-sm font-bold">1</span>
              <span>Open <a href="https://analytics.google.com" target="_blank" rel="noopener noreferrer" className="text-indigo-400 hover:underline">Google Analytics</a> in a new tab</span>
            </li>
            <li className="flex gap-3">
              <span className="flex-shrink-0 w-6 h-6 rounded-full bg-indigo-500/20 text-indigo-400 flex items-center justify-center text-sm font-bold">2</span>
              <span>Select your Visionary Suite property</span>
            </li>
            <li className="flex gap-3">
              <span className="flex-shrink-0 w-6 h-6 rounded-full bg-indigo-500/20 text-indigo-400 flex items-center justify-center text-sm font-bold">3</span>
              <span>Go to <strong>Reports → Realtime</strong></span>
            </li>
            <li className="flex gap-3">
              <span className="flex-shrink-0 w-6 h-6 rounded-full bg-indigo-500/20 text-indigo-400 flex items-center justify-center text-sm font-bold">4</span>
              <span>Click the event buttons on this page</span>
            </li>
            <li className="flex gap-3">
              <span className="flex-shrink-0 w-6 h-6 rounded-full bg-indigo-500/20 text-indigo-400 flex items-center justify-center text-sm font-bold">5</span>
              <span>Watch events appear in the GA4 Realtime view (may take 5-10 seconds)</span>
            </li>
          </ol>
        </div>
      </div>
    </div>
  );
}
