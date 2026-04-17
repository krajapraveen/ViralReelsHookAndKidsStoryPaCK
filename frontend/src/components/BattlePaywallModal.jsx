import React, { useState, useEffect, useCallback } from 'react';
import { X, Zap, Crown, Flame, Loader2, Check, Swords } from 'lucide-react';
import { toast } from 'sonner';
import api from '../utils/api';
import { trackFunnel } from '../utils/funnelTracker';

/**
 * BattlePaywallModal — Competition-specific paywall.
 * MODAL ONLY — never navigates away. Returns user to exact blocked action.
 *
 * Triggers:
 *  - Free entries exhausted
 *  - Loss moment (user dropped rank, wants to re-enter)
 *  - Near #1 (urgency upsell)
 *
 * Props:
 *  - open: boolean
 *  - onClose: () => void
 *  - onSuccess: () => void — called after payment, resumes blocked action
 *  - trigger: 'free_limit' | 'loss_moment' | 'near_win' | 'enter_battle'
 *  - battleContext: { rootTitle, currentRank, competitorCount }
 */

function loadCashfreeCheckout(env = 'production') {
  return new Promise((resolve) => {
    if (window.Cashfree) {
      resolve(window.Cashfree({ mode: env }));
      return;
    }
    const script = document.createElement('script');
    script.src = 'https://sdk.cashfree.com/js/v3/cashfree.js';
    script.onload = () => {
      if (window.Cashfree) resolve(window.Cashfree({ mode: env }));
      else resolve(null);
    };
    script.onerror = () => resolve(null);
    document.head.appendChild(script);
  });
}

const TRIGGER_COPY = {
  free_limit: {
    title: "You've used your free entries",
    subtitle: 'One more entry could win the whole battle',
  },
  loss_moment: {
    title: "Someone just beat you",
    subtitle: "Enter again and take the top spot",
  },
  near_win: {
    title: "You're 1 move away from #1",
    subtitle: "Someone is beating you right now — don't let them win",
  },
  enter_battle: {
    title: 'Win the battle',
    subtitle: 'Your next entry could take #1',
  },
};

