"""
Advanced ML-Based Threat Detection Module
Implements anomaly detection, bot detection, content moderation, and semantic analysis
"""
import logging
import re
import math
import hashlib
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Tuple
from collections import defaultdict
import statistics

logger = logging.getLogger(__name__)

# =============================================================================
# REQUEST PATTERN ANALYZER (Anomaly Detection)
# =============================================================================
class RequestPatternAnalyzer:
    """ML-based anomaly detection for request patterns"""
    
    def __init__(self):
        self.ip_history: Dict[str, List[dict]] = defaultdict(list)
        self.user_history: Dict[str, List[dict]] = defaultdict(list)
        self.baseline_stats: Dict[str, dict] = {}
        self.anomaly_threshold = 2.5  # Standard deviations
        self.burst_threshold = 50  # Requests per minute threshold
        self.sliding_window_minutes = 5
        
    def record_request(self, ip: str, user_id: Optional[str], endpoint: str, 
                       response_time: float, status_code: int):
        """Record a request for analysis"""
        now = datetime.now(timezone.utc)
        request_data = {
            "timestamp": now,
            "endpoint": endpoint,
            "response_time": response_time,
            "status_code": status_code
        }
        
        # Keep last 1000 requests per IP
        self.ip_history[ip].append(request_data)
        if len(self.ip_history[ip]) > 1000:
            self.ip_history[ip] = self.ip_history[ip][-500:]
        
        if user_id:
            self.user_history[user_id].append(request_data)
            if len(self.user_history[user_id]) > 1000:
                self.user_history[user_id] = self.user_history[user_id][-500:]
    
    def calculate_request_rate(self, history: List[dict], window_minutes: int = 1) -> float:
        """Calculate requests per minute"""
        if not history:
            return 0.0
        
        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(minutes=window_minutes)
        recent = [r for r in history if r["timestamp"] > cutoff]
        return len(recent) / window_minutes
    
    def detect_burst_attack(self, ip: str) -> Tuple[bool, str, float]:
        """Detect burst/DDoS attack patterns"""
        history = self.ip_history.get(ip, [])
        if len(history) < 5:
            return False, "", 0.0
        
        # Check requests in last minute
        rate_1min = self.calculate_request_rate(history, 1)
        rate_5min = self.calculate_request_rate(history, 5)
        
        # Sudden spike detection
        if rate_1min > self.burst_threshold:
            return True, f"Burst attack detected: {rate_1min:.0f} req/min", 0.95
        
        # Sustained high rate
        if rate_5min > self.burst_threshold / 2:
            return True, f"Sustained high rate: {rate_5min:.0f} req/min average", 0.8
        
        return False, "", 0.0
    
    def detect_anomaly(self, ip: str, user_id: Optional[str] = None) -> Tuple[bool, str, float]:
        """
        Detect anomalous behavior using statistical analysis
        Returns: (is_anomaly, reason, confidence_score)
        """
        history = self.ip_history.get(ip, [])
        if len(history) < 10:
            return False, "", 0.0
        
        # Check for burst attack first
        is_burst, burst_reason, burst_conf = self.detect_burst_attack(ip)
        if is_burst:
            return True, burst_reason, burst_conf
        
        # Calculate current metrics
        current_rate = self.calculate_request_rate(history, 1)
        recent_errors = len([r for r in history[-50:] if r["status_code"] >= 400])
        
        # Calculate baseline (historical average)
        rates = []
        for i in range(0, len(history) - 10, 10):
            window = history[i:i+10]
            if window:
                time_diff = (window[-1]["timestamp"] - window[0]["timestamp"]).total_seconds()
                if time_diff > 0:
                    rates.append(len(window) / (time_diff / 60))
        
        if not rates:
            return False, "", 0.0
        
        avg_rate = statistics.mean(rates)
        std_rate = statistics.stdev(rates) if len(rates) > 1 else avg_rate * 0.5
        
        # Anomaly detection using Z-score
        if std_rate > 0:
            z_score = (current_rate - avg_rate) / std_rate
        else:
            z_score = 0
        
        # High request rate anomaly
        if z_score > self.anomaly_threshold:
            confidence = min(1.0, z_score / 5.0)
            return True, f"Abnormal request rate: {current_rate:.1f}/min (avg: {avg_rate:.1f})", confidence
        
        # High error rate anomaly
        error_rate = recent_errors / 50 if len(history) >= 50 else recent_errors / len(history)
        if error_rate > 0.5:
            return True, f"High error rate: {error_rate*100:.0f}% of recent requests", error_rate
        
        return False, "", 0.0


