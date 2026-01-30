# AI Features - Quick Start Guide

## 🎯 What's New?

Two new AI-powered sections have been added to every patient profile page:

### 1. **AI Patient Summary** (Purple Card)
- Automatically summarizes patient's clinical condition
- Shows key findings and risk level
- Updates when patient data changes

### 2. **AI Referral Solution** (Pink Card)
- Recommends if patient needs referral to hospital
- Shows urgency level and confidence score
- Suggests specific facilities and specialties

---

## 🚀 Quick Start (Testing with Mock Data)

**The system works RIGHT NOW without any additional setup!**

1. **Login** to your application
2. **Navigate to any patient profile**
3. **Scroll down** below the "Notes" and "Referrals" buttons
4. **See the AI sections** - they auto-generate on first view!

That's it! The system uses intelligent mock data for testing.

---

## 🔑 Enable Real AI (OpenAI Integration)

### Step 1: Get OpenAI API Key
1. Go to https://platform.openai.com/api-keys
2. Sign up or login
3. Click "Create new secret key"
4. Copy the key (starts with `sk-`)

### Step 2: Install OpenAI Package
```bash
cd backend
.\venv\Scripts\activate  # Windows
pip install openai
```

### Step 3: Configure API Key
Edit `backend/.env` file:
```env
# Uncomment and add your key:
OPENAI_API_KEY=sk-your-actual-key-here
OPENAI_MODEL=gpt-4
```

### Step 4: Restart Backend
```bash
cd backend
.\venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Step 5: Test
Visit any patient profile and click the refresh button on AI cards!

---

## 🎨 Where to Find It

**Patient Profile Page → Scroll Down:**

```
[Patient Demographics Card]
       ↓
[Notes & Referrals Buttons]
       ↓
[🟣 AI Patient Summary]        ← NEW!
       ↓
[🔴 AI Referral Solution]      ← NEW!
       ↓
[Clinical Summary Section]
```

---

## 🔄 Automatic Updates

The AI analysis automatically regenerates when:
- ✅ New clinical events added
- ✅ Patient data updated
- ✅ Medical records modified
- ✅ Referrals created/updated

**You don't need to do anything - it's automatic!**

---

## 🧪 Testing the Feature

### Test Script (Optional)
```bash
cd backend
python test_ai_endpoints.py
```

This will:
- ✅ Test all AI API endpoints
- ✅ Verify auto-generation works
- ✅ Show sample responses
- ✅ Confirm everything is working

---

## 💡 Key Features

### Mock Data Mode (Current State)
- ✅ Works immediately, no setup required
- ✅ No API costs
- ✅ Perfect for development and testing
- ✅ Provides realistic sample data

### Real AI Mode (With OpenAI)
- 🤖 Actual AI analysis of patient data
- 📊 Intelligent risk assessment
- 🏥 Smart referral recommendations
- 💰 ~$0.10 per patient analysis

---

## 📱 UI Components

### Purple Card - AI Summary
- **What it shows:**
  - Natural language summary
  - Key findings (bullet points)
  - Risk level (low/medium/high/critical)
  - Last analyzed timestamp
- **Actions:**
  - 🔄 Refresh button to regenerate

### Pink Card - Referral Recommendation
- **What it shows:**
  - Referral decision (needed/not needed)
  - Urgency level with color coding
  - Confidence score (0-100%)
  - Reasons for recommendation
  - Recommended facility + distance
  - Required specialties
- **Actions:**
  - 🔄 Refresh button to regenerate

---

## 🎯 Use Cases

### For Clinicians:
1. **Quick Patient Overview** - Instant summary of complex cases
2. **Decision Support** - AI-powered referral recommendations
3. **Risk Assessment** - Automatic identification of high-risk cases
4. **Time Saving** - No need to manually review all records

### For Administrators:
1. **Quality Assurance** - Monitor AI recommendations vs actual outcomes
2. **Resource Planning** - Track referral patterns and needs
3. **Performance Metrics** - Measure time-to-decision improvements

---

## ❓ FAQ

### Q: Do I need to configure anything to test it?
**A:** No! It works immediately with mock data.

### Q: How much does OpenAI cost?
**A:** ~$0.10 per patient analysis. For 1000 patients/month = ~$100/month.

### Q: Can I use a different AI model?
**A:** Yes! Edit the code in `ai_patient_service.py` to use any model.

### Q: Is patient data secure?
**A:** Yes! Only necessary clinical data is processed. API keys are never committed to git.

### Q: How often does it update?
**A:** Automatically whenever patient data changes.

### Q: Can I customize the analysis?
**A:** Yes! Edit the prompts in `ai_patient_service.py`.

### Q: What if OpenAI is down?
**A:** System automatically falls back to mock data mode.

---

## 🆘 Troubleshooting

### AI sections not showing?
- Clear browser cache
- Check browser console for errors
- Verify backend is running on port 8000

### "Mock data" showing instead of real analysis?
- Confirm OPENAI_API_KEY is in .env
- Verify `openai` package is installed
- Check backend logs for errors

### Slow performance?
- First generation takes a few seconds (normal)
- Subsequent views are instant (cached)
- Consider background processing for production

---

## 📚 More Information

- **Full Documentation:** `AI_FEATURES_README.md`
- **Implementation Details:** `IMPLEMENTATION_SUMMARY.md`
- **API Endpoints:** `backend/app/api/v1/endpoints/ai_analysis.py`

---

## ✨ That's It!

The AI features are ready to use! Visit any patient profile to see them in action.

**Enjoy! 🎉**
