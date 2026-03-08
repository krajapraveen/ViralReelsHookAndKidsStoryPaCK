import React from 'react';
import { Link } from 'react-router-dom';
import { Button } from './ui/button';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from './ui/dialog';
import { Crown, Download, X, Check } from 'lucide-react';

export default function UpgradeModal({ isOpen, onClose, onDownloadWithWatermark }) {
  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="max-w-md bg-white">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2 text-xl">
            <Crown className="w-6 h-6 text-purple-500" />
            Remove Watermark?
          </DialogTitle>
        </DialogHeader>

        <div className="py-4">
          <p className="text-slate-600 mb-6">
            Your download will include a <span className="font-semibold text-purple-600">"Made with Visionary Suite"</span> watermark. 
            Upgrade to get watermark-free downloads!
          </p>

          <div className="bg-slate-50 rounded-lg p-4 mb-6">
            <h4 className="font-semibold text-slate-800 mb-3">Premium Benefits:</h4>
            <ul className="space-y-2">
              <li className="flex items-center gap-2 text-sm text-slate-600">
                <Check className="w-4 h-4 text-green-500" />
                Watermark-free downloads
              </li>
              <li className="flex items-center gap-2 text-sm text-slate-600">
                <Check className="w-4 h-4 text-green-500" />
                Priority generation queue
              </li>
              <li className="flex items-center gap-2 text-sm text-slate-600">
                <Check className="w-4 h-4 text-green-500" />
                Higher quality outputs
              </li>
              <li className="flex items-center gap-2 text-sm text-slate-600">
                <Check className="w-4 h-4 text-green-500" />
                Access to premium templates
              </li>
            </ul>
          </div>

          <div className="flex flex-col gap-3">
            <Link to="/pricing" className="w-full">
              <Button className="w-full bg-gradient-to-r from-indigo-500 to-purple-500 hover:from-indigo-600 hover:to-purple-600 text-white" data-testid="modal-upgrade-btn">
                <Crown className="w-4 h-4 mr-2" />
                Upgrade Now - Remove Watermark
              </Button>
            </Link>
            
            <Button 
              variant="outline" 
              className="w-full" 
              onClick={onDownloadWithWatermark}
              data-testid="modal-download-watermark-btn"
            >
              <Download className="w-4 h-4 mr-2" />
              Download with Watermark
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