export default function BattlePaywallModal({ open, onClose, onSuccess, trigger = 'enter_battle', battleContext }) {
  const [packs, setPacks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [purchasing, setPurchasing] = useState(null);
  const [entryStatus, setEntryStatus] = useState(null);

  useEffect(() => {
    if (!open) return;
    setLoading(true);
    api.get('/api/stories/battle-entry-status')
      .then(res => {
        if (res.data?.success) {
          setPacks(res.data.packs || []);
          setEntryStatus(res.data);
        }
      })
      .catch(() => {})
      .finally(() => setLoading(false));

    trackFunnel('battle_paywall_viewed', {
      meta: { trigger, rank: battleContext?.currentRank },
    });
  }, [open, trigger, battleContext?.currentRank]);

  const handlePurchase = useCallback(async (pack) => {
    setPurchasing(pack.id);

    trackFunnel('battle_pack_selected', {
      meta: { pack_id: pack.id, price: pack.price_inr, trigger },
    });

    try {
      const response = await api.post('/api/cashfree/create-order', {
        productId: pack.id,
        currency: 'INR',
      });

      if (!response.data?.paymentSessionId) {
        toast.error('Payment configuration error.');
        setPurchasing(null);
        return;
      }

      const cashfreeEnv = response.data.environment === 'production' ? 'production' : 'sandbox';
      const cashfree = await loadCashfreeCheckout(cashfreeEnv);

      if (!cashfree) {
        toast.error('Unable to load payment gateway.');
        setPurchasing(null);
        return;
      }

      cashfree.checkout({
        paymentSessionId: response.data.paymentSessionId,
        redirectTarget: '_modal',
      }).then(async (result) => {
        if (result.error) {
          const msg = result.error.message || '';
          if (msg.includes('cancel') || msg.includes('closed') || msg.includes('dismiss')) {
            toast.info('Payment cancelled. No charges made.');
          } else {
            toast.error(`Payment failed: ${msg}`);
          }
          trackFunnel('battle_payment_abandoned', { meta: { pack_id: pack.id } });
        } else if (result.paymentDetails) {
          try {
            const verifyRes = await api.post('/api/cashfree/verify', { order_id: response.data.orderId });
            if (verifyRes.data?.success) {
              trackFunnel('battle_payment_success', {
                meta: { pack_id: pack.id, credits: verifyRes.data.creditsAdded, trigger },
              });
              toast.success(`${pack.entries} entries unlocked!`);
              window.dispatchEvent(new CustomEvent('credits-updated'));
              onSuccess?.();
              onClose();
            } else {
              toast.info('Processing... credits will appear shortly.');
            }
          } catch {
            toast.warning('Payment succeeded. Credits syncing.');
          }
        } else {
          toast.info('Payment window closed.');
          trackFunnel('battle_payment_abandoned', { meta: { pack_id: pack.id } });
        }
      }).catch(() => {
        toast.info('Payment window closed.');
      }).finally(() => setPurchasing(null));
    } catch (err) {
      toast.error('Failed to start payment. Try again.');
      setPurchasing(null);
    }
  }, [trigger, onSuccess, onClose]);

  if (!open) return null;

  const copy = TRIGGER_COPY[trigger] || TRIGGER_COPY.enter_battle;

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/80 backdrop-blur-sm p-4" data-testid="battle-paywall-modal">
      <div className="bg-[#0c0c14] border border-white/10 rounded-2xl shadow-2xl max-w-sm w-full mx-4 overflow-hidden animate-in fade-in zoom-in-95 duration-200">
        {/* Header */}
        <div className="relative px-6 pt-6 pb-4">
          <button
            onClick={onClose}
            className="absolute top-4 right-4 text-white/20 hover:text-white/60 transition-colors"
            data-testid="paywall-close-btn"
          >
            <X className="w-5 h-5" />
          </button>

          <div className="flex items-center gap-3 mb-3">
            <div className={`w-10 h-10 rounded-xl flex items-center justify-center ${
              trigger === 'loss_moment' ? 'bg-rose-500/20' :
              trigger === 'near_win' ? 'bg-amber-500/20' :
              'bg-violet-500/20'
            }`}>
              {trigger === 'loss_moment' ? <Flame className="w-5 h-5 text-rose-400" /> :
               trigger === 'near_win' ? <Crown className="w-5 h-5 text-amber-400" /> :
               <Swords className="w-5 h-5 text-violet-400" />}
            </div>
            <div>
              <h3 className="text-base font-black text-white" data-testid="paywall-title">{copy.title}</h3>
              <p className="text-xs text-white/40">{copy.subtitle}</p>
            </div>
          </div>

          {/* Context: rank + competitors */}
          {battleContext?.currentRank && (
            <div className="bg-white/[0.03] border border-white/5 rounded-lg p-3 flex items-center justify-between text-xs mb-1" data-testid="paywall-battle-context">
              <div>
                <span className="text-white/30">Your rank</span>
                <p className="text-lg font-black text-white">#{battleContext.currentRank}</p>
              </div>
              {battleContext.competitorCount > 0 && (
                <div>
                  <span className="text-white/30">Competing</span>
                  <p className="text-lg font-black text-amber-400">{battleContext.competitorCount}</p>
                </div>
              )}
              {entryStatus && (
                <div>
                  <span className="text-white/30">Credits</span>
                  <p className="text-lg font-black text-emerald-400">{entryStatus.credits}</p>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Packs */}
        <div className="px-6 pb-4 space-y-2">
          {loading ? (
            <div className="flex justify-center py-8">
              <Loader2 className="w-6 h-6 text-violet-400 animate-spin" />
            </div>
          ) : (
            packs.map((pack, i) => {
              const isPopular = pack.badge === 'POPULAR';
              const isBest = pack.badge === 'BEST VALUE';
              return (
                <button
                  key={pack.id}
                  onClick={() => handlePurchase(pack)}
                  disabled={!!purchasing}
                  className={`w-full rounded-xl p-3.5 text-left transition-all relative overflow-hidden ${
                    isPopular
                      ? 'bg-gradient-to-r from-amber-500/15 to-rose-500/15 border-2 border-amber-500/30 hover:border-amber-500/50'
                      : 'bg-white/[0.03] border border-white/10 hover:border-white/20'
                  } ${purchasing === pack.id ? 'opacity-70' : ''}`}
                  data-testid={`battle-pack-${pack.id}`}
                >
                  {pack.badge && (
                    <span className={`absolute top-2 right-2 text-[9px] font-bold rounded-full px-2 py-0.5 ${
                      isPopular ? 'bg-amber-500/30 text-amber-300' : 'bg-emerald-500/30 text-emerald-300'
                    }`}>
                      {pack.badge}
                    </span>
                  )}
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-sm font-bold text-white">{pack.entries} entries</p>
                      <p className="text-[10px] text-white/40">
                        {pack.entries <= 3 ? 'Try again now' : pack.entries <= 5 ? 'Keep competing' : 'Dominate the battle'}
                      </p>
                    </div>
                    <div className="text-right">
                      {purchasing === pack.id ? (
                        <Loader2 className="w-4 h-4 text-white animate-spin" />
                      ) : (
                        <>
                          <p className="text-base font-black text-white">₹{pack.price_inr}</p>
                        </>
                      )}
                    </div>
                  </div>
                  {pack.savings && (
                    <p className="text-[10px] text-emerald-400 font-semibold mt-1">Save {pack.savings}</p>
                  )}
                </button>
              );
            })
          )}
        </div>

        {/* Free entries remaining */}
        {entryStatus && entryStatus.free_remaining > 0 && (
          <div className="px-6 pb-4">
            <button
              onClick={onClose}
              className="w-full text-center text-xs text-white/30 hover:text-white/50 py-2 transition-colors"
              data-testid="continue-free-btn"
            >
              Continue with {entryStatus.free_remaining} free {entryStatus.free_remaining === 1 ? 'entry' : 'entries'} remaining
            </button>
          </div>
        )}

        {/* Urgency footer */}
        <div className="px-6 pb-5">
          <p className="text-[10px] text-white/20 text-center">
            {trigger === 'loss_moment'
              ? 'Every second counts — your rank is dropping'
              : trigger === 'near_win'
              ? 'One entry away from the top spot'
              : 'Rankings change fast — act now'}
          </p>
        </div>
      </div>
    </div>
  );
}
