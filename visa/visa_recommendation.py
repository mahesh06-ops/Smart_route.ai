"""
Visa Recommendation Engine for Smart Visa Route.
Executes end-to-end matching pipeline across all supported global nations,
ranks destinations dynamically, and synthesizes explainable recommendations.
"""
from datetime import datetime
from typing import List, Dict, Any, Optional
from visa.visa_models import (
    UserProfile,
    CountryDetail,
    RecommendationItem,
    RecommendationResponse,
    SmartScoreBreakdown,
    WhatIfSimulationRequest,
    WhatIfSimulationResponse,
    OfficialSource
)
from visa.visa_data_service import visa_data_service
from visa.visa_scoring import scoring_engine
from src.utils.logging_config import logger


class VisaRecommendationPipeline:
    @classmethod
    def evaluate_profile(cls, profile: UserProfile) -> RecommendationResponse:
        """
        Runs the complete profile matching and ranking algorithm against ALL supported countries.
        """
        # Step 1: Fetch all supported countries from live database
        all_country_summaries = visa_data_service.get_all_countries()
        total_available = len(all_country_summaries)

        evaluated_items: List[RecommendationItem] = []

        for summary in all_country_summaries:
            # Check regional preference if specified
            if profile.target_regions and len(profile.target_regions) > 0:
                if not any(r.lower() in summary.region.lower() for r in profile.target_regions):
                    continue

            # Fetch detailed country object
            detail = visa_data_service.get_country_detail(summary.code)
            if not detail:
                continue

            # Calculate multi-factor Smart Score
            breakdown = scoring_engine.calculate_score(profile, detail)

            # Extract matching category details
            visa_cat_info = detail.visas.get(profile.purpose)
            visa_name = visa_cat_info.visa_name if visa_cat_info else f"{detail.name} {profile.purpose}"

            # Generate pros and trade-offs
            pros, trade_offs, next_steps = cls._generate_insights(profile, detail, breakdown, visa_cat_info)

            rec_item = RecommendationItem(
                rank=0,  # Assigned after sorting
                country_code=detail.code,
                country_name=detail.name,
                flag_emoji=detail.flag_emoji,
                region=detail.region,
                smart_score=breakdown.total_score,
                badge=None,
                best_visa_category=profile.purpose,
                visa_name=visa_name,
                score_breakdown=breakdown,
                pros=pros,
                trade_offs=trade_offs,
                official_source=detail.official_source,
                next_steps=next_steps
            )
            evaluated_items.append(rec_item)

        # Sort all evaluated countries strictly by Smart Score descending
        evaluated_items.sort(key=lambda x: x.smart_score, reverse=True)

        # Assign ranks and badges
        badges = [
            "⭐ BEST VISA ROUTE",
            "🥈 TOP RUNNER-UP",
            "🥉 HIGHLY RECOMMENDED"
        ]

        for i, item in enumerate(evaluated_items):
            item.rank = i + 1
            if i < len(badges):
                item.badge = badges[i]

        top_3 = evaluated_items[:3]
        top_10 = evaluated_items[:10]

        all_ranked_summary = [
            {
                "rank": item.rank,
                "country_code": item.country_code,
                "country_name": item.country_name,
                "flag_emoji": item.flag_emoji,
                "region": item.region,
                "smart_score": item.smart_score,
                "badge": item.badge,
                "visa_name": item.visa_name,
                "official_source": item.official_source.name,
                "official_url": item.official_source.url
            }
            for item in evaluated_items
        ]

        now_str = datetime.now().strftime("%d %B %Y, %H:%M")

        return RecommendationResponse(
            total_countries_evaluated=len(evaluated_items),
            user_purpose=profile.purpose,
            user_priority=profile.priority.value if hasattr(profile.priority, "value") else str(profile.priority),
            top_3=top_3,
            top_10=top_10,
            all_ranked_summary=all_ranked_summary,
            evaluation_timestamp=now_str,
            live_data_used=True
        )

    @classmethod
    def simulate_what_if(cls, request: WhatIfSimulationRequest) -> WhatIfSimulationResponse:
        """
        Performs real-time What-If scenario re-scoring and delta analysis.
        """
        base_resp = cls.evaluate_profile(request.base_profile)
        orig_score_map = {item.country_code: item.smart_score for item in base_resp.top_10}

        # Build modified profile
        sim_profile = request.base_profile.model_copy(deep=True)
        if request.adjusted_age is not None:
            sim_profile.age = request.adjusted_age
        if request.adjusted_budget is not None:
            sim_profile.monthly_budget_usd = request.adjusted_budget
        if request.adjusted_experience is not None:
            sim_profile.work_experience_years = request.adjusted_experience
        if request.adjusted_education is not None:
            sim_profile.education = request.adjusted_education
        if request.adjusted_languages is not None:
            sim_profile.language_skills = request.adjusted_languages
        if request.adjusted_priority is not None:
            sim_profile.priority = request.adjusted_priority

        sim_resp = cls.evaluate_profile(sim_profile)
        sim_score_map = {item.country_code: item.smart_score for item in sim_resp.top_10}

        # Compute deltas across countries
        deltas: Dict[str, float] = {}
        target_codes = request.target_country_codes or list(orig_score_map.keys())

        for code in target_codes:
            orig = orig_score_map.get(code, 0.0)
            # Find in sim
            sim_score = next((x["smart_score"] for x in sim_resp.all_ranked_summary if x["country_code"] == code), orig)
            delta = round(sim_score - orig, 1)
            deltas[code] = delta

        # Identify top gainers
        sorted_deltas = sorted(deltas.items(), key=lambda x: x[1], reverse=True)
        top_gainers = [
            {"country_code": c, "delta": d, "new_score": sim_score_map.get(c, 0.0)}
            for c, d in sorted_deltas if d > 0
        ]

        insights: List[str] = []
        if request.adjusted_experience and request.adjusted_experience > request.base_profile.work_experience_years:
            insights.append(f"Increasing work experience to {request.adjusted_experience} years boosts points across skilled work pathways.")
        if request.adjusted_budget and request.adjusted_budget > request.base_profile.monthly_budget_usd:
            insights.append("Higher monthly budget increases feasibility in high quality-of-life destinations.")
        if not insights:
            insights.append("Parameter adjustments updated destination scores dynamically based on official qualification criteria.")

        return WhatIfSimulationResponse(
            original_scores=orig_score_map,
            simulated_scores=sim_score_map,
            score_deltas=deltas,
            top_gainers=top_gainers,
            key_insights=insights,
            timestamp=datetime.now().strftime("%d %B %Y, %H:%M")
        )

    @classmethod
    def _generate_insights(
        cls,
        profile: UserProfile,
        country: CountryDetail,
        breakdown: SmartScoreBreakdown,
        visa_cat_info: Optional[Any]
    ) -> tuple[List[str], List[str], List[str]]:
        """Generates dynamic pros, trade-offs, and actionable next steps."""
        pros = []
        trade_offs = []
        next_steps = []

        # Pros
        if breakdown.safety >= 85:
            pros.append(f"Exceptional global safety rating ({country.safety_index:.1f}/100)")
        if breakdown.job_opportunities >= 85:
            pros.append(f"High industry demand for {profile.field.capitalize()} professionals")
        if country.avg_annual_salary_usd >= 50000:
            pros.append(f"Attractive average annual salary (~${country.avg_annual_salary_usd:,.0f} USD)")
        if breakdown.visa_suitability >= 80:
            pros.append(f"Streamlined eligibility pathway under {visa_cat_info.visa_name if visa_cat_info else 'immigration rules'}")
        if not pros:
            pros.append("Balanced living standards and established immigration framework")

        # Trade-offs
        if country.cost_of_living_index >= 70:
            trade_offs.append(f"Higher cost of living index ({country.cost_of_living_index:.1f}/100)")
        if breakdown.language_compatibility < 75:
            trade_offs.append(f"Language integration required ({', '.join(country.primary_languages)})")
        if visa_cat_info and "month" in visa_cat_info.processing_time.lower():
            trade_offs.append(f"Longer processing window ({visa_cat_info.processing_time})")
        if not trade_offs:
            trade_offs.append("Standard documentation and verification requirements apply")

        # Next Steps
        portal_name = country.official_source.name
        next_steps.append(f"Check document checklists on the official {portal_name} portal")
        if visa_cat_info and visa_cat_info.required_documents:
            next_steps.append(f"Prepare key documents: {', '.join(visa_cat_info.required_documents[:2])}")
        next_steps.append("Validate current processing fees and consular appointment availability")

        return pros, trade_offs, next_steps


recommendation_pipeline = VisaRecommendationPipeline()