# =============================================================================
# BOT DETECTION
# =============================================================================
class BotDetector:
    """ML-based bot detection using behavioral analysis"""
    
    # Known bot user agents patterns
    BOT_PATTERNS = [
        r'bot', r'crawler', r'spider', r'scraper', r'curl', r'wget',
        r'python-requests', r'python-urllib', r'java/', r'libwww',
        r'httpclient', r'okhttp', r'axios', r'node-fetch',
        r'phantomjs', r'headless', r'selenium', r'puppeteer'
    ]
    
    # Legitimate browser patterns
    BROWSER_PATTERNS = [
        r'Mozilla.*Chrome', r'Mozilla.*Firefox', r'Mozilla.*Safari',
        r'Mozilla.*Edge', r'Mozilla.*Opera'
    ]
    
    def __init__(self):
        self.ip_behavior: Dict[str, dict] = {}
        
    def analyze_user_agent(self, user_agent: str) -> Tuple[bool, float]:
        """
        Analyze user agent for bot indicators
        Returns: (is_bot, confidence)
        """
        if not user_agent:
            return True, 0.9  # No user agent is suspicious
        
        ua_lower = user_agent.lower()
        
        # Check for explicit bot patterns
        for pattern in self.BOT_PATTERNS:
            if re.search(pattern, ua_lower, re.IGNORECASE):
                return True, 0.95
        
        # Check for legitimate browser
        for pattern in self.BROWSER_PATTERNS:
            if re.search(pattern, user_agent):
                return False, 0.1
        
        # Suspicious if no recognized browser pattern
        return True, 0.6
    
    def analyze_behavior(self, ip: str, request_interval_ms: float, 
                        mouse_movements: bool, js_enabled: bool) -> Tuple[bool, float]:
        """
        Analyze request behavior for bot indicators
        Returns: (is_bot, confidence)
        """
        bot_score = 0.0
        
        # Very regular request intervals suggest automation
        if request_interval_ms > 0 and request_interval_ms < 100:
            bot_score += 0.3  # Too fast for human
        
        # No mouse movements in session
        if not mouse_movements:
            bot_score += 0.2
        
        # JavaScript disabled
        if not js_enabled:
            bot_score += 0.3
        
        return bot_score > 0.5, bot_score
    
    def is_bot(self, ip: str, user_agent: str, headers: dict) -> Tuple[bool, str, float]:
        """
        Comprehensive bot detection
        Returns: (is_bot, reason, confidence)
        """
        # Check user agent
        ua_is_bot, ua_confidence = self.analyze_user_agent(user_agent)
        
        if ua_is_bot and ua_confidence > 0.9:
            return True, "Bot user agent detected", ua_confidence
        
        # Check for missing standard browser headers
        missing_headers = []
        expected_headers = ['accept', 'accept-language', 'accept-encoding']
        for h in expected_headers:
            if h not in [k.lower() for k in headers.keys()]:
                missing_headers.append(h)
        
        if len(missing_headers) >= 2:
            return True, f"Missing browser headers: {missing_headers}", 0.7
        
        # Check for automation tool headers
        automation_headers = ['x-automation', 'x-selenium', 'x-puppeteer']
        for h in automation_headers:
            if h.lower() in [k.lower() for k in headers.keys()]:
                return True, f"Automation header detected: {h}", 0.99
        
        return False, "", ua_confidence


