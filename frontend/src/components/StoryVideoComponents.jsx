import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Badge } from '../components/ui/badge';
import { Progress } from '../components/ui/progress';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '../components/ui/dialog';
import { 
  Play, Sparkles, BookOpen, Rocket, Heart, GraduationCap, 
  Cat, Search, Share2, Download, Facebook, Twitter, 
  MessageCircle, Linkedin, Mail, Gamepad2, Brain, 
  Puzzle, HelpCircle, Trophy, Clock, ChevronRight,
  RefreshCw, CheckCircle, XCircle
} from 'lucide-react';
import { toast } from 'sonner';
import api from '../utils/api';

// Template Icons Map
const templateIcons = {
  bedtime_adventure: BookOpen,
  superhero_origin: Rocket,
  fairy_tale: Sparkles,
  space_explorer: Rocket,
  friendship_story: Heart,
  educational_journey: GraduationCap,
  animal_adventure: Cat,
  mystery_detective: Search
};

// =============================================================================
// VIDEO TEMPLATES COMPONENT
// =============================================================================

export function VideoTemplates({ onSelectTemplate }) {
  const [templates, setTemplates] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedAge, setSelectedAge] = useState('all');
  const [selectedStyle, setSelectedStyle] = useState('all');

  useEffect(() => {
    fetchTemplates();
  }, []);

  const fetchTemplates = async () => {
    try {
      const res = await api.get('/api/story-video-studio/templates/list');
      if (res.data.success) {
        setTemplates(res.data.templates);
      }
    } catch (error) {
      console.error('Failed to fetch templates:', error);
    } finally {
      setLoading(false);
    }
  };

  const filteredTemplates = templates.filter(t => {
    if (selectedAge !== 'all' && t.age_group !== selectedAge) return false;
    if (selectedStyle !== 'all' && t.style !== selectedStyle) return false;
    return true;
  });

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <RefreshCw className="w-8 h-8 animate-spin text-purple-500" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap gap-4">
        <select
          value={selectedAge}
          onChange={(e) => setSelectedAge(e.target.value)}
          className="px-4 py-2 rounded-lg bg-slate-800 border border-slate-700 text-white"
          data-testid="template-age-filter"
        >
          <option value="all">All Ages</option>
          <option value="toddler">Toddlers (2-4)</option>
          <option value="kids_5_8">Kids (5-8)</option>
          <option value="kids_9_12">Tweens (9-12)</option>
          <option value="teen">Teens (13+)</option>
          <option value="all_ages">All Ages</option>
        </select>

        <select
          value={selectedStyle}
          onChange={(e) => setSelectedStyle(e.target.value)}
          className="px-4 py-2 rounded-lg bg-slate-800 border border-slate-700 text-white"
          data-testid="template-style-filter"
        >
          <option value="all">All Styles</option>
          <option value="watercolor">Watercolor</option>
          <option value="cartoon_2d">2D Cartoon</option>
          <option value="3d_animation">3D Animation</option>
          <option value="comic_book">Comic Book</option>
          <option value="storybook">Storybook</option>
        </select>
      </div>

      <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
        {filteredTemplates.map((template) => {
          const IconComponent = templateIcons[template.template_id] || Sparkles;
          return (
            <Card 
              key={template.template_id}
              className="bg-slate-800/50 border-slate-700/50 hover:border-purple-500/50 transition-all cursor-pointer group"
              onClick={() => onSelectTemplate(template)}
              data-testid={`template-card-${template.template_id}`}
            >
              <CardHeader>
                <div className="flex items-center justify-between">
                  <div className="w-12 h-12 rounded-xl bg-purple-500/20 flex items-center justify-center group-hover:bg-purple-500/30 transition-colors">
                    <IconComponent className="w-6 h-6 text-purple-400" />
                  </div>
                  <Badge variant="secondary" className="bg-slate-700">
                    {template.scene_count} scenes
                  </Badge>
                </div>
                <CardTitle className="text-white mt-3">{template.name}</CardTitle>
                <CardDescription className="text-slate-400">{template.description}</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="flex flex-wrap gap-2">
                  <Badge className="bg-blue-500/20 text-blue-400">{template.age_group.replace('_', ' ')}</Badge>
                  <Badge className="bg-green-500/20 text-green-400">{template.style.replace('_', ' ')}</Badge>
                  <Badge className="bg-amber-500/20 text-amber-400">{template.duration_estimate}</Badge>
                </div>
              </CardContent>
            </Card>
          );
        })}
      </div>
    </div>
  );
}

