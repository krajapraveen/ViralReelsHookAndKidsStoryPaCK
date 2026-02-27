import React, { useState } from 'react';
import { X, Download, Shield, Briefcase, Archive, Sparkles, Check } from 'lucide-react';
import { Button } from './ui/button';
import { toast } from 'sonner';
import api from '../utils/api';

const UPSELL_ICONS = {
  hd_download: Download,
  remove_watermark: Shield,
  commercial_license: Briefcase,
  batch_download: Archive
};

export default function UpsellModal({ isOpen, onClose, generationId, feature, onSuccess }) {
  const [loading, setLoading] = useState({});
  const [purchased, setPurchased] = useState({});
  const [upsells, setUpsells] = useState(null);

  React.useEffect(() => {
    if (isOpen) {
      fetchUpsells();
    }
  }, [isOpen]);

  const fetchUpsells = async () => {
    try {
      const res = await api.get('/api/monetization/upsells');
      if (res.data.success) {
        setUpsells(res.data.upsells);
      }
    } catch (error) {
      console.error('Failed to fetch upsells:', error);
    }
  };

  const handlePurchase = async (upsellId) => {
    setLoading(prev => ({ ...prev, [upsellId]: true }));
    
    try {
      const res = await api.post('/api/monetization/upsell/purchase', {
        generationId,
        upsellId
      });
      
      if (res.data.success) {
        setPurchased(prev => ({ ...prev, [upsellId]: true }));
        toast.success(res.data.message);
        
        if (onSuccess) {
          onSuccess(upsellId, res.data);
        }
      }
    } catch (error) {
      const detail = error.response?.data?.detail;
      if (detail?.error === 'insufficient_credits') {
        toast.error(`Need ${detail.required} credits. You have ${detail.available}.`);
      } else {
        toast.error('Failed to purchase upgrade');
      }
    } finally {
      setLoading(prev => ({ ...prev, [upsellId]: false }));
    }
  };

  if (!isOpen || !upsells) return null;

  // Filter upsells available for this feature
  const availableUpsells = Object.entries(upsells).filter(([id, upsell]) => 
    upsell.available_for?.includes(feature)
  );

  return (
    <div className="fixed inset-0 bg-black/70 backdrop-blur-sm flex items-center justify-center z-50 p-4">
      <div className="bg-slate-900 border border-slate-700 rounded-2xl w-full max-w-lg overflow-hidden">
        {/* Header */}
        <div className="bg-gradient-to-r from-purple-600 to-pink-600 p-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <Sparkles className="w-8 h-8 text-white" />
              <div>
                <h2 className="text-xl font-bold text-white">Enhance Your Creation</h2>
                <p className="text-white/80 text-sm">Unlock premium features</p>
              </div>
            </div>
            <button 
              onClick={onClose}
              className="text-white/80 hover:text-white transition-colors"
            >
              <X className="w-6 h-6" />
            </button>
          </div>
        </div>

        {/* Upsell Options */}
        <div className="p-6 space-y-4">
          {availableUpsells.length === 0 ? (
            <p className="text-slate-400 text-center py-4">No upgrades available for this content</p>
          ) : (
            availableUpsells.map(([id, upsell]) => {
              const Icon = UPSELL_ICONS[id] || Sparkles;
              const isPurchased = purchased[id];
              const isLoading = loading[id];
              const isFree = upsell.free_for_user;

              return (
                <div 
                  key={id}
                  className={`border rounded-xl p-4 transition-all ${
                    isPurchased 
                      ? 'border-green-500/50 bg-green-500/10' 
                      : 'border-slate-700 hover:border-purple-500/50'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <div className={`p-2 rounded-lg ${
                        isPurchased ? 'bg-green-500/20' : 'bg-purple-500/20'
                      }`}>
                        {isPurchased ? (
                          <Check className="w-5 h-5 text-green-400" />
                        ) : (
                          <Icon className="w-5 h-5 text-purple-400" />
                        )}
                      </div>
                      <div>
                        <h3 className="font-semibold text-white">{upsell.name}</h3>
                        <p className="text-sm text-slate-400">{upsell.description}</p>
                      </div>
                    </div>
                    
                    {isPurchased ? (
                      <span className="text-green-400 text-sm font-medium">Applied ✓</span>
                    ) : (
                      <Button
                        onClick={() => handlePurchase(id)}
                        disabled={isLoading}
                        variant={isFree ? "default" : "outline"}
                        className={isFree 
                          ? "bg-green-600 hover:bg-green-700" 
                          : "border-purple-500 text-purple-400 hover:bg-purple-500/20"
                        }
                      >
                        {isLoading ? (
                          <span className="animate-spin">⏳</span>
                        ) : isFree ? (
                          'FREE'
                        ) : (
                          `${upsell.cost} credits`
                        )}
                      </Button>
                    )}
                  </div>
                </div>
              );
            })
          )}
        </div>

        {/* Footer */}
        <div className="border-t border-slate-700 p-4 flex justify-between items-center">
          <p className="text-slate-500 text-sm">
            Upgrade your plan for more free features
          </p>
          <Button 
            onClick={onClose}
            variant="outline"
            className="border-slate-600"
          >
            Done
          </Button>
        </div>
      </div>
    </div>
  );
}
