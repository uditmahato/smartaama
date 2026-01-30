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

# Maternal Health Risk Factor Framework (10 major factors, 10% each)
MATERNAL_RISK_FACTORS = {
    "pre_eclampsia_eclampsia": {
        "name": "Pre-eclampsia/Eclampsia",
        "weight": 0.10,  # 10%
        "sub_factors": [
            "primigravida",
            "obesity",
            "family_history_htn_preeclampsia",
            "edema_not_resolving",
            "multiple_gestation",
            "hypertension",
            "assisted_pregnancy",
            "clinical_features_vision_headache_pain",
            "coagulation_disorders",
            "diabetes",
            "high_blood_pressure"  # SBP >140 OR DBP >90
        ]
    },
    "placenta_previa": {
        "name": "Placenta Previa",
        "weight": 0.10,
        "sub_factors": [
            "multiple_gestation",
            "vaginal_bleeding",
            "age_over_35",
            "pregnancy_after_art",
            "prior_uterine_surgeries",
            "prior_placenta_previa",
            "smoking"
        ]
    },
    "abruptio_placenta": {
        "name": "Abruptio Placenta",
        "weight": 0.10,
        "sub_factors": [
            "age_over_35",
            "vaginal_bleeding",
            "high_birth_order",
            "smoking_cocaine",
            "hypertension_in_pregnancy",
            "uterine_anomaly",
            "coagulation_disorder",
            "prior_abruption",
            "trauma"
        ]
    },
    "gestational_diabetes": {
        "name": "Gestational Diabetes Mellitus",
        "weight": 0.10,
        "sub_factors": [
            "family_history_diabetes",
            "prior_overweight_baby",
            "prior_stillbirth",
            "prior_polyhydramnios",
            "age_over_30",
            "obesity",
            "diabetes"
        ]
    },
    "preterm_birth": {
        "name": "Preterm Birth",
        "weight": 0.10,
        "sub_factors": [
            "prior_preterm_birth",
            "multiple_gestation",
            "prior_cervical_surgery",
            "short_interpregnancy_interval",
            "smoking",
            "polyhydramnios",
            "infection_uti",
            "pregnancy_after_art"
        ]
    },
    "postpartum_hemorrhage": {
        "name": "Postpartum Hemorrhage",
        "weight": 0.10,
        "sub_factors": [
            "grand_multipara",
            "over_distention_uterus",
            "multiple_gestation",
            "polyhydramnios",
            "large_baby",
            "malnutrition_anemia",
            "low_hemoglobin",
            "antepartum_hemorrhage",
            "placenta_previa",
            "abruptio_placenta",
            "prolonged_labor",
            "precipitated_labor",
            "uterine_fibroid",
            "uterine_malformation",
            "prior_pph"
        ]
    },
    "recurrent_pregnancy_loss": {
        "name": "Recurrent Pregnancy Loss",
        "weight": 0.10,
        "sub_factors": [
            "uterine_anomaly",
            "advanced_maternal_age",
            "prior_pregnancy_loss",
            "genetic_chromosomal_disease",
            "infection_pregnancy",
            "overt_hypothyroidism",
            "uncontrolled_diabetes",
            "obesity",
            "smoking_alcohol_intoxicants"
        ]
    },
    "anemia_pregnancy": {
        "name": "Anemia in Pregnancy",
        "weight": 0.10,
        "sub_factors": [
            "short_birth_spacing",
            "pallor",
            "iron_tablets_not_taken",
            "low_hemoglobin"
        ]
    },
    "obstructed_prolonged_labor": {
        "name": "Obstructed/Prolonged Labor",
        "weight": 0.10,
        "sub_factors": [
            "maternal_height_short",
            "malpresentation",
            "primigravida",
            "prior_stillbirth",
            "prior_prolonged_labor",
            "excessive_sfh",
            "prior_large_baby",
            "gestational_diabetes",
            "obesity",
            "excessive_weight_gain",
            "difficult_fetal_palpation",
            "polyhydramnios"
        ]
    },
    "maternal_sepsis": {
        "name": "Maternal Sepsis (Antenatal/Postnatal)",
        "weight": 0.10,
        "sub_factors": [
            "unhygienic_practices",
            "fever",
            "home_delivery_no_kit",
            "foul_smelling_discharge",
            "delivery_unwashed_hands",
            "prolonged_rupture_membranes",
            "non_sterile_instruments",
            "home_delivery",
            "application_harmful_substances"
        ]
    }
}

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
        """Generate simplified clinical summary focusing on crucial signs"""
        demographics = patient_data.get('demographics', {})
        clinical_events = patient_data.get('clinical_events', [])
        referrals = patient_data.get('referrals', [])
        
        age = demographics.get('age', 'Unknown')
        num_events = len(clinical_events)
        
        # Analyze actual clinical data for crucial signs
        crucial_findings = []
        normal_findings = []
        elevated_findings = []
        
        # Clinical thresholds for maternal health
        CLINICAL_THRESHOLDS = {
            'blood_pressure_systolic': {'normal': (90, 139), 'elevated': 140, 'unit': 'mmHg'},
            'blood_pressure_diastolic': {'normal': (60, 89), 'elevated': 90, 'unit': 'mmHg'},
            'heart_rate': {'normal': (60, 100), 'elevated': 100, 'unit': 'bpm'},
            'temperature': {'normal': (36.1, 37.2), 'elevated': 37.5, 'unit': '°C'},
            'hemoglobin': {'normal': (11.0, 15.0), 'low': 11.0, 'unit': 'g/dL'},
            'glucose': {'normal': (70, 140), 'elevated': 140, 'unit': 'mg/dL'},
            'weight_gain': {'normal': (11.5, 16), 'excessive': 16, 'unit': 'kg'}
        }
        
        for event in clinical_events:
            factor = event.get('factor', '').lower()
            value = event.get('value', '')
            section = event.get('section', '')
            
            # Extract numeric value if possible
            numeric_value = None
            if isinstance(value, (int, float)):
                numeric_value = float(value)
            elif isinstance(value, dict) and 'value' in value:
                try:
                    numeric_value = float(value['value'])
                except (ValueError, TypeError):
                    pass
            elif isinstance(value, str):
                try:
                    numeric_value = float(value)
                except ValueError:
                    pass
            
            # Check against clinical thresholds
            for threshold_key, threshold_data in CLINICAL_THRESHOLDS.items():
                if threshold_key in factor and numeric_value is not None:
                    unit = threshold_data.get('unit', '')
                    
                    if 'normal' in threshold_data:
                        normal_range = threshold_data['normal']
                        if normal_range[0] <= numeric_value <= normal_range[1]:
                            normal_findings.append(f"{threshold_key.replace('_', ' ').title()}: {numeric_value} {unit} (Normal)")
                        elif 'elevated' in threshold_data and numeric_value >= threshold_data['elevated']:
                            elevated_findings.append(f"{threshold_key.replace('_', ' ').title()}: {numeric_value} {unit} (⚠️ Elevated)")
                        elif 'low' in threshold_data and numeric_value <= threshold_data['low']:
                            elevated_findings.append(f"{threshold_key.replace('_', ' ').title()}: {numeric_value} {unit} (⚠️ Low)")
                    break
        
        # Check for concerning patterns
        event_sections = {}
        for event in clinical_events:
            section = event.get('section', 'other')
            if section not in event_sections:
                event_sections[section] = 0
            event_sections[section] += 1
        
        # Build findings list
        findings = []
        
        # Add elevated/concerning findings first (most important)
        if elevated_findings:
            findings.extend(elevated_findings[:3])  # Top 3 concerning findings
        
        # Add normal findings (reassuring)
        if normal_findings:
            findings.extend(normal_findings[:2])  # Top 2 normal findings
        
        # Add event summary if no specific clinical values found
        if not elevated_findings and not normal_findings:
            if num_events > 0:
                findings.append(f"Clinical events recorded: {num_events}")
                for section, count in list(event_sections.items())[:2]:
                    findings.append(f"{section.replace('_', ' ').title()}: {count} entries")
            else:
                findings.append("📋 No clinical measurements recorded yet")
        
        # Add referral history if exists
        if len(referrals) > 0:
            findings.append(f"Previous referrals: {len(referrals)}")
        
        # Determine risk based on elevated findings
        if len(elevated_findings) >= 3:
            risk_level = "high"
        elif len(elevated_findings) >= 1:
            risk_level = "medium"
        elif num_events == 0:
            risk_level = "unknown"
        else:
            risk_level = "low"
        
        # Simple, focused summary
        if num_events == 0:
            summary_text = f"Patient ({age} years old) - No clinical data recorded. Assessment pending."
        elif elevated_findings:
            summary_text = f"Patient ({age} years old) - {len(elevated_findings)} elevated signs detected. Clinical attention needed."
        else:
            summary_text = f"Patient ({age} years old) - {num_events} clinical entries. Signs within normal ranges."
        
        return AIPatientSummary(
            summary=summary_text,
            key_findings=findings[:4],  # Keep it simple - max 4 key findings
            risk_level=risk_level,
            metadata={"clinical_events": num_events, "elevated_signs": len(elevated_findings)}
        )
    
    def _generate_mock_referral(self, patient_data: Dict[str, Any]) -> AIReferralRecommendation:
        """Generate data-driven referral recommendation without facility/doctor suggestions"""
        clinical_events = patient_data.get('clinical_events', [])
        
        # Clinical risk indicators based on actual data
        risk_indicators = {
            'elevated_bp': {'weight': 0.25, 'found': False, 'value': None},
            'low_hemoglobin': {'weight': 0.20, 'found': False, 'value': None},
            'high_glucose': {'weight': 0.15, 'found': False, 'value': None},
            'abnormal_heart_rate': {'weight': 0.15, 'found': False, 'value': None},
            'fever': {'weight': 0.10, 'found': False, 'value': None},
            'excessive_weight_gain': {'weight': 0.10, 'found': False, 'value': None},
            'previous_complications': {'weight': 0.05, 'found': False, 'value': None}
        }
        
        # Analyze actual clinical data
        reasons = []
        
        for event in clinical_events:
            factor = event.get('factor', '').lower()
            value = event.get('value', '')
            
            # Extract numeric value
            numeric_value = None
            if isinstance(value, (int, float)):
                numeric_value = float(value)
            elif isinstance(value, dict) and 'value' in value:
                try:
                    numeric_value = float(value['value'])
                except (ValueError, TypeError):
                    pass
            
            if numeric_value is not None:
                # Check for elevated blood pressure
                if 'blood_pressure' in factor or 'systolic' in factor:
                    if numeric_value >= 140:
                        risk_indicators['elevated_bp']['found'] = True
                        risk_indicators['elevated_bp']['value'] = f"{numeric_value} mmHg"
                        reasons.append(f"High blood pressure detected: {numeric_value} mmHg (≥140)")
                
                # Check for low hemoglobin (anemia)
                elif 'hemoglobin' in factor or 'hb' in factor:
                    if numeric_value <= 11.0:
                        risk_indicators['low_hemoglobin']['found'] = True
                        risk_indicators['low_hemoglobin']['value'] = f"{numeric_value} g/dL"
                        reasons.append(f"Low hemoglobin (anemia): {numeric_value} g/dL (≤11.0)")
                
                # Check for high glucose
                elif 'glucose' in factor or 'sugar' in factor:
                    if numeric_value >= 140:
                        risk_indicators['high_glucose']['found'] = True
                        risk_indicators['high_glucose']['value'] = f"{numeric_value} mg/dL"
                        reasons.append(f"Elevated glucose: {numeric_value} mg/dL (≥140)")
                
                # Check for abnormal heart rate
                elif 'heart_rate' in factor or 'pulse' in factor:
                    if numeric_value >= 100 or numeric_value <= 60:
                        risk_indicators['abnormal_heart_rate']['found'] = True
                        risk_indicators['abnormal_heart_rate']['value'] = f"{numeric_value} bpm"
                        if numeric_value >= 100:
                            reasons.append(f"Elevated heart rate: {numeric_value} bpm (≥100)")
                        else:
                            reasons.append(f"Low heart rate: {numeric_value} bpm (≤60)")
                
                # Check for fever
                elif 'temperature' in factor or 'fever' in factor:
                    if numeric_value >= 37.5:
                        risk_indicators['fever']['found'] = True
                        risk_indicators['fever']['value'] = f"{numeric_value}°C"
                        reasons.append(f"Fever detected: {numeric_value}°C (≥37.5)")
                
                # Check for excessive weight gain
                elif 'weight' in factor and 'gain' in factor:
                    if numeric_value >= 16:
                        risk_indicators['excessive_weight_gain']['found'] = True
                        risk_indicators['excessive_weight_gain']['value'] = f"{numeric_value} kg"
                        reasons.append(f"Excessive weight gain: {numeric_value} kg (≥16)")
        
        # Calculate confidence based on actual risk factors found
        total_risk_score = 0
        active_risks = []
        
        for risk_name, risk_data in risk_indicators.items():
            if risk_data['found']:
                total_risk_score += risk_data['weight']
                active_risks.append({
                    'name': risk_name.replace('_', ' ').title(),
                    'weight': risk_data['weight'],
                    'value': risk_data['value']
                })
        
        # Confidence is the actual calculated risk score (0-1)
        confidence = min(0.95, total_risk_score)  # Cap at 95%
        
        # Determine referral decision based on confidence
        referral_needed = confidence >= 0.15  # 15% threshold
        
        # Set urgency based on confidence level
        if confidence >= 0.50:
            urgency = "critical"
        elif confidence >= 0.30:
            urgency = "high"
        elif confidence >= 0.15:
            urgency = "medium"
        else:
            urgency = "low"
        
        # If no specific risks found but referral history exists
        referrals = patient_data.get('referrals', [])
        if not reasons and len(referrals) > 0:
            reasons.append("Previous referral history requires follow-up")
            confidence = max(confidence, 0.10)  # Minimum 10% for referral history
            referral_needed = True
            urgency = "low"
        
        # Default message if no risks found
        if not reasons:
            reasons.append("No elevated risk factors detected - routine monitoring")
        
        # Build clinical indicators showing what drove the decision
        clinical_indicators = {
            "total_risk_factors": len(active_risks),
            "confidence_score": f"{round(confidence * 100, 1)}%"
        }
        
        # Add specific indicators
        for risk in active_risks:
            key = risk['name'].lower().replace(' ', '_')
            clinical_indicators[key] = f"DETECTED: {risk['value']}"
        
        return AIReferralRecommendation(
            referral_needed=referral_needed,
            urgency=urgency,
            confidence=confidence,
            reasons=reasons[:3],  # Top 3 reasons
            recommended_facility=None,  # Removed as requested
            recommended_specialties=[],  # Removed as requested
            risk_factors={
                "detected_risks": active_risks,
                "confidence_calculation": f"Sum of risk weights: {round(confidence * 100, 1)}%",
                "data_points_analyzed": len(clinical_events)
            },
            clinical_indicators=clinical_indicators,
            estimated_distance_km=None  # Removed as requested
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
        
        analysis.model_used = "clinical-thresholds" if not self.openai_enabled else self.settings.OPENAI_MODEL
        analysis.tokens_used = 0
        analysis.last_analyzed_at = datetime.utcnow()
        
        if not existing:
            self.db.add(analysis)
        
        self.db.commit()
        self.db.refresh(analysis)
        
        return analysis