// =============================================================================
// TEMPLATE CUSTOMIZATION DIALOG
// =============================================================================

export function TemplateCustomizer({ template, onGenerate, onClose }) {
  const [customizations, setCustomizations] = useState({});
  const [additionalDetails, setAdditionalDetails] = useState('');
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (template?.fill_in_blanks) {
      setCustomizations({ ...template.fill_in_blanks });
    }
  }, [template]);

  const handleGenerate = async () => {
    setLoading(true);
    try {
      const res = await api.post('/api/story-video-studio/templates/generate-from-template', {
        template_id: template.template_id,
        customizations,
        additional_details: additionalDetails
      });

      if (res.data.success) {
        onGenerate(res.data);
        toast.success('Story generated from template!');
      }
    } catch (error) {
      toast.error('Failed to generate story');
    } finally {
      setLoading(false);
    }
  };

  if (!template) return null;

  return (
    <div className="space-y-6">
      <div className="space-y-4">
        <h3 className="text-lg font-semibold text-white">Customize Your Story</h3>
        <p className="text-slate-400">Personalize the template by filling in the blanks</p>
        
        <div className="grid gap-4">
          {Object.entries(template.fill_in_blanks || {}).map(([key, defaultValue]) => (
            <div key={key}>
              <label className="block text-sm font-medium text-slate-300 mb-1 capitalize">
                {key.replace(/_/g, ' ')}
              </label>
              <Input
                value={customizations[key] || ''}
                onChange={(e) => setCustomizations({ ...customizations, [key]: e.target.value })}
                placeholder={defaultValue}
                className="bg-slate-900/50 border-slate-600 text-white"
                data-testid={`template-input-${key}`}
              />
            </div>
          ))}
        </div>

        <div>
          <label className="block text-sm font-medium text-slate-300 mb-1">Additional Details (Optional)</label>
          <textarea
            value={additionalDetails}
            onChange={(e) => setAdditionalDetails(e.target.value)}
            placeholder="Add any extra story details..."
            className="w-full px-4 py-3 rounded-lg bg-slate-900/50 border border-slate-600 text-white resize-none"
            rows={3}
            data-testid="template-additional-details"
          />
        </div>
      </div>

      <div className="flex gap-3">
        <Button variant="outline" onClick={onClose} className="flex-1">
          Cancel
        </Button>
        <Button 
          onClick={handleGenerate} 
          disabled={loading}
          className="flex-1 bg-purple-500 hover:bg-purple-600"
          data-testid="template-generate-btn"
        >
          {loading ? <RefreshCw className="w-4 h-4 mr-2 animate-spin" /> : <Sparkles className="w-4 h-4 mr-2" />}
          Generate Story
        </Button>
      </div>
    </div>
  );
}

// =============================================================================
// WAITING GAMES COMPONENT
// =============================================================================

