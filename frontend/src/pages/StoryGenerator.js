import React, { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { generationAPI, creditAPI } from '../utils/api';
import { toast } from 'sonner';
import { Sparkles, Download, Loader2, ArrowLeft, Coins, Clock } from 'lucide-react';

export default function StoryGenerator() {
  const [credits, setCredits] = useState(0);
  const [loading, setLoading] = useState(false);
  const [polling, setPolling] = useState(false);
  const [generationId, setGenerationId] = useState(null);
  const [result, setResult] = useState(null);
  const navigate = useNavigate();

  const [formData, setFormData] = useState({
    ageGroup: '4-6',
    theme: 'Adventure',
    genre: 'Fantasy',
    moral: 'Friendship',
    characters: ['Kid', 'Dog'],
    setting: 'forest',
    scenes: 8,
    language: 'English',
    style: 'Pixar-like 3D',
    length: '60s'
  });

  useEffect(() => {
    fetchCredits();
  }, []);

  useEffect(() => {
    if (generationId && polling) {
      const interval = setInterval(checkGenerationStatus, 3000);
      return () => clearInterval(interval);
    }
  }, [generationId, polling]);

  const fetchCredits = async () => {
    try {
      const response = await creditAPI.getBalance();
      setCredits(response.data.balance);
    } catch (error) {
      toast.error('Failed to load credits');
    }
  };

  const getCreditCost = () => {
    const costs = { 8: 6, 10: 7, 12: 8 };
    return costs[formData.scenes] || 6;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    const cost = getCreditCost();
    if (credits < cost) {
      toast.error(`Insufficient credits! Need ${cost} credits.`);
      navigate('/app/billing');
      return;
    }

    setLoading(true);
    try {
      const response = await generationAPI.generateStory(formData);
      setGenerationId(response.data.generationId);
      setCredits(credits - cost);
      setPolling(true);
      toast.success('Story generation started! This may take 30-90 seconds.');
    } catch (error) {
      toast.error(error.response?.data?.message || 'Generation failed');
      setLoading(false);
    }
  };

  const checkGenerationStatus = async () => {
    try {
      const response = await generationAPI.getGeneration(generationId);
      if (response.data.status === 'SUCCEEDED') {
        setResult(response.data.outputJson);
        setPolling(false);
        setLoading(false);
        toast.success('Story pack generated successfully!');
      } else if (response.data.status === 'FAILED') {
        setPolling(false);
        setLoading(false);
        toast.error('Generation failed');
      }
    } catch (error) {
      console.error('Polling error:', error);
    }
  };

  const downloadJSON = () => {
    const blob = new Blob([JSON.stringify(result, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `story-pack-${Date.now()}.json`;
    a.click();
    toast.success('Downloaded!');
  };

  const downloadPDF = async () => {
    try {
      const response = await generationAPI.downloadPDF(generationId);
      const blob = new Blob([response.data], { type: 'application/pdf' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `story-pack-${generationId}.pdf`;
      a.click();
      toast.success('PDF Downloaded!');
    } catch (error) {
      toast.error('Failed to download PDF');
    }
  };

  return (
    <div className="min-h-screen bg-slate-50">
      <header className="bg-white border-b border-slate-200">
        <div className="max-w-7xl mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Link to="/app"><Button variant="ghost" size="sm"><ArrowLeft className="w-4 h-4 mr-2" />Dashboard</Button></Link>
            <div className="flex items-center gap-2"><Sparkles className="w-6 h-6 text-orange-500" /><span className="text-xl font-bold">Story Generator</span></div>
          </div>
          <div className="flex items-center gap-2 bg-slate-100 rounded-full px-4 py-2"><Coins className="w-4 h-4 text-orange-500" /><span className="font-semibold">{credits} Credits</span></div>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-4 py-8">
        <div className="grid lg:grid-cols-2 gap-8">
          <div className="bg-white rounded-xl border border-slate-200 p-6">
            <h2 className="text-2xl font-bold mb-6">Create Kids Story Pack</h2>
            <form onSubmit={handleSubmit} className="space-y-6" data-testid="story-form">
              <div className="grid md:grid-cols-2 gap-4">
                <div><Label>Age Group</Label>
                  <Select value={formData.ageGroup} onValueChange={(value) => setFormData({...formData, ageGroup: value})}>
                    <SelectTrigger><SelectValue /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="3-5">3-5 years (Preschool)</SelectItem>
                      <SelectItem value="6-8">6-8 years (Early Elementary)</SelectItem>
                      <SelectItem value="9-12">9-12 years (Middle Childhood)</SelectItem>
                      <SelectItem value="13-15">13-15 years (Early Teens)</SelectItem>
                      <SelectItem value="16-17">16-17 years (Late Teens)</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div><Label>Genre</Label>
                  <Select value={formData.genre} onValueChange={(value) => setFormData({...formData, genre: value})}>
                    <SelectTrigger data-testid="story-genre-select"><SelectValue /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="Fantasy">Fantasy</SelectItem>
                      <SelectItem value="Adventure">Adventure</SelectItem>
                      <SelectItem value="Mystery">Mystery/Detective</SelectItem>
                      <SelectItem value="SciFi">Science Fiction</SelectItem>
                      <SelectItem value="Fairy Tale">Fairy Tale</SelectItem>
                      <SelectItem value="Mythology">Mythology</SelectItem>
                      <SelectItem value="Historical">Historical Fiction</SelectItem>
                      <SelectItem value="Comedy">Comedy/Humor</SelectItem>
                      <SelectItem value="Animal">Animal Stories</SelectItem>
                      <SelectItem value="Superhero">Superhero</SelectItem>
                      <SelectItem value="Friendship">Friendship</SelectItem>
                      <SelectItem value="Educational">Educational</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>
              <div><Label>Number of Scenes</Label>
                <Select value={formData.scenes.toString()} onValueChange={(value) => setFormData({...formData, scenes: parseInt(value)})}>
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="8">8 scenes (6 credits)</SelectItem>
                    <SelectItem value="10">10 scenes (7 credits)</SelectItem>
                    <SelectItem value="12">12 scenes (8 credits)</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="bg-orange-50 border border-orange-200 rounded-lg p-4">
                <div className="flex items-center gap-2 text-orange-700"><Coins className="w-4 h-4" /><span className="font-medium">Cost: {getCreditCost()} credits</span></div>
              </div>
              <Button type="submit" disabled={loading} className="w-full bg-orange-500 hover:bg-orange-600 text-white" data-testid="story-generate-btn">
                {loading ? <><Loader2 className="w-4 h-4 mr-2 animate-spin" />{polling ? 'Generating... (30-90s)' : 'Starting...'}</> : <><Sparkles className="w-4 h-4 mr-2" />Generate Story Pack</>}
              </Button>
            </form>
          </div>

          <div className="bg-white rounded-xl border border-slate-200 p-6">
            <div className="flex items-center justify-between mb-6"><h2 className="text-2xl font-bold">Story Pack</h2>
              {result && (
                <div className="flex gap-2">
                  <Button variant="outline" size="sm" onClick={downloadPDF} data-testid="download-story-pdf">
                    <Download className="w-4 h-4 mr-2" />
                    Download PDF
                  </Button>
                  <Button variant="outline" size="sm" onClick={downloadJSON} data-testid="download-story-btn">
                    <Download className="w-4 h-4 mr-2" />
                    Download JSON
                  </Button>
                </div>
              )}
            </div>
            {loading && !result && <div className="text-center py-12"><Loader2 className="w-12 h-12 mx-auto mb-4 text-orange-500 animate-spin" /><p className="text-slate-600 font-medium">Generating story pack...</p><p className="text-sm text-slate-500 mt-2">Takes 30-90 seconds</p></div>}
            {!loading && !result && <div className="text-center py-12 text-slate-500"><Clock className="w-12 h-12 mx-auto mb-4 text-slate-300" /><p>Your story pack will appear here</p></div>}
            {result && <div className="space-y-4 max-h-[600px] overflow-y-auto" data-testid="story-result"><div className="bg-gradient-to-r from-orange-50 to-yellow-50 border border-orange-200 rounded-lg p-6"><h3 className="text-2xl font-bold text-orange-900 mb-2">{result.title}</h3><p className="text-slate-700">{result.synopsis}</p></div>
              {result.scenes && <div><h3 className="font-bold text-lg mb-3">Scenes: {result.scenes.length}</h3><p className="text-sm text-slate-600">Complete scene breakdown available in downloaded JSON</p></div>}
            </div>}
          </div>
        </div>
      </div>
    </div>
  );
}