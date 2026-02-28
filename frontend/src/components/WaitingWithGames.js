import React, { useState, useEffect, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { 
  Loader2, Sparkles, Lightbulb, Puzzle, Gamepad2, Quote, Brain, 
  RefreshCw, Trophy, Star, Bell, ExternalLink, Clock, ArrowRight,
  Palette, Film, BookOpen, Image, Zap, Gift
} from 'lucide-react';
import { Button } from './ui/button';
import { Progress } from './ui/progress';

// Inspirational quotes for creators
const QUOTES = [
  { text: "Creativity is intelligence having fun.", author: "Albert Einstein" },
  { text: "Every child is an artist. The problem is how to remain an artist once we grow up.", author: "Pablo Picasso" },
  { text: "The chief enemy of creativity is good sense.", author: "Pablo Picasso" },
  { text: "Creativity takes courage.", author: "Henri Matisse" },
  { text: "You can't use up creativity. The more you use, the more you have.", author: "Maya Angelou" },
  { text: "Imagination is the beginning of creation.", author: "George Bernard Shaw" },
  { text: "The desire to create is one of the deepest yearnings of the human soul.", author: "Dieter F. Uchtdorf" },
  { text: "Don't think. Thinking is the enemy of creativity.", author: "Ray Bradbury" },
  { text: "Creativity is contagious. Pass it on.", author: "Albert Einstein" },
  { text: "Art is not what you see, but what you make others see.", author: "Edgar Degas" },
  { text: "The creative adult is the child who survived.", author: "Ursula K. Le Guin" },
  { text: "Create with the heart; build with the mind.", author: "Criss Jami" },
  { text: "Life isn't about finding yourself. Life is about creating yourself.", author: "George Bernard Shaw" },
  { text: "Everything you can imagine is real.", author: "Pablo Picasso" },
  { text: "The only way to do great work is to love what you do.", author: "Steve Jobs" },
];

// Word scramble puzzles
const WORD_SCRAMBLES = [
  { scrambled: "RCTAIVEE", answer: "CREATIVE", hint: "What you are being right now" },
  { scrambled: "NSIPIIAONRT", answer: "INSPIRATION", hint: "The spark that starts ideas" },
  { scrambled: "IAGMNAITNO", answer: "IMAGINATION", hint: "Where all stories begin" },
  { scrambled: "TNYFSAA", answer: "FANTASY", hint: "A genre of magic and wonder" },
  { scrambled: "HERTUPSO", answer: "SUPERHERO", hint: "They save the day" },
  { scrambled: "YDOTMEC", answer: "COMEDY", hint: "Makes you laugh" },
  { scrambled: "YSTMREY", answer: "MYSTERY", hint: "Full of suspense and clues" },
  { scrambled: "RUNCAEDTE", answer: "ADVENTURE", hint: "Exciting journeys await" },
  { scrambled: "CMOIC", answer: "COMIC", hint: "What you're creating!" },
  { scrambled: "RYTSO", answer: "STORY", hint: "Every great piece has one" },
];

// Quick math puzzles
const MATH_PUZZLES = [
  { question: "7 x 8 = ?", answer: 56, options: [54, 56, 58, 62] },
  { question: "144 ÷ 12 = ?", answer: 12, options: [10, 11, 12, 14] },
  { question: "23 + 49 = ?", answer: 72, options: [70, 71, 72, 73] },
  { question: "15 x 6 = ?", answer: 90, options: [85, 88, 90, 95] },
  { question: "81 ÷ 9 = ?", answer: 9, options: [7, 8, 9, 10] },
  { question: "Square root of 64?", answer: 8, options: [6, 7, 8, 9] },
  { question: "17 + 28 = ?", answer: 45, options: [43, 44, 45, 46] },
  { question: "96 ÷ 8 = ?", answer: 12, options: [10, 11, 12, 13] },
];

// Trivia questions
const TRIVIA = [
  { question: "Which planet is known as the Red Planet?", answer: "Mars", options: ["Venus", "Mars", "Jupiter", "Saturn"] },
  { question: "How many colors are in a rainbow?", answer: "7", options: ["5", "6", "7", "8"] },
  { question: "What is the largest ocean on Earth?", answer: "Pacific", options: ["Atlantic", "Pacific", "Indian", "Arctic"] },
  { question: "How many continents are there?", answer: "7", options: ["5", "6", "7", "8"] },
  { question: "What is the fastest land animal?", answer: "Cheetah", options: ["Lion", "Cheetah", "Tiger", "Leopard"] },
  { question: "Which element has the symbol 'Au'?", answer: "Gold", options: ["Silver", "Gold", "Copper", "Iron"] },
  { question: "How many sides does a hexagon have?", answer: "6", options: ["5", "6", "7", "8"] },
  { question: "What gas do plants breathe in?", answer: "CO2", options: ["O2", "CO2", "N2", "H2"] },
];

// Memory game patterns
const MEMORY_PATTERNS = ['circle', 'square', 'triangle', 'star', 'heart', 'diamond'];
const PATTERN_EMOJIS = {
  circle: '⭕',
  square: '⬛',
  triangle: '🔺',
  star: '⭐',
  heart: '❤️',
  diamond: '💎',
};

// Fun facts while waiting
const FUN_FACTS = [
  "Did you know? The first comic book was published in 1933!",
  "Fun fact: Walt Disney was rejected 302 times before getting financing for Disneyland.",
  "Did you know? The average person has about 70,000 thoughts per day!",
  "Fun fact: Creativity uses both sides of your brain simultaneously.",
  "Did you know? The word 'creativity' wasn't in the dictionary until 1875!",
  "Fun fact: Leonardo da Vinci could write with one hand while drawing with the other.",
  "Did you know? Playing games can boost your creativity by 50%!",
  "Fun fact: The most creative time of day is typically late evening.",
];

export default function WaitingWithGames({ 
  progress = 0, 
  status = "Generating...", 
  estimatedTime = "30-60 seconds",
  onCancel 
}) {
  const [activeGame, setActiveGame] = useState('quotes');
  const [currentQuote, setCurrentQuote] = useState(QUOTES[0]);
  const [currentPuzzle, setCurrentPuzzle] = useState(null);
  const [userAnswer, setUserAnswer] = useState('');
  const [score, setScore] = useState(0);
  const [streak, setStreak] = useState(0);
  const [feedback, setFeedback] = useState(null);
  const [memorySequence, setMemorySequence] = useState([]);
  const [userSequence, setUserSequence] = useState([]);
  const [memoryPhase, setMemoryPhase] = useState('watch'); // 'watch' | 'play'
  const [showingPattern, setShowingPattern] = useState(false);
  const [currentFactIndex, setCurrentFactIndex] = useState(0);

  // Rotate quotes every 8 seconds
  useEffect(() => {
    const interval = setInterval(() => {
      const randomQuote = QUOTES[Math.floor(Math.random() * QUOTES.length)];
      setCurrentQuote(randomQuote);
    }, 8000);
    return () => clearInterval(interval);
  }, []);

  // Rotate fun facts every 12 seconds
  useEffect(() => {
    const interval = setInterval(() => {
      setCurrentFactIndex(prev => (prev + 1) % FUN_FACTS.length);
    }, 12000);
    return () => clearInterval(interval);
  }, []);

  // Initialize puzzle when game changes
  useEffect(() => {
    if (activeGame === 'wordscramble') {
      setCurrentPuzzle(WORD_SCRAMBLES[Math.floor(Math.random() * WORD_SCRAMBLES.length)]);
      setUserAnswer('');
      setFeedback(null);
    } else if (activeGame === 'math') {
      setCurrentPuzzle(MATH_PUZZLES[Math.floor(Math.random() * MATH_PUZZLES.length)]);
      setFeedback(null);
    } else if (activeGame === 'trivia') {
      setCurrentPuzzle(TRIVIA[Math.floor(Math.random() * TRIVIA.length)]);
      setFeedback(null);
    } else if (activeGame === 'memory') {
      startNewMemoryGame();
    }
  }, [activeGame]);

  const startNewMemoryGame = useCallback(() => {
    const newSequence = [];
    for (let i = 0; i < 3 + Math.floor(score / 2); i++) {
      newSequence.push(MEMORY_PATTERNS[Math.floor(Math.random() * MEMORY_PATTERNS.length)]);
    }
    setMemorySequence(newSequence);
    setUserSequence([]);
    setMemoryPhase('watch');
    setShowingPattern(true);
    
    // Show pattern for 2 seconds
    setTimeout(() => {
      setShowingPattern(false);
      setMemoryPhase('play');
    }, 2000 + newSequence.length * 500);
  }, [score]);

  const handleWordGuess = () => {
    if (!currentPuzzle) return;
    
    if (userAnswer.toUpperCase() === currentPuzzle.answer) {
      setFeedback({ type: 'correct', message: 'Correct! Great job!' });
      setScore(prev => prev + 10);
      setStreak(prev => prev + 1);
      setTimeout(() => {
        setCurrentPuzzle(WORD_SCRAMBLES[Math.floor(Math.random() * WORD_SCRAMBLES.length)]);
        setUserAnswer('');
        setFeedback(null);
      }, 1500);
    } else {
      setFeedback({ type: 'wrong', message: `Not quite! The answer was ${currentPuzzle.answer}` });
      setStreak(0);
      setTimeout(() => {
        setCurrentPuzzle(WORD_SCRAMBLES[Math.floor(Math.random() * WORD_SCRAMBLES.length)]);
        setUserAnswer('');
        setFeedback(null);
      }, 2000);
    }
  };

  const handleMultipleChoice = (answer) => {
    if (!currentPuzzle) return;
    
    const isCorrect = activeGame === 'math' 
      ? answer === currentPuzzle.answer 
      : answer === currentPuzzle.answer;
    
    if (isCorrect) {
      setFeedback({ type: 'correct', message: 'Correct!' });
      setScore(prev => prev + 10);
      setStreak(prev => prev + 1);
    } else {
      setFeedback({ type: 'wrong', message: `Oops! The answer was ${currentPuzzle.answer}` });
      setStreak(0);
    }
    
    setTimeout(() => {
      const puzzles = activeGame === 'math' ? MATH_PUZZLES : TRIVIA;
      setCurrentPuzzle(puzzles[Math.floor(Math.random() * puzzles.length)]);
      setFeedback(null);
    }, 1500);
  };

  const handleMemoryClick = (pattern) => {
    if (memoryPhase !== 'play') return;
    
    const newUserSequence = [...userSequence, pattern];
    setUserSequence(newUserSequence);
    
    // Check if correct so far
    if (memorySequence[newUserSequence.length - 1] !== pattern) {
      setFeedback({ type: 'wrong', message: 'Oops! Try again!' });
      setStreak(0);
      setTimeout(startNewMemoryGame, 1500);
      return;
    }
    
    // Check if sequence complete
    if (newUserSequence.length === memorySequence.length) {
      setFeedback({ type: 'correct', message: 'Perfect memory!' });
      setScore(prev => prev + memorySequence.length * 5);
      setStreak(prev => prev + 1);
      setTimeout(startNewMemoryGame, 1500);
    }
  };

  const renderQuotes = () => (
    <div className="text-center space-y-4">
      <Quote className="w-12 h-12 mx-auto text-indigo-400 opacity-50" />
      <blockquote className="text-xl text-white font-light italic leading-relaxed">
        "{currentQuote.text}"
      </blockquote>
      <p className="text-indigo-300 font-medium">— {currentQuote.author}</p>
      <p className="text-slate-400 text-sm mt-4">{FUN_FACTS[currentFactIndex]}</p>
    </div>
  );

  const renderWordScramble = () => (
    <div className="text-center space-y-4">
      <Puzzle className="w-10 h-10 mx-auto text-purple-400" />
      <h3 className="text-lg text-white font-semibold">Unscramble the Word</h3>
      {currentPuzzle && (
        <>
          <div className="text-3xl font-bold text-amber-400 tracking-widest">
            {currentPuzzle.scrambled}
          </div>
          <p className="text-slate-400 text-sm">Hint: {currentPuzzle.hint}</p>
          <div className="flex gap-2 justify-center">
            <input
              type="text"
              value={userAnswer}
              onChange={(e) => setUserAnswer(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleWordGuess()}
              placeholder="Your answer..."
              className="px-4 py-2 bg-slate-800 border border-slate-600 rounded-lg text-white text-center uppercase"
              autoFocus
            />
            <Button onClick={handleWordGuess} className="bg-purple-600 hover:bg-purple-700">
              Check
            </Button>
          </div>
        </>
      )}
    </div>
  );

  const renderMath = () => (
    <div className="text-center space-y-4">
      <Brain className="w-10 h-10 mx-auto text-green-400" />
      <h3 className="text-lg text-white font-semibold">Quick Math</h3>
      {currentPuzzle && (
        <>
          <div className="text-2xl font-bold text-white">{currentPuzzle.question}</div>
          <div className="grid grid-cols-2 gap-3 max-w-xs mx-auto">
            {currentPuzzle.options.map((option, idx) => (
              <Button
                key={idx}
                onClick={() => handleMultipleChoice(option)}
                disabled={feedback !== null}
                className="bg-slate-700 hover:bg-slate-600 text-lg py-3"
              >
                {option}
              </Button>
            ))}
          </div>
        </>
      )}
    </div>
  );

  const renderTrivia = () => (
    <div className="text-center space-y-4">
      <Lightbulb className="w-10 h-10 mx-auto text-yellow-400" />
      <h3 className="text-lg text-white font-semibold">Trivia Time</h3>
      {currentPuzzle && (
        <>
          <div className="text-lg text-white">{currentPuzzle.question}</div>
          <div className="grid grid-cols-2 gap-3 max-w-md mx-auto">
            {currentPuzzle.options.map((option, idx) => (
              <Button
                key={idx}
                onClick={() => handleMultipleChoice(option)}
                disabled={feedback !== null}
                className="bg-slate-700 hover:bg-slate-600"
              >
                {option}
              </Button>
            ))}
          </div>
        </>
      )}
    </div>
  );

  const renderMemory = () => (
    <div className="text-center space-y-4">
      <Gamepad2 className="w-10 h-10 mx-auto text-pink-400" />
      <h3 className="text-lg text-white font-semibold">Memory Game</h3>
      <p className="text-slate-400 text-sm">
        {memoryPhase === 'watch' ? 'Watch the pattern...' : 'Repeat the pattern!'}
      </p>
      
      {showingPattern && (
        <div className="flex justify-center gap-2 py-4">
          {memorySequence.map((pattern, idx) => (
            <span key={idx} className="text-3xl animate-pulse">
              {PATTERN_EMOJIS[pattern]}
            </span>
          ))}
        </div>
      )}
      
      {memoryPhase === 'play' && !showingPattern && (
        <div className="grid grid-cols-3 gap-3 max-w-xs mx-auto">
          {MEMORY_PATTERNS.map((pattern) => (
            <Button
              key={pattern}
              onClick={() => handleMemoryClick(pattern)}
              className="bg-slate-700 hover:bg-slate-600 text-2xl py-4"
            >
              {PATTERN_EMOJIS[pattern]}
            </Button>
          ))}
        </div>
      )}
      
      {userSequence.length > 0 && (
        <div className="flex justify-center gap-1">
          {userSequence.map((pattern, idx) => (
            <span key={idx} className="text-xl">{PATTERN_EMOJIS[pattern]}</span>
          ))}
        </div>
      )}
    </div>
  );

  return (
    <div className="w-full max-w-lg mx-auto p-6 bg-slate-900/80 border border-slate-700 rounded-2xl backdrop-blur-sm">
      {/* Progress Section */}
      <div className="text-center mb-6">
        <div className="flex items-center justify-center gap-2 mb-3">
          <Loader2 className="w-6 h-6 text-indigo-400 animate-spin" />
          <span className="text-white font-medium">{status}</span>
        </div>
        <Progress value={progress} className="h-2 mb-2" />
        <p className="text-slate-400 text-sm">Estimated time: {estimatedTime}</p>
      </div>

      {/* Score Display */}
      {score > 0 && (
        <div className="flex items-center justify-center gap-4 mb-4">
          <div className="flex items-center gap-1 text-amber-400">
            <Trophy className="w-4 h-4" />
            <span className="font-bold">{score}</span>
          </div>
          {streak > 1 && (
            <div className="flex items-center gap-1 text-orange-400">
              <Star className="w-4 h-4" />
              <span className="text-sm">{streak} streak!</span>
            </div>
          )}
        </div>
      )}

      {/* Game Tabs */}
      <div className="flex justify-center gap-2 mb-6 flex-wrap">
        {[
          { id: 'quotes', icon: Quote, label: 'Quotes' },
          { id: 'wordscramble', icon: Puzzle, label: 'Words' },
          { id: 'math', icon: Brain, label: 'Math' },
          { id: 'trivia', icon: Lightbulb, label: 'Trivia' },
          { id: 'memory', icon: Gamepad2, label: 'Memory' },
        ].map(({ id, icon: Icon, label }) => (
          <button
            key={id}
            onClick={() => setActiveGame(id)}
            className={`flex items-center gap-1 px-3 py-1.5 rounded-full text-sm transition-all ${
              activeGame === id
                ? 'bg-indigo-600 text-white'
                : 'bg-slate-800 text-slate-400 hover:text-white'
            }`}
          >
            <Icon className="w-4 h-4" />
            {label}
          </button>
        ))}
      </div>

      {/* Feedback */}
      {feedback && (
        <div className={`text-center mb-4 py-2 px-4 rounded-lg ${
          feedback.type === 'correct' 
            ? 'bg-green-500/20 text-green-400' 
            : 'bg-red-500/20 text-red-400'
        }`}>
          {feedback.message}
        </div>
      )}

      {/* Game Content */}
      <div className="min-h-[200px] flex items-center justify-center">
        {activeGame === 'quotes' && renderQuotes()}
        {activeGame === 'wordscramble' && renderWordScramble()}
        {activeGame === 'math' && renderMath()}
        {activeGame === 'trivia' && renderTrivia()}
        {activeGame === 'memory' && renderMemory()}
      </div>

      {/* Tip */}
      <p className="text-center text-slate-500 text-xs mt-6">
        <Sparkles className="w-3 h-3 inline mr-1" />
        Play games while you wait to earn bonus points!
      </p>

      {/* Cancel Button */}
      {onCancel && (
        <div className="text-center mt-4">
          <Button variant="outline" size="sm" onClick={onCancel}>
            Cancel Generation
          </Button>
        </div>
      )}
    </div>
  );
}
