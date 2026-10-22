"""
Data models and schemas for Smart Visa Route.
Defines strongly-typed Pydantic models for countries, visa categories, live sources,
user profiles, score breakdowns, comparisons, and simulation scenarios.
"""
from enum import Enum
from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field


class VisaCategoryEnum(str, Enum):
    WORK = "Work Visa"
    STUDENT = "Student Visa"
    BUSINESS = "Business/Entrepreneur Visa"
    FAMILY = "Family Visa"
    RESIDENCE = "Residence/Immigration"
    DIGITAL_NOMAD = "Digital Nomad Visa"
    VISITOR = "Visitor/Tourist Visa"


class PriorityEnum(str, Enum):
    BALANCED = "balanced"
    SAFETY = "safety"
    JOB = "job"
    VISA = "visa"
    LOW_COST = "low_cost"
    QUALITY = "quality"


class OfficialSource(BaseModel):
    name: str = Field(..., description="Official government immigration authority name")
    url: str = Field(..., description="Direct URL to official immigration portal")
    last_checked: str = Field(..., description="Date/timestamp when source was verified")
    is_live: bool = Field(default=True, description="Whether live connectivity is active")


class VisaDetail(BaseModel):
    category: str
    visa_name: str
    description: str
    eligibility: List[str]
    processing_time: str
    fees: str
    required_documents: List[str]
    official_source: OfficialSource
    last_updated: str
    is_available: bool = True
    notes: Optional[str] = None


class CountrySummary(BaseModel):
    code: str
    name: str
    flag_emoji: str
    region: str
    capital: str
    primary_languages: List[str]
    safety_index: float  # 0 to 100
    cost_of_living_index: float  # Baseline 100 (e.g. NYC = 100, India = 24, Germany = 65)
    quality_of_life_index: float  # 0 to 100
    avg_annual_salary_usd: float
    tech_job_demand_index: float  # 0 to 100
    official_source: OfficialSource
    supported_categories: List[str]
    live_data_available: bool = True
    last_checked: str


class CountryDetail(CountrySummary):
    visas: Dict[str, VisaDetail] = Field(default_factory=dict)
    visa_free_access_count: int = 150
    minimum_monthly_budget_usd: float = 1200.0
    common_pathways: List[str] = Field(default_factory=list)


class UserProfile(BaseModel):
    current_country: str = Field(..., description="Applicant's current country of citizenship/residence")
    age: int = Field(default=28, ge=18, le=99)
    education: str = Field(default="bachelor", description="high_school, bachelor, master, phd")
    field: str = Field(default="tech", description="tech, healthcare, business, engineering, arts, hospitality, trade, other")
    work_experience_years: int = Field(default=4, ge=0, le=50)
    purpose: str = Field(default="Work Visa", description="Selected visa category purpose")
    monthly_budget_usd: float = Field(default=2500.0, ge=100.0)
    language_skills: List[str] = Field(default_factory=lambda: ["English"])
    family_status: str = Field(default="single", description="single, married, married_with_kids")
    priority: PriorityEnum = Field(default=PriorityEnum.BALANCED)
    target_regions: Optional[List[str]] = Field(default=None, description="Optional region filter")


class SmartScoreBreakdown(BaseModel):
    visa_suitability: float = Field(..., description="Score 0-100 based on eligibility and requirements")
    safety: float = Field(..., description="Score 0-100 based on global safety index")
    job_opportunities: float = Field(..., description="Score 0-100 based on field alignment and demand")
    salary_potential: float = Field(..., description="Score 0-100 relative earning potential")
    cost_affordability: float = Field(..., description="Score 0-100 financial feasibility vs budget")
    healthcare_quality: float = Field(..., description="Score 0-100 quality of life and public infrastructure")
    language_compatibility: float = Field(..., description="Score 0-100 language alignment")
    total_score: float = Field(..., description="Weighted composite Smart Score 0-100")


class RecommendationItem(BaseModel):
    rank: int
    country_code: str
    country_name: str
    flag_emoji: str
    region: str
    smart_score: float
    badge: Optional[str] = None  # e.g., "⭐ BEST VISA ROUTE", "🥈 TOP RUNNER-UP", "🥉 HIGHLY RECOMMENDED"
    best_visa_category: str
    visa_name: str
    score_breakdown: SmartScoreBreakdown
    pros: List[str]
    trade_offs: List[str]
    official_source: OfficialSource
    next_steps: List[str]


class RecommendationResponse(BaseModel):
    total_countries_evaluated: int
    user_purpose: str
    user_priority: str
    top_3: List[RecommendationItem]
    top_10: List[RecommendationItem]
    all_ranked_summary: List[Dict[str, Any]]
    evaluation_timestamp: str
    live_data_used: bool
    disclaimer: str = (
        "Visa and immigration information can change. This application provides decision-support information "
        "only and does not guarantee visa approval. Always verify current requirements with the relevant "
        "official government/immigration authority."
    )


class ComparisonItem(BaseModel):
    country_code: str
    country_name: str
    flag_emoji: str
    region: str
    safety_index: float
    cost_of_living_index: float
    avg_annual_salary_usd: float
    quality_of_life_index: float
    visa_details_for_purpose: Optional[VisaDetail] = None
    smart_score: float
    official_source: OfficialSource


class ComparisonResponse(BaseModel):
    purpose: str
    countries: List[ComparisonItem]
    timestamp: str
    disclaimer: str


class WhatIfSimulationRequest(BaseModel):
    base_profile: UserProfile
    adjusted_age: Optional[int] = None
    adjusted_budget: Optional[float] = None
    adjusted_experience: Optional[int] = None
    adjusted_education: Optional[str] = None
    adjusted_languages: Optional[List[str]] = None
    adjusted_priority: Optional[PriorityEnum] = None
    target_country_codes: Optional[List[str]] = None


class WhatIfSimulationResponse(BaseModel):
    original_scores: Dict[str, float]
    simulated_scores: Dict[str, float]
    score_deltas: Dict[str, float]
    top_gainers: List[Dict[str, Any]]
    key_insights: List[str]
    timestamp: str
