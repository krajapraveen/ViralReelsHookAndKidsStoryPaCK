/**
 * WaitingExperience Component
 * Shows progress bar, games, puzzles, and quotes during file generation
 */
import React, { useState, useEffect, useCallback } from 'react';
import { Progress } from './ui/progress';
import { Button } from './ui/button';
import { 
  Loader2, Clock, Gamepad2, Puzzle, Quote, Sparkles, 
  RefreshCw, ChevronRight, Brain, Lightbulb, Trophy,
  ArrowRight, Zap, Star
} from 'lucide-react';

// Inspirational Quotes
const QUOTES = [
  { text: "Creativity is intelligence having fun.", author: "Albert Einstein" },
  { text: "The only way to do great work is to love what you do.", author: "Steve Jobs" },
  { text: "Imagination is the beginning of creation.", author: "George Bernard Shaw" },
  { text: "Every artist was first an amateur.", author: "Ralph Waldo Emerson" },
  { text: "The future belongs to those who believe in the beauty of their dreams.", author: "Eleanor Roosevelt" },
  { text: "Art is not what you see, but what you make others see.", author: "Edgar Degas" },
  { text: "Creativity takes courage.", author: "Henri Matisse" },
  { text: "The chief enemy of creativity is good sense.", author: "Pablo Picasso" },
  { text: "You can't use up creativity. The more you use, the more you have.", author: "Maya Angelou" },
  { text: "Innovation distinguishes between a leader and a follower.", author: "Steve Jobs" },
  { text: "Life is either a daring adventure or nothing at all.", author: "Helen Keller" },
  { text: "The best way to predict the future is to create it.", author: "Peter Drucker" }
];

// Mini Games
const MINI_GAMES = [
  { id: 'memory', name: 'Memory Match', icon: Brain, description: 'Test your memory!' },
  { id: 'trivia', name: 'Quick Trivia', icon: Lightbulb, description: 'Answer fun questions' },
  { id: 'word', name: 'Word Scramble', icon: Puzzle, description: 'Unscramble words' },
  { id: 'math', name: 'Speed Math', icon: Zap, description: 'Quick calculations' }
];

// Trivia Questions
const TRIVIA_QUESTIONS = [
  { q: "What planet is known as the Red Planet?", a: ["Mars", "Venus", "Jupiter", "Saturn"], correct: 0 },
  { q: "What is the largest ocean on Earth?", a: ["Pacific", "Atlantic", "Indian", "Arctic"], correct: 0 },
  { q: "Who painted the Mona Lisa?", a: ["Da Vinci", "Picasso", "Van Gogh", "Monet"], correct: 0 },
  { q: "What year did the first iPhone launch?", a: ["2007", "2005", "2009", "2010"], correct: 0 },
  { q: "What is the chemical symbol for gold?", a: ["Au", "Ag", "Fe", "Cu"], correct: 0 },
  { q: "Which country has the most time zones?", a: ["France", "USA", "Russia", "China"], correct: 0 },
  { q: "What is the fastest land animal?", a: ["Cheetah", "Lion", "Horse", "Leopard"], correct: 0 },
  { q: "How many bones are in the human body?", a: ["206", "186", "226", "256"], correct: 0 }
];

// Word Scramble Words
const WORDS_TO_SCRAMBLE = [
  "CREATE", "DESIGN", "STORY", "VIDEO", "IMAGE", "MAGIC", 
  "DREAM", "SPARK", "VISION", "CREATIVE", "INSPIRE", "WONDER"
];