# =============================================================================
# ADVANCED CONTENT MODERATION (ML-based with Semantic Analysis)
# =============================================================================
class ContentModerator:
    """ML-based content moderation for AI generation prompts with semantic analysis"""
    
    # Severity levels
    SEVERITY_CRITICAL = "CRITICAL"  # Block immediately
    SEVERITY_HIGH = "HIGH"  # Block and log
    SEVERITY_MEDIUM = "MEDIUM"  # Warn and sanitize
    SEVERITY_LOW = "LOW"  # Monitor only
    
    # Content categories with patterns, severity, and semantic keywords
    CONTENT_RULES = {
        "identity_theft": {
            "patterns": [
                r"deepfake", r"face\s*swap", r"identity\s*clone",
                r"impersonate", r"fake\s*id", r"forge", r"clone\s*face",
                r"steal\s*identity", r"create\s*fake\s*video"
            ],
            "semantic_keywords": ["deepfake", "impersonate", "identity", "clone", "fake person"],
            "severity": SEVERITY_CRITICAL,
            "message": "Identity theft content is strictly prohibited"
        },
        "celebrity": {
            "patterns": [
                r"celebrity", r"famous\s*person", r"real\s*person",
                r"public\s*figure", r"politician", r"president",
                r"actor\s+name", r"singer\s+name", r"influencer"
            ],
            "semantic_keywords": ["celebrity", "famous", "real person", "public figure"],
            "severity": SEVERITY_HIGH,
            "message": "Celebrity/public figure content requires explicit consent"
        },
        "explicit": {
            "patterns": [
                r"nude", r"naked", r"porn", r"xxx", r"nsfw",
                r"sexual", r"erotic", r"adult\s*content", r"explicit",
                r"18\+", r"x-rated", r"lewd"
            ],
            "semantic_keywords": ["nude", "naked", "sexual", "explicit", "adult"],
            "severity": SEVERITY_CRITICAL,
            "message": "Explicit adult content is not allowed"
        },
        "violence": {
            "patterns": [
                r"gore", r"murder", r"torture", r"blood",
                r"violent\s*death", r"massacre", r"terrorist",
                r"kill\s*someone", r"execution", r"brutal"
            ],
            "semantic_keywords": ["gore", "violence", "murder", "torture", "brutal"],
            "severity": SEVERITY_CRITICAL,
            "message": "Violent or graphic content is prohibited"
        },
        "child_safety": {
            "patterns": [
                r"child\s*abuse", r"minor", r"underage",
                r"pedophil", r"child\s*exploit", r"young\s*child",
                r"inappropriate.*child"
            ],
            "semantic_keywords": ["child", "minor", "underage", "abuse"],
            "severity": SEVERITY_CRITICAL,
            "message": "Child safety violation detected"
        },
        "illegal": {
            "patterns": [
                r"drug\s*deal", r"cocaine", r"heroin", r"meth",
                r"weapon\s*sale", r"bomb\s*making", r"hack\s*into",
                r"illegal\s*activity", r"criminal"
            ],
            "semantic_keywords": ["drugs", "illegal", "hack", "weapon", "bomb"],
            "severity": SEVERITY_CRITICAL,
            "message": "Illegal activity content is prohibited"
        },
        "hate_speech": {
            "patterns": [
                r"racist", r"hate\s*speech", r"discriminat",
                r"supremac", r"ethnic\s*cleans", r"slur",
                r"bigot", r"xenophob"
            ],
            "semantic_keywords": ["racist", "hate", "discrimination", "supremacy"],
            "severity": SEVERITY_HIGH,
            "message": "Hate speech and discrimination are not allowed"
        },
        "scam": {
            "patterns": [
                r"phishing", r"scam", r"fraud", r"fake\s*website",
                r"steal\s*money", r"ponzi", r"get\s*rich\s*quick",
                r"pyramid\s*scheme"
            ],
            "semantic_keywords": ["scam", "fraud", "phishing", "steal money"],
            "severity": SEVERITY_HIGH,
            "message": "Scam/fraud content is prohibited"
        },
        "copyright": {
            "patterns": [
                r"copyright\s*infring", r"pirat", r"stolen\s*content",
                r"trademark\s*violat", r"without\s*permission"
            ],
            "semantic_keywords": ["copyright", "pirate", "stolen", "trademark"],
            "severity": SEVERITY_MEDIUM,
            "message": "Potential copyright concern detected"
        },
        "self_harm": {
            "patterns": [
                r"suicide", r"self\s*harm", r"cut\s*myself",
                r"end\s*my\s*life", r"kill\s*myself"
            ],
            "semantic_keywords": ["suicide", "self harm", "hurt myself"],
            "severity": SEVERITY_CRITICAL,
            "message": "Self-harm content is not allowed. If you need help, please reach out to a crisis helpline."
        },
        "misinformation": {
            "patterns": [
                r"fake\s*news", r"conspiracy", r"hoax",
                r"false\s*information", r"propaganda"
            ],
            "semantic_keywords": ["fake news", "conspiracy", "hoax", "misinformation"],
            "severity": SEVERITY_MEDIUM,
            "message": "Potential misinformation detected"
        }
    }
    
    # Toxicity indicators (contextual analysis)
    TOXICITY_PATTERNS = {
        "insult": [r"stupid", r"idiot", r"moron", r"dumb", r"loser"],
        "threat": [r"kill\s*you", r"hurt\s*you", r"destroy", r"attack"],
        "profanity": [r"f\*ck", r"sh\*t", r"damn", r"hell"],
        "harassment": [r"harass", r"stalk", r"bully", r"intimidate"]
    }
    
    def __init__(self):
        self.violation_history: Dict[str, List[dict]] = defaultdict(list)
        self.toxicity_cache: Dict[str, float] = {}
    
    def calculate_toxicity_score(self, text: str) -> float:
        """Calculate overall toxicity score (0-1)"""
        if not text:
            return 0.0
        
        text_lower = text.lower()
        toxicity = 0.0
        matches = 0
        
        for category, patterns in self.TOXICITY_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, text_lower, re.IGNORECASE):
                    matches += 1
                    if category == "threat":
                        toxicity += 0.4
                    elif category == "harassment":
                        toxicity += 0.3
                    elif category == "insult":
                        toxicity += 0.2
                    else:
                        toxicity += 0.1
        
        return min(1.0, toxicity)
    
    def semantic_similarity(self, text: str, keywords: List[str]) -> float:
        """Calculate semantic similarity with keywords"""
        if not text or not keywords:
            return 0.0
        
        text_words = set(text.lower().split())
        keyword_words = set()
        for kw in keywords:
            keyword_words.update(kw.lower().split())
        
        if not keyword_words:
            return 0.0
        
        overlap = len(text_words & keyword_words)
        return overlap / len(keyword_words)
    
    def moderate_content(self, text: str, user_id: Optional[str] = None) -> dict:
        """
        Analyze content for policy violations with advanced ML features
        Returns moderation result with action and details
        """
        if not text:
            return {"allowed": True, "violations": [], "action": "ALLOW", "toxicity_score": 0.0}
        
        text_lower = text.lower()
        violations = []
        max_severity = None
        
        # Calculate toxicity score
        toxicity_score = self.calculate_toxicity_score(text)
        
        for category, rule in self.CONTENT_RULES.items():
            # Pattern matching
            pattern_match = False
            for pattern in rule["patterns"]:
                if re.search(pattern, text_lower, re.IGNORECASE):
                    pattern_match = True
                    break
            
            # Semantic analysis
            semantic_score = self.semantic_similarity(text, rule.get("semantic_keywords", []))
            
            # Combined detection
            if pattern_match or semantic_score > 0.5:
                violation = {
                    "category": category,
                    "severity": rule["severity"],
                    "message": rule["message"],
                    "confidence": 0.95 if pattern_match else semantic_score,
                    "detection_method": "pattern" if pattern_match else "semantic"
                }
                violations.append(violation)
                
                # Track highest severity
                if max_severity is None or self._severity_rank(rule["severity"]) > self._severity_rank(max_severity):
                    max_severity = rule["severity"]
        
        # Record violation for repeat offender tracking
        if violations and user_id:
            self.violation_history[user_id].append({
                "timestamp": datetime.now(timezone.utc),
                "violations": violations,
                "toxicity_score": toxicity_score
            })
        
        # Determine action based on severity and toxicity
        if max_severity == self.SEVERITY_CRITICAL or toxicity_score > 0.8:
            action = "BLOCK"
            allowed = False
        elif max_severity == self.SEVERITY_HIGH or toxicity_score > 0.6:
            action = "BLOCK"
            allowed = False
        elif max_severity == self.SEVERITY_MEDIUM or toxicity_score > 0.4:
            action = "WARN"
            allowed = True  # Allow with warning
        else:
            action = "ALLOW"
            allowed = len(violations) == 0 and toxicity_score < 0.3
        
        return {
            "allowed": allowed,
            "violations": violations,
            "action": action,
            "severity": max_severity,
            "toxicity_score": toxicity_score,
            "analysis": {
                "total_violations": len(violations),
                "categories_flagged": list(set(v["category"] for v in violations))
            }
        }
    
    def _severity_rank(self, severity: str) -> int:
        """Get numeric rank for severity comparison"""
        ranks = {
            self.SEVERITY_LOW: 1,
            self.SEVERITY_MEDIUM: 2,
            self.SEVERITY_HIGH: 3,
            self.SEVERITY_CRITICAL: 4
        }
        return ranks.get(severity, 0)
    
    def is_repeat_offender(self, user_id: str, window_hours: int = 24) -> Tuple[bool, int]:
        """Check if user is a repeat offender"""
        if user_id not in self.violation_history:
            return False, 0
        
        cutoff = datetime.now(timezone.utc) - timedelta(hours=window_hours)
        recent = [v for v in self.violation_history[user_id] if v["timestamp"] > cutoff]
        
        return len(recent) >= 3, len(recent)
    
    def get_user_risk_score(self, user_id: str) -> float:
        """Calculate overall risk score for a user"""
        if user_id not in self.violation_history:
            return 0.0
        
        history = self.violation_history[user_id]
        if not history:
            return 0.0
        
        # Weight recent violations more heavily
        now = datetime.now(timezone.utc)
        weighted_score = 0.0
        
        for entry in history[-20:]:  # Last 20 violations
            age_hours = (now - entry["timestamp"]).total_seconds() / 3600
            decay = math.exp(-age_hours / 24)  # Decay over 24 hours
            
            violation_score = len(entry.get("violations", [])) * 0.2
            toxicity = entry.get("toxicity_score", 0)
            
            weighted_score += (violation_score + toxicity) * decay
        
        return min(1.0, weighted_score / 5)