export function WaitingGames({ jobId, onVideoReady }) {
  const [activeGame, setActiveGame] = useState('trivia');
  const [triviaQuestions, setTriviaQuestions] = useState([]);
  const [currentQuestion, setCurrentQuestion] = useState(0);
  const [score, setScore] = useState(0);
  const [answered, setAnswered] = useState(false);
  const [wordPuzzle, setWordPuzzle] = useState(null);
  const [puzzleGuess, setPuzzleGuess] = useState('');
  const [riddle, setRiddle] = useState(null);
  const [riddleGuess, setRiddleGuess] = useState('');
  const [videoStatus, setVideoStatus] = useState(null);

  useEffect(() => {
    fetchTrivia();
    fetchWordPuzzle();
    fetchRiddle();
    
    // Poll for video status
    const interval = setInterval(checkVideoStatus, 5000);
    return () => clearInterval(interval);
  }, [jobId]);

  const checkVideoStatus = async () => {
    if (!jobId) return;
    try {
      const res = await api.get(`/api/story-video-studio/templates/video-ready/${jobId}`);
      setVideoStatus(res.data);
      if (res.data.is_ready) {
        onVideoReady?.(res.data);
        toast.success('Your video is ready! 🎉');
      }
    } catch (error) {
      console.error('Failed to check video status:', error);
    }
  };

  const fetchTrivia = async () => {
    try {
      const res = await api.get('/api/story-video-studio/templates/waiting-games/trivia?count=5');
      if (res.data.success) {
        setTriviaQuestions(res.data.questions);
      }
    } catch (error) {
      console.error('Failed to fetch trivia:', error);
    }
  };

  const fetchWordPuzzle = async () => {
    try {
      const res = await api.get('/api/story-video-studio/templates/waiting-games/word-puzzle');
      if (res.data.success) {
        setWordPuzzle(res.data);
        setPuzzleGuess('');
      }
    } catch (error) {
      console.error('Failed to fetch word puzzle:', error);
    }
  };

  const fetchRiddle = async () => {
    try {
      const res = await api.get('/api/story-video-studio/templates/waiting-games/riddle');
      if (res.data.success) {
        setRiddle(res.data);
        setRiddleGuess('');
      }
    } catch (error) {
      console.error('Failed to fetch riddle:', error);
    }
  };

  const handleTriviaAnswer = async (answerIndex) => {
    if (answered) return;
    setAnswered(true);

    try {
      const res = await api.post(`/api/story-video-studio/templates/waiting-games/trivia/check?question_id=${currentQuestion}&answer_index=${answerIndex}`);
      if (res.data.correct) {
        setScore(score + 1);
        toast.success('Correct! 🎉');
      } else {
        toast.error(`Wrong! The answer was: ${res.data.correct_answer}`);
      }

      setTimeout(() => {
        if (currentQuestion < triviaQuestions.length - 1) {
          setCurrentQuestion(currentQuestion + 1);
          setAnswered(false);
        } else {
          toast.info(`Quiz complete! Score: ${score + (res.data.correct ? 1 : 0)}/${triviaQuestions.length}`);
        }
      }, 1500);
    } catch (error) {
      toast.error('Failed to check answer');
    }
  };

  const handlePuzzleCheck = async () => {
    if (!puzzleGuess.trim()) return;

    try {
      const res = await api.post(`/api/story-video-studio/templates/waiting-games/word-puzzle/check?scrambled=${wordPuzzle.scrambled}&guess=${puzzleGuess}`);
      if (res.data.correct) {
        toast.success('Correct! 🎉');
        setScore(score + 1);
        fetchWordPuzzle();
      } else {
        toast.error(`Wrong! The answer was: ${res.data.answer}`);
        fetchWordPuzzle();
      }
    } catch (error) {
      toast.error('Failed to check answer');
    }
  };

  const handleRiddleCheck = async () => {
    if (!riddleGuess.trim()) return;

    try {
      const res = await api.post(`/api/story-video-studio/templates/waiting-games/riddle/check?riddle_text=${encodeURIComponent(riddle.riddle)}&guess=${riddleGuess}`);
      if (res.data.correct) {
        toast.success('Correct! 🎉');
        setScore(score + 1);
        fetchRiddle();
      } else {
        toast.error(`Not quite! The answer was: ${res.data.answer}`);
        fetchRiddle();
      }
    } catch (error) {
      toast.error('Failed to check answer');
    }
  };

  return (
    <div className="space-y-6">
      {/* Video Status Banner */}
      {videoStatus && (
        <div className={`p-4 rounded-xl ${videoStatus.is_ready ? 'bg-green-500/20 border border-green-500/50' : 'bg-blue-500/20 border border-blue-500/50'}`}>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              {videoStatus.is_ready ? (
                <CheckCircle className="w-6 h-6 text-green-400" />
              ) : (
                <RefreshCw className="w-6 h-6 text-blue-400 animate-spin" />
              )}
              <div>
                <p className="font-medium text-white">{videoStatus.message}</p>
                {!videoStatus.is_ready && (
                  <p className="text-sm text-slate-400">Progress: {videoStatus.progress}%</p>
                )}
              </div>
            </div>
            {videoStatus.is_ready && (
              <Button 
                onClick={() => window.location.href = videoStatus.redirect_to}
                className="bg-green-500 hover:bg-green-600"
              >
                View Video
                <ChevronRight className="w-4 h-4 ml-2" />
              </Button>
            )}
          </div>
          {!videoStatus.is_ready && <Progress value={videoStatus.progress} className="mt-3 h-2" />}
        </div>
      )}

      {/* Score Display */}
      <div className="flex items-center justify-center gap-3 p-4 bg-gradient-to-r from-purple-500/20 to-pink-500/20 rounded-xl">
        <Trophy className="w-6 h-6 text-yellow-400" />
        <span className="text-2xl font-bold text-white">{score}</span>
        <span className="text-slate-400">points</span>
      </div>

      {/* Game Tabs */}
      <Tabs value={activeGame} onValueChange={setActiveGame} className="w-full">
        <TabsList className="grid grid-cols-3 bg-slate-800/50">
          <TabsTrigger value="trivia" className="flex items-center gap-2">
            <Brain className="w-4 h-4" /> Trivia
          </TabsTrigger>
          <TabsTrigger value="puzzle" className="flex items-center gap-2">
            <Puzzle className="w-4 h-4" /> Word Puzzle
          </TabsTrigger>
          <TabsTrigger value="riddle" className="flex items-center gap-2">
            <HelpCircle className="w-4 h-4" /> Riddles
          </TabsTrigger>
        </TabsList>

        {/* Trivia Tab */}
        <TabsContent value="trivia" className="mt-4">
          {triviaQuestions.length > 0 && currentQuestion < triviaQuestions.length ? (
            <Card className="bg-slate-800/50 border-slate-700/50">
              <CardHeader>
                <div className="flex justify-between items-center">
                  <Badge>Question {currentQuestion + 1}/{triviaQuestions.length}</Badge>
                  <Badge variant="outline">Score: {score}</Badge>
                </div>
                <CardTitle className="text-white mt-4">
                  {triviaQuestions[currentQuestion].question}
                </CardTitle>
              </CardHeader>
              <CardContent className="grid gap-3">
                {triviaQuestions[currentQuestion].options.map((option, idx) => (
                  <Button
                    key={idx}
                    variant="outline"
                    className={`w-full justify-start text-left ${answered ? 'opacity-50 cursor-not-allowed' : 'hover:bg-purple-500/20'}`}
                    onClick={() => handleTriviaAnswer(idx)}
                    disabled={answered}
                    data-testid={`trivia-option-${idx}`}
                  >
                    {String.fromCharCode(65 + idx)}. {option}
                  </Button>
                ))}
              </CardContent>
            </Card>
          ) : (
            <div className="text-center py-8">
              <Trophy className="w-12 h-12 text-yellow-400 mx-auto mb-4" />
              <p className="text-white text-xl font-semibold">Quiz Complete!</p>
              <p className="text-slate-400">Final Score: {score}/{triviaQuestions.length}</p>
              <Button onClick={() => { fetchTrivia(); setCurrentQuestion(0); setAnswered(false); }} className="mt-4">
                Play Again
              </Button>
            </div>
          )}
        </TabsContent>

        {/* Word Puzzle Tab */}
        <TabsContent value="puzzle" className="mt-4">
          {wordPuzzle && (
            <Card className="bg-slate-800/50 border-slate-700/50">
              <CardHeader>
                <CardTitle className="text-white">Unscramble the Word</CardTitle>
                <CardDescription>Hint: {wordPuzzle.hint}</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="text-center py-6">
                  <p className="text-4xl font-bold text-purple-400 tracking-widest">
                    {wordPuzzle.scrambled}
                  </p>
                  <p className="text-sm text-slate-400 mt-2">{wordPuzzle.length} letters</p>
                </div>
                <div className="flex gap-3">
                  <Input
                    value={puzzleGuess}
                    onChange={(e) => setPuzzleGuess(e.target.value.toUpperCase())}
                    placeholder="Your answer..."
                    className="bg-slate-900/50 border-slate-600 text-white uppercase"
                    onKeyPress={(e) => e.key === 'Enter' && handlePuzzleCheck()}
                    data-testid="puzzle-input"
                  />
                  <Button onClick={handlePuzzleCheck} className="bg-purple-500 hover:bg-purple-600">
                    Check
                  </Button>
                </div>
                <Button variant="ghost" onClick={fetchWordPuzzle} className="w-full">
                  <RefreshCw className="w-4 h-4 mr-2" /> New Puzzle
                </Button>
              </CardContent>
            </Card>
          )}
        </TabsContent>

        {/* Riddles Tab */}
        <TabsContent value="riddle" className="mt-4">
          {riddle && (
            <Card className="bg-slate-800/50 border-slate-700/50">
              <CardHeader>
                <CardTitle className="text-white">Solve the Riddle</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="p-6 bg-slate-900/50 rounded-xl">
                  <p className="text-xl text-white italic">"{riddle.riddle}"</p>
                </div>
                <div className="flex gap-3">
                  <Input
                    value={riddleGuess}
                    onChange={(e) => setRiddleGuess(e.target.value)}
                    placeholder="Your answer..."
                    className="bg-slate-900/50 border-slate-600 text-white"
                    onKeyPress={(e) => e.key === 'Enter' && handleRiddleCheck()}
                    data-testid="riddle-input"
                  />
                  <Button onClick={handleRiddleCheck} className="bg-purple-500 hover:bg-purple-600">
                    Check
                  </Button>
                </div>
                <Button variant="ghost" onClick={fetchRiddle} className="w-full">
                  <RefreshCw className="w-4 h-4 mr-2" /> New Riddle
                </Button>
              </CardContent>
            </Card>
          )}
        </TabsContent>
      </Tabs>
    </div>
  );
}

