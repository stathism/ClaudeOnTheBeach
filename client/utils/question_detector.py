"""
Enhanced Question Detector Module
Handles detection and similarity checking of questions with improved accuracy
"""

import re
import time
from typing import Optional, Dict, List, Tuple
from difflib import SequenceMatcher
from collections import deque

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import Config


class QuestionDetector:
    """Enhanced question detection and similarity checking with confidence scoring"""
    
    def __init__(self):
        self.last_question_sent = ""
        self.question_history = deque(maxlen=Config.QUESTION_CONTEXT_WINDOW)
        self.question_timestamps = deque(maxlen=Config.QUESTION_CONTEXT_WINDOW)
        self.last_question_time = 0
    
    def is_question(self, status_info: dict) -> Tuple[bool, float, str]:
        """
        Enhanced question detection with confidence scoring
        
        Args:
            status_info: LLM analysis result
            
        Returns:
            Tuple of (is_question, confidence_score, question_type)
        """
        if not status_info.get('needs_input', False) or not status_info.get('question'):
            return False, 0.0, "none"
        
        question_text = status_info['question']
        confidence, question_type = self._analyze_question_confidence(question_text)
        
        return True, confidence, question_type
    
    def _analyze_question_confidence(self, question_text: str) -> Tuple[float, str]:
        """
        Analyze question confidence and type
        
        Args:
            question_text: The question text to analyze
            
        Returns:
            Tuple of (confidence_score, question_type)
        """
        question_lower = question_text.lower()
        max_confidence = 0.0
        detected_type = "unknown"
        
        # Check high confidence patterns
        for pattern in Config.QUESTION_DETECTION_PATTERNS['high_confidence']:
            if pattern in question_lower:
                max_confidence = max(max_confidence, 0.95)
                detected_type = "high_confidence"
                break
        
        # Check medium confidence patterns
        if max_confidence < 0.95:
            for pattern in Config.QUESTION_DETECTION_PATTERNS['medium_confidence']:
                if pattern in question_lower:
                    max_confidence = max(max_confidence, 0.85)
                    detected_type = "medium_confidence"
                    break
        
        # Check low confidence patterns
        if max_confidence < 0.85:
            for pattern in Config.QUESTION_DETECTION_PATTERNS['low_confidence']:
                if pattern in question_lower:
                    max_confidence = max(max_confidence, 0.70)
                    detected_type = "low_confidence"
                    break
        
        # Check specialized patterns
        for pattern_type, patterns in Config.QUESTION_DETECTION_PATTERNS.items():
            if pattern_type in ['high_confidence', 'medium_confidence', 'low_confidence']:
                continue
            
            for pattern in patterns:
                if pattern in question_lower:
                    if pattern_type == 'file_operations':
                        max_confidence = max(max_confidence, 0.90)
                        detected_type = "file_operation"
                    elif pattern_type == 'permissions':
                        max_confidence = max(max_confidence, 0.88)
                        detected_type = "permission"
                    elif pattern_type == 'configuration':
                        max_confidence = max(max_confidence, 0.85)
                        detected_type = "configuration"
                    break
        
        # Check for question marks and other punctuation
        if '?' in question_text:
            max_confidence = max(max_confidence, 0.80)
            if detected_type == "unknown":
                detected_type = "general"
        
        # Check for numbered options (1., 2., 3.)
        if re.search(r'\d+\.', question_text):
            max_confidence = max(max_confidence, 0.92)
            detected_type = "numbered_options"
        
        # Check for selection indicators (❯, >, *)
        if re.search(r'[❯>*]', question_text):
            max_confidence = max(max_confidence, 0.90)
            detected_type = "selection_menu"
        
        # Check for yes/no patterns
        if re.search(r'\b(yes|no|y|n)\b', question_lower):
            max_confidence = max(max_confidence, 0.88)
            detected_type = "yes_no"
        
        return max_confidence, detected_type
    
    def is_same_question(self, current_question: str, previous_question: str) -> Tuple[bool, float, str]:
        """
        Enhanced similarity checking with confidence scoring
        
        Args:
            current_question: Current question text
            previous_question: Previous question text
            
        Returns:
            Tuple of (is_same, similarity_score, reason)
        """
        if not current_question or not previous_question:
            return False, 0.0, "empty_question"
        
        # Normalize both questions for comparison
        current_q = current_question.strip().lower()
        last_q = previous_question.strip().lower()
        
        # Exact match
        if current_q == last_q:
            return True, 1.0, "exact_match"
        
        # Check for high similarity using multiple methods
        similarity_score, reason = self._calculate_question_similarity(current_q, last_q)
        
        # Determine if they're the same based on similarity score
        is_same = similarity_score >= Config.QUESTION_SIMILARITY_THRESHOLD
        
        return is_same, similarity_score, reason
    
    def _calculate_question_similarity(self, q1: str, q2: str) -> Tuple[float, str]:
        """
        Calculate similarity between two questions using multiple methods
        
        Args:
            q1: First question
            q2: Second question
            
        Returns:
            Tuple of (similarity_score, reason)
        """
        # Method 1: Sequence matcher similarity
        sequence_similarity = SequenceMatcher(None, q1, q2).ratio()
        
        # Method 2: Word-based similarity
        word_similarity = self._word_based_similarity(q1, q2)
        
        # Method 3: Pattern-based similarity
        pattern_similarity = self._pattern_based_similarity(q1, q2)
        
        # Method 4: Semantic similarity (using key phrases)
        semantic_similarity = self._semantic_similarity(q1, q2)
        
        # Combine similarities (weighted average)
        combined_similarity = (
            sequence_similarity * 0.3 +
            word_similarity * 0.3 +
            pattern_similarity * 0.2 +
            semantic_similarity * 0.2
        )
        
        # Determine the reason
        if combined_similarity >= Config.QUESTION_SIMILARITY_HIGH:
            reason = "high_similarity"
        elif combined_similarity >= Config.QUESTION_SIMILARITY_MEDIUM:
            reason = "medium_similarity"
        elif combined_similarity >= Config.QUESTION_SIMILARITY_LOW:
            reason = "low_similarity"
        else:
            reason = "different_questions"
        
        return combined_similarity, reason
    
    def _word_based_similarity(self, q1: str, q2: str) -> float:
        """Calculate similarity based on word overlap"""
        words1 = set(q1.split())
        words2 = set(q2.split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        return len(intersection) / len(union) if union else 0.0
    
    def _pattern_based_similarity(self, q1: str, q2: str) -> float:
        """Calculate similarity based on pattern matching"""
        # Check if both questions contain the same patterns
        patterns1 = self._extract_patterns(q1)
        patterns2 = self._extract_patterns(q2)
        
        if not patterns1 and not patterns2:
            return 0.5  # Neutral if no patterns
        
        if not patterns1 or not patterns2:
            return 0.0  # Different if one has patterns and other doesn't
        
        intersection = patterns1.intersection(patterns2)
        union = patterns1.union(patterns2)
        
        return len(intersection) / len(union) if union else 0.0
    
    def _extract_patterns(self, text: str) -> set:
        """Extract meaningful patterns from text"""
        patterns = set()
        
        # Extract file names
        file_patterns = re.findall(r'\b\w+\.\w+\b', text)
        patterns.update(file_patterns)
        
        # Extract numbers
        number_patterns = re.findall(r'\b\d+\b', text)
        patterns.update(number_patterns)
        
        # Extract key phrases
        for pattern_type, pattern_list in Config.QUESTION_DETECTION_PATTERNS.items():
            for pattern in pattern_list:
                if pattern in text:
                    patterns.add(pattern)
        
        return patterns
    
    def _semantic_similarity(self, q1: str, q2: str) -> float:
        """Calculate semantic similarity using key concepts"""
        # Extract key concepts from both questions
        concepts1 = self._extract_concepts(q1)
        concepts2 = self._extract_concepts(q2)
        
        if not concepts1 and not concepts2:
            return 0.5  # Neutral if no concepts
        
        if not concepts1 or not concepts2:
            return 0.0  # Different if one has concepts and other doesn't
        
        intersection = concepts1.intersection(concepts2)
        union = concepts1.union(concepts2)
        
        return len(intersection) / len(union) if union else 0.0
    
    def _extract_concepts(self, text: str) -> set:
        """Extract key concepts from text"""
        concepts = set()
        
        # Common question concepts
        question_concepts = {
            'file', 'directory', 'path', 'name', 'create', 'edit', 'delete',
            'install', 'configure', 'setup', 'permission', 'access',
            'framework', 'library', 'package', 'version', 'option',
            'choice', 'select', 'confirm', 'proceed', 'continue'
        }
        
        text_lower = text.lower()
        for concept in question_concepts:
            if concept in text_lower:
                concepts.add(concept)
        
        return concepts
    
    def _questions_are_similar(self, q1: str, q2: str, threshold: float = 0.8) -> bool:
        """
        Check if two questions are similar using sequence matching
        
        Args:
            q1: First question
            q2: Second question
            threshold: Similarity threshold (0.0 to 1.0)
            
        Returns:
            True if questions are similar above threshold
        """
        # Remove common words that don't affect meaning
        common_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by'}
        
        def clean_text(text: str) -> str:
            words = text.split()
            filtered_words = [word for word in words if word.lower() not in common_words]
            return ' '.join(filtered_words)
        
        clean_q1 = clean_text(q1)
        clean_q2 = clean_text(q2)
        
        # Use sequence matcher for similarity
        similarity = SequenceMatcher(None, clean_q1, clean_q2).ratio()
        return similarity >= threshold
    
    def _is_file_edit_question(self, question: str) -> bool:
        """
        Check if this is a file edit confirmation question
        
        Args:
            question: Question text to check
            
        Returns:
            True if this is a file edit question
        """
        file_edit_indicators = [
            'do you want to create',
            'do you want to edit',
            'do you want to make this edit',
            'edit confirmation',
            'file edit',
            'make this edit'
        ]
        
        return any(indicator in question.lower() for indicator in file_edit_indicators)
    
    def update_last_question(self, question: str, confidence: float = 0.0, question_type: str = "unknown") -> None:
        """
        Update the last question with enhanced tracking
        
        Args:
            question: New question text
            confidence: Confidence score for the question
            question_type: Type of question detected
        """
        current_time = time.time()
        
        # Update last question
        self.last_question_sent = question
        self.last_question_time = current_time
        
        # Add to history
        self.question_history.append({
            'question': question,
            'confidence': confidence,
            'type': question_type,
            'timestamp': current_time
        })
        self.question_timestamps.append(current_time)
    
    def clear_last_question(self) -> None:
        """Clear the last question and history"""
        self.last_question_sent = ""
        self.last_question_time = 0
        self.question_history.clear()
        self.question_timestamps.clear()
    
    def get_last_question(self) -> str:
        """
        Get the last question sent
        
        Returns:
            Last question text or empty string
        """
        return self.last_question_sent
    

    
    def is_recent_question(self, question: str, time_window: int = 60) -> bool:
        """
        Check if this question was asked recently
        
        Args:
            question: Question to check
            time_window: Time window in seconds
            
        Returns:
            True if question was asked recently
        """
        current_time = time.time()
        
        for q_data in self.question_history:
            if current_time - q_data['timestamp'] <= time_window:
                is_same, similarity, _ = self.is_same_question(question, q_data['question'])
                if is_same:
                    return True
        
        return False
    

    
    def should_send_question_notification(self, question: str, confidence: float) -> bool:
        """
        Determine if a question notification should be sent
        
        Args:
            question: Question text
            confidence: Confidence score
            
        Returns:
            True if notification should be sent
        """
        # High confidence questions should always be sent
        if confidence >= 0.85:
            return True
        
        # Check if this is a recent duplicate
        if self.is_recent_question(question, time_window=30):
            return False
        
        # Medium confidence questions should be sent unless very recent
        if confidence >= 0.70:
            return not self.is_recent_question(question, time_window=10)
        
        # Low confidence questions only if not recent
        return not self.is_recent_question(question, time_window=5)