# =============================================================================
# THREAT INTELLIGENCE AGGREGATOR
# =============================================================================
class ThreatIntelligence:
    """Aggregates all threat detection systems"""
    
    def __init__(self):
        self.pattern_analyzer = RequestPatternAnalyzer()
        self.bot_detector = BotDetector()
        self.content_moderator = ContentModerator()
        self.threat_scores: Dict[str, float] = {}
        self.blocked_ips: Dict[str, datetime] = {}
        self.block_duration_minutes = 30
        
    def is_ip_blocked(self, ip: str) -> Tuple[bool, Optional[datetime]]:
        """Check if IP is currently blocked"""
        if ip not in self.blocked_ips:
            return False, None
        
        block_time = self.blocked_ips[ip]
        if datetime.now(timezone.utc) - block_time > timedelta(minutes=self.block_duration_minutes):
            del self.blocked_ips[ip]
            return False, None
        
        return True, block_time
    
    def block_ip(self, ip: str, reason: str):
        """Block an IP address"""
        self.blocked_ips[ip] = datetime.now(timezone.utc)
        logger.warning(f"IP blocked: {ip} - {reason}")
    
    def analyze_request(self, ip: str, user_agent: str, headers: dict,
                       user_id: Optional[str] = None) -> dict:
        """
        Comprehensive threat analysis for a request
        Returns threat assessment
        """
        threats = []
        total_score = 0.0
        
        # Check if IP is blocked
        is_blocked, block_time = self.is_ip_blocked(ip)
        if is_blocked:
            return {
                "ip": ip,
                "threats": [{"type": "BLOCKED", "reason": "IP temporarily blocked"}],
                "threat_score": 1.0,
                "action": "BLOCK",
                "block_remaining_minutes": self.block_duration_minutes - int((datetime.now(timezone.utc) - block_time).total_seconds() / 60)
            }
        
        # Bot detection
        is_bot, bot_reason, bot_confidence = self.bot_detector.is_bot(ip, user_agent, headers)
        if is_bot:
            threats.append({
                "type": "BOT",
                "reason": bot_reason,
                "confidence": bot_confidence
            })
            total_score += bot_confidence * 0.4
        
        # Anomaly detection
        is_anomaly, anomaly_reason, anomaly_confidence = self.pattern_analyzer.detect_anomaly(ip, user_id)
        if is_anomaly:
            threats.append({
                "type": "ANOMALY",
                "reason": anomaly_reason,
                "confidence": anomaly_confidence
            })
            total_score += anomaly_confidence * 0.3
        
        # Update threat score with decay
        prev_score = self.threat_scores.get(ip, 0)
        self.threat_scores[ip] = min(1.0, prev_score * 0.95 + total_score * 0.1)
        
        # Auto-block if cumulative score is too high
        if self.threat_scores[ip] > 0.9:
            self.block_ip(ip, "Cumulative threat score exceeded threshold")
        
        action = "BLOCK" if total_score > 0.7 else "MONITOR" if total_score > 0.3 else "ALLOW"
        
        return {
            "ip": ip,
            "threats": threats,
            "threat_score": total_score,
            "cumulative_score": self.threat_scores[ip],
            "action": action
        }
    
    def moderate_content(self, text: str, user_id: Optional[str] = None) -> dict:
        """Content moderation wrapper with enhanced analysis"""
        result = self.content_moderator.moderate_content(text, user_id)
        
        # Check if user is repeat offender
        if user_id:
            is_repeat, violation_count = self.content_moderator.is_repeat_offender(user_id)
            result["is_repeat_offender"] = is_repeat
            result["violation_count_24h"] = violation_count
            result["user_risk_score"] = self.content_moderator.get_user_risk_score(user_id)
        
        return result
    
    def record_request(self, ip: str, user_id: Optional[str], endpoint: str,
                      response_time: float, status_code: int):
        """Record request for pattern analysis"""
        self.pattern_analyzer.record_request(ip, user_id, endpoint, response_time, status_code)
    
    def get_threat_stats(self) -> dict:
        """Get overall threat statistics"""
        return {
            "total_tracked_ips": len(self.threat_scores),
            "blocked_ips": len(self.blocked_ips),
            "high_risk_ips": len([ip for ip, score in self.threat_scores.items() if score > 0.7]),
            "medium_risk_ips": len([ip for ip, score in self.threat_scores.items() if 0.3 < score <= 0.7])
        }


# Global instance
threat_intel = ThreatIntelligence()

# =============================================================================
# EXPORTS
# =============================================================================
__all__ = [
    'RequestPatternAnalyzer',
    'BotDetector', 
    'ContentModerator',
    'ThreatIntelligence',
    'threat_intel'
]