// =============================================================================
// SOCIAL SHARING COMPONENT
// =============================================================================

export function SocialSharing({ videoId, title }) {
  const [shareLinks, setShareLinks] = useState(null);
  const [customMessage, setCustomMessage] = useState('');
  const [loading, setLoading] = useState(false);

  const generateShareLinks = async () => {
    setLoading(true);
    try {
      const res = await api.post('/api/story-video-studio/templates/share', {
        video_id: videoId,
        platform: 'all',
        custom_message: customMessage || `Check out my AI-generated video: ${title}`
      });
      if (res.data.success) {
        setShareLinks(res.data.share_links);
      }
    } catch (error) {
      toast.error('Failed to generate share links');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (videoId) {
      generateShareLinks();
    }
  }, [videoId]);

  const socialPlatforms = [
    { key: 'facebook', name: 'Facebook', icon: Facebook, color: 'bg-blue-600 hover:bg-blue-700' },
    { key: 'twitter', name: 'Twitter', icon: Twitter, color: 'bg-sky-500 hover:bg-sky-600' },
    { key: 'whatsapp', name: 'WhatsApp', icon: MessageCircle, color: 'bg-green-500 hover:bg-green-600' },
    { key: 'linkedin', name: 'LinkedIn', icon: Linkedin, color: 'bg-blue-700 hover:bg-blue-800' },
    { key: 'email', name: 'Email', icon: Mail, color: 'bg-slate-600 hover:bg-slate-700' }
  ];

  const handleShare = (platform, link) => {
    window.open(link, '_blank', 'width=600,height=400');
    toast.success(`Opening ${platform}...`);
  };

  const handleCopyLink = () => {
    if (shareLinks) {
      navigator.clipboard.writeText(shareLinks.share_url || window.location.href);
      toast.success('Link copied to clipboard!');
    }
  };

  return (
    <Card className="bg-slate-800/50 border-slate-700/50">
      <CardHeader>
        <CardTitle className="text-white flex items-center gap-2">
          <Share2 className="w-5 h-5 text-purple-400" />
          Share Your Video
        </CardTitle>
        <CardDescription>Share your creation on social media</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-slate-300 mb-2">Custom Message</label>
          <Input
            value={customMessage}
            onChange={(e) => setCustomMessage(e.target.value)}
            placeholder="Check out my AI-generated video!"
            className="bg-slate-900/50 border-slate-600 text-white"
            data-testid="share-custom-message"
          />
        </div>

        <Button 
          onClick={generateShareLinks} 
          disabled={loading}
          className="w-full bg-purple-500 hover:bg-purple-600"
        >
          {loading ? <RefreshCw className="w-4 h-4 mr-2 animate-spin" /> : <Share2 className="w-4 h-4 mr-2" />}
          Generate Share Links
        </Button>

        {shareLinks && (
          <div className="grid grid-cols-2 gap-3 pt-4">
            {socialPlatforms.map((platform) => (
              <Button
                key={platform.key}
                onClick={() => handleShare(platform.name, shareLinks[platform.key])}
                className={`${platform.color} text-white`}
                data-testid={`share-${platform.key}`}
              >
                <platform.icon className="w-4 h-4 mr-2" />
                {platform.name}
              </Button>
            ))}
            <Button
              onClick={handleCopyLink}
              variant="outline"
              className="col-span-2"
              data-testid="share-copy-link"
            >
              Copy Link
            </Button>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

// =============================================================================
// VIDEO DOWNLOAD COMPONENT
// =============================================================================

export function VideoDownload({ videoId, title }) {
  const [downloadInfo, setDownloadInfo] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchDownloadInfo();
  }, [videoId]);

  const fetchDownloadInfo = async () => {
    try {
      const res = await api.get(`/api/story-video-studio/templates/download/${videoId}`);
      if (res.data.success) {
        setDownloadInfo(res.data);
      }
    } catch (error) {
      console.error('Failed to fetch download info:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleDownload = () => {
    if (downloadInfo?.download_url) {
      window.open(`${process.env.REACT_APP_BACKEND_URL}${downloadInfo.download_url}`, '_blank');
      toast.success('Download started!');
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-8">
        <RefreshCw className="w-6 h-6 animate-spin text-purple-500" />
      </div>
    );
  }

  return (
    <Card className="bg-gradient-to-r from-purple-500/20 to-pink-500/20 border-purple-500/30">
      <CardContent className="pt-6">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-lg font-semibold text-white">{title || 'Your Video'}</h3>
            <p className="text-sm text-slate-400">
              {downloadInfo?.format} • {downloadInfo?.file_size_estimate}
            </p>
          </div>
          <Button 
            onClick={handleDownload}
            className="bg-purple-500 hover:bg-purple-600"
            data-testid="download-video-btn"
          >
            <Download className="w-4 h-4 mr-2" />
            Download
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}

export default { VideoTemplates, TemplateCustomizer, WaitingGames, SocialSharing, VideoDownload };
