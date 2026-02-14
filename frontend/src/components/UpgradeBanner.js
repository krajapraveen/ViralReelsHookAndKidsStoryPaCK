import React from 'react';
import { Link } from 'react-router-dom';
import { Button } from './ui/button';
import { AlertTriangle, Sparkles, Crown } from 'lucide-react';

export default function UpgradeBanner({ credits, isFreeTier, type = 'low' }) {
  // type: 'low' (credits < 10), 'exhausted' (credits = 0), 'watermark' (free tier warning)
  
  if (type === 'exhausted' || credits === 0) {
    return (
      <div className="bg-gradient-to-r from-red-500/10 to-orange-500/10 border border-red-300 rounded-xl p-6 mb-6">
        <div className="flex items-start gap-4">
          <div className="w-12 h-12 bg-red-100 rounded-full flex items-center justify-center flex-shrink-0">
            <AlertTriangle className="w-6 h-6 text-red-500" />
          </div>
          <div className="flex-1">
            <h3 className="text-lg font-bold text-red-700 mb-1">Credits Exhausted!</h3>
            <p className="text-red-600 text-sm mb-4">
              You've used all your free credits. Upgrade to continue generating amazing content.
            </p>
            <div className="flex gap-3">
              <Link to="/pricing">
                <Button className="bg-gradient-to-r from-indigo-500 to-purple-500 hover:from-indigo-600 hover:to-purple-600 text-white" data-testid="upgrade-btn-exhausted">
                  <Crown className="w-4 h-4 mr-2" />
                  View Plans & Upgrade
                </Button>
              </Link>
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (type === 'low' && credits > 0 && credits <= 10) {
    return (
      <div className="bg-gradient-to-r from-purple-500/10 to-indigo-500/10 border border-purple-300 rounded-xl p-4 mb-6">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-purple-100 rounded-full flex items-center justify-center flex-shrink-0">
            <AlertTriangle className="w-5 h-5 text-purple-500" />
          </div>
          <div className="flex-1">
            <p className="text-purple-700 font-medium">
              Running low on credits! Only <span className="font-bold">{credits}</span> credits remaining.
            </p>
          </div>
          <Link to="/pricing">
            <Button variant="outline" className="border-purple-500 text-purple-700 hover:bg-purple-50" data-testid="upgrade-btn-low">
              Get More Credits
            </Button>
          </Link>
        </div>
      </div>
    );
  }

  if (type === 'watermark' && isFreeTier) {
    return (
      <div className="bg-gradient-to-r from-purple-500/10 to-indigo-500/10 border border-purple-300 rounded-xl p-4 mb-6">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-purple-100 rounded-full flex items-center justify-center flex-shrink-0">
            <Sparkles className="w-5 h-5 text-purple-500" />
          </div>
          <div className="flex-1">
            <p className="text-purple-700 font-medium">
              Free tier includes watermarks on downloads. <span className="font-bold">Upgrade to remove them!</span>
            </p>
          </div>
          <Link to="/pricing">
            <Button className="bg-purple-500 hover:bg-purple-600 text-white" data-testid="upgrade-btn-watermark">
              <Crown className="w-4 h-4 mr-2" />
              Upgrade Now
            </Button>
          </Link>
        </div>
      </div>
    );
  }

  return null;
}
