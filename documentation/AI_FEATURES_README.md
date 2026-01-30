# AI Patient Analysis Feature

## Overview

The AI Patient Analysis feature provides automated patient summaries and referral recommendations using OpenAI's GPT models. This feature enhances clinical decision-making by analyzing patient data and providing intelligent insights.

## Features

### 1. **AI Patient Summary**
- Generates natural language summaries of patient clinical condition
- Identifies key findings from clinical events
- Assesses overall risk level (low, medium, high, critical)
- Updates automatically when patient data changes

### 2. **AI Referral Recommendation**
- Analyzes patient data to determine if referral is needed
- Provides urgency level (low, medium, high, critical)
- Calculates confidence score (0-100%)
- Suggests recommended facilities and specialties
- Estimates distance to recommended facility
- Lists specific reasons for recommendation

## Setup Instructions

### 1. Install OpenAI Package (Optional)

```bash
cd backend
.\venv\Scripts\activate  # Windows
source venv/bin/activate  # Linux/Mac

pip install openai
```

### 2. Configure OpenAI API Key

1. Get your API key from [OpenAI Platform](https://platform.openai.com/api-keys)
2. Add to your `.env` file:

```env
# OpenAI Configuration
OPENAI_API_KEY=your-openai-api-key-here
OPENAI_MODEL=gpt-4
```

**Note:** The system works without OpenAI configured - it will use mock data for testing.

### 3. Database Migration

The migration has already been applied. To verify:

```bash
cd backend
.\venv\Scripts\python.exe -m alembic current
```

## API Endpoints

### Get AI Analysis
```http
GET /api/v1/ai-analysis/patient/{patient_id}?auto_generate=true
```

**Response:**
```json
{
  "patient_id": "uuid",
  "summary": {
    "summary": "Natural language summary...",
    "key_findings": ["Finding 1", "Finding 2"],
    "risk_level": "medium"
  },
  "referral_recommendation": {
    "referral_needed": true,
    "urgency": "medium",
    "confidence": 0.75,
    "reasons": ["Reason 1", "Reason 2"],
    "recommended_facility": "District Hospital",
    "recommended_specialties": ["Obstetrics", "Gynecology"],
    "estimated_distance_km": 15.5
  },
  "last_analyzed_at": "2026-01-29T00:00:00Z",
  "data_version": 1,
  "model_used": "gpt-4"
}
```

### Force Regenerate Analysis
```http
POST /api/v1/ai-analysis/generate
{
  "patient_id": "uuid",
  "force_regenerate": true
}
```

### Get Analysis Status
```http
GET /api/v1/ai-analysis/patient/{patient_id}/status
```

### Delete Analysis
```http
DELETE /api/v1/ai-analysis/patient/{patient_id}
```

## Frontend Components

### AIPatientSummary Component
Located at: `frontend/src/components/AIPatientSummary.tsx`

**Usage:**
```tsx
import AIPatientSummary from '../components/AIPatientSummary';

<AIPatientSummary patientId={patientId} />
```

### AIReferralRecommendation Component
Located at: `frontend/src/components/AIReferralRecommendation.tsx`

**Usage:**
```tsx
import AIReferralRecommendation from '../components/AIReferralRecommendation';

<AIReferralRecommendation patientId={patientId} />
```

## Automatic Updates

The AI analysis automatically regenerates when:
- New clinical events are added
- Patient data is updated
- Medical records are modified

**Implementation:** The `mark_ai_analysis_for_update()` function in `app/services/ai_update_service.py` is called whenever patient data changes. It deletes the existing analysis, which triggers regeneration on next access.

## Customizing AI Prompts

Edit the prompts in `backend/app/services/ai_patient_service.py`:

```python
def _create_summary_prompt(self, patient_data: Dict[str, Any]) -> str:
    """Customize this to change how AI analyzes patient data"""
    return f"""Your custom prompt here..."""

def _create_referral_prompt(self, patient_data: Dict[str, Any]) -> str:
    """Customize referral recommendation logic"""
    return f"""Your custom prompt here..."""
```

## Mock Data Mode

When OpenAI is not configured, the system uses mock data:

```python
def _generate_mock_summary(self, patient_data: Dict[str, Any]) -> AIPatientSummary:
    """Returns sample data for testing without API costs"""
```

This allows you to:
- Test the UI without API costs
- Develop and debug without API dependency
- Demo the feature to stakeholders

## OpenAI Integration

To enable real AI analysis:

1. **Update the service methods:**

```python
# In ai_patient_service.py
async def generate_ai_summary(self, patient_data: Dict[str, Any]) -> AIPatientSummary:
    prompt = self._create_summary_prompt(patient_data)
    
    response = await openai.ChatCompletion.acreate(
        model=self.settings.OPENAI_MODEL,
        messages=[
            {"role": "system", "content": "You are a medical AI assistant..."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.3,
        max_tokens=500
    )
    
    # Parse response and return AIPatientSummary
```

2. **Handle response parsing:**

```python
result = response.choices[0].message.content
# Parse JSON from result or extract structured data
```

## Database Schema

**Table:** `ai_patient_analyses`

| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| patient_id | UUID | Foreign key to patients (unique) |
| summary | TEXT | Natural language summary |
| summary_metadata | JSONB | Key findings and metadata |
| referral_needed | BOOLEAN | Whether referral is recommended |
| referral_urgency | VARCHAR(20) | Urgency level |
| referral_confidence | FLOAT | Confidence score 0-1 |
| referral_reasons | JSONB | List of reasons |
| recommended_facility | VARCHAR(255) | Facility name |
| recommended_specialties | JSONB | List of specialties |
| risk_factors | JSONB | Identified risk factors |
| clinical_indicators | JSONB | Key clinical indicators |
| model_used | VARCHAR(100) | AI model used |
| tokens_used | INTEGER | Token consumption |
| data_version | INTEGER | Data version for tracking changes |
| last_analyzed_at | TIMESTAMP | Last analysis time |

## Performance Considerations

1. **Caching:** Analysis is cached in database until patient data changes
2. **Lazy Loading:** Analysis only generated when accessed
3. **Background Processing:** Use Celery or BackgroundTasks for async generation
4. **Token Limits:** Monitor OpenAI token usage and costs

## Security & Privacy

1. **Data Minimization:** Only send necessary clinical data to AI
2. **Audit Logging:** All AI analysis requests are logged
3. **API Key Security:** Never commit API keys to version control
4. **PHI Protection:** Ensure OpenAI usage complies with HIPAA/local regulations

## Troubleshooting

### AI Analysis Not Showing
- Check backend logs for errors
- Verify patient has clinical events
- Try forcing regeneration with refresh button

### OpenAI API Errors
- Verify API key is correct
- Check API quota and billing
- Review rate limits

### Mock Data Showing Instead of Real Analysis
- Confirm `OPENAI_API_KEY` is set in `.env`
- Check `openai` package is installed
- Review backend logs for initialization errors

## Future Enhancements

- [ ] Background task queue with Celery
- [ ] Multiple AI model support (GPT-3.5, GPT-4, local models)
- [ ] Batch analysis for multiple patients
- [ ] Historical trend analysis
- [ ] Explainable AI features
- [ ] Integration with clinical guidelines databases
- [ ] Real-time streaming responses
- [ ] Cost tracking and optimization

## Cost Estimation

**Average costs per analysis (GPT-4):**
- Summary generation: ~$0.03-0.05
- Referral recommendation: ~$0.05-0.08
- **Total per patient:** ~$0.08-0.13

**For 1000 patients/month:** ~$80-130/month

**Cost optimization:**
- Use GPT-3.5-turbo for non-critical analysis
- Implement smart caching (only regenerate when needed)
- Batch process during off-hours

## License

This feature is part of the SmartAama maternal health system.