export default function WaitingExperience({ 
  progress = 0, 
  stage = 'processing',
  message = 'Processing...',
  onTryOtherFeature,
  estimatedTime = null
}) {
  const [currentQuote, setCurrentQuote] = useState(QUOTES[0]);
  const [activeGame, setActiveGame] = useState(null);
  const [gameScore, setGameScore] = useState(0);
  const [triviaIndex, setTriviaIndex] = useState(0);
  const [scrambledWord, setScrambledWord] = useState('');
  const [userGuess, setUserGuess] = useState('');
  const [currentWord, setCurrentWord] = useState('');
  const [mathProblem, setMathProblem] = useState(null);
  const [mathAnswer, setMathAnswer] = useState('');

  // Rotate quotes every 8 seconds
  useEffect(() => {
    const interval = setInterval(() => {
      setCurrentQuote(QUOTES[Math.floor(Math.random() * QUOTES.length)]);
    }, 8000);
    return () => clearInterval(interval);
  }, []);

  // Scramble word helper
  const scrambleWord = useCallback((word) => {
    const arr = word.split('');
    for (let i = arr.length - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1));
      [arr[i], arr[j]] = [arr[j], arr[i]];
    }
    return arr.join('');
  }, []);

  // Generate math problem
  const generateMathProblem = useCallback(() => {
    const ops = ['+', '-', '*'];
    const op = ops[Math.floor(Math.random() * ops.length)];
    let a, b, answer;
    
    if (op === '*') {
      a = Math.floor(Math.random() * 12) + 1;
      b = Math.floor(Math.random() * 12) + 1;
      answer = a * b;
    } else if (op === '+') {
      a = Math.floor(Math.random() * 50) + 10;
      b = Math.floor(Math.random() * 50) + 10;
      answer = a + b;
    } else {
      a = Math.floor(Math.random() * 50) + 50;
      b = Math.floor(Math.random() * 50) + 1;
      answer = a - b;
    }
    
    setMathProblem({ a, b, op, answer });
    setMathAnswer('');
  }, []);

  // Start a game
  const startGame = (gameId) => {
    setActiveGame(gameId);
    setGameScore(0);
    
    if (gameId === 'word') {
      const word = WORDS_TO_SCRAMBLE[Math.floor(Math.random() * WORDS_TO_SCRAMBLE.length)];
      setCurrentWord(word);
      setScrambledWord(scrambleWord(word));
      setUserGuess('');
    } else if (gameId === 'trivia') {
      setTriviaIndex(Math.floor(Math.random() * TRIVIA_QUESTIONS.length));
    } else if (gameId === 'math') {
      generateMathProblem();
    }
  };

  // Handle trivia answer
  const handleTriviaAnswer = (answerIndex) => {
    if (answerIndex === TRIVIA_QUESTIONS[triviaIndex].correct) {
      setGameScore(prev => prev + 10);
    }
    // Next question
    setTriviaIndex((triviaIndex + 1) % TRIVIA_QUESTIONS.length);
  };

  // Handle word guess
  const handleWordGuess = () => {
    if (userGuess.toUpperCase() === currentWord) {
      setGameScore(prev => prev + 15);
      // New word
      const word = WORDS_TO_SCRAMBLE[Math.floor(Math.random() * WORDS_TO_SCRAMBLE.length)];
      setCurrentWord(word);
      setScrambledWord(scrambleWord(word));
    }
    setUserGuess('');
  };

  // Handle math answer
  const handleMathAnswer = () => {
    if (parseInt(mathAnswer) === mathProblem?.answer) {
      setGameScore(prev => prev + 10);
    }
    generateMathProblem();
  };

  return (
    <div className="bg-slate-800/50 rounded-xl border border-slate-700/50 p-6" data-testid="waiting-experience">
      {/* Progress Section */}
      <div className="mb-6">
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center gap-2">
            <Loader2 className="w-5 h-5 text-purple-400 animate-spin" />
            <span className="text-white font-medium">{message}</span>
          </div>
          <span className="text-purple-400 font-bold">{Math.round(progress)}%</span>
        </div>
        <Progress value={progress} className="h-3 bg-slate-700" />
        {estimatedTime && (
          <div className="flex items-center gap-1 mt-2 text-sm text-slate-400">
            <Clock className="w-4 h-4" />
            <span>Estimated: {estimatedTime}</span>
          </div>
        )}
      </div>

      {/* Try Other Features Button */}
      {onTryOtherFeature && (
        <div className="mb-6 p-4 bg-purple-500/20 rounded-lg border border-purple-500/30">
          <p className="text-purple-300 text-sm mb-3">
            Your generation is running in the background. Feel free to explore other features!
          </p>
          <Button 
            onClick={onTryOtherFeature}
            className="bg-purple-600 hover:bg-purple-700"
            data-testid="try-other-features-btn"
          >
            <Sparkles className="w-4 h-4 mr-2" />
            Try Other Features
            <ArrowRight className="w-4 h-4 ml-2" />
          </Button>
        </div>
      )}

      {/* Entertainment Section */}
      <div className="space-y-4">
        <h3 className="text-white font-semibold flex items-center gap-2">
          <Gamepad2 className="w-5 h-5 text-green-400" />
          While You Wait...
        </h3>

        {!activeGame ? (
          <>
            {/* Quote Display */}
            <div className="bg-slate-900/50 rounded-lg p-4 border border-slate-700/50" data-testid="quote-display">
              <Quote className="w-6 h-6 text-amber-400 mb-2" />
              <p className="text-white italic text-lg">"{currentQuote.text}"</p>
              <p className="text-slate-400 text-sm mt-2">— {currentQuote.author}</p>
            </div>

            {/* Mini Games Selection */}
            <div className="grid grid-cols-2 gap-3">
              {MINI_GAMES.map((game) => (
                <button
                  key={game.id}
                  onClick={() => startGame(game.id)}
                  className="p-4 bg-slate-900/50 rounded-lg border border-slate-700/50 hover:border-purple-500/50 transition-all text-left group"
                  data-testid={`game-${game.id}`}
                >
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-lg bg-purple-500/20 flex items-center justify-center group-hover:bg-purple-500/30">
                      <game.icon className="w-5 h-5 text-purple-400" />
                    </div>
                    <div>
                      <p className="text-white font-medium">{game.name}</p>
                      <p className="text-slate-400 text-xs">{game.description}</p>
                    </div>
                  </div>
                </button>
              ))}
            </div>
          </>
        ) : (
          /* Active Game UI */
          <div className="bg-slate-900/50 rounded-lg p-4 border border-slate-700/50">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-2">
                <Trophy className="w-5 h-5 text-amber-400" />
                <span className="text-amber-400 font-bold">Score: {gameScore}</span>
              </div>
              <Button 
                variant="ghost" 
                size="sm" 
                onClick={() => setActiveGame(null)}
                className="text-slate-400"
              >
                Back to Games
              </Button>
            </div>

            {/* Trivia Game */}
            {activeGame === 'trivia' && (
              <div className="space-y-4" data-testid="trivia-game">
                <p className="text-white text-lg">{TRIVIA_QUESTIONS[triviaIndex].q}</p>
                <div className="grid grid-cols-2 gap-2">
                  {TRIVIA_QUESTIONS[triviaIndex].a.map((answer, idx) => (
                    <Button
                      key={idx}
                      variant="outline"
                      onClick={() => handleTriviaAnswer(idx)}
                      className="border-slate-600 text-white hover:bg-purple-500/20"
                    >
                      {answer}
                    </Button>
                  ))}
                </div>
              </div>
            )}

            {/* Word Scramble Game */}
            {activeGame === 'word' && (
              <div className="space-y-4" data-testid="word-game">
                <p className="text-slate-400">Unscramble this word:</p>
                <p className="text-3xl font-bold text-purple-400 tracking-widest text-center">
                  {scrambledWord}
                </p>
                <div className="flex gap-2">
                  <input
                    type="text"
                    value={userGuess}
                    onChange={(e) => setUserGuess(e.target.value)}
                    onKeyDown={(e) => e.key === 'Enter' && handleWordGuess()}
                    placeholder="Your guess..."
                    className="flex-1 px-4 py-2 bg-slate-800 border border-slate-600 rounded-lg text-white"
                  />
                  <Button onClick={handleWordGuess} className="bg-purple-600">
                    Check
                  </Button>
                </div>
                <Button 
                  variant="ghost" 
                  size="sm"
                  onClick={() => {
                    const word = WORDS_TO_SCRAMBLE[Math.floor(Math.random() * WORDS_TO_SCRAMBLE.length)];
                    setCurrentWord(word);
                    setScrambledWord(scrambleWord(word));
                  }}
                  className="text-slate-400"
                >
                  <RefreshCw className="w-4 h-4 mr-2" />
                  Skip Word
                </Button>
              </div>
            )}

            {/* Math Game */}
            {activeGame === 'math' && mathProblem && (
              <div className="space-y-4" data-testid="math-game">
                <p className="text-slate-400">Solve this quickly:</p>
                <p className="text-3xl font-bold text-white text-center">
                  {mathProblem.a} {mathProblem.op} {mathProblem.b} = ?
                </p>
                <div className="flex gap-2">
                  <input
                    type="number"
                    value={mathAnswer}
                    onChange={(e) => setMathAnswer(e.target.value)}
                    onKeyDown={(e) => e.key === 'Enter' && handleMathAnswer()}
                    placeholder="Answer..."
                    className="flex-1 px-4 py-2 bg-slate-800 border border-slate-600 rounded-lg text-white text-center text-xl"
                  />
                  <Button onClick={handleMathAnswer} className="bg-purple-600">
                    Submit
                  </Button>
                </div>
              </div>
            )}

            {/* Memory Game - Placeholder */}
            {activeGame === 'memory' && (
              <div className="text-center py-8" data-testid="memory-game">
                <Brain className="w-16 h-16 text-purple-400 mx-auto mb-4" />
                <p className="text-white text-lg">Memory Match</p>
                <p className="text-slate-400 text-sm mt-2">
                  Watch the pattern and repeat it!
                </p>
                <div className="grid grid-cols-3 gap-2 mt-4 max-w-xs mx-auto">
                  {[1,2,3,4,5,6,7,8,9].map(n => (
                    <button
                      key={n}
                      className="w-12 h-12 bg-purple-500/20 rounded-lg hover:bg-purple-500/40 transition-colors"
                      onClick={() => setGameScore(prev => prev + 5)}
                    />
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

export { WaitingExperience };
