import React, { useState, useEffect, useRef } from 'react';
import api from '../utils/api';
import { toast } from 'sonner';
import { Button } from '../components/ui/button';
import { 
  Upload, Camera, Star, Share2, Users, Sparkles, 
  RefreshCw, ChevronRight, Trophy, Heart, Twitter
} from 'lucide-react';

export default function TwinFinder() {
  const [credits, setCredits] = useState(0);
  const [step, setStep] = useState('upload'); // upload, analyzing, results
  const [loading, setLoading] = useState(false);
  const [analysisId, setAnalysisId] = useState(null);
  const [matches, setMatches] = useState([]);
  const [topMatch, setTopMatch] = useState(null);
  const [consentChecked, setConsentChecked] = useState(false);
  const [previewUrl, setPreviewUrl] = useState(null);
  const fileInputRef = useRef(null);

  useEffect(() => {
    fetchCredits();
    fetchDashboard();
  }, []);

  const fetchCredits = async () => {
    try {
      const res = await api.get('/api/credits/balance');
      setCredits(res.data.credits || 0);
    } catch (error) {
      console.error('Failed to fetch credits:', error);
    }
  };

  const fetchDashboard = async () => {
    try {
      const res = await api.get('/api/twinfinder/dashboard');
      // Could display leaderboard data here
    } catch (error) {
      console.error('Failed to fetch dashboard:', error);
    }
  };

  const handleFileSelect = (e) => {
    const file = e.target.files[0];
    if (file) {
      if (!file.type.startsWith('image/')) {
        toast.error('Please select an image file');
        return;
      }
      if (file.size > 10 * 1024 * 1024) {
        toast.error('Image too large (max 10MB)');
        return;
      }
      setPreviewUrl(URL.createObjectURL(file));
    }
  };

  const analyzeFace = async () => {
    if (!consentChecked) {
      toast.error('Please confirm consent before proceeding');
      return;
    }
    
    const file = fileInputRef.current?.files[0];
    if (!file) {
      toast.error('Please select an image first');
      return;
    }

    setLoading(true);
    setStep('analyzing');

    try {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('consent_confirmed', 'true');

      const res = await api.post('/api/twinfinder/analyze', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });

      setAnalysisId(res.data.analysisId);
      toast.success('Face analyzed! Finding your celebrity match...');
      
      // Automatically find matches
      await findMatches(res.data.analysisId);
      
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Analysis failed');
      setStep('upload');
    } finally {
      setLoading(false);
    }
  };

  const findMatches = async (analysisIdParam) => {
    const id = analysisIdParam || analysisId;
    if (!id) return;

    setLoading(true);
    try {
      const res = await api.post(`/api/twinfinder/find-match/${id}?limit=5`);
      setMatches(res.data.matches || []);
      setTopMatch(res.data.topMatch);
      setStep('results');
      fetchCredits();
      toast.success('Match found!');
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to find matches');
    } finally {
      setLoading(false);
    }
  };

  const shareResult = async (platform) => {
    if (!topMatch) return;
    
    try {
      const res = await api.post(`/api/twinfinder/share/${analysisId}?platform=${platform}`);
      
      // Copy to clipboard
      navigator.clipboard.writeText(res.data.shareText);
      toast.success('Share text copied to clipboard!');
      
      // Open share URL (simplified)
      if (platform === 'twitter') {
        window.open(`https://twitter.com/intent/tweet?text=${encodeURIComponent(res.data.shareText)}`, '_blank');
      }
    } catch (error) {
      toast.error('Failed to generate share link');
    }
  };

  const resetFlow = () => {
    setStep('upload');
    setAnalysisId(null);
    setMatches([]);
    setTopMatch(null);
    setPreviewUrl(null);
    setConsentChecked(false);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-950 via-indigo-950 to-slate-950 text-white">
      <div className="max-w-4xl mx-auto px-4 py-8">
        {/* Header */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center gap-2 px-4 py-2 bg-purple-500/20 rounded-full mb-4">
            <Star className="w-5 h-5 text-yellow-400" />
            <span className="text-purple-300 font-medium">TwinFinder AI</span>
          </div>
          <h1 className="text-4xl md:text-5xl font-bold mb-4">
            Find Your Celebrity
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-purple-400 to-pink-400"> Lookalike</span>
          </h1>
          <p className="text-slate-300 text-lg max-w-xl mx-auto">
            Upload your photo and discover which celebrity you look most like using AI-powered face analysis
          </p>
          <div className="mt-4">
            <span className="text-slate-400">Your Credits: </span>
            <span className="text-xl font-bold text-purple-400">{credits}</span>
          </div>
        </div>

        {/* Upload Step */}
        {step === 'upload' && (
          <div className="bg-slate-800/50 backdrop-blur-xl rounded-2xl p-8 border border-slate-700">
            {/* Upload Area */}
            <div 
              className="border-2 border-dashed border-slate-600 rounded-xl p-8 text-center cursor-pointer hover:border-purple-500 transition-colors"
              onClick={() => fileInputRef.current?.click()}
            >
              {previewUrl ? (
                <div className="relative">
                  <img 
                    src={previewUrl} 
                    alt="Preview" 
                    className="max-h-64 mx-auto rounded-lg object-cover"
                  />
                  <Button 
                    variant="ghost" 
                    size="sm"
                    className="absolute top-2 right-2 bg-slate-900/80"
                    onClick={(e) => { e.stopPropagation(); setPreviewUrl(null); }}
                  >
                    Change
                  </Button>
                </div>
              ) : (
                <>
                  <Upload className="w-12 h-12 text-slate-400 mx-auto mb-4" />
                  <p className="text-lg font-medium text-white mb-2">Upload Your Photo</p>
                  <p className="text-slate-400 text-sm">Click to browse or drag and drop</p>
                  <p className="text-slate-500 text-xs mt-2">JPG, PNG up to 10MB</p>
                </>
              )}
              <input
                ref={fileInputRef}
                type="file"
                accept="image/*"
                className="hidden"
                onChange={handleFileSelect}
              />
            </div>

            {/* Consent Checkbox */}
            <div className="mt-6 flex items-start gap-3">
              <input
                type="checkbox"
                id="consent"
                checked={consentChecked}
                onChange={(e) => setConsentChecked(e.target.checked)}
                className="mt-1 w-5 h-5 rounded border-slate-600 bg-slate-700 text-purple-500 focus:ring-purple-500"
              />
              <label htmlFor="consent" className="text-sm text-slate-300">
                I confirm that I have the rights to this image and consent to it being analyzed by AI. 
                The image will be processed securely and not stored permanently.
              </label>
            </div>

            {/* Analyze Button */}
            <Button 
              onClick={analyzeFace} 
              disabled={loading || !previewUrl}
              className="w-full mt-6 bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-700 hover:to-pink-700 text-lg py-6"
            >
              {loading ? (
                <>
                  <RefreshCw className="w-5 h-5 mr-2 animate-spin" />
                  Analyzing...
                </>
              ) : (
                <>
                  <Sparkles className="w-5 h-5 mr-2" />
                  Find My Celebrity Twin (20 credits)
                </>
              )}
            </Button>

            {/* Info Cards */}
            <div className="grid grid-cols-3 gap-4 mt-8">
              <div className="text-center p-4 bg-slate-700/30 rounded-lg">
                <Camera className="w-6 h-6 text-purple-400 mx-auto mb-2" />
                <p className="text-sm text-slate-300">AI Analysis</p>
              </div>
              <div className="text-center p-4 bg-slate-700/30 rounded-lg">
                <Users className="w-6 h-6 text-purple-400 mx-auto mb-2" />
                <p className="text-sm text-slate-300">100+ Celebrities</p>
              </div>
              <div className="text-center p-4 bg-slate-700/30 rounded-lg">
                <Share2 className="w-6 h-6 text-purple-400 mx-auto mb-2" />
                <p className="text-sm text-slate-300">Easy Sharing</p>
              </div>
            </div>
          </div>
        )}

        {/* Analyzing Step */}
        {step === 'analyzing' && (
          <div className="bg-slate-800/50 backdrop-blur-xl rounded-2xl p-12 border border-slate-700 text-center">
            <RefreshCw className="w-16 h-16 text-purple-500 mx-auto mb-6 animate-spin" />
            <h2 className="text-2xl font-bold mb-4">Analyzing Your Face...</h2>
            <p className="text-slate-400 mb-8">Our AI is scanning facial features and finding your celebrity match</p>
            <div className="max-w-xs mx-auto">
              <div className="h-2 bg-slate-700 rounded-full overflow-hidden">
                <div className="h-full bg-gradient-to-r from-purple-500 to-pink-500 rounded-full animate-pulse w-3/4"></div>
              </div>
            </div>
          </div>
        )}

        {/* Results Step */}
        {step === 'results' && topMatch && (
          <div className="space-y-6">
            {/* Top Match Card */}
            <div className="bg-gradient-to-br from-purple-900/50 to-pink-900/50 backdrop-blur-xl rounded-2xl p-8 border border-purple-500/30 text-center">
              <div className="inline-flex items-center gap-2 px-4 py-2 bg-yellow-500/20 rounded-full mb-6">
                <Trophy className="w-5 h-5 text-yellow-400" />
                <span className="text-yellow-300 font-medium">Your Celebrity Twin!</span>
              </div>
              
              <div className="mb-6">
                <div className="w-32 h-32 mx-auto bg-gradient-to-br from-purple-500 to-pink-500 rounded-full flex items-center justify-center text-5xl font-bold mb-4">
                  {topMatch.celebrity?.charAt(0)}
                </div>
                <h2 className="text-3xl font-bold">{topMatch.celebrity}</h2>
                <p className="text-purple-300 capitalize">{topMatch.category}</p>
              </div>

              <div className="inline-flex items-center gap-2 px-6 py-3 bg-slate-800/50 rounded-full mb-6">
                <Heart className="w-5 h-5 text-pink-400" />
                <span className="text-2xl font-bold text-white">{topMatch.similarity}%</span>
                <span className="text-slate-400">Match</span>
              </div>

              {topMatch.matchingTraits && topMatch.matchingTraits.length > 0 && (
                <div className="flex flex-wrap justify-center gap-2 mb-6">
                  {topMatch.matchingTraits.map((trait, i) => (
                    <span key={i} className="px-3 py-1 bg-purple-500/20 rounded-full text-sm text-purple-300">
                      {trait.replace('_', ' ')}
                    </span>
                  ))}
                </div>
              )}

              {/* Share Buttons */}
              <div className="flex justify-center gap-4 mt-6">
                <Button 
                  onClick={() => shareResult('twitter')}
                  className="bg-[#1DA1F2] hover:bg-[#1a8cd8]"
                >
                  <Twitter className="w-4 h-4 mr-2" />
                  Share on X
                </Button>
                <Button 
                  onClick={() => shareResult('instagram')}
                  variant="outline"
                  className="border-pink-500 text-pink-400 hover:bg-pink-500/10"
                >
                  <Share2 className="w-4 h-4 mr-2" />
                  Copy for Instagram
                </Button>
              </div>
            </div>

            {/* Other Matches */}
            {matches.length > 1 && (
              <div className="bg-slate-800/50 backdrop-blur-xl rounded-2xl p-6 border border-slate-700">
                <h3 className="text-lg font-semibold mb-4">Other Matches</h3>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  {matches.slice(1).map((match, i) => (
                    <div key={i} className="text-center p-4 bg-slate-700/30 rounded-lg">
                      <div className="w-12 h-12 mx-auto bg-slate-600 rounded-full flex items-center justify-center text-xl font-bold mb-2">
                        {match.celebrity?.charAt(0)}
                      </div>
                      <p className="font-medium text-white text-sm">{match.celebrity}</p>
                      <p className="text-purple-400 text-sm">{match.similarity}%</p>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Try Again Button */}
            <div className="text-center">
              <Button 
                onClick={resetFlow}
                variant="outline"
                className="border-slate-600 text-slate-300 hover:bg-slate-800"
              >
                <RefreshCw className="w-4 h-4 mr-2" />
                Try Another Photo
              </Button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
