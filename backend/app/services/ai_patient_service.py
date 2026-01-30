# backend/app/services/ai_patient_service.py

"""
AI Patient Analysis Service
Generates AI-powered patient summaries and referral recommendations using OpenAI API
"""

import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.core.config import Settings
from app.models.ai_patient_analysis import AIPatientAnalysis
from app.models.clinical_event import ClinicalEvent
from app.models.patient import Patient
from app.models.referral import Referral
from app.schemas.ai_analysis import AIPatientSummary, AIReferralRecommendation

logger = logging.getLogger(__name__)

# TODO: Add your OpenAI API key to .env file
# OPENAI_API_KEY=your-api-key-here

try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    logger.warning("OpenAI package not installed. Install with: pip install openai")


class AIPatientService:
    """Service for generating AI-powered patient analysis"""
    
    def __init__(self, db: Session, settings: Settings):
        self.db = db
        self.settings = settings
        
        # Initialize OpenAI client if available
        if OPENAI_AVAILABLE and hasattr(settings, 'OPENAI_API_KEY'):
            openai.api_key = settings.OPENAI_API_KEY
            self.openai_enabled = True
        else:
            self.openai_enabled = False
            logger.warning("OpenAI API not configured. AI features will return mock data.")
    
    def get_patient_complete_data(self, patient_id: UUID) -> Optional[Dict[str, Any]]:
        """Fetch all patient data for AI analysis"""
        stmt = (
            select(Patient)
            .options(
                joinedload(Patient.clinical_events),
                joinedload(Patient.referrals)
            )
            .where(Patient.id == patient_id)
        )
        patient = self.db.execute(stmt).unique().scalar_one_or_none()
        
        if not patient:
            return None
        
        # Compile all patient data
        data = {
            "patient_id": str(patient.id),
            "demographics": {
                "name": patient.full_name,
                "age": patient.age_in_years,
                "sex": patient.sex,
                "location": {
                    "district": patient.district,
                    "province": patient.province,
                    "municipality": patient.municipality,
                }
            },
            "clinical_events": [
                {
                    "section": event.section,
                    "factor": event.factor,
                    "event_time": event.event_time.isoformat(),
                    "value": event.value,
                    "note": event.note,
                }
                for event in patient.clinical_events
            ],
            "referrals": [
                {
                    "status": ref.status.value,
                    "from_facility": ref.from_facility,
                    "to_facility": ref.to_facility,
                    "reason": ref.reason,
                    "created_at": ref.created_at.isoformat(),
                }
                for ref in patient.referrals
            ],
        }
        
        return data
    
    async def generate_ai_summary(self, patient_data: Dict[str, Any]) -> AIPatientSummary:
        """Generate AI summary using OpenAI API"""
        
        if not self.openai_enabled:
            # Return mock summary when OpenAI is not available
            return self._generate_mock_summary(patient_data)
        
        try:
            # TODO: Replace with your OpenAI API call
            # Prepare the prompt
            prompt = self._create_summary_prompt(patient_data)
            
            # Call OpenAI API (example for GPT-4)
            # response = await openai.ChatCompletion.acreate(
            #     model="gpt-4",
            #     messages=[
            #         {"role": "system", "content": "You are a medical AI assistant..."},
            #         {"role": "user", "content": prompt}
            #     ],
            #     temperature=0.3,
            #     max_tokens=500
            # )
            
            # For now, return mock data
            return self._generate_mock_summary(patient_data)
            
        except Exception as e:
            logger.error(f"Error generating AI summary: {e}")
            return self._generate_mock_summary(patient_data)
    
    async def generate_referral_recommendation(
        self, 
        patient_data: Dict[str, Any]
    ) -> AIReferralRecommendation:
        """Generate AI referral recommendation using OpenAI API"""
        
        if not self.openai_enabled:
            # Return mock recommendation when OpenAI is not available
            return self._generate_mock_referral(patient_data)
        
        try:
            # TODO: Replace with your OpenAI API call
            # Prepare the prompt
            prompt = self._create_referral_prompt(patient_data)
            
            # Call OpenAI API (example for GPT-4)
            # response = await openai.ChatCompletion.acreate(
            #     model="gpt-4",
            #     messages=[
            #         {"role": "system", "content": "You are a maternal health specialist..."},
            #         {"role": "user", "content": prompt}
            #     ],
            #     temperature=0.2,
            #     max_tokens=800
            # )
            
            # For now, return mock data
            return self._generate_mock_referral(patient_data)
            
        except Exception as e:
            logger.error(f"Error generating referral recommendation: {e}")
            return self._generate_mock_referral(patient_data)
    
    def _create_summary_prompt(self, patient_data: Dict[str, Any]) -> str:
        """Create prompt for AI summary generation"""
        return f"""
Analyze the following patient data and provide a concise clinical summary:

Patient Demographics:
{json.dumps(patient_data['demographics'], indent=2)}

Clinical Events ({len(patient_data['clinical_events'])} total):
{json.dumps(patient_data['clinical_events'][:10], indent=2)}

Referral History ({len(patient_data['referrals'])} total):
{json.dumps(patient_data['referrals'], indent=2)}

Please provide:
1. A brief clinical summary (2-3 sentences)
2. Key findings (bullet points)
3. Overall risk assessment (low/medium/high/critical)
"""
    
    def _create_referral_prompt(self, patient_data: Dict[str, Any]) -> str:
        """Create prompt for AI referral recommendation"""
        return f"""
Analyze the following maternal health patient data and recommend whether hospital referral is needed:

Patient Demographics:
{json.dumps(patient_data['demographics'], indent=2)}

Clinical Events:
{json.dumps(patient_data['clinical_events'], indent=2)}

Referral History:
{json.dumps(patient_data['referrals'], indent=2)}

Based on WHO maternal health guidelines and Nepal's referral protocols, provide:
1. Whether referral is needed (yes/no)
2. Urgency level (low/medium/high/critical)
3. Confidence score (0.0-1.0)
4. Specific reasons for recommendation
5. Recommended facility type and specialties
6. Key risk factors identified
"""
    
    def _generate_mock_summary(self, patient_data: Dict[str, Any]) -> AIPatientSummary:
        """Generate detailed mock summary from actual patient data"""
        demographics = patient_data.get('demographics', {})
        clinical_events = patient_data.get('clinical_events', [])
        referrals = patient_data.get('referrals', [])
        
        age = demographics.get('age', 'Unknown')
        num_events = len(clinical_events)
        num_referrals = len(referrals)
        
        # Extract actual clinical event types
        event_sections = {}
        for event in clinical_events:
            section = event.get('section', 'Unknown')
            factor = event.get('factor', 'Unknown')
            value = event.get('value', 'Unknown')
            
            if section not in event_sections:
                event_sections[section] = []
            event_sections[section].append(f"{factor}: {value}")
        
        # Build summary with real data
        findings = []
        
        # Add event summary
        findings.append(f"Total clinical events: {num_events}")
        
        # Add clinical event details ONLY if there are events
        if num_events > 0:
            for section, factors in event_sections.items():
                # Show unique factors to avoid duplication
                unique_factors = list(set(factors))[:2]
                findings.append(f"{section}: {', '.join(unique_factors)}")
        else:
            findings.append("⚠️ No clinical events recorded yet")
        
        # Add referral info
        if num_referrals > 0:
            findings.append(f"Previous referrals: {num_referrals} recorded")
        
        # Determine risk level based on actual data
        risk_level = "low"
        if num_events >= 10:
            risk_level = "high"
        elif num_events >= 5:
            risk_level = "medium"
        
        # Build summary text based on what data exists
        if num_events == 0:
            summary_text = f"Patient is a {age}-year-old. No clinical events have been recorded yet. Awaiting clinical data entry for assessment."
        elif num_events > 5:
            summary_text = (
                f"Patient is a {age}-year-old with {num_events} clinical events recorded. "
                f"Currently monitoring {len(event_sections)} different clinical areas. "
                f"Regular specialist consultation recommended."
            )
        else:
            summary_text = (
                f"Patient is a {age}-year-old with {num_events} clinical events recorded. "
                f"Currently monitoring {len(event_sections)} clinical area(s). "
                f"Routine monitoring recommended."
            )
        
        return AIPatientSummary(
            summary=summary_text,
            key_findings=findings[:5],  # Top 5 findings
            risk_level=risk_level,
            metadata={"mock_data": True, "reason": "OpenAI API not configured", "events_analyzed": num_events}
        )
    
    def _generate_mock_referral(self, patient_data: Dict[str, Any]) -> AIReferralRecommendation:
        """Generate detailed referral recommendation from actual patient data"""
        demographics = patient_data.get('demographics', {})
        clinical_events = patient_data.get('clinical_events', [])
        referrals = patient_data.get('referrals', [])
        
        num_events = len(clinical_events)
        has_previous_referrals = len(referrals) > 0
        
        # Analyze clinical events for specific findings
        high_risk_factors = []
        unusual_findings = []
        critical_findings = []
        event_count_by_section = {}
        
        for event in clinical_events:
            section = event.get('section', 'Unknown')
            factor = event.get('factor', 'Unknown')
            value = event.get('value', 'Unknown')
            
            if section not in event_count_by_section:
                event_count_by_section[section] = []
            event_count_by_section[section].append(f"{factor}: {value}")
            
            # Flag unusual values (simple heuristic)
            lower_val = str(value).lower()
            
            # Critical findings that always warrant referral
            if any(keyword in lower_val for keyword in ['critical', 'severe', 'emergency', 'acute', 'life-threatening']):
                critical_findings.append(f"{factor}: {value}")
            
            # Abnormal findings (less critical)
            if any(keyword in lower_val for keyword in ['abnormal', 'high', 'low', 'positive']):
                unusual_findings.append(f"{factor}: {value}")
        
        # Determine referral need based on CRITICAL THRESHOLDS
        referral_needed = False
        urgency = "low"
        confidence = 0.8
        reasons = []
        recommended_specialties = []
        
        # CRITICAL FINDINGS - HIGHEST PRIORITY
        if critical_findings:
            referral_needed = True
            urgency = "critical"
            confidence = 0.95
            reasons.append(f"CRITICAL FINDINGS: {', '.join(set(critical_findings[:2]))}")
        
        # HIGH COMPLEXITY - needs significant clinical data
        elif num_events >= 12:
            referral_needed = True
            urgency = "high"
            confidence = 0.85
            reasons.append(f"High clinical complexity: {num_events} different clinical events recorded")
        
        # MEDIUM COMPLEXITY - needs moderate clinical data
        elif num_events >= 7:
            referral_needed = True
            urgency = "medium"
            confidence = 0.75
            reasons.append(f"Moderate clinical complexity: {num_events} clinical events")
        
        # ABNORMAL FINDINGS - only if there's also some clinical data
        elif unusual_findings and num_events >= 3:
            reasons.append(f"Abnormal findings detected: {', '.join(set(unusual_findings[:2]))}")
            referral_needed = True
            urgency = "medium"
            confidence = 0.70
        
        # PREVIOUS REFERRALS - ONLY if there's clinical data to support
        if has_previous_referrals and (num_events > 0 or critical_findings or unusual_findings):
            if not reasons:  # Only add if no other reasons yet
                reasons.append("Previous hospital referral history - ongoing monitoring needed")
                referral_needed = True
                if urgency == "low":
                    urgency = "low"
                confidence = 0.60
            else:
                # Enhance existing reasons
                confidence = min(0.95, confidence + 0.05)
        
        # Recommend specialties based on clinical areas
        if any('obstetric' in str(sec).lower() or 'pregnancy' in str(sec).lower() for sec in event_count_by_section.keys()):
            recommended_specialties = ["Obstetrics", "Maternal Health"]
        if any('gynecol' in str(sec).lower() for sec in event_count_by_section.keys()):
            recommended_specialties.extend(["Gynecology"])
        if any('anemias' in str(sec).lower() or 'anemia' in str(sec).lower() for sec in event_count_by_section.keys()):
            recommended_specialties.extend(["Hematology"])
        
        # Only assign specialties if referral is actually needed
        if not referral_needed:
            recommended_specialties = []
        elif not recommended_specialties:
            recommended_specialties = ["General Internal Medicine", "Family Medicine"]
        
        # Default reason if none found
        if not reasons:
            if referral_needed:
                reasons.append("Clinical evaluation recommended")
            else:
                reasons.append("Patient stable - no referral needed at this time")
        
        return AIReferralRecommendation(
            referral_needed=referral_needed,
            urgency=urgency if referral_needed else "low",
            confidence=confidence,
            reasons=reasons,
            recommended_facility="District Hospital" if referral_needed else None,
            recommended_specialties=list(set(recommended_specialties)) if referral_needed else [],
            risk_factors={
                "clinical_events_count": num_events,
                "event_categories": list(event_count_by_section.keys()),
                "unusual_findings": unusual_findings[:5],
                "critical_findings": critical_findings[:5],
                "previous_referrals": has_previous_referrals,
            },
            clinical_indicators={
                "high_complexity": num_events > 5,
                "abnormal_findings": len(unusual_findings) > 0,
                "critical_findings": len(critical_findings) > 0,
                "referral_history": has_previous_referrals,
                "total_distinct_issues": len(event_count_by_section),
            },
            estimated_distance_km=12  # Mock distance
        )
    
    async def get_or_generate_analysis(
        self, 
        patient_id: UUID,
        force_regenerate: bool = False
    ) -> Optional[AIPatientAnalysis]:
        """Get existing analysis or generate new one"""
        
        # Check for existing analysis
        stmt = select(AIPatientAnalysis).where(AIPatientAnalysis.patient_id == patient_id)
        existing = self.db.execute(stmt).scalar_one_or_none()
        
        # If exists and not forcing regeneration, return existing
        if existing and not force_regenerate:
            return existing
        
        # Get patient data
        patient_data = self.get_patient_complete_data(patient_id)
        if not patient_data:
            logger.error(f"Patient {patient_id} not found")
            return None
        
        # Generate AI analysis
        summary = await self.generate_ai_summary(patient_data)
        referral_rec = await self.generate_referral_recommendation(patient_data)
        
        # Create or update analysis record
        if existing:
            analysis = existing
            analysis.data_version += 1
        else:
            analysis = AIPatientAnalysis(patient_id=patient_id)
        
        # Update fields
        analysis.summary = summary.summary
        analysis.summary_metadata = {
            "key_findings": summary.key_findings,
            "risk_level": summary.risk_level,
            **(summary.metadata or {})
        }
        
        analysis.referral_needed = referral_rec.referral_needed
        analysis.referral_urgency = referral_rec.urgency
        analysis.referral_confidence = referral_rec.confidence
        analysis.referral_reasons = referral_rec.reasons
        analysis.recommended_facility = referral_rec.recommended_facility
        analysis.recommended_specialties = referral_rec.recommended_specialties
        analysis.risk_factors = referral_rec.risk_factors
        analysis.clinical_indicators = referral_rec.clinical_indicators
        
        analysis.model_used = "mock-model" if not self.openai_enabled else self.settings.OPENAI_MODEL
        analysis.tokens_used = 0
        analysis.last_analyzed_at = datetime.utcnow()
        
        if not existing:
            self.db.add(analysis)
        
        self.db.commit()
        self.db.refresh(analysis)
        
        return analysis
