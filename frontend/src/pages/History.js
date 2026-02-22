import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { Button } from '../components/ui/button';
import { generationAPI } from '../utils/api';
import { toast } from 'sonner';
import { Sparkles, Video, BookOpen, ArrowLeft, Filter, ChevronDown, ChevronUp, Download, Eye, Clock, Coins, Calendar, FileText } from 'lucide-react';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../components/ui/dialog';

export default function History() {
  const [generations, setGenerations] = useState([]);
  const [filter, setFilter] = useState('ALL');
  const [loading, setLoading] = useState(true);
  const [expandedId, setExpandedId] = useState(null);
  const [selectedGeneration, setSelectedGeneration] = useState(null);
  const [viewModalOpen, setViewModalOpen] = useState(false);

  useEffect(() => {
    fetchGenerations();
  }, [filter]);

  const fetchGenerations = async () => {
    setLoading(true);
    try {
      const typeParam = filter === 'ALL' ? null : filter;
      const response = await generationAPI.getGenerations(typeParam, 0, 50);
      // API returns 'generations' not 'content'
      setGenerations(response.data.generations || response.data.content || []);
    } catch (error) {
      toast.error('Failed to load history');
    } finally {
      setLoading(false);
    }
  };

  const handleDownloadPDF = async (id) => {
    try {
      const response = await generationAPI.downloadPDF(id);
      const blob = new Blob([response.data], { type: 'application/pdf' });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `story-pack-${id}.pdf`;
      a.click();
      window.URL.revokeObjectURL(url);
      toast.success('PDF downloaded successfully!');
    } catch (error) {
      toast.error('Failed to download PDF');
    }
  };

  const viewGenerationDetails = (gen) => {
    setSelectedGeneration(gen);
    setViewModalOpen(true);
  };

  const getInputSummary = (gen) => {
    if (!gen.inputJson) return 'N/A';
    
    if (gen.type === 'REEL') {
      return gen.inputJson.topic || 'N/A';
    } else {
      const genre = gen.inputJson.genre || 'N/A';
      const ageGroup = gen.inputJson.ageGroup || 'N/A';
      return `${genre} (Age: ${ageGroup})`;
    }
  };

  const formatDate = (dateStr) => {
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-US', { 
      month: 'short', 
      day: 'numeric', 
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  // Stats calculation
  const stats = {
    total: generations.length,
    reels: generations.filter(g => g.type === 'REEL').length,
    stories: generations.filter(g => g.type === 'STORY').length,
    totalCredits: generations.reduce((sum, g) => sum + (g.creditsUsed || 0), 0)
  };

  return (
    <div className="min-h-screen bg-slate-50">
      <header className="bg-white border-b border-slate-200">
        <div className="max-w-7xl mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Link to="/app">
              <Button variant="ghost" size="sm">
                <ArrowLeft className="w-4 h-4 mr-2" />
                Dashboard
              </Button>
            </Link>
            <div className="flex items-center gap-2">
              <Sparkles className="w-6 h-6 text-indigo-500" />
              <span className="text-xl font-bold">Generation History</span>
            </div>
          </div>
          <Select value={filter} onValueChange={setFilter}>
            <SelectTrigger className="w-[180px]" data-testid="history-filter">
              <Filter className="w-4 h-4 mr-2" />
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="ALL">All Types</SelectItem>
              <SelectItem value="REEL">Reels Only</SelectItem>
              <SelectItem value="STORY">Stories Only</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-4 py-8">
        {/* Stats Cards */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
          <div className="bg-white rounded-xl border border-slate-200 p-4">
            <div className="flex items-center gap-2 text-slate-500 text-sm mb-1">
              <FileText className="w-4 h-4" />
              Total Generations
            </div>
            <p className="text-2xl font-bold text-slate-900">{stats.total}</p>
          </div>
          <div className="bg-white rounded-xl border border-slate-200 p-4">
            <div className="flex items-center gap-2 text-indigo-500 text-sm mb-1">
              <Video className="w-4 h-4" />
              Reels Created
            </div>
            <p className="text-2xl font-bold text-indigo-600">{stats.reels}</p>
          </div>
          <div className="bg-white rounded-xl border border-slate-200 p-4">
            <div className="flex items-center gap-2 text-purple-500 text-sm mb-1">
              <BookOpen className="w-4 h-4" />
              Stories Created
            </div>
            <p className="text-2xl font-bold text-purple-600">{stats.stories}</p>
          </div>
          <div className="bg-white rounded-xl border border-slate-200 p-4">
            <div className="flex items-center gap-2 text-amber-500 text-sm mb-1">
              <Coins className="w-4 h-4" />
              Credits Used
            </div>
            <p className="text-2xl font-bold text-amber-600">{stats.totalCredits}</p>
          </div>
        </div>

        {loading ? (
          <div className="text-center py-12">
            <div className="animate-spin w-8 h-8 border-4 border-indigo-500 border-t-transparent rounded-full mx-auto mb-4"></div>
            <p className="text-slate-500">Loading your creations...</p>
          </div>
        ) : generations.length === 0 ? (
          <div className="text-center py-12 bg-white rounded-xl border border-slate-200">
            <Sparkles className="w-12 h-12 text-slate-300 mx-auto mb-4" />
            <p className="text-slate-500 mb-4">No generations yet. Start creating!</p>
            <Link to="/app">
              <Button className="bg-indigo-500 hover:bg-indigo-600 text-white">
                Go to Dashboard
              </Button>
            </Link>
          </div>
        ) : (
          <div className="space-y-4" data-testid="history-list">
            {generations.map((gen) => (
              <div 
                key={gen.id} 
                className="bg-white rounded-xl border border-slate-200 overflow-hidden hover:shadow-md transition-shadow"
              >
                {/* Main Row */}
                <div 
                  className="p-6 cursor-pointer"
                  onClick={() => setExpandedId(expandedId === gen.id ? null : gen.id)}
                >
                  <div className="flex items-start justify-between">
                    <div className="flex items-start gap-4 flex-1">
                      {gen.type === 'REEL' ? (
                        <div className="w-12 h-12 bg-indigo-100 rounded-lg flex items-center justify-center flex-shrink-0">
                          <Video className="w-6 h-6 text-indigo-600" />
                        </div>
                      ) : (
                        <div className="w-12 h-12 bg-purple-100 rounded-lg flex items-center justify-center flex-shrink-0">
                          <BookOpen className="w-6 h-6 text-purple-600" />
                        </div>
                      )}
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-1">
                          <h3 className="font-bold text-lg">
                            {gen.type === 'REEL' ? 'Reel Script' : 'Kids Story Pack'}
                          </h3>
                          <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${
                            gen.status === 'SUCCEEDED' ? 'bg-green-100 text-green-700' :
                            gen.status === 'FAILED' ? 'bg-red-100 text-red-700' :
                            gen.status === 'RUNNING' ? 'bg-blue-100 text-blue-700' :
                            'bg-slate-100 text-slate-700'
                          }`}>
                            {gen.status}
                          </span>
                        </div>
                        <p className="text-slate-600 truncate" title={getInputSummary(gen)}>
                          {getInputSummary(gen)}
                        </p>
                        <div className="flex items-center gap-4 mt-2 text-sm text-slate-500">
                          <span className="flex items-center gap-1">
                            <Calendar className="w-3.5 h-3.5" />
                            {formatDate(gen.createdAt)}
                          </span>
                          <span className="flex items-center gap-1">
                            <Coins className="w-3.5 h-3.5" />
                            {gen.creditsUsed} credits
                          </span>
                        </div>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      {gen.status === 'SUCCEEDED' && (
                        <>
                          <Button 
                            variant="outline" 
                            size="sm"
                            onClick={(e) => { e.stopPropagation(); viewGenerationDetails(gen); }}
                            data-testid={`view-${gen.id}`}
                          >
                            <Eye className="w-4 h-4 mr-1" />
                            View
                          </Button>
                          {gen.type === 'STORY' && (
                            <Button 
                              variant="outline" 
                              size="sm"
                              onClick={(e) => { e.stopPropagation(); handleDownloadPDF(gen.id); }}
                              data-testid={`download-${gen.id}`}
                            >
                              <Download className="w-4 h-4 mr-1" />
                              PDF
                            </Button>
                          )}
                        </>
                      )}
                      {expandedId === gen.id ? (
                        <ChevronUp className="w-5 h-5 text-slate-400" />
                      ) : (
                        <ChevronDown className="w-5 h-5 text-slate-400" />
                      )}
                    </div>
                  </div>
                </div>

                {/* Expanded Details */}
                {expandedId === gen.id && (
                  <div className="border-t border-slate-200 bg-slate-50 p-6">
                    <div className="grid md:grid-cols-2 gap-6">
                      {/* Input Parameters */}
                      <div>
                        <h4 className="font-semibold text-slate-700 mb-3 flex items-center gap-2">
                          <span className="w-6 h-6 bg-slate-200 rounded-full flex items-center justify-center text-xs">1</span>
                          Input Parameters
                        </h4>
                        {gen.inputJson ? (
                          <div className="bg-white rounded-lg border border-slate-200 p-4 space-y-2 text-sm">
                            {gen.type === 'REEL' ? (
                              <>
                                <div><span className="text-slate-500">Topic:</span> <span className="font-medium">{gen.inputJson.topic}</span></div>
                                <div><span className="text-slate-500">Niche:</span> <span className="font-medium">{gen.inputJson.niche}</span></div>
                                <div><span className="text-slate-500">Tone:</span> <span className="font-medium">{gen.inputJson.tone}</span></div>
                                <div><span className="text-slate-500">Duration:</span> <span className="font-medium">{gen.inputJson.duration}</span></div>
                                <div><span className="text-slate-500">Goal:</span> <span className="font-medium">{gen.inputJson.goal}</span></div>
                              </>
                            ) : (
                              <>
                                <div><span className="text-slate-500">Genre:</span> <span className="font-medium">{gen.inputJson.genre}</span></div>
                                <div><span className="text-slate-500">Age Group:</span> <span className="font-medium">{gen.inputJson.ageGroup}</span></div>
                                <div><span className="text-slate-500">Theme:</span> <span className="font-medium">{gen.inputJson.theme || 'Default'}</span></div>
                                <div><span className="text-slate-500">Scenes:</span> <span className="font-medium">{gen.inputJson.sceneCount}</span></div>
                              </>
                            )}
                          </div>
                        ) : (
                          <p className="text-slate-500 text-sm">No input data available</p>
                        )}
                      </div>

                      {/* Output Preview */}
                      <div>
                        <h4 className="font-semibold text-slate-700 mb-3 flex items-center gap-2">
                          <span className="w-6 h-6 bg-slate-200 rounded-full flex items-center justify-center text-xs">2</span>
                          Output Preview
                        </h4>
                        {gen.status === 'SUCCEEDED' && gen.outputJson ? (
                          <div className="bg-white rounded-lg border border-slate-200 p-4 text-sm">
                            {gen.type === 'REEL' ? (
                              <>
                                <div className="mb-2">
                                  <span className="text-slate-500">Hook:</span>
                                  <p className="font-medium text-indigo-600 line-clamp-2">{gen.outputJson.hooks?.[0] || 'N/A'}</p>
                                </div>
                                <div>
                                  <span className="text-slate-500">Hashtags:</span>
                                  <p className="text-slate-700 line-clamp-1">{gen.outputJson.hashtags?.slice(0, 5).join(' ') || 'N/A'}</p>
                                </div>
                              </>
                            ) : (
                              <>
                                <div className="mb-2">
                                  <span className="text-slate-500">Title:</span>
                                  <p className="font-medium text-purple-600">{gen.outputJson.title || 'N/A'}</p>
                                </div>
                                <div>
                                  <span className="text-slate-500">Scenes:</span>
                                  <p className="text-slate-700">{gen.outputJson.scenes?.length || 0} scenes generated</p>
                                </div>
                              </>
                            )}
                            <Button 
                              className="mt-3 w-full bg-indigo-500 hover:bg-indigo-600" 
                              size="sm"
                              onClick={() => viewGenerationDetails(gen)}
                            >
                              <Eye className="w-4 h-4 mr-2" />
                              View Full Output
                            </Button>
                          </div>
                        ) : gen.status === 'FAILED' ? (
                          <div className="bg-red-50 rounded-lg border border-red-200 p-4 text-sm text-red-700">
                            <p className="font-medium">Generation Failed</p>
                            <p className="mt-1">{gen.errorMessage || 'Unknown error occurred'}</p>
                          </div>
                        ) : (
                          <div className="bg-blue-50 rounded-lg border border-blue-200 p-4 text-sm text-blue-700">
                            <Clock className="w-5 h-5 inline mr-2" />
                            Generation in progress...
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* View Full Output Modal */}
      <Dialog open={viewModalOpen} onOpenChange={setViewModalOpen}>
        <DialogContent className="max-w-3xl max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              {selectedGeneration?.type === 'REEL' ? (
                <Video className="w-5 h-5 text-indigo-600" />
              ) : (
                <BookOpen className="w-5 h-5 text-purple-600" />
              )}
              {selectedGeneration?.type === 'REEL' ? 'Reel Script' : 'Story Pack'} Details
            </DialogTitle>
          </DialogHeader>
          
          {selectedGeneration && selectedGeneration.outputJson && (
            <div className="space-y-4 mt-4">
              {selectedGeneration.type === 'REEL' ? (
                <>
                  {/* Hooks */}
                  <div>
                    <h4 className="font-semibold text-slate-700 mb-2">Hooks</h4>
                    <div className="space-y-2">
                      {selectedGeneration.outputJson.hooks?.map((hook, i) => (
                        <div key={i} className="bg-indigo-50 rounded-lg p-3 text-indigo-800">
                          {i + 1}. {hook}
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* Script */}
                  <div>
                    <h4 className="font-semibold text-slate-700 mb-2">Script</h4>
                    <div className="bg-slate-100 rounded-lg p-4 whitespace-pre-wrap text-sm">
                      {selectedGeneration.outputJson.script}
                    </div>
                  </div>

                  {/* Captions */}
                  <div>
                    <h4 className="font-semibold text-slate-700 mb-2">Caption Options</h4>
                    <div className="space-y-2">
                      {selectedGeneration.outputJson.captions?.map((caption, i) => (
                        <div key={i} className="bg-slate-50 rounded-lg p-3 text-sm border border-slate-200">
                          {caption}
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* Hashtags */}
                  <div>
                    <h4 className="font-semibold text-slate-700 mb-2">Hashtags</h4>
                    <div className="flex flex-wrap gap-2">
                      {selectedGeneration.outputJson.hashtags?.map((tag, i) => (
                        <span key={i} className="bg-blue-100 text-blue-700 px-2 py-1 rounded-full text-sm">
                          {tag}
                        </span>
                      ))}
                    </div>
                  </div>

                  {/* Posting Tips */}
                  <div>
                    <h4 className="font-semibold text-slate-700 mb-2">Posting Tips</h4>
                    <ul className="list-disc list-inside space-y-1 text-sm text-slate-600">
                      {selectedGeneration.outputJson.postingTips?.map((tip, i) => (
                        <li key={i}>{tip}</li>
                      ))}
                    </ul>
                  </div>
                </>
              ) : (
                <>
                  {/* Story Title */}
                  <div>
                    <h4 className="font-semibold text-slate-700 mb-2">Story Title</h4>
                    <p className="text-xl font-bold text-purple-600">{selectedGeneration.outputJson.title}</p>
                  </div>

                  {/* Scenes */}
                  <div>
                    <h4 className="font-semibold text-slate-700 mb-2">Scenes ({selectedGeneration.outputJson.scenes?.length})</h4>
                    <div className="space-y-3">
                      {selectedGeneration.outputJson.scenes?.map((scene, i) => (
                        <div key={i} className="bg-purple-50 rounded-lg p-4 border border-purple-100">
                          <div className="font-semibold text-purple-800 mb-2">Scene {i + 1}</div>
                          <p className="text-sm text-slate-700 mb-2">{scene.narration}</p>
                          <p className="text-xs text-slate-500 italic">Visual: {scene.visualPrompt}</p>
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* YouTube Metadata */}
                  {selectedGeneration.outputJson.youtubeMetadata && (
                    <div>
                      <h4 className="font-semibold text-slate-700 mb-2">YouTube Metadata</h4>
                      <div className="bg-red-50 rounded-lg p-4 border border-red-100 space-y-2 text-sm">
                        <div><span className="font-medium">Title:</span> {selectedGeneration.outputJson.youtubeMetadata.title}</div>
                        <div><span className="font-medium">Description:</span> {selectedGeneration.outputJson.youtubeMetadata.description}</div>
                        <div className="flex flex-wrap gap-1">
                          {selectedGeneration.outputJson.youtubeMetadata.tags?.map((tag, i) => (
                            <span key={i} className="bg-red-100 text-red-700 px-2 py-0.5 rounded text-xs">{tag}</span>
                          ))}
                        </div>
                      </div>
                    </div>
                  )}
                </>
              )}
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
