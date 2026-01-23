# backend/app/models/medical_schema.py
"""
Medical schema configuration for Smart Aama.
Defines all clinical sections, fields, data types, units, and validation rules.
This configuration is used by the API to enforce data consistency and provide
structured forms to the frontend.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel


class FieldType(str, Enum):
    """Supported field data types."""
    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    DATE = "date"
    DATETIME = "datetime"
    ENUM = "enum"
    OBJECT = "object"
    ARRAY = "array"


class FieldDefinition(BaseModel):
    """Definition of a single clinical field."""
    name: str
    label: str
    field_type: FieldType
    unit: Optional[str] = None
    nullable: bool = False
    enum_values: Optional[List[str]] = None
    default_value: Any = None
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    description: Optional[str] = None


class SectionDefinition(BaseModel):
    """Definition of a clinical section with its fields."""
    section_key: str
    section_label: str
    category: str  # "static", "obstetric", "event_based"
    fields: List[FieldDefinition]
    description: Optional[str] = None
    show_in_updates: bool = True  # Whether to show in clinical update forms


# ============================================================================
# PATIENT MASTER PROFILE (STATIC DATA)
# ============================================================================

PATIENT_PARTICULARS = SectionDefinition(
    section_key="patient_particulars",
    section_label="Patient Particulars",
    category="static",
    description="Basic demographic and lifestyle information",
    show_in_updates=False,  # Part of patient registration, not clinical updates
    fields=[
        FieldDefinition(name="name", label="Name", field_type=FieldType.STRING),
        FieldDefinition(name="age", label="Age", field_type=FieldType.INTEGER, unit="years"),
        FieldDefinition(name="occupation", label="Occupation", field_type=FieldType.STRING),
        FieldDefinition(name="address", label="Address", field_type=FieldType.STRING),
        FieldDefinition(
            name="education_level",
            label="Education Level",
            field_type=FieldType.ENUM,
            enum_values=["None", "Primary", "Secondary", "Higher Secondary", "Bachelor", "Master", "Other"],
        ),
        FieldDefinition(
            name="marital_status",
            label="Marital Status",
            field_type=FieldType.ENUM,
            enum_values=["Single", "Married", "Divorced", "Widowed"],
        ),
        FieldDefinition(
            name="duration_of_marriage",
            label="Duration of Marriage",
            field_type=FieldType.INTEGER,
            unit="years",
            nullable=True,
        ),
        FieldDefinition(name="smoking_use", label="Smoking Use", field_type=FieldType.BOOLEAN),
        FieldDefinition(name="alcohol_use", label="Alcohol Use", field_type=FieldType.BOOLEAN),
        FieldDefinition(name="intoxicant_use", label="Intoxicant Use", field_type=FieldType.BOOLEAN),
    ],
)

MENSTRUAL_HISTORY = SectionDefinition(
    section_key="menstrual_history",
    section_label="Menstrual History",
    category="static",
    description="Menstrual cycle information",
    fields=[
        FieldDefinition(
            name="age_at_menarche",
            label="Age at Menarche",
            field_type=FieldType.INTEGER,
            unit="years",
        ),
        FieldDefinition(
            name="cycle_regularity",
            label="Cycle Regularity",
            field_type=FieldType.ENUM,
            enum_values=["Regular", "Irregular"],
        ),
        FieldDefinition(
            name="pads_per_day",
            label="Pads Per Day",
            field_type=FieldType.INTEGER,
            unit="pads/day",
        ),
        FieldDefinition(
            name="last_menstrual_period",
            label="Last Menstrual Period",
            field_type=FieldType.DATE,
        ),
    ],
)

CONTRACEPTIVE_HISTORY = SectionDefinition(
    section_key="contraceptive_history",
    section_label="Contraceptive History",
    category="static",
    description="Contraceptive usage history",
    fields=[
        FieldDefinition(
            name="contraceptive_use_history",
            label="Contraceptive Use History",
            field_type=FieldType.BOOLEAN,
        ),
        FieldDefinition(
            name="contraceptive_method",
            label="Contraceptive Method",
            field_type=FieldType.ENUM,
            enum_values=[
                "Oral pills",
                "Injection",
                "Implant",
                "IUD",
                "Condom",
                "Natural methods",
                "Other",
            ],
            nullable=True,
        ),
        FieldDefinition(
            name="last_contraceptive_use_date",
            label="Last Contraceptive Use Date",
            field_type=FieldType.DATE,
            nullable=True,
        ),
    ],
)

PAST_MEDICAL_HISTORY = SectionDefinition(
    section_key="past_medical_history",
    section_label="Past Medical History",
    category="static",
    description="Existing medical conditions",
    fields=[
        FieldDefinition(
            name="chronic_illness",
            label="Chronic Illness",
            field_type=FieldType.BOOLEAN,
        ),
        FieldDefinition(name="hypertension", label="Hypertension", field_type=FieldType.BOOLEAN),
        FieldDefinition(name="diabetes", label="Diabetes", field_type=FieldType.BOOLEAN),
        FieldDefinition(
            name="thyroid_disorder",
            label="Thyroid Disorder",
            field_type=FieldType.BOOLEAN,
        ),
        FieldDefinition(
            name="other_conditions",
            label="Other Conditions",
            field_type=FieldType.STRING,
            nullable=True,
        ),
    ],
)

FAMILY_HISTORY = SectionDefinition(
    section_key="family_history",
    section_label="Family History",
    category="static",
    description="Family medical history",
    fields=[
        FieldDefinition(
            name="hereditary_disease_present",
            label="Hereditary Disease Present",
            field_type=FieldType.BOOLEAN,
        ),
        FieldDefinition(
            name="consanguineous_marriage",
            label="Consanguineous Marriage",
            field_type=FieldType.BOOLEAN,
        ),
    ],
)

# ============================================================================
# OBSTETRIC HISTORY MODULE
# ============================================================================

OBSTETRIC_HISTORY = SectionDefinition(
    section_key="obstetric_history",
    section_label="Obstetric History",
    category="obstetric",
    description="Previous pregnancy outcomes",
    fields=[
        FieldDefinition(
            name="total_pregnancies",
            label="Total Pregnancies",
            field_type=FieldType.INTEGER,
            unit="count",
        ),
        FieldDefinition(
            name="pregnancy_outcomes",
            label="Pregnancy Outcomes",
            field_type=FieldType.ARRAY,
            description="Array of {year, outcome}",
        ),
        FieldDefinition(
            name="mode_of_delivery",
            label="Mode of Delivery",
            field_type=FieldType.ENUM,
            enum_values=["Normal vaginal", "Cesarean section", "Assisted delivery", "Other"],
        ),
        FieldDefinition(
            name="neonate_birth_weight",
            label="Neonate Birth Weight",
            field_type=FieldType.FLOAT,
            unit="kg",
        ),
        FieldDefinition(
            name="neonate_sex",
            label="Neonate Sex",
            field_type=FieldType.ENUM,
            enum_values=["Male", "Female", "Other"],
        ),
        FieldDefinition(
            name="breastfeeding_history",
            label="Breastfeeding History",
            field_type=FieldType.BOOLEAN,
        ),
        FieldDefinition(
            name="gestational_age_at_delivery",
            label="Gestational Age at Delivery",
            field_type=FieldType.INTEGER,
            unit="weeks",
        ),
        FieldDefinition(
            name="place_of_delivery",
            label="Place of Delivery",
            field_type=FieldType.STRING,
        ),
        FieldDefinition(
            name="previous_complications",
            label="Previous Complications",
            field_type=FieldType.STRING,
            nullable=True,
        ),
        FieldDefinition(
            name="pregnancy_loss_history",
            label="Pregnancy Loss History",
            field_type=FieldType.ENUM,
            enum_values=["None", "Miscarriage", "Stillbirth", "Neonatal death"],
        ),
    ],
)

# ============================================================================
# PRESENT PREGNANCY MODULE
# ============================================================================

PRESENT_PREGNANCY = SectionDefinition(
    section_key="present_pregnancy",
    section_label="Present Pregnancy",
    category="static",
    description="Current pregnancy information",
    fields=[
        FieldDefinition(
            name="pregnancy_planned",
            label="Pregnancy Planned",
            field_type=FieldType.BOOLEAN,
        ),
        FieldDefinition(
            name="confirmation_method",
            label="Confirmation Method",
            field_type=FieldType.ENUM,
            enum_values=["Urine pregnancy test", "Blood test", "Ultrasound", "Clinical examination"],
        ),
        FieldDefinition(
            name="estimated_date_of_delivery",
            label="Estimated Date of Delivery (EDD)",
            field_type=FieldType.DATE,
            description="Auto-calculated from LMP",
        ),
    ],
)

# ============================================================================
# TRIMESTER-WISE ANC MODULE (EVENT-BASED)
# ============================================================================

FIRST_TRIMESTER_ANC = SectionDefinition(
    section_key="first_trimester_anc",
    section_label="First Trimester ANC",
    category="event_based",
    description="First trimester antenatal care visits",
    fields=[
        FieldDefinition(name="anc_visits", label="ANC Visits", field_type=FieldType.INTEGER, unit="count"),
        FieldDefinition(name="folic_acid_intake", label="Folic Acid Intake", field_type=FieldType.BOOLEAN),
        FieldDefinition(
            name="blood_investigations_done",
            label="Blood Investigations Done",
            field_type=FieldType.BOOLEAN,
        ),
        FieldDefinition(
            name="urine_investigation_done",
            label="Urine Investigation Done",
            field_type=FieldType.BOOLEAN,
        ),
        FieldDefinition(name="ultrasound_done", label="Ultrasound Done", field_type=FieldType.BOOLEAN),
        FieldDefinition(name="radiation_exposure", label="Radiation Exposure", field_type=FieldType.BOOLEAN),
        FieldDefinition(
            name="drug_intake",
            label="Drug Intake",
            field_type=FieldType.STRING,
            nullable=True,
        ),
        FieldDefinition(
            name="fever_or_urinary_symptoms",
            label="Fever or Urinary Symptoms",
            field_type=FieldType.BOOLEAN,
        ),
        FieldDefinition(
            name="vaginal_bleeding_or_discharge",
            label="Vaginal Bleeding or Discharge",
            field_type=FieldType.BOOLEAN,
        ),
    ],
)

SECOND_TRIMESTER_ANC = SectionDefinition(
    section_key="second_trimester_anc",
    section_label="Second Trimester ANC",
    category="event_based",
    description="Second trimester antenatal care visits",
    fields=[
        FieldDefinition(name="anc_visits", label="ANC Visits", field_type=FieldType.INTEGER, unit="count"),
        FieldDefinition(name="ultrasound_done", label="Ultrasound Done", field_type=FieldType.BOOLEAN),
        FieldDefinition(
            name="iron_supplementation",
            label="Iron Supplementation",
            field_type=FieldType.BOOLEAN,
        ),
        FieldDefinition(
            name="calcium_supplementation",
            label="Calcium Supplementation",
            field_type=FieldType.BOOLEAN,
        ),
        FieldDefinition(
            name="tetanus_toxoid_given",
            label="Tetanus Toxoid Given",
            field_type=FieldType.BOOLEAN,
        ),
        FieldDefinition(name="deworming_done", label="Deworming Done", field_type=FieldType.BOOLEAN),
        FieldDefinition(
            name="glucose_challenge_test",
            label="Glucose Challenge Test",
            field_type=FieldType.BOOLEAN,
        ),
        FieldDefinition(
            name="fever_or_urinary_symptoms",
            label="Fever or Urinary Symptoms",
            field_type=FieldType.BOOLEAN,
        ),
        FieldDefinition(
            name="headache_epigastric_visual_symptoms",
            label="Headache/Epigastric/Visual Symptoms",
            field_type=FieldType.BOOLEAN,
        ),
    ],
)

THIRD_TRIMESTER_ANC = SectionDefinition(
    section_key="third_trimester_anc",
    section_label="Third Trimester ANC",
    category="event_based",
    description="Third trimester antenatal care visits",
    fields=[
        FieldDefinition(name="anc_visits", label="ANC Visits", field_type=FieldType.INTEGER, unit="count"),
        FieldDefinition(
            name="iron_supplementation",
            label="Iron Supplementation",
            field_type=FieldType.BOOLEAN,
        ),
        FieldDefinition(
            name="calcium_supplementation",
            label="Calcium Supplementation",
            field_type=FieldType.BOOLEAN,
        ),
        FieldDefinition(
            name="fetal_movement_normal",
            label="Fetal Movement Normal",
            field_type=FieldType.BOOLEAN,
        ),
        FieldDefinition(
            name="fever_or_urinary_symptoms",
            label="Fever or Urinary Symptoms",
            field_type=FieldType.BOOLEAN,
        ),
        FieldDefinition(
            name="vaginal_bleeding_or_discharge",
            label="Vaginal Bleeding or Discharge",
            field_type=FieldType.BOOLEAN,
        ),
        FieldDefinition(
            name="headache_epigastric_visual_symptoms",
            label="Headache/Epigastric/Visual Symptoms",
            field_type=FieldType.BOOLEAN,
        ),
    ],
)

# ============================================================================
# CLINICAL EXAMINATION MODULE (EVENT-BASED)
# ============================================================================

GENERAL_EXAMINATION = SectionDefinition(
    section_key="general_examination",
    section_label="General Examination",
    category="event_based",
    description="General physical examination findings",
    fields=[
        FieldDefinition(
            name="general_appearance",
            label="General Appearance",
            field_type=FieldType.ENUM,
            enum_values=["Normal", "Ill-looking", "Toxic", "Well-nourished", "Malnourished"],
        ),
        FieldDefinition(
            name="level_of_consciousness",
            label="Level of Consciousness",
            field_type=FieldType.ENUM,
            enum_values=["Alert", "Drowsy", "Confused", "Unconscious"],
        ),
        FieldDefinition(name="orientation", label="Orientation", field_type=FieldType.BOOLEAN),
    ],
)

VITALS = SectionDefinition(
    section_key="vitals",
    section_label="Vital Signs",
    category="event_based",
    description="Patient vital signs",
    fields=[
        FieldDefinition(name="pulse_rate", label="Pulse Rate", field_type=FieldType.INTEGER, unit="bpm"),
        FieldDefinition(
            name="blood_pressure_systolic",
            label="Blood Pressure (Systolic)",
            field_type=FieldType.INTEGER,
            unit="mmHg",
        ),
        FieldDefinition(
            name="blood_pressure_diastolic",
            label="Blood Pressure (Diastolic)",
            field_type=FieldType.INTEGER,
            unit="mmHg",
        ),
        FieldDefinition(
            name="respiratory_rate",
            label="Respiratory Rate",
            field_type=FieldType.INTEGER,
            unit="breaths/min",
        ),
        FieldDefinition(name="temperature", label="Temperature", field_type=FieldType.FLOAT, unit="°C"),
        FieldDefinition(name="height", label="Height", field_type=FieldType.FLOAT, unit="cm"),
        FieldDefinition(name="weight", label="Weight", field_type=FieldType.FLOAT, unit="kg"),
        FieldDefinition(
            name="body_mass_index",
            label="Body Mass Index (BMI)",
            field_type=FieldType.FLOAT,
            unit="kg/m²",
            description="Auto-calculated",
        ),
    ],
)

GENERAL_SIGNS = SectionDefinition(
    section_key="general_signs",
    section_label="General Signs",
    category="event_based",
    description="General clinical signs",
    fields=[
        FieldDefinition(name="pallor", label="Pallor", field_type=FieldType.BOOLEAN),
        FieldDefinition(name="icterus", label="Icterus", field_type=FieldType.BOOLEAN),
        FieldDefinition(name="cyanosis", label="Cyanosis", field_type=FieldType.BOOLEAN),
        FieldDefinition(name="clubbing", label="Clubbing", field_type=FieldType.BOOLEAN),
        FieldDefinition(name="edema", label="Edema", field_type=FieldType.BOOLEAN),
        FieldDefinition(name="dehydration", label="Dehydration", field_type=FieldType.BOOLEAN),
        FieldDefinition(name="lymphadenopathy", label="Lymphadenopathy", field_type=FieldType.BOOLEAN),
    ],
)

# ============================================================================
# SYSTEMIC AND OBSTETRIC EXAMINATION
# ============================================================================

PER_ABDOMINAL_EXAMINATION = SectionDefinition(
    section_key="per_abdominal_examination",
    section_label="Per Abdominal Examination",
    category="event_based",
    description="Obstetric abdominal examination",
    fields=[
        FieldDefinition(name="fundal_height", label="Fundal Height", field_type=FieldType.FLOAT, unit="cm"),
        FieldDefinition(
            name="symphysio_fundal_height",
            label="Symphysio-Fundal Height",
            field_type=FieldType.FLOAT,
            unit="cm",
        ),
        FieldDefinition(
            name="abdominal_girth",
            label="Abdominal Girth",
            field_type=FieldType.FLOAT,
            unit="cm",
        ),
        FieldDefinition(name="tenderness", label="Tenderness", field_type=FieldType.BOOLEAN),
        FieldDefinition(
            name="uterine_contractions",
            label="Uterine Contractions",
            field_type=FieldType.BOOLEAN,
        ),
        FieldDefinition(
            name="fetal_presentation",
            label="Fetal Presentation",
            field_type=FieldType.ENUM,
            enum_values=["Cephalic", "Breech", "Transverse", "Oblique"],
        ),
        FieldDefinition(
            name="fetal_heart_rate",
            label="Fetal Heart Rate",
            field_type=FieldType.INTEGER,
            unit="bpm",
        ),
    ],
)

CARDIOVASCULAR_RESPIRATORY = SectionDefinition(
    section_key="cardiovascular_respiratory",
    section_label="Cardiovascular & Respiratory Examination",
    category="event_based",
    description="Heart and lung examination",
    fields=[
        FieldDefinition(
            name="heart_sounds",
            label="Heart Sounds",
            field_type=FieldType.ENUM,
            enum_values=["Normal", "S1 loud", "S2 loud", "Murmur present", "Abnormal"],
        ),
        FieldDefinition(
            name="lung_auscultation",
            label="Lung Auscultation",
            field_type=FieldType.ENUM,
            enum_values=["Clear", "Crepitations", "Wheeze", "Reduced air entry", "Abnormal"],
        ),
    ],
)

# ============================================================================
# INVESTIGATION MODULE (DATE-WISE / EVENT-BASED)
# ============================================================================

BLOOD_INVESTIGATIONS = SectionDefinition(
    section_key="blood_investigations",
    section_label="Blood Investigations",
    category="event_based",
    description="Complete blood count and basic blood tests",
    fields=[
        FieldDefinition(name="hemoglobin", label="Hemoglobin", field_type=FieldType.FLOAT, unit="g/dL"),
        FieldDefinition(
            name="total_leukocyte_count",
            label="Total Leukocyte Count (TLC)",
            field_type=FieldType.INTEGER,
            unit="cells/mm³",
        ),
        FieldDefinition(
            name="platelet_count",
            label="Platelet Count",
            field_type=FieldType.INTEGER,
            unit="cells/mm³",
        ),
        FieldDefinition(name="blood_group", label="Blood Group", field_type=FieldType.STRING),
        FieldDefinition(
            name="blood_glucose",
            label="Blood Glucose",
            field_type=FieldType.FLOAT,
            unit="mg/dL",
        ),
        FieldDefinition(name="uric_acid", label="Uric Acid", field_type=FieldType.FLOAT, unit="mg/dL"),
        FieldDefinition(
            name="serum_cholesterol",
            label="Serum Cholesterol",
            field_type=FieldType.FLOAT,
            unit="mg/dL",
        ),
    ],
)

RENAL_FUNCTION_TESTS = SectionDefinition(
    section_key="renal_function_tests",
    section_label="Renal Function Tests",
    category="event_based",
    description="Kidney function markers",
    fields=[
        FieldDefinition(name="blood_urea", label="Blood Urea", field_type=FieldType.FLOAT, unit="mg/dL"),
        FieldDefinition(
            name="serum_creatinine",
            label="Serum Creatinine",
            field_type=FieldType.FLOAT,
            unit="mg/dL",
        ),
        FieldDefinition(
            name="serum_electrolytes",
            label="Serum Electrolytes",
            field_type=FieldType.OBJECT,
            unit="mmol/L",
            description="Object with Na, K, Cl",
        ),
    ],
)

LIVER_FUNCTION_TESTS = SectionDefinition(
    section_key="liver_function_tests",
    section_label="Liver Function Tests",
    category="event_based",
    description="Liver function markers",
    fields=[
        FieldDefinition(
            name="total_protein",
            label="Total Protein",
            field_type=FieldType.FLOAT,
            unit="g/dL",
        ),
        FieldDefinition(name="albumin", label="Albumin", field_type=FieldType.FLOAT, unit="g/dL"),
        FieldDefinition(name="globulin", label="Globulin", field_type=FieldType.FLOAT, unit="g/dL"),
        FieldDefinition(
            name="bilirubin_total",
            label="Bilirubin (Total)",
            field_type=FieldType.FLOAT,
            unit="mg/dL",
        ),
        FieldDefinition(
            name="bilirubin_conjugated",
            label="Bilirubin (Conjugated)",
            field_type=FieldType.FLOAT,
            unit="mg/dL",
        ),
        FieldDefinition(
            name="bilirubin_unconjugated",
            label="Bilirubin (Unconjugated)",
            field_type=FieldType.FLOAT,
            unit="mg/dL",
        ),
        FieldDefinition(
            name="liver_enzymes",
            label="Liver Enzymes",
            field_type=FieldType.OBJECT,
            unit="IU/L",
            description="Object with AST, ALT",
        ),
    ],
)

SEROLOGY = SectionDefinition(
    section_key="serology",
    section_label="Serology",
    category="event_based",
    description="Infectious disease screening",
    fields=[
        FieldDefinition(name="hiv", label="HIV", field_type=FieldType.BOOLEAN),
        FieldDefinition(name="hepatitis_b", label="Hepatitis B", field_type=FieldType.BOOLEAN),
        FieldDefinition(name="syphilis", label="Syphilis", field_type=FieldType.BOOLEAN),
    ],
)

THYROID_FUNCTION_TESTS = SectionDefinition(
    section_key="thyroid_function_tests",
    section_label="Thyroid Function Tests",
    category="event_based",
    description="Thyroid hormone levels",
    fields=[
        FieldDefinition(name="tsh", label="TSH", field_type=FieldType.FLOAT, unit="µIU/mL"),
        FieldDefinition(name="t3", label="T3", field_type=FieldType.FLOAT, unit="ng/dL"),
        FieldDefinition(name="t4", label="T4", field_type=FieldType.FLOAT, unit="µg/dL"),
    ],
)

# ============================================================================
# ULTRASONOGRAPHY MODULE
# ============================================================================

ULTRASONOGRAPHY = SectionDefinition(
    section_key="ultrasonography",
    section_label="Ultrasonography",
    category="event_based",
    description="Ultrasound findings",
    fields=[
        FieldDefinition(
            name="gestational_age",
            label="Gestational Age",
            field_type=FieldType.INTEGER,
            unit="weeks",
        ),
        FieldDefinition(
            name="fetal_heart_rate",
            label="Fetal Heart Rate",
            field_type=FieldType.INTEGER,
            unit="bpm",
        ),
        FieldDefinition(
            name="placental_location",
            label="Placental Location",
            field_type=FieldType.ENUM,
            enum_values=["Anterior", "Posterior", "Fundal", "Low-lying", "Previa"],
        ),
        FieldDefinition(
            name="amniotic_fluid_index",
            label="Amniotic Fluid Index (AFI)",
            field_type=FieldType.FLOAT,
            unit="cm",
        ),
        FieldDefinition(
            name="fetal_presentation",
            label="Fetal Presentation",
            field_type=FieldType.ENUM,
            enum_values=["Cephalic", "Breech", "Transverse", "Oblique"],
        ),
        FieldDefinition(
            name="estimated_fetal_weight",
            label="Estimated Fetal Weight",
            field_type=FieldType.FLOAT,
            unit="kg",
        ),
    ],
)

# ============================================================================
# URINE EXAMINATION MODULE
# ============================================================================

URINE_EXAMINATION = SectionDefinition(
    section_key="urine_examination",
    section_label="Urine Examination",
    category="event_based",
    description="Urine analysis results",
    fields=[
        FieldDefinition(
            name="dipstick_protein",
            label="Dipstick Protein",
            field_type=FieldType.ENUM,
            enum_values=["Negative", "Trace", "+", "++", "+++", "++++"],
        ),
        FieldDefinition(
            name="urine_protein_24hr",
            label="24-hour Urine Protein",
            field_type=FieldType.FLOAT,
            unit="mg/24h",
        ),
        FieldDefinition(
            name="protein_creatinine_ratio",
            label="Protein:Creatinine Ratio",
            field_type=FieldType.FLOAT,
            unit="mg/mg",
        ),
    ],
)

# ============================================================================
# COMPLETE SCHEMA REGISTRY
# ============================================================================

MEDICAL_SCHEMA: Dict[str, SectionDefinition] = {
    # Static/Master sections
    "patient_particulars": PATIENT_PARTICULARS,
    "menstrual_history": MENSTRUAL_HISTORY,
    "contraceptive_history": CONTRACEPTIVE_HISTORY,
    "past_medical_history": PAST_MEDICAL_HISTORY,
    "family_history": FAMILY_HISTORY,
    "present_pregnancy": PRESENT_PREGNANCY,
    
    # Obstetric history
    "obstetric_history": OBSTETRIC_HISTORY,
    
    # Event-based ANC sections
    "first_trimester_anc": FIRST_TRIMESTER_ANC,
    "second_trimester_anc": SECOND_TRIMESTER_ANC,
    "third_trimester_anc": THIRD_TRIMESTER_ANC,
    
    # Event-based examination sections
    "general_examination": GENERAL_EXAMINATION,
    "vitals": VITALS,
    "general_signs": GENERAL_SIGNS,
    "per_abdominal_examination": PER_ABDOMINAL_EXAMINATION,
    "cardiovascular_respiratory": CARDIOVASCULAR_RESPIRATORY,
    
    # Event-based investigation sections
    "blood_investigations": BLOOD_INVESTIGATIONS,
    "renal_function_tests": RENAL_FUNCTION_TESTS,
    "liver_function_tests": LIVER_FUNCTION_TESTS,
    "serology": SEROLOGY,
    "thyroid_function_tests": THYROID_FUNCTION_TESTS,
    "ultrasonography": ULTRASONOGRAPHY,
    "urine_examination": URINE_EXAMINATION,
}


def get_section_definition(section_key: str) -> Optional[SectionDefinition]:
    """Get section definition by key."""
    return MEDICAL_SCHEMA.get(section_key)


def get_all_sections() -> List[SectionDefinition]:
    """Get all section definitions."""
    return list(MEDICAL_SCHEMA.values())


def get_sections_by_category(category: str) -> List[SectionDefinition]:
    """Get sections filtered by category."""
    return [s for s in MEDICAL_SCHEMA.values() if s.category == category]
