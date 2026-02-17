"""
Advanced ML-Based Threat Detection Module
Implements anomaly detection, bot detection, and content moderation
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
    
    def detect_anomaly(self, ip: str, user_id: Optional[str] = None) -> Tuple[bool, str, float]:
        """
        Detect anomalous behavior using statistical analysis
        Returns: (is_anomaly, reason, confidence_score)
        """
        history = self.ip_history.get(ip, [])
        if len(history) < 10:
            return False, "", 0.0
        
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
# CONTENT MODERATION (ML-based)
# =============================================================================
class ContentModerator:
    """ML-based content moderation for AI generation prompts"""
    
    # Severity levels
    SEVERITY_CRITICAL = "CRITICAL"  # Block immediately
    SEVERITY_HIGH = "HIGH"  # Block and log
    SEVERITY_MEDIUM = "MEDIUM"  # Warn and sanitize
    SEVERITY_LOW = "LOW"  # Monitor only
    
    # Content categories with patterns and severity
    CONTENT_RULES = {
        "identity_theft": {
            "patterns": [
                r"deepfake", r"face\s*swap", r"identity\s*clone",
                r"impersonate", r"fake\s*id", r"forge"
            ],
            "severity": SEVERITY_CRITICAL,
            "message": "Identity theft content is strictly prohibited"
        },
        "celebrity": {
            "patterns": [
                r"celebrity", r"famous\s*person", r"real\s*person",
                r"public\s*figure", r"politician", r"president"
            ],
            "severity": SEVERITY_HIGH,
            "message": "Celebrity/public figure content requires explicit consent"
        },
        "explicit": {
            "patterns": [
                r"nude", r"naked", r"porn", r"xxx", r"nsfw",
                r"sexual", r"erotic", r"adult\s*content"
            ],
            "severity": SEVERITY_CRITICAL,
            "message": "Explicit adult content is not allowed"
        },
        "violence": {
            "patterns": [
                r"gore", r"murder", r"torture", r"blood",
                r"violent\s*death", r"massacre", r"terrorist"
            ],
            "severity": SEVERITY_CRITICAL,
            "message": "Violent or graphic content is prohibited"
        },
        "child_safety": {
            "patterns": [
                r"child\s*abuse", r"minor", r"underage",
                r"pedophil", r"child\s*exploit"
            ],
            "severity": SEVERITY_CRITICAL,
            "message": "Child safety violation detected"
        },
        "illegal": {
            "patterns": [
                r"drug\s*deal", r"cocaine", r"heroin", r"meth",
                r"weapon\s*sale", r"bomb\s*making", r"hack\s*into"
            ],
            "severity": SEVERITY_CRITICAL,
            "message": "Illegal activity content is prohibited"
        },
        "hate_speech": {
            "patterns": [
                r"racist", r"hate\s*speech", r"discriminat",
                r"supremac", r"ethnic\s*cleans"
            ],
            "severity": SEVERITY_HIGH,
            "message": "Hate speech and discrimination are not allowed"
        },
        "scam": {
            "patterns": [
                r"phishing", r"scam", r"fraud", r"fake\s*website",
                r"steal\s*money", r"ponzi"
            ],
            "severity": SEVERITY_HIGH,
            "message": "Scam/fraud content is prohibited"
        },
        "copyright": {
            "patterns": [
                r"copyright\s*infring", r"pirat", r"stolen\s*content",
                r"trademark\s*violat"
            ],
            "severity": SEVERITY_MEDIUM,
            "message": "Potential copyright concern detected"
        }
    }
    
    def __init__(self):
        self.violation_history: Dict[str, List[dict]] = defaultdict(list)
    
    def moderate_content(self, text: str, user_id: Optional[str] = None) -> dict:
        """
        Analyze content for policy violations
        Returns moderation result with action and details
        """
        if not text:
            return {"allowed": True, "violations": [], "action": "ALLOW"}
        
        text_lower = text.lower()
        violations = []
        max_severity = None
        
        for category, rule in self.CONTENT_RULES.items():
            for pattern in rule["patterns"]:
                if re.search(pattern, text_lower, re.IGNORECASE):
                    violation = {
                        "category": category,
                        "severity": rule["severity"],
                        "message": rule["message"],
                        "matched_pattern": pattern
                    }
                    violations.append(violation)
                    
                    # Track highest severity
                    if max_severity is None or self._severity_rank(rule["severity"]) > self._severity_rank(max_severity):
                        max_severity = rule["severity"]
                    
                    break  # One match per category is enough
        
        # Record violation for repeat offender tracking
        if violations and user_id:
            self.violation_history[user_id].append({
                "timestamp": datetime.now(timezone.utc),
                "violations": violations
            })
        
        # Determine action
        if max_severity == self.SEVERITY_CRITICAL:
            action = "BLOCK"
            allowed = False
        elif max_severity == self.SEVERITY_HIGH:
            action = "BLOCK"
            allowed = False
        elif max_severity == self.SEVERITY_MEDIUM:
            action = "WARN"
            allowed = True  # Allow with warning
        else:
            action = "ALLOW"
            allowed = len(violations) == 0
        
        return {
            "allowed": allowed,
            "violations": violations,
            "action": action,
            "severity": max_severity
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
        
    def analyze_request(self, ip: str, user_agent: str, headers: dict,
                       user_id: Optional[str] = None) -> dict:
        """
        Comprehensive threat analysis for a request
        Returns threat assessment
        """
        threats = []
        total_score = 0.0
        
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
        
        # Update threat score
        self.threat_scores[ip] = min(1.0, self.threat_scores.get(ip, 0) * 0.9 + total_score * 0.1)
        
        return {
            "ip": ip,
            "threats": threats,
            "threat_score": total_score,
            "cumulative_score": self.threat_scores[ip],
            "action": "BLOCK" if total_score > 0.7 else "MONITOR" if total_score > 0.3 else "ALLOW"
        }
    
    def moderate_content(self, text: str, user_id: Optional[str] = None) -> dict:
        """Content moderation wrapper"""
        return self.content_moderator.moderate_content(text, user_id)
    
    def record_request(self, ip: str, user_id: Optional[str], endpoint: str,
                      response_time: float, status_code: int):
        """Record request for pattern analysis"""
        self.pattern_analyzer.record_request(ip, user_id, endpoint, response_time, status_code)


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
