"""
Smart Score Engine for Smart Visa Route.
Computes multi-dimensional objective destination scores (0-100) based on verified
macroeconomic indicators, immigration criteria matching, and user priority weighting.
"""
from typing import Dict, Any, Tuple
from visa.visa_models import (
    UserProfile,
    CountryDetail,
    CountrySummary,
    SmartScoreBreakdown,
    PriorityEnum
)


class VisaScoringEngine:
    # Priority weighting profiles
    WEIGHTS_TABLE: Dict[str, Dict[str, float]] = {
        PriorityEnum.BALANCED: {
            "visa_suitability": 0.25,
            "safety": 0.15,
            "job_opportunities": 0.15,
            "salary_potential": 0.15,
            "cost_affordability": 0.15,
            "healthcare_quality": 0.10,
            "language_compatibility": 0.05
        },
        PriorityEnum.SAFETY: {
            "visa_suitability": 0.20,
            "safety": 0.35,
            "job_opportunities": 0.10,
            "salary_potential": 0.10,
            "cost_affordability": 0.10,
            "healthcare_quality": 0.10,
            "language_compatibility": 0.05
        },
        PriorityEnum.JOB: {
            "visa_suitability": 0.20,
            "safety": 0.10,
            "job_opportunities": 0.30,
            "salary_potential": 0.25,
            "cost_affordability": 0.05,
            "healthcare_quality": 0.05,
            "language_compatibility": 0.05
        },
        PriorityEnum.VISA: {
            "visa_suitability": 0.40,
            "safety": 0.10,
            "job_opportunities": 0.15,
            "salary_potential": 0.10,
            "cost_affordability": 0.10,
            "healthcare_quality": 0.10,
            "language_compatibility": 0.05
        },
        PriorityEnum.LOW_COST: {
            "visa_suitability": 0.20,
            "safety": 0.10,
            "job_opportunities": 0.10,
            "salary_potential": 0.10,
            "cost_affordability": 0.35,
            "healthcare_quality": 0.10,
            "language_compatibility": 0.05
        },
        PriorityEnum.QUALITY: {
            "visa_suitability": 0.20,
            "safety": 0.20,
            "job_opportunities": 0.10,
            "salary_potential": 0.10,
            "cost_affordability": 0.10,
            "healthcare_quality": 0.25,
            "language_compatibility": 0.05
        }
    }

    @classmethod
    def calculate_score(
        cls,
        profile: UserProfile,
        country: CountryDetail
    ) -> SmartScoreBreakdown:
        """
        Calculates granular factor scores and composite weighted Smart Score.
        """
        # 1. Visa Suitability & Pathway Fit (0 - 100)
        visa_suitability = cls._evaluate_visa_suitability(profile, country)

        # 2. Safety Index (0 - 100)
        safety = max(0.0, min(100.0, country.safety_index))

        # 3. Job Opportunities (0 - 100)
        job_opportunities = cls._evaluate_job_market(profile, country)

        # 4. Salary Potential (0 - 100)
        # Scaled relative to $100k benchmark
        salary_norm = min(100.0, (country.avg_annual_salary_usd / 100000.0) * 100.0)
        # Boost for master/phd or high experience
        exp_boost = min(10.0, profile.work_experience_years * 1.5)
        salary_potential = min(100.0, salary_norm + exp_boost)

        # 5. Cost Affordability vs Budget (0 - 100)
        cost_affordability = cls._evaluate_affordability(profile, country)

        # 6. Quality of Life & Healthcare (0 - 100)
        healthcare_quality = max(0.0, min(100.0, country.quality_of_life_index))

        # 7. Language Compatibility (0 - 100)
        language_compatibility = cls._evaluate_language(profile, country)

        # Apply Priority Weights
        priority_key = profile.priority.value if hasattr(profile.priority, "value") else str(profile.priority)
        weights = cls.WEIGHTS_TABLE.get(priority_key, cls.WEIGHTS_TABLE[PriorityEnum.BALANCED])

        total_score = (
            visa_suitability * weights["visa_suitability"] +
            safety * weights["safety"] +
            job_opportunities * weights["job_opportunities"] +
            salary_potential * weights["salary_potential"] +
            cost_affordability * weights["cost_affordability"] +
            healthcare_quality * weights["healthcare_quality"] +
            language_compatibility * weights["language_compatibility"]
        )

        total_score = round(max(0.0, min(100.0, total_score)), 1)

        return SmartScoreBreakdown(
            visa_suitability=round(visa_suitability, 1),
            safety=round(safety, 1),
            job_opportunities=round(job_opportunities, 1),
            salary_potential=round(salary_potential, 1),
            cost_affordability=round(cost_affordability, 1),
            healthcare_quality=round(healthcare_quality, 1),
            language_compatibility=round(language_compatibility, 1),
            total_score=total_score
        )

    @classmethod
    def _evaluate_visa_suitability(cls, profile: UserProfile, country: CountryDetail) -> float:
        """Calculates suitability score based on age, education, and purpose availability."""
        score = 70.0

        # Purpose availability
        if profile.purpose in country.supported_categories:
            score += 10.0
        else:
            score -= 25.0

        # Age points (Points-tested visas favor 22-35)
        if 22 <= profile.age <= 32:
            score += 10.0
        elif 33 <= profile.age <= 39:
            score += 5.0
        elif profile.age > 45:
            score -= 10.0

        # Education qualification
        edu_lower = profile.education.lower()
        if "phd" in edu_lower or "doctorate" in edu_lower:
            score += 10.0
        elif "master" in edu_lower:
            score += 8.0
        elif "bachelor" in edu_lower:
            score += 5.0

        # Experience
        if profile.work_experience_years >= 5:
            score += 5.0
        elif profile.work_experience_years >= 2:
            score += 2.0

        return max(20.0, min(98.0, score))

    @classmethod
    def _evaluate_job_market(cls, profile: UserProfile, country: CountryDetail) -> float:
        """Evaluates industry demand in the country."""
        base_demand = country.tech_job_demand_index
        field_lower = profile.field.lower()

        if field_lower in ["tech", "software", "engineering", "ai", "data"]:
            return min(100.0, base_demand + 4.0)
        elif field_lower in ["healthcare", "medicine", "nursing"]:
            # High universal global demand
            return min(100.0, base_demand + 6.0)
        elif field_lower in ["business", "finance", "management"]:
            return min(100.0, base_demand)
        else:
            return max(40.0, base_demand - 5.0)

    @classmethod
    def _evaluate_affordability(cls, profile: UserProfile, country: CountryDetail) -> float:
        """Evaluates financial headroom: user budget vs country's cost of living index."""
        # Baseline living cost in USD/mo estimated as (cost_of_living_index / 100) * $2,200
        est_monthly_cost = (country.cost_of_living_index / 100.0) * 2200.0
        user_budget = profile.monthly_budget_usd

        if user_budget >= est_monthly_cost * 1.5:
            return 95.0
        elif user_budget >= est_monthly_cost:
            ratio = user_budget / est_monthly_cost
            return 70.0 + (ratio - 1.0) * 40.0
        else:
            # Budget below estimated cost
            deficit_ratio = user_budget / max(100.0, est_monthly_cost)
            return max(20.0, deficit_ratio * 70.0)

    @classmethod
    def _evaluate_language(cls, profile: UserProfile, country: CountryDetail) -> float:
        """Evaluates language compatibility."""
        user_langs = [l.lower().strip() for l in profile.language_skills]
        country_langs = [l.lower().strip() for l in country.primary_languages]

        # Exact overlap
        common = set(user_langs).intersection(set(country_langs))
        if common:
            return 95.0

        # English lingua-franca check
        if "english" in user_langs:
            # High English proficiency countries in Europe / Asia
            if country.region in ["Europe", "Asia-Pacific"] or country.code in ["SGP", "DEU", "NLD", "SWE", "NOR", "DNK", "FIN", "CHE", "ARE", "QAT", "IND", "MYS"]:
                return 82.0
            return 65.0

        return 50.0


scoring_engine = VisaScoringEngine()
