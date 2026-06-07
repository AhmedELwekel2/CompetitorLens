import os
import aiohttp
import json
import asyncio  # Add this import
import re
import traceback
from typing import Dict, List, Optional, Any
from datetime import datetime
from openai import AzureOpenAI
import logging
import base64
from dotenv import load_dotenv
from token_monitor import token_monitor, track_tokens
class GPTInsightsService:
    """
    AI Integration service for generating AI-powered SEO and marketing insights
    """
    
    def __init__(self):
        # Load ai_api/.env reliably even when launched from repo root
        env_path = os.path.join(os.path.dirname(__file__), ".env")
        load_dotenv(dotenv_path=env_path, override=False)
        self.azure_endpoint = os.environ.get('AZURE_OPENAI_ENDPOINT')
        self.api_key = os.environ.get('AZURE_OPENAI_API_KEY')
        self.api_version = os.environ.get('AZURE_OPENAI_API_VERSION')
        
        if not self.api_key:
            print("Warning: No Azure OpenAI API key found. AI insights will use mock data.")
        else:
            # Configure the Azure OpenAI client
            self.client = AzureOpenAI(
                azure_endpoint=self.azure_endpoint,
                api_key=self.api_key,
                api_version=self.api_version
            )
            
        # Use Azure deployment name for requests; fall back to a default
        self.model_name = os.environ.get("AZURE_OPENAI_DEPLOYMENT") or "gpt-5.2-chat"
        if self.api_key and not os.environ.get("AZURE_OPENAI_DEPLOYMENT"):
            logging.warning("AZURE_OPENAI_DEPLOYMENT is not set; using default deployment name.")
    
    async def generate_seo_insights(self, seo_data: Dict[str, Any], business_description: str, company_name: str, country: str, goal: str) -> Dict[str, Any]:
        """
        Generate AI-powered SEO insights and recommendations
        
        Args:
            seo_data: SEO analysis data from SEOAnalyzer
            
        Returns:
            Dictionary containing GPT-generated insights
        """
        
        if not self.api_key:
            logging.info("No Azure OpenAI API key found. AI insights will use mock data.")
            return self._generate_mock_seo_insights_api(seo_data)
        
        # Prepare prompt with caching optimization
        static_template, variable_data = self._create_seo_analysis_prompt(seo_data, business_description, company_name, country, goal, return_split=True)
        
        try:
            # Call Azure OpenAI API
            result = await self._call_ai_api(
                prompt="",  # Not used when static_template and variable_data are provided
                max_tokens=5000, 
                operation="seo_analysis",
                static_template=static_template,
                variable_data=variable_data
            )
            
            response = result.get("response", "") if isinstance(result, dict) else result
            token_usage = result.get("token_usage", {}) if isinstance(result, dict) else {}
            
            # Parse and structure the response
            insights = self._parse_seo_insights(response)
            
            return {
                "url": seo_data.get("url"),
                "generated_at": datetime.now().isoformat(),
                "insights": insights,
                "recommendations": self._extract_recommendations(response),
                "priority_score": self._calculate_priority_score(seo_data),
                "improvement_areas": self._identify_improvement_areas(seo_data),
                "token_usage": token_usage
            }
            
        except Exception as e:
            print(f"Azure OpenAI API error: {str(e)}")
            traceback.print_exc()
            mock_result = self._generate_mock_seo_insights(seo_data)
            mock_result["_debug_error"] = f"{str(e)}\n{traceback.format_exc()}"
            return mock_result

    async def generate_competitor_seo_insights(self, seo_data: Dict[str, Any], company_name: Optional[str] = None, business_description: Optional[str] = None, country: Optional[str] = None, goal: Optional[str] = None) -> Dict[str, Any]:
        """
        Generate AI-powered competitor SEO insights and recommendations
        
        Args:
            seo_data: SEO analysis data from SEOAnalyzer for competitor
            company_name: Optional company name for context
            business_description: Optional business description for context
            country: Optional country for context
            goal: Optional goal for context
            
        Returns:
            Dictionary containing GPT-generated competitor SEO insights
        """
        
        if not self.api_key:
            logging.info("No Azure OpenAI API key found. AI insights will use mock data.")
            return self._generate_mock_seo_insights_api(seo_data)
        
        # Prepare prompt with caching optimization
        static_template, variable_data = self._create_competitor_seo_analysis_prompt(seo_data, company_name, business_description, country, goal, return_split=True)
        
        try:
            # Call Azure OpenAI API
            result = await self._call_ai_api(
                prompt="",  # Not used when static_template and variable_data are provided
                max_tokens=5000, 
                operation="competitor_seo_analysis",
                static_template=static_template,
                variable_data=variable_data
            )
            
            response = result.get("response", "") if isinstance(result, dict) else result
            token_usage = result.get("token_usage", {}) if isinstance(result, dict) else {}
            
            # Ensure response is a string
            if response is None:
                response = ""
            if not isinstance(response, str):
                response = str(response) if response else ""
            
            # Log response status for debugging
            if not response or len(response.strip()) == 0:
                logging.warning(f"Empty response from competitor SEO analysis API. Result keys: {list(result.keys()) if isinstance(result, dict) else 'N/A'}")
            
            # Parse and structure the response
            insights = self._parse_seo_insights(response)
            
            # Ensure insights dict has required keys with fallback values
            if not insights or not isinstance(insights, dict):
                insights = {}
            
            # Ensure both keys exist with non-empty values
            if not insights.get("summary") or (isinstance(insights.get("summary"), str) and len(insights.get("summary", "").strip()) == 0):
                insights["summary"] = response[:200] + "..." if len(response) > 200 else response if response else ""
            if not insights.get("full_analysis") or (isinstance(insights.get("full_analysis"), str) and len(insights.get("full_analysis", "").strip()) == 0):
                insights["full_analysis"] = response if response else ""
            
            logging.info(f"Competitor SEO insights parsed - summary length: {len(str(insights.get('summary', '')))}, full_analysis length: {len(str(insights.get('full_analysis', '')))}")
            
            return {
                "url": seo_data.get("url"),
                "generated_at": datetime.now().isoformat(),
                "insights": insights,
                "recommendations": self._extract_recommendations(response),
                "priority_score": self._calculate_priority_score(seo_data),
                "improvement_areas": self._identify_improvement_areas(seo_data),
                "token_usage": token_usage
            }
            
        except Exception as e:
            print(f"Azure OpenAI API error: {str(e)}")
            traceback.print_exc()
            logging.error(f"Error in generate_competitor_seo_insights: {str(e)}", exc_info=True)
            mock_result = self._generate_mock_seo_insights(seo_data)
            mock_result["_debug_error"] = f"{str(e)}\n{traceback.format_exc()}"
            return mock_result
    
    async def generate_social_insights(self, social_data: Dict[str, Any],company_name: str,business_description: str,goal: str) -> Dict[str, Any]:
        """
        Generate AI-powered social media insights
        
        Args:
            social_data: Social media analysis data
            company_name: Company name
            business_description: Business description
            goal: Goal
        Returns:
            Dictionary containing social media insights
        """
        
        if not self.api_key:
            return self._generate_mock_social_insights(social_data)
        
        # Prepare prompt with caching optimization
        static_template, variable_data = self._create_social_analysis_prompt(social_data,company_name,business_description,goal, return_split=True)
        
        try:
            # Call Azure OpenAI API
            result = await self._call_ai_api(
                prompt="",  # Not used when static_template and variable_data are provided
                max_tokens=5000, 
                operation="social_analysis",
                static_template=static_template,
                variable_data=variable_data
            )
            
            response = result.get("response", "") if isinstance(result, dict) else result
            token_usage = result.get("token_usage", {}) if isinstance(result, dict) else {}
            
            return {
                "url": social_data.get("url"),
                "platform": social_data.get("platform"),
                "generated_at": datetime.now().isoformat(),
                "insights": self._parse_social_insights(response),
                "content_strategy": self._extract_content_strategy(response),
                "engagement_opportunities": self._identify_engagement_opportunities(social_data),
                "token_usage": token_usage
            }
            
        except Exception as e:
            print(f"Azure OpenAI API error: {str(e)}")
            traceback.print_exc()
            mock_result = self._generate_mock_social_insights(social_data)
            mock_result["_debug_error"] = f"{str(e)}\n{traceback.format_exc()}"
            return mock_result

    async def generate_competitor_social_insights(self, social_data: Dict[str, Any], company_name: Optional[str] = None, business_description: Optional[str] = None, country: Optional[str] = None, goal: Optional[str] = None) -> Dict[str, Any]:
        """
        Generate AI-powered competitor social media insights
        
        Args:
            social_data: Social media analysis data for competitor
            company_name: Optional company name for context
            business_description: Optional business description for context
            country: Optional country for context
            goal: Optional goal for context
            
        Returns:
            Dictionary containing competitor social media insights
        """
        
        if not self.api_key:
            return self._generate_mock_social_insights(social_data)
        
        # Prepare prompt with caching optimization
        static_template, variable_data = self._create_competitor_social_analysis_prompt(social_data, company_name, business_description, country, goal, return_split=True)
        
        try:
            # Call Azure OpenAI API
            result = await self._call_ai_api(
                prompt="",  # Not used when static_template and variable_data are provided
                max_tokens=5000, 
                operation="competitor_social_analysis",
                static_template=static_template,
                variable_data=variable_data
            )
            
            response = result.get("response", "") if isinstance(result, dict) else result
            token_usage = result.get("token_usage", {}) if isinstance(result, dict) else {}
            
            return {
                "url": social_data.get("url"),
                "platform": social_data.get("platform"),
                "generated_at": datetime.now().isoformat(),
                "insights": self._parse_social_insights(response),
                "content_strategy": self._extract_content_strategy(response),
                "engagement_opportunities": self._identify_engagement_opportunities(social_data),
                "token_usage": token_usage
            }
            
        except Exception as e:
            print(f"Azure OpenAI API error: {str(e)}")
            traceback.print_exc()
            mock_result = self._generate_mock_social_insights(social_data)
            mock_result["_debug_error"] = f"{str(e)}\n{traceback.format_exc()}"
            return mock_result
    
    async def generate_comprehensive_report(self, seo_data: Dict[str, Any], social_data: List[Dict[str, Any]], branding_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Generate a comprehensive marketing report combining SEO, social media, and branding insights
        
        Args:
            seo_data: SEO analysis results
            social_data: List of social media analysis results
            branding_data: Branding analysis results
            
        Returns:
            Comprehensive marketing insights report
        """
        
        prompt = self._create_comprehensive_report_prompt(seo_data, social_data, branding_data)
        
        try:
            token_usage = {}
            if self.api_key:
                result = await self._call_ai_api(prompt, max_tokens=5000, operation="comprehensive_report")
                response = result.get("response", "") if isinstance(result, dict) else result
                token_usage = result.get("token_usage", {}) if isinstance(result, dict) else {}
                comprehensive_insights = self._parse_comprehensive_insights(response)
            else:
                comprehensive_insights = self._generate_mock_comprehensive_insights(branding_data)
            
            return {
                "generated_at": datetime.now().isoformat(),
                "website_url": seo_data.get("url"),
                "social_profiles_analyzed": len(social_data),
                "executive_summary": comprehensive_insights.get("executive_summary"),
                "key_findings": comprehensive_insights.get("key_findings", []),
                "strategic_recommendations": comprehensive_insights.get("strategic_recommendations", []),
                "priority_actions": comprehensive_insights.get("priority_actions", []),
                "performance_benchmarks": self._generate_benchmarks(seo_data, social_data, branding_data),
                "next_steps": comprehensive_insights.get("next_steps", []),
                "token_usage": token_usage
            }
            
        except Exception as e:
            print(f"Error generating comprehensive report: {str(e)}")
            traceback.print_exc()
            mock_report = self._generate_mock_comprehensive_report(seo_data, social_data, branding_data)
            mock_report["_debug_error"] = f"{str(e)}\n{traceback.format_exc()}"
            return mock_report
    def _get_optimal_max_tokens(self, operation: str) -> int:
        """Return optimal max_tokens based on operation type"""
        token_map = {
            "seo_analysis": 3500,  # Reduced from 5000
            "competitor_seo_analysis": 3500,  # Same as normal SEO analysis
            "social_analysis": 3500,  # Reduced from 5000
            "competitor_social_analysis": 3500,  # Same as normal social analysis
            "branding_analysis": 3500,  # Reduced from 5000
            "competitor_branding_analysis": 3500,  # Same as normal branding analysis
            "sentiment_analysis": 3500,  # Reduced from 5000
            "comprehensive_report": 3500,  # Reduced from 5000
            "competitive_suggestions": 3500,  # Reduced from 2000
            "ai_analysis": 3500
        }
        return token_map.get(operation, 1500)  
    async def _call_ai_api(self, prompt: str, max_tokens: int = 3500, operation: str = "ai_analysis", 
                          cache_system_prompt: bool = True, static_template: Optional[str] = None, 
                          variable_data: Optional[str] = None) -> str:
        """
        Call Azure OpenAI API
        
        Args:
            prompt: Full prompt (used if static_template/variable_data not provided)
            static_template: Static prompt template (instructions, format, etc.)
            variable_data: Variable data that changes per request (actual data to analyze)
            cache_system_prompt: Whether to cache the system message (for future caching implementation)
        """
        try:
            # Standard system message
            system_message = """You are an expert SEO and digital marketing consultant. Provide actionable, data-driven insights and recommendations.

    Analysis Framework:
    - Focus on measurable metrics and KPIs
    - Prioritize recommendations by impact and effort
    - Provide specific, actionable steps
    - Consider cross-platform opportunities
    - Base insights on data patterns"""
            
            # Prepare messages for Azure OpenAI
            messages = []
            
            # Add system message
            messages.append({
                "role": "system", 
                "content": system_message
            })
            
            # Combine static template and variable data if both provided, otherwise use full prompt
            if static_template and variable_data:
                user_content = f"{static_template}\n\n{variable_data}"
            else:
                user_content = prompt
            
            messages.append({
                "role": "user", 
                "content": user_content
            })
            
            # Get optimal token allocation
            optimal_tokens = self._get_optimal_max_tokens(operation)
            max_tokens = min(max_tokens, optimal_tokens)
            
            # Map operation to MLflow experiment
            experiment_map = {
                "seo_analysis": "seo_analysis",
                "social_analysis": "social_analysis",
                "branding_analysis": "branding_analysis",
                "sentiment_analysis": "sentiment_analysis",
                "comprehensive_report": "comprehensive_report",
                "ai_analysis": "ai_general"
            }
            experiment_name = experiment_map.get(operation, "ai_general")

            # Track with token monitor (will be updated to work with Azure OpenAI)
            result = await token_monitor.track_openai_call(
                operation=operation,
                model=self.model_name,
                messages=messages,
                max_tokens=max_tokens,
                experiment_name=experiment_name,
                client=self.client
            )
            
            # Return both response and token_usage
            return {
                "response": result["response"],
                "token_usage": result.get("token_usage", {})
            }
        except Exception as e:
            print(f"Azure OpenAI API error: {str(e)}")
            traceback.print_exc()
            raise Exception(f"Azure OpenAI API error: {str(e)}")
    
    def _split_prompt_for_caching(self, full_prompt: str, data_placeholder: str = "{{DATA}}") -> tuple[str, str]:
        """
        Helper method to split a prompt into static template (cacheable) and variable data.
        
        Returns:
            tuple: (static_template, variable_data) where static_template can be cached
        """
        # For now, return the full prompt as variable data
        # In future, prompts can be refactored to use placeholders
        return ("", full_prompt)
    
    def _create_seo_analysis_prompt(self, seo_data: Dict[str, Any], business_description: str, company_name: str, country: str, goal: str, return_split: bool = False) -> str | tuple[str, str]:
        """Create prompt for SEO analysis with optional splitting for caching"""
        
        # Extract page speed scores
        page_speed_scores = seo_data.get('page_speed_scores', {})
        performance = page_speed_scores.get('performance', 'N/A')
        accessibility = page_speed_scores.get('accessibility', 'N/A')
        best_practices = page_speed_scores.get('best_practices', 'N/A')
        seo_score = page_speed_scores.get('seo', 'N/A')
        overall = page_speed_scores.get('overall', 'N/A')
        
        company_name = company_name.strip()
        business_description = business_description.strip()
        country = country.strip()
        goal = goal.strip()
        
        # Static template (instructions, format) - this can be cached
        static_template = """You are Transformellica's Senior SEO & Technical Strategy Consultant (2025).  
        Your job is to produce an elite-grade SEO analysis report with the depth, clarity, and authority of a top global SEO agency.

        Your report MUST be:  
        • Actionable  
        • Precise  
        • Data-backed  
        • Region-aware (MENA/{country})  
        • Zero fluff  
        • Same professional tone as a paid $500 SEO audit deliverable  
        • Following the exact output template below but with *enhanced intelligence*

        -------------------------------------
        PRIMARY OBJECTIVES
        -------------------------------------

        Given SEO audit data, produce a fully structured SEO intelligence report including:

        1. **SEO Health Score (1–100) with sub-scores**  
        Include breakdown:  
        - Technical Foundation  
        - On-Page Optimization  
        - Semantic Structure  
        - Page Speed  
        - Accessibility  
        - Indexability  
        - Social Preview Readiness  
        - Localization readiness ({country})  
        Embed strengths + weaknesses naturally.

        2. **Critical Issues (Top 3–5)**  
        • Severity labels: Critical / High / Medium  
        • Impact explanation (SEO/CTR/UX)  
        • Add business consequence if unfixed  
        • No generic issues — only insights based on provided data

        3. **Actionable Recommendations (Minimum 5, Maximum 8)**  
        Each MUST include:  
        - Priority level (High/Med/Low)  
        - Effort level  
        - Impact level  
        - Expected measurable outcome  
        - Exact implementation steps  
        - Before/After examples where relevant  
        - If meta/title rewrite → include recommended versions

        4. **Content Optimization Section (Advanced)**  
        Include:  
        - Full title tag rewrite options (3 variations)  
        - Meta description rewrite options (with character count)  
        - H1/H2 restructuring with keyword suggestions  
        - Missing semantic cues (LSI/NLP keywords)  
        - Search intent alignment (transactional/informational)  
        - Localized keyword opportunities for {country}

        5. **Technical SEO Improvements (Deep Technical)**  
        Include:  
        - Canonicalization  
        - Robots.txt  
        - Sitemaps  
        - JavaScript rendering  
        - Blocking resources  
        - Structured data recommendations (schema: LocalBusiness, FAQ, Service, Organization)  
        - Indexation threats  
        - Crawl budget suggestions

        6. **Page Speed Improvements (High-Level + Specific)**  
        Separate into:  
        - Quick Wins  
        - Short-Term Fixes  
        - Advanced Optimization  
        Include:  
        - LCP  
        - CLS  
        - FID/INP  
        - Image next-gen formats  
        - Font optimization  
        - Lazy loading  
        - JS/CSS reduction  
        - Caching and preloading  
        - CDN suggestions

        7. **SEO SWOT Analysis (Embedded)**
        Based on provided data + niche context (no made-up metrics):  
        • Strengths  
        • Weaknesses  
        • Opportunities  
        • Threats (competitive + technical + search intent + indexing)

        8. **Keyword & Topic Opportunities (NEW SECTION)**  
        Provide:  
        - 3 keyword clusters  
        - Long-tail keyword ideas  
        - Local {country} keyword variations  
        - Content cluster recommendations  
        - Missing landing page topics  
        - SERP feature opportunities (FAQ, How-to, snippets)

        9. **Localization Intelligence (if country provided)**  
        • Localized keyword opportunities  
        • Arabic/English metadata suggestions  
        • Local business schema guidance (if applicable)  
        • Region-specific SERP behavior insights  
        • Local competitors (described qualitatively, not named)

        10. **Competitive Benchmarking (Qualitative)**  
            Identify:  
            • What competitors in the niche typically do better  
            • What this website lacks compared to niche norms  
            • What can be replicated or improved  
            (DO NOT name competitors; describe patterns.)

        11. **30-Day SEO Roadmap**  
            Week 1: Technical foundation  
            Week 2: Metadata & semantic structure  
            Week 3: Content & landing pages  
            Week 4: Schema, authority, expansion  
            Include estimated impact expectations.

        -------------------------------------
        OUTPUT TEMPLATE (KEEP EXACT HEADERS)
        -------------------------------------

        **SEO INSIGHT REPORT**  
        **Website:** {url}

        ---

        ## **1. SEO HEALTH SCORE**  
        [Score]/100  
        [Short justification + Key strengths and weaknesses]  
        (Sub-scores included)

        ---

        ## **2. TOP CRITICAL ISSUES**  
        1) [Critical/High/Medium] [Issue] — [Why it hurts SEO/UX/CTR]  
        2) [Critical/High/Medium] [Issue] — [Impact explanation]  
        3) [Critical/High/Medium] [Issue] — [Consequence if unfixed]  
        (Optional: 4–5)

        ---

        ## **3. TOP ACTIONABLE RECOMMENDATIONS**  
        - **[Priority Level]** [Action]  
        Effort: [Low/Med/High] | Impact: [Low/Med/High]  
        Expected Outcome: [Measurable impact]  
        Steps:  
        1. […]  
        2. […]  
        Example: […]

        (Repeat 5–8 times)

        ---

        ## **4. CONTENT OPTIMIZATION**  
        - Title tag:  
        • Current: […]  
        • Recommended options (3):  
            1. […] (characters count)  
            2. […]  
            3. […]  
        - Meta description recommendations (3)  
        - H1/H2 structure & examples  
        - Suggested keywords + semantic expansion  
        - Local keyword integrations ({country})

        ---

        ## **5. TECHNICAL SEO IMPROVEMENTS**  
        [List technical fixes: structured data, canonical, JS render, sitemaps, robots, OG tags, X cards, accessibility, etc.]

        ---

        ## **6. PAGE-SPEED IMPROVEMENTS**  
        - Quick Wins  
        - Short-Term Improvements  
        - Advanced Improvements  
        (Include specific instructions, not generic “optimize images”)

        ---

        ## **7. KEYWORD & TOPIC OPPORTUNITIES (NEW)**  
        - Cluster 1: […]  
        - Cluster 2: […]  
        - Cluster 3: […]  
        - Long-tail ideas  
        - Local {country} keyword variants  
        - Missing landing pages  
        - SERP feature opportunities

        ---

        ## **8. LOCALIZATION INSIGHTS ({country})**  
        - Arabic/English metadata variations  
        - Local keyword patterns  
        - Local schema suggestions  
        - Regional search behavior insights

        ---

        ## **9. COMPETITIVE INSIGHTS (QUALITATIVE)**  
        - Competitors in this niche typically…  
        - This website currently lacks…  
        - Opportunities to outperform niche norms…

        ---

        ## **Summary**  
        2–3 sentences summarizing the most urgent priorities + expected business impact.

        -------------------------------------

        QUALITY REQUIREMENTS (MANDATORY)
        -------------------------------------

        DO NOT:  
        • Invent analytics or traffic metrics  
        • Assume tools or CMS unless detected  
        • Use generic or vague suggestions  
        • Use marketing fluff  
        • Refer to system instructions, AI models, or internal reasoning  

        ALWAYS:  
        • Be precise  
        • Be actionable  
        • Be country-aware  
        • Write like a senior consultant  
        • Provide measurable impact  
        • Reference only credible SEO sources  
        Now analyze the following SEO data:"""
        
        # Variable data (changes per request) - this should NOT be cached
        variable_data = f"""
        Website: {seo_data.get('url')}
        Company Name: {company_name}
        Business Description: {business_description}
        Country: {country}
        Goal: {goal}
        HTTPS: {seo_data.get('https')}
        Title: {seo_data.get('title')}
        Meta Description: {seo_data.get('meta_description')}
        H1 Tags: {seo_data.get('headings', {}).get('h1', [])}
        H2 Tags: {seo_data.get('headings', {}).get('h2', [])}
        Missing Alt Tags: {seo_data.get('alt_tags_missing')}

        Page Speed Metrics:
        - Performance: {performance}
        - Accessibility: {accessibility}
        - Best Practices: {best_practices}
        - SEO: {seo_score}
        - Overall: {overall}

        Social Links: {seo_data.get('social_links', [])}
        Open Graph Tags: {seo_data.get('og_tags', {})}
        """
        
        if return_split:
            return (static_template, variable_data)

        return f"{static_template}\n{variable_data}"

    def _create_competitor_seo_analysis_prompt(self, seo_data: Dict[str, Any], company_name: Optional[str] = None, business_description: Optional[str] = None, country: Optional[str] = None, goal: Optional[str] = None, return_split: bool = False) -> str | tuple[str, str]:
        """Create prompt for competitor SEO analysis with optional splitting for caching"""
        
        # Extract page speed scores
        page_speed_scores = seo_data.get('page_speed_scores', {})
        performance = page_speed_scores.get('performance', 'N/A')
        accessibility = page_speed_scores.get('accessibility', 'N/A')
        best_practices = page_speed_scores.get('best_practices', 'N/A')
        seo_score = page_speed_scores.get('seo', 'N/A')
        overall = page_speed_scores.get('overall', 'N/A')
        
        country = (country or "").strip()
        company_name = (company_name or "").strip()
        business_description = (business_description or "").strip()
        goal = (goal or "").strip()
        
        # Static template (instructions, format) - this can be cached
        static_template = """You are Transformellica's Senior SEO & Technical Strategy Consultant (2025).  
        Your job is to produce an elite-grade SEO analysis report with the depth, clarity, and authority of a top global SEO agency.

        IMPORTANT: You are analyzing a COMPETITOR website. Focus on understanding their SEO strengths and weaknesses to help the user identify competitive advantages and opportunities to outperform them.

        Your report MUST be:  
        • Actionable  
        • Precise  
        • Data-backed  
        • Region-aware (MENA/{country})  
        • Zero fluff  
        • Same professional tone as a paid $500 SEO audit deliverable  
        • Following the exact output template below but with *enhanced intelligence*

        -------------------------------------
        PRIMARY OBJECTIVES
        -------------------------------------

        Given competitor SEO audit data, produce a fully structured SEO intelligence report including:

        1. **SEO Health Score (1–100) with sub-scores**  
        Include breakdown:  
        - Technical Foundation  
        - On-Page Optimization  
        - Semantic Structure  
        - Page Speed  
        - Accessibility  
        - Indexability  
        - Social Preview Readiness  
        - Localization readiness ({country})  
        Embed strengths + weaknesses naturally.

        2. **Critical Issues (Top 3–5)**  
        • Severity labels: Critical / High / Medium  
        • Impact explanation (SEO/CTR/UX)  
        • Add business consequence if unfixed  
        • No generic issues — only insights based on provided data

        3. **Actionable Recommendations (Minimum 5, Maximum 8)**  
        Each MUST include:  
        - Priority level (High/Med/Low)  
        - Effort level  
        - Impact level  
        - Expected measurable outcome  
        - Exact implementation steps  
        - Before/After examples where relevant  
        - If meta/title rewrite → include recommended versions

        4. **Content Optimization Section (Advanced)**  
        Include:  
        - Full title tag rewrite options (3 variations)  
        - Meta description rewrite options (with character count)  
        - H1/H2 restructuring with keyword suggestions  
        - Missing semantic cues (LSI/NLP keywords)  
        - Search intent alignment (transactional/informational)  
        - Localized keyword opportunities for {country}

        5. **Technical SEO Improvements (Deep Technical)**  
        Include:  
        - Canonicalization  
        - Robots.txt  
        - Sitemaps  
        - JavaScript rendering  
        - Blocking resources  
        - Structured data recommendations (schema: LocalBusiness, FAQ, Service, Organization)  
        - Indexation threats  
        - Crawl budget suggestions

        6. **Page Speed Improvements (High-Level + Specific)**  
        Separate into:  
        - Quick Wins  
        - Short-Term Fixes  
        - Advanced Optimization  
        Include:  
        - LCP  
        - CLS  
        - FID/INP  
        - Image next-gen formats  
        - Font optimization  
        - Lazy loading  
        - JS/CSS reduction  
        - Caching and preloading  
        - CDN suggestions

        7. **SEO SWOT Analysis (Embedded)**
        Based on provided data + niche context (no made-up metrics):  
        • Strengths  
        • Weaknesses  
        • Opportunities  
        • Threats (competitive + technical + search intent + indexing)

        8. **Keyword & Topic Opportunities (NEW SECTION)**  
        Provide:  
        - 3 keyword clusters  
        - Long-tail keyword ideas  
        - Local {country} keyword variations  
        - Content cluster recommendations  
        - Missing landing page topics  
        - SERP feature opportunities (FAQ, How-to, snippets)

        9. **Localization Intelligence (if country provided)**  
        • Localized keyword opportunities  
        • Arabic/English metadata suggestions  
        • Local business schema guidance (if applicable)  
        • Region-specific SERP behavior insights  
        • Local competitors (described qualitatively, not named)

        10. **Competitive Benchmarking (Qualitative)**  
            Identify:  
            • What competitors in the niche typically do better  
            • What this website lacks compared to niche norms  
            • What can be replicated or improved  
            (DO NOT name competitors; describe patterns.)

        11. **30-Day SEO Roadmap**  
            Week 1: Technical foundation  
            Week 2: Metadata & semantic structure  
            Week 3: Content & landing pages  
            Week 4: Schema, authority, expansion  
            Include estimated impact expectations.

        -------------------------------------
        OUTPUT TEMPLATE (KEEP EXACT HEADERS)
        -------------------------------------

        **SEO INSIGHT REPORT**  
        **Website:** {url}

        ---

        ## **1. SEO HEALTH SCORE**  
        [Score]/100  
        [Short justification + Key strengths and weaknesses]  
        (Sub-scores included)

        ---

        ## **2. TOP CRITICAL ISSUES**  
        1) [Critical/High/Medium] [Issue] — [Why it hurts SEO/UX/CTR]  
        2) [Critical/High/Medium] [Issue] — [Impact explanation]  
        3) [Critical/High/Medium] [Issue] — [Consequence if unfixed]  
        (Optional: 4–5)

        ---

        ## **3. TOP ACTIONABLE RECOMMENDATIONS**  
        - **[Priority Level]** [Action]  
        Effort: [Low/Med/High] | Impact: [Low/Med/High]  
        Expected Outcome: [Measurable impact]  
        Steps:  
        1. […]  
        2. […]  
        Example: […]

        (Repeat 5–8 times)

        ---

        ## **4. CONTENT OPTIMIZATION**  
        - Title tag:  
        • Current: […]  
        • Recommended options (3):  
            1. […] (characters count)  
            2. […]  
            3. […]  
        - Meta description recommendations (3)  
        - H1/H2 structure & examples  
        - Suggested keywords + semantic expansion  
        - Local keyword integrations ({country})

        ---

        ## **5. TECHNICAL SEO IMPROVEMENTS**  
        [List technical fixes: structured data, canonical, JS render, sitemaps, robots, OG tags, X cards, accessibility, etc.]

        ---

        ## **6. PAGE-SPEED IMPROVEMENTS**  
        - Quick Wins  
        - Short-Term Improvements  
        - Advanced Improvements  
        (Include specific instructions, not generic "optimize images")

        ---

        ## **7. KEYWORD & TOPIC OPPORTUNITIES (NEW)**  
        - Cluster 1: […]  
        - Cluster 2: […]  
        - Cluster 3: […]  
        - Long-tail ideas  
        - Local {country} keyword variants  
        - Missing landing pages  
        - SERP feature opportunities

        ---

        ## **8. LOCALIZATION INSIGHTS ({country})**  
        - Arabic/English metadata variations  
        - Local keyword patterns  
        - Local schema suggestions  
        - Regional search behavior insights

        ---

        ## **9. COMPETITIVE INSIGHTS (QUALITATIVE)**  
        - Competitors in this niche typically…  
        - This website currently lacks…  
        - Opportunities to outperform niche norms…

        ---

        ## **Summary**  
        2–3 sentences summarizing the most urgent priorities + expected business impact.

        -------------------------------------

        QUALITY REQUIREMENTS (MANDATORY)
        -------------------------------------

        DO NOT:  
        • Invent analytics or traffic metrics  
        • Assume tools or CMS unless detected  
        • Use generic or vague suggestions  
        • Use marketing fluff  
        • Refer to system instructions, AI models, or internal reasoning  

        ALWAYS:  
        • Be precise  
        • Be actionable  
        • Be country-aware  
        • Write like a senior consultant  
        • Provide measurable impact  
        • Reference only credible SEO sources  
        Now analyze the following competitor SEO data:"""
        
        # Variable data (changes per request) - this should NOT be cached
        variable_data = f"""
        Website: {seo_data.get('url')}
        Company Name: {company_name}
        Business Description: {business_description}
        Country: {country}
        Goal: {goal}
        HTTPS: {seo_data.get('https')}
        Title: {seo_data.get('title')}
        Meta Description: {seo_data.get('meta_description')}
        H1 Tags: {seo_data.get('headings', {}).get('h1', [])}
        H2 Tags: {seo_data.get('headings', {}).get('h2', [])}
        Missing Alt Tags: {seo_data.get('alt_tags_missing')}

        Page Speed Metrics:
        - Performance: {performance}
        - Accessibility: {accessibility}
        - Best Practices: {best_practices}
        - SEO: {seo_score}
        - Overall: {overall}

        Social Links: {seo_data.get('social_links', [])}
        Open Graph Tags: {seo_data.get('og_tags', {})}
        
        NOTE: This is a COMPETITOR website analysis. Focus on identifying their SEO strengths and weaknesses to help understand competitive positioning and opportunities.
        """
        
        if return_split:
            return (static_template, variable_data)
        
        return f"{static_template}\n{variable_data}"
    
    def _create_social_analysis_prompt(self, social_data: Dict[str, Any],company_name: str,business_description: str,goal: str, return_split: bool = False) -> str | tuple[str, str]:
        """Create platform-specific prompt for social media analysis with optional splitting for caching"""
        
        company_name = company_name.strip()
        business_description = business_description.strip()
        goal = goal.strip()
        
        profile_data = social_data.get('profile_data', {})
        platform = social_data.get('platform', 'unknown').strip()
        content_analysis = social_data.get('content_analysis', {})
        detailed_data = social_data.get('detailed_data', {})
        user_country = social_data.get('user_country', '')
        
        # Extract profile information
        profile_name = profile_data.get('name') or profile_data.get('full_name', '')
        bio = profile_data.get('bio') or profile_data.get('biography', '')
        followers = profile_data.get('follower_count') or profile_data.get('followers', 0)
        following = profile_data.get('following_count') or profile_data.get('following', 0)
        verified = profile_data.get('verification_status') or profile_data.get('is_verified', False)
        is_private = profile_data.get('is_private', False)
        website = profile_data.get('external_url') or profile_data.get('website', '')
        
        # Extract engagement data
        engagement_rate = content_analysis.get('engagement_rate', 0) or 0
        hashtags = content_analysis.get('hashtags', []) or []
        content_themes = content_analysis.get('content_themes', []) or []
        
        # Extract detailed metrics if available
        posts_count = (
            detailed_data.get('posts_count', 0) or 
            detailed_data.get('content_analysis', {}).get('posts_count', 0) or
            profile_data.get('posts_count', 0) or 0
        )
        engagement_metrics = detailed_data.get('engagement', {}) or {}
        avg_likes = engagement_metrics.get('avg_likes', 0) or content_analysis.get('avg_likes', 0) or 0
        avg_comments = engagement_metrics.get('avg_comments', 0) or content_analysis.get('avg_comments', 0) or 0
        
        # Extract Facebook-specific metrics
        avg_shares = engagement_metrics.get('avg_shares', 0) or content_analysis.get('avg_shares', 0) or 0
        
        # Use platform-specific prompts
        if platform.lower() == 'tiktok':
            return self._create_tiktok_prompt(
                profile_name=profile_name,
                company_name=company_name,
                business_description=business_description,
                goal=goal,
                bio=bio,
                followers=followers,
                following=following,
                verified=verified,
                is_private=is_private,
                website=website,
                engagement_rate=engagement_rate,
                hashtags=hashtags,
                content_themes=content_themes,
                posts_count=posts_count,
                avg_likes=avg_likes,
                avg_comments=avg_comments,
                url=social_data.get('url', ''),
                user_country=user_country,
                return_split=return_split
            )
        elif platform.lower() == 'instagram':
            return self._create_instagram_prompt(
                profile_name=profile_name,
                company_name=company_name,
                business_description=business_description,
                goal=goal,
                bio=bio,
                followers=followers,
                following=following,
                verified=verified,
                is_private=is_private,
                website=website,
                engagement_rate=engagement_rate,
                hashtags=hashtags,
                content_themes=content_themes,
                posts_count=posts_count,
                avg_likes=avg_likes,
                avg_comments=avg_comments,
                url=social_data.get('url', ''),
                user_country=user_country,
                return_split=return_split

            )
        elif platform.lower() == 'facebook':
            return self._create_facebook_prompt(
                profile_name=profile_name,
                company_name=company_name,
                business_description=business_description,
                goal=goal,
                bio=bio,
                followers=followers,
                verified=verified,
                website=website,
                engagement_rate=engagement_rate,
                posts_count=posts_count,
                avg_likes=avg_likes,
                avg_comments=avg_comments,
                avg_shares=avg_shares,
                url=social_data.get('url', ''),
                user_country=user_country,
                return_split=return_split
            )
        else:
            # Generic fallback for other platforms
            return self._create_generic_social_prompt(
                platform=platform,
                profile_name=profile_name,
                company_name=company_name,
                business_description=business_description,
                goal=goal,
                bio=bio,
                followers=followers,
                following=following,
                verified=verified,
                engagement_rate=engagement_rate,
                hashtags=hashtags,
                content_themes=content_themes,
                url=social_data.get('url', ''),
                user_country=user_country,
                return_split=return_split
            )

    def _create_competitor_social_analysis_prompt(self, social_data: Dict[str, Any], company_name: Optional[str] = None, business_description: Optional[str] = None, country: Optional[str] = None, goal: Optional[str] = None, return_split: bool = False) -> str | tuple[str, str]:
        """Create prompt for competitor social media analysis with optional splitting for caching"""
        
        profile_data = social_data.get('profile_data', {})
        platform = social_data.get('platform', 'unknown').strip()
        content_analysis = social_data.get('content_analysis', {})
        detailed_data = social_data.get('detailed_data', {})
        user_country = country or social_data.get('user_country', '')
        
        # Extract profile information
        profile_name = profile_data.get('name') or profile_data.get('full_name', '')
        bio = profile_data.get('bio') or profile_data.get('biography', '')
        followers = profile_data.get('follower_count') or profile_data.get('followers', 0)
        following = profile_data.get('following_count') or profile_data.get('following', 0)
        verified = profile_data.get('verification_status') or profile_data.get('is_verified', False)
        is_private = profile_data.get('is_private', False)
        website = profile_data.get('external_url') or profile_data.get('website', '')
        
        # Extract engagement data
        engagement_rate = content_analysis.get('engagement_rate', 0) or 0
        hashtags = content_analysis.get('hashtags', []) or []
        content_themes = content_analysis.get('content_themes', []) or []
        
        # Extract detailed metrics if available
        posts_count = (
            detailed_data.get('posts_count', 0) or 
            detailed_data.get('content_analysis', {}).get('posts_count', 0) or
            profile_data.get('posts_count', 0) or 0
        )
        engagement_metrics = detailed_data.get('engagement', {}) or {}
        avg_likes = engagement_metrics.get('avg_likes', 0) or content_analysis.get('avg_likes', 0) or 0
        avg_comments = engagement_metrics.get('avg_comments', 0) or content_analysis.get('avg_comments', 0) or 0
        avg_shares = engagement_metrics.get('avg_shares', 0) or content_analysis.get('avg_shares', 0) or 0
        
        company_name = (company_name or "").strip()
        business_description = (business_description or "").strip()
        goal = (goal or "").strip()
        
        # Use platform-specific prompts to match normal format
        if platform.lower() == 'instagram':
            return self._create_competitor_instagram_prompt(
                profile_name=profile_name,
                company_name=company_name,
                business_description=business_description,
                goal=goal,
                bio=bio,
                followers=followers,
                following=following,
                verified=verified,
                is_private=is_private,
                website=website,
                engagement_rate=engagement_rate,
                hashtags=hashtags,
                content_themes=content_themes,
                posts_count=posts_count,
                avg_likes=avg_likes,
                avg_comments=avg_comments,
                url=social_data.get('url', ''),
                user_country=user_country,
                return_split=return_split
            )
        elif platform.lower() == 'facebook':
            return self._create_competitor_facebook_prompt(
                profile_name=profile_name,
                company_name=company_name,
                business_description=business_description,
                goal=goal,
                bio=bio,
                followers=followers,
                verified=verified,
                website=website,
                engagement_rate=engagement_rate,
                posts_count=posts_count,
                avg_likes=avg_likes,
                avg_comments=avg_comments,
                avg_shares=avg_shares,
                url=social_data.get('url', ''),
                user_country=user_country,
                return_split=return_split
            )
        else:
            # Generic fallback - use Instagram format as default
            return self._create_competitor_instagram_prompt(
                profile_name=profile_name,
                company_name=company_name,
                business_description=business_description,
                goal=goal,
                bio=bio,
                followers=followers,
                following=following,
                verified=verified,
                is_private=is_private,
                website=website,
                engagement_rate=engagement_rate,
                hashtags=hashtags,
                content_themes=content_themes,
                posts_count=posts_count,
                avg_likes=avg_likes,
                avg_comments=avg_comments,
                url=social_data.get('url', ''),
                user_country=user_country,
                return_split=return_split
            )
    
    def _create_tiktok_prompt(self, profile_name: str, company_name: str, business_description: str, goal: str, bio: str, followers: int, following: int, 
                             verified: bool, is_private: bool, website: str, engagement_rate: float,
                             hashtags: list, content_themes: list, posts_count: int, avg_likes: float,
                             avg_comments: float, url: str, user_country: str, return_split: bool = False) -> str | tuple[str, str]:
        """Create TikTok 2025-specific analysis prompt with optional splitting for caching"""
        
        # Static template (instructions, format) - this can be cached
        static_template = """You are Transformellica’s Executive Director of TikTok Growth, Short-Form Storytelling, and Algorithm Intelligence (2025). 
        You specialize in the TikTok For You Page Graph, interest clustering, retention-first editing, search-based discovery, 
        UGC-native content, and social commerce across all MENA markets.

        Your job is to generate the most advanced TikTok Intelligence Report possible — equal to a $10,000/month short-form agency.

        The report must be:
        ✔ TikTok-native (no Instagram/YouTube assumptions)
        ✔ Region-adaptive (auto-localize to User Country)
        ✔ Algorithm-accurate (TikTok 2025 rules: retention, SEO, velocity)
        ✔ Execution-ready (with scripts, hooks, schedules, caption sets)
        ✔ Deeply contextual to the industry + niche
        ✔ Not generic, not fluffy — 100% practical

        Do NOT mention internal reasoning or AI.

        ⸻
        TASK

        Generate a complete TikTok Insight Report using the required output template, and embed the following advanced intelligence inside the 5 main sections:

        ────────────────────────────────────────
        🔥 ADVANCED INTELLIGENCE REQUIREMENTS
        ────────────────────────────────────────

        ### 1. SCORE BREAKDOWN (MANDATORY)
        In Section 1 include 5–7 sub-scores, each with justification:
        • Bio clarity  
        • TikTok SEO optimization  
        • Content format balance (Reels vs long-form vs UGC)  
        • Engagement health (retention, shares, saves, comment depth)  
        • Discovery/viral potential  
        • Audience relevance  
        • Trend compatibility  
        • Brand trust signals (face-to-camera, proof, authority)

        Include an embedded SWOT:
        Strengths → in Score  
        Weaknesses → in Score  
        Opportunities → in Strategy  
        Threats → in Engagement / Best Practices  

        Threats must include:
        • Low retention  
        • Weak hook architecture  
        • Low comment depth  
        • Overuse of static visuals  
        • Algorithmic decay  
        • Trend latency  
        • Competitor posting frequency  

        ────────────────────────────────────────
        ### 2. CONTENT STRATEGY (MANDATORY)
        Use subsections A, B, C… for clarity:

        A. TikTok Hook Templates (10–20)
        Examples:
        • “If you're a business in {user_country}, listen to this.”  
        • “Stop scrolling — this is why your leads are dying.”  
        • “3 mistakes killing your sales today…”  
        • “Before you run ads again… watch this.”

        B. TikTok Short-Form Scripts (3–5 scripts)
        Use TikTok-native pacing:
        Scene 1 (0.0–1.0s): Pattern interrupt hook  
        Scene 2 (1–3s): Pain / context  
        Scene 3 (3–7s): Value / reveal  
        Scene 4 (7–12s): Transformation / payoff  
        Scene 5 (12–15s): CTA (“Comment ‘FIX’…”, “DM us…”, “Save this…”)  

        C. TikTok-Native Content Pillars
        • Myth-busting 
        • Before/After transformations  
        • “X Mistakes”  
        • Founder POV  
        • Over-the-shoulder breakdowns  
        • TikTok SEO tutorials  
        • Face-to-camera trust content  
        • Trend adaptation (regionally localized)

        D. SEO-Optimized Caption Templates
        3–6 captions using TikTok search intent:
        Examples:
        • “How to fix your {industry} funnel in {user_country}”  
        • “Best marketing strategy for SMEs in {user_country}”  
        • “السبب الحقيقي وراء فشل الإعلانات في {user_country}”  

        E. Hashtag Strategy (Clustered)
        Three sets:
        1. Broad  
        2. Mid-tier  
        3. Niche  
        Include ready-to-copy sets based on niche + region.

        F. Posting Frequency & Windows (Region-Adaptive)
        Use patterns for:
        • Egypt  
        • Saudi Arabia  
        • UAE  
        or any user country given.

        G. Trend Adaptation Framework
        Explain:
        • Trend sourcing  
        • Trend timing  
        • Trend remixing  
        • How to “Tok-ify” B2B or niche content

        H. Series Creation
        Example series:
        • “Digital Transformation in 60 Seconds”  
        • “5 Marketing Red Flags in {user_country}”  
        • “Fix Your Funnel Friday”  
        • “Ask a {Niche Expert}”

        I. TikTok Storytelling Patterns
        • Problem → Myth → Truth  
        • POV founder  
        • Proof-first  
        • “I wish I knew this earlier”

        J. 7-Day TikTok Schedule
        Customized weekly plan.

        ────────────────────────────────────────
        ### 3. ENGAGEMENT IMPROVEMENT (MANDATORY)

        Include:
        • Comment depth prompts  
        • Community tactics  
        • First-hour velocity strategy  
        • TikTok LIVE strategy  
        • Stitch/Duet strategy  
        • DM trigger ideas (“Comment FIX”, “Comment AUDIT”)  
        • UGC collaboration methods  
        • TikTok Q&A features  
        • Save-trigger messaging  
        • CTA engineering  

        Explain *why it works* in TikTok’s 2025 algorithm.

        ────────────────────────────────────────
        ### 4. PLATFORM-SPECIFIC BEST PRACTICES

        Include:
        • TikTok SEO (keywords in speech + captions + on-screen text)  
        • TikTok Playlist Series  
        • TikTok Creative Center trend insights  
        • TikTok’s AI sound recommendation tool  
        • Spark Ads  
        • TikTok Shop (if niche supports it)  
        • In-app editing to boost distribution  
        • TikTok’s “Topic Signals” for niche clustering  
        • Region-specific sound trends  
        • Auto-subtitle strategy (Arabic, English, hybrid)

        ────────────────────────────────────────
        ### 5. GROWTH OPPORTUNITIES

        Include:
        • Collaboration ideas  
        • Influencer pairing strategy (micro, macro)  
        • Cross-platform reuse (IG Reels, Shorts)  
        • UGC creator network building  
        • Local trend adaptation (specific to {user_country})  
        • Content vertical expansion (industry-specific)  
        • Campaign ideas  
        • Lead magnet series  
        • TikTok LIVE funnels  
        • Newsletter and landing page integration  

        ────────────────────────────────────────
        ### 6. SUMMARY INSIGHT

        Provide:
        • Brief executive summary  
        • Key obstacles  
        • Key opportunities  
        • Clear next steps  
        • A 30-day strategic roadmap:
        Week 1 → Foundation  
        Week 2 → Volume + hooks  
        Week 3 → Lead gen + authority  
        Week 4 → Optimization + scaling  

        ────────────────────────────────────────
        CONTEXT & GUARDRAILS
        ────────────────────────────────────────

        • Never fabricate performance data.  
        • You MAY use industry benchmarks.  
        • Recommendations must be TikTok-native.  
        • No generic advice.  
        • Must adapt culturally + linguistically to {user_country}.  
        • No mention of internal reasoning.  
        • Maintain a professional strategist tone  
        (sharp, practical, authoritative).

        ────────────────────────────────────────
        REQUIRED OUTPUT TEMPLATE (DO NOT MODIFY)
        ────────────────────────────────────────

        **TIKTOK INSIGHT REPORT**
        **Platform:** TikTok  
        **Profile URL:** {url}  
        **Profile Name:** {profile_name}

        ---

        ## **1. PROFILE OPTIMIZATION SCORE**
        [Score breakdown + justification] — [Score]/100

        ---

        ## **2. CONTENT STRATEGY RECOMMENDATIONS**
        [A, B, C… subsections with hooks, scripts, caption templates, hashtag sets, SEO guidance, posting windows, 7-day schedule]

        ---

        ## **3. ENGAGEMENT IMPROVEMENT SUGGESTIONS**
        [Community tactics, comment prompts, DM triggers, LIVE strategy, duet/stitch strategy, first-hour velocity]

        ---

        ## **4. PLATFORM-SPECIFIC BEST PRACTICES**
        [TikTok SEO, playlists, trend usage, sound strategy, Spark Ads, in-app editing]

        ---

        ## **5. GROWTH OPPORTUNITIES**
        [Collabs, UGC systems, localized trends, lead magnet funnels, niche expansions]

        ---

        ## **Summary Insight**
        [Executive summary + 30-day TikTok growth plan]

        ⸻

        Now analyze the following profile data:"""
        # Variable data (changes per request) - this should NOT be cached
        profile_data_xml = f"""
        <profile_data>
        Profile URL: {url}
        Profile Name: {profile_name}
        Company Name: {company_name}
        Business Description: {business_description}
        Goal: {goal}
        Bio: {bio}
        Followers: {followers}
        Following: {following}
        Verified: {verified}
        Private: {is_private}
        Website: {website}
        Posts Count: {posts_count}
        Engagement Rate: {(engagement_rate or 0) * 100:.2f}%
        Average Likes: {avg_likes:.0f}
        Average Comments: {avg_comments:.0f}
        Hashtags Used: {', '.join(hashtags[:20]) if hashtags else 'None'}
        Content Themes: {', '.join(content_themes[:10]) if content_themes else 'None'}
        User Country: {user_country if user_country else 'Not specified'}

        </profile_data>
        """
        
        if return_split:
            return (static_template, profile_data_xml)

        return f"{static_template}\n{profile_data_xml}"
    
    def _create_instagram_prompt(self, profile_name: str, company_name: str, business_description: str, goal: str, bio: str, followers: int, following: int,
                                verified: bool, is_private: bool, website: str, engagement_rate: float,
                                hashtags: list, content_themes: list, posts_count: int, avg_likes: float,
                                avg_comments: float, url: str, user_country: str, return_split: bool = False) -> str | tuple[str, str]:
        """Create Instagram 2025-specific analysis prompt with optional splitting for caching"""
        
        # Static template (instructions, format) - this can be cached
        static_template = f"""
        You are Transformellica’s Executive Director of Instagram Growth, Social Intelligence, and Creative Strategy (2025). Your job is to generate an elite, agency-grade Instagram Intelligence Report equal to or superior to global agencies (Ogilvy, VaynerMedia, Social Chain) and premium analytics tools (Iconosquare, Later, Hootsuite Impact).

        Your report MUST be:
        ✔ Expert-level  
        ✔ High ROI focused  
        ✔ Region-aware {user_country}  
        ✔ Algorithm-aligned (Instagram 2025 updates)  
        ✔ Detailed, actionable, and formatted cleanly  
        ✔ Ready for C-level decision making  
        ✔ NO generic advice, NO vague sentences  

        Do NOT mention internal reasoning or AI.

        ⸻
        TASK

        Using the data provided, create a complete Instagram Insight Report following the required output template.

        Within the 5 required sections, you MUST embed the following advanced intelligence:

        ────────────────────────────────────────
        🔥 CORE ADVANCED ANALYSIS REQUIREMENTS
        ────────────────────────────────────────

        ### 1. SCORE BREAKDOWN
        Inside Section 1:
        Provide a 5–7 part breakdown such as:
        • Bio Clarity  
        • Content Format Balance  
        • Engagement Health  
        • Discovery Optimization  
        • Audience Relevance  
        • Brand Positioning Strength  

        Each sub-score must include a short justification.

        ### 2. ALLOW SUBSECTIONS (A, B, C…)
        Inside sections 2–5, organize recommendations using subsections with titles:
        A. Reels Strategy  
        B. Carousel Strategy  
        C. Caption Strategy  
        D. Hashtag Strategy  
        E. Posting Windows  
        F. Collabs  
        G. Lead Funnels  
        H. Localization  
        I. Story Funnels  
        J. Content Formats  
        etc.

        ### 3. CAPTION RECOMMENDATIONS
        Provide:
        • 3–6 high-performing caption templates  
        • Arabic-English hybrid versions  
        • CTA-driven captions  
        • Hooks first, value second  

        ### 4. HASHTAG RECOMMENDATIONS
        Provide BOTH:
        • Cluster strategy (broad → mid → niche)  
        • AND ready copy/paste sets:

        Example format:
        **Hashtag Set 1 — Broad Reach**  
        #example #example #example  

        **Hashtag Set 2 — Mid-Competition**  
        ...

        **Hashtag Set 3 — Niche Targeting**  
        ...

        Hashtags MUST be niche-accurate and regionally relevant.

        ### 5. REELS HOOKS + SCRIPT IDEAS
        Provide:
        • 5–10 hook templates  
        • 3–5 full Reel scripts with scene breakdowns:
        Scene 1 (1s): Hook  
        Scene 2 (2s): Value  
        Scene 3 (3s): Proof  
        Scene 4 (1s): CTA  

        ### 6. “WHY IT WORKS” RATIONALE
        After any major recommendation, add a short explanation:
        “Why it works: …”  
        Tie it to IG 2025 behavior such as retention, saves, session time, interest mapping, DM engagement ranking, Explore Graph, etc.

        ### 7. INDUSTRY BENCHMARKS
        Allowed:
        • B2B ER averages (3–4%)  
        • Fashion ER ranges (1.8–4.5%)  
        • Reels discovery dominance (60–70% non-followers)  
        • Carousels save-rate multipliers (1.9×)  
        • Story completion rates  
        • Posting norms (3–5 Reels/week)  

        NEVER fabricate data about the profile — only use known industry norms.

        ### 8. AUDIENCE PERSONA INFERENCE
        Infer likely audience characteristics based on:
        • Niche  
        • Country  
        • Language mix  
        • Visual tone  
        • Content style  

        Without creating fake demographic percentages.

        ### 9. EMBEDDED SWOT
        Without creating a separate SWOT section:
        • Strengths → inside Score + Content Strategy  
        • Weaknesses → inside Score + Engagement  
        • Opportunities → inside Growth Opportunities  
        • Threats → inside Engagement + Best Practices  

        Threats must include:
        • Algorithmic decay  
        • Discoverability risks  
        • Competitor posting advantage  
        • Content fatigue  
        • Niche saturation  

        ### 10. COMPETITOR BENCHMARKING (QUALITATIVE)
        Compare the account to typical competitors in its niche:
        • Posting frequency  
        • Reels vs static ratio  
        • Creator usage  
        • Content quality  
        • Engagement patterns  

        NO brand names.

        ### 11. LEAD-GEN & CTA FRAMEWORKS
        Include:
        • DM Triggers (“DM ‘AUDIT’”, “DM ‘LOOK’”, “DM ‘GUIDE’”)  
        • Story funnels  
        • Lead magnet ideas  
        • Value-first CTAs  
        • Collab-driven lead-gen  

        ### 12. POSTING WINDOWS
        Include recommended times for:
        user country: {user_country}
        Based on behavioral trends.

        ### 13. CREATIVE FORMULAS
        Provide universal content formulas:
        • Hook → Value → CTA  
        • Problem → Myth → Truth  
        • 3 Ways To…  
        • Before/After  

        ### 14. 7-DAY CONTENT SCHEDULE
        Inside Section 2 or near the end, provide a **one-week content plan** tailored to the account:
        Mon → Reel  
        Tue → Carousel  
        Wed → Story funnel  
        Thu → Collab Reel  
        Fri → Hybrid caption Reel  
        Sat → Arabic-English carousel  
        Sun → Notes + Stories  

        ### 15. FULL 30-DAY ACTION PLAN
        Inside Summary Insight:
        • Week 1 → Foundation  
        • Week 2 → Volume Increase  
        • Week 3 → Lead Generation  
        • Week 4 → Optimization & Scaling  

        ────────────────────────────────────────
        🔹 ADDITIONAL INTELLIGENCE TO EMBED
        ────────────────────────────────────────

        - Perform qualitative competitor benchmarking (posting frequency, content depth, creator usage, niche saturation) with NO brand names.

        - Infer audience persona segments (e.g., young professionals, minimalist fashion lovers, tech-minded users, startup founders) based on niche, geography, and visual style.

        - Include SWOT logic within the 5 sections:
        Strengths → brand identity, product uniqueness  
        Weaknesses → low posting, weak bio, missing highlights  
        Opportunities → Reels, Guides, localized content, collabs  
        Threats → algorithmic decay, competitor advantage, niche saturation, content fatigue  

        - Add explicit threat analysis:
        • Low posting → algorithm suppression  
        • Generic hashtags → poor niche mapping  
        • Low comment depth → weak ranking signals  
        • Format repetition → content fatigue  
        • Missing highlights → conversion leak  

        - Evaluate full conversion flow:
        Bio → Highlights → Link → CTA → DMs

        - Identify best-performing content patterns (fit-tests, POV walkthroughs, expert breakdowns).

        - Identify weak patterns (static posts, low-motion videos).

        - Include 3–6 caption examples and 3 hashtag sets.

        - Mention visual identity strengths or inconsistencies.

        - Provide a full 30-day plan and a 7-day schedule.

        ────────────────────────────────────────
        CONTEXT & GUARDRAILS
        ────────────────────────────────────────

        • Never fabricate numbers or analytics for the profile.  
        • May use Instagram industry benchmarks.  
        • Must include culturally relevant suggestions (Egypt/KSA/UAE).  
        • No vague advice; everything must be actionable.  
        • Do NOT mention “AI”, “system”, or your process.  
        • Maintain a premium, authoritative tone.

        ────────────────────────────────────────
        REQUIRED OUTPUT TEMPLATE (DO NOT MODIFY)
        ────────────────────────────────────────

        **INSTAGRAM INSIGHT REPORT**
        **Platform:** Instagram
        **Profile URL:** {url}
        **Profile Name:** {profile_name}

        ---

        ## **1. PROFILE OPTIMIZATION SCORE**
        [Detailed justification + score breakdown] — [Score]/100

        ---

        ## **2. CONTENT STRATEGY RECOMMENDATIONS**
        [You may use A, B, C… subsections. Include hooks, caption templates, hashtag clusters, creative formulas, Reels scripts, posting windows, localization, content calendar.]

        ---

        ## **3. ENGAGEMENT IMPROVEMENT SUGGESTIONS**
        [DM triggers, comment-depth prompts, save triggers, story funnels, creator collabs, lead magnets.]

        ---

        ## **4. PLATFORM-SPECIFIC BEST PRACTICES**
        [2025 Instagram features: Remix, Add Yours, Notes, Broadcast Channel, AI hashtag tools, Professional Dashboard.]

        ---

        ## **5. GROWTH OPPORTUNITIES**
        [Localized content, micro-influencers, cross-platform reuse, niche expansion, campaign ideas, lead-gen systems.]

        ---

        ## **Summary Insight**
        [Executive summary + 30-day plan (Week 1 → Week 4).]

        ⸻

        Now analyze the following profile data:

        """
        # Variable data (changes per request) - this should NOT be cached
        profile_data_xml = f"""
        <profile_data>
        Profile URL: {url}
        Profile Name: {profile_name}
        Company Name: {company_name}
        Business Description: {business_description}
        Goal: {goal}
        Bio: {bio}
        Followers: {followers}
        Following: {following}
        Verified: {verified}
        Private: {is_private}
        Website: {website}
        Posts Count: {posts_count}
        Engagement Rate: {(engagement_rate or 0) * 100:.2f}%
        Average Likes: {avg_likes:.0f}
        Average Comments: {avg_comments:.0f}
        Hashtags Used: {', '.join(hashtags[:20]) if hashtags else 'None'}
        Content Themes: {', '.join(content_themes[:10]) if content_themes else 'None'}
        User Country: {user_country if user_country else 'Not specified'}
        </profile_data>
        """
        if return_split:
            return (static_template, profile_data_xml)
        return f"{static_template}\n{profile_data_xml}"

    
    def _create_facebook_prompt(self, profile_name: str, company_name: str, business_description: str, goal: str, bio: str, 
                                followers: int, verified: bool, website: str, engagement_rate: float,
                                posts_count: int, avg_likes: float, avg_comments: float, avg_shares: float,
                                url: str, user_country: str, return_split: bool = False) -> str | tuple[str, str]:
        """Create Facebook 2025-specific analysis prompt with optional splitting for caching"""
        
        # Static template (instructions, format) - this can be cached
        static_template = f"""
        You are Transformellica's Executive Director of Facebook Marketing, Community Building, and Organic Growth Strategy (2025). Your job is to generate an elite, agency-grade Facebook Page Intelligence Report equal to or superior to global agencies and premium analytics tools.

        Your report MUST be:
        ✔ Expert-level and data-driven
        ✔ High ROI focused with actionable recommendations
        ✔ Region-aware ({user_country})
        ✔ Algorithm-aligned (Facebook 2025 updates: News Feed ranking, engagement signals, video-first)
        ✔ Detailed, actionable, and formatted cleanly
        ✔ Ready for C-level decision making
        ✔ NO generic advice, NO vague sentences

        Do NOT mention internal reasoning or AI.

        ⸻
        TASK

        Using the data provided, create a complete Facebook Page Insight Report following the required output template.

        Within the 5 required sections, you MUST embed the following advanced intelligence:

        ────────────────────────────────────────
        🔥 CORE ADVANCED ANALYSIS REQUIREMENTS
        ────────────────────────────────────────

        ### 1. SCORE BREAKDOWN
        Inside Section 1:
        Provide a 5–7 part breakdown such as:
        • Page Optimization (About section, cover photo, profile picture)
        • Content Strategy & Format Balance
        • Engagement Health (likes, comments, shares ratio)
        • Video Performance (if applicable)
        • Community Building
        • Posting Consistency
        • Call-to-Action Effectiveness

        Each sub-score must include a short justification.

        ### 2. FACEBOOK-SPECIFIC METRICS ANALYSIS
        Analyze:
        • Likes vs Comments vs Shares ratio (shares are high-value signals)
        • Engagement rate benchmarks for the industry
        • Post frequency impact on reach
        • Video vs Image vs Text post performance
        • Best posting times for {user_country} audience

        ### 3. CONTENT STRATEGY RECOMMENDATIONS
        Provide:
        • Post type mix (Video 60%, Image 30%, Text 10% recommended)
        • Video content ideas (native Facebook videos perform best)
        • Carousel post strategies
        • Live video opportunities
        • Story/Reels integration (if applicable)
        • User-generated content campaigns

        ### 4. ENGAGEMENT TACTICS
        Provide:
        • Comment engagement strategies
        • Share-worthy content formats
        • Community building tactics
        • Facebook Groups integration
        • Messenger automation opportunities
        • Event promotion strategies

        ### 5. POSTING SCHEDULE
        Provide:
        • Optimal posting frequency (3-5x/week for pages)
        • Best times for {user_country} timezone
        • Content calendar template
        • Seasonal content opportunities

        ### 6. FACEBOOK AD INTEGRATION
        Include:
        • Organic-to-paid amplification strategies
        • Boost post recommendations
        • Audience targeting insights
        • Retargeting opportunities

        ### 7. "WHY IT WORKS" RATIONALE
        After any major recommendation, add a short explanation:
        "Why it works: …"
        Tie it to Facebook 2025 behavior such as:
        • News Feed ranking signals (engagement, recency, relationship)
        • Video watch time importance
        • Share value (highest ranking signal)
        • Comment depth and quality
        • Page authority signals

        ### 8. INDUSTRY BENCHMARKS
        Reference:
        • B2B Facebook ER averages (0.5–1.5%)
        • B2C Facebook ER ranges (1–3%)
        • E-commerce ER benchmarks (0.8–2%)
        • Local business ER (2–5%)
        • Adjust expectations based on industry

        ### 9. SWOT ANALYSIS
        Include within sections:
        Strengths → strong engagement, verified status, consistent posting
        Weaknesses → low share rate, infrequent posting, weak CTAs
        Opportunities → video content, Facebook Groups, Events, Live videos
        Threats → algorithm changes, declining organic reach, competitor advantage

        ### 10. CONVERSION OPTIMIZATION
        Evaluate:
        • Call-to-action button effectiveness
        • Link placement strategies
        • Messenger integration
        • Lead generation forms
        • Shop/Store integration (if applicable)

        ────────────────────────────────────────
        🔹 ADDITIONAL INTELLIGENCE TO EMBED
        ────────────────────────────────────────

        - Perform qualitative competitor benchmarking (posting frequency, content depth, engagement patterns) with NO brand names.

        - Infer audience persona segments based on engagement patterns, geography, and content preferences.

        - Include threat analysis:
        • Low share rate → weak viral potential
        • Infrequent posting → algorithm suppression
        • Low comment quality → weak ranking signals
        • Video underutilization → missed reach opportunity
        • Missing CTAs → conversion leak

        - Identify best-performing content patterns (videos, carousels, live content).

        - Identify weak patterns (text-only posts, low-engagement formats).

        - Provide 3–6 post copy examples optimized for Facebook.

        - Mention visual identity strengths or inconsistencies.

        - Provide a full 30-day action plan and weekly posting schedule.

        ────────────────────────────────────────
        📋 REQUIRED OUTPUT TEMPLATE
        ────────────────────────────────────────

        You MUST structure your response EXACTLY as follows:

        **Summary Insight:**
        [2-3 paragraph executive summary with overall score, key findings, and top 3 priorities]

        **Full Analysis:**
        [Comprehensive analysis covering all 5 sections with subsections as needed]

        **Recommendations:**
        [Actionable, prioritized recommendations with implementation steps]

        **Content Strategy:**
        [Specific content ideas, formats, and posting strategies]

        **30-Day Action Plan:**
        [Week-by-week breakdown of implementation steps]
        """

        # Variable data (changes per request) - this should NOT be cached
        variable_data = f"""
        ────────────────────────────────────────
        📊 FACEBOOK PAGE DATA
        ────────────────────────────────────────

        **Page Information:**
        - Page Name: {profile_name}
        - Company: {company_name}
        - Business Description: {business_description}
        - Goal: {goal}
        - Bio/About: {bio}
        - Verified: {'Yes' if verified else 'No'}
        - Website: {website or 'Not provided'}
        - Page URL: {url}
        - Target Region: {user_country}

        **Metrics:**
        - Followers: {followers:,}
        - Posts Analyzed: {posts_count}
        - Average Likes per Post: {avg_likes:.1f}
        - Average Comments per Post: {avg_comments:.1f}
        - Average Shares per Post: {avg_shares:.1f}
        - Engagement Rate: {engagement_rate:.2f}%

        **Engagement Breakdown:**
        - Total Engagement per Post: {avg_likes + avg_comments + avg_shares:.1f}
        - Likes: {avg_likes:.1f} ({((avg_likes / (avg_likes + avg_comments + avg_shares)) * 100) if (avg_likes + avg_comments + avg_shares) > 0 else 0:.1f}%)
        - Comments: {avg_comments:.1f} ({((avg_comments / (avg_likes + avg_comments + avg_shares)) * 100) if (avg_likes + avg_comments + avg_shares) > 0 else 0:.1f}%)
        - Shares: {avg_shares:.1f} ({((avg_shares / (avg_likes + avg_comments + avg_shares)) * 100) if (avg_likes + avg_comments + avg_shares) > 0 else 0:.1f}%)

        Now generate the complete Facebook Intelligence Report following the template above.
        """

        if return_split:
            return (static_template, variable_data)
        else:
            return f"{static_template}\n\n{variable_data}"

    def _create_generic_social_prompt(self, platform: str, profile_name: str, company_name: str, business_description: str, goal: str, bio: str, 
                                     followers: int, following: int, verified: bool,
                                     engagement_rate: float, hashtags: list, content_themes: list,
                                     url: str, user_country: str, return_split: bool = False) -> str | tuple[str, str]:
        """Create generic social media analysis prompt for other platforms with optional splitting for caching"""
        
        # Static template (instructions, format) - this can be cached
        static_template = f"""You are Transformellica's Senior Social Media and Digital Marketing AI Consultant. You specialize in multi-platform analytics, content optimization, and audience behavior across MENA markets. Your purpose is to deliver accurate, data-driven, and platform-specific insights that help brands grow measurable engagement and awareness. You act as a strategic advisor focused on ROI and execution-ready recommendations.

        Your task is to analyze the provided profile data and provide a complete, insight-based marketing report that includes:

        1. *Profile Optimization Score (1–100)* based on bio clarity, visual identity, posting consistency, and engagement health
        2. *Content Strategy Recommendations* with clear examples of what to post, frequency, and tone
        3. *Engagement Improvement Suggestions* based on behavior and algorithm trends
        4. *Platform-Specific Best Practices* relevant to the platform mentioned in the data
        5. *Growth Opportunities* including emerging trends, collaborations, or underused formats

        *Context and Requirements:*
        - Your audience consists of SMEs, agencies, and entrepreneurs in MENA who need practical, realistic, and locally relevant insights
        - Avoid general statements such as "post more often" or "use engaging content"
        - Every recommendation must be specific, measurable, and actionable
        - Include culturally contextual advice where relevant (regional posting hours, Arabic hashtag usage, etc.)
        - Base insights strictly on the provided profile data and verified digital marketing sources
        - You may reference current best practices from trusted sources like Meta Blueprint, LinkedIn Marketing Solutions, HubSpot, and official platform blogs

        *Tone and Persona:*
        Write as a senior strategist with deep knowledge of content algorithms, audience psychology, and digital growth frameworks. Your report should be concise and professional - something marketing managers can immediately execute. Interpret data like an expert consultant, not an AI model. Be professional, confident, and insight-driven while avoiding hype, marketing clichés, or unnecessary adjectives.

        *Output Format:*
        Structure your response exactly as follows:

        SOCIAL MEDIA INSIGHT REPORT
        Platform: {platform}
        Profile URL: {url}
        Profile Name: {profile_name}
        Company Name: {company_name}
        Business Description: {business_description}
        Goal: {goal}
    
        1. PROFILE OPTIMIZATION SCORE: [Provide brief justification first, then score]/100

        2. CONTENT STRATEGY RECOMMENDATIONS
        [Provide 3–5 precise, outcome-oriented suggestions]

        3. ENGAGEMENT IMPROVEMENT SUGGESTIONS
        [Provide 2–4 tactics grounded in platform behavior]

        4. PLATFORM-SPECIFIC BEST PRACTICES
        [Provide 2–3 relevant platform insights]

        5. GROWTH OPPORTUNITIES
        [Provide 2–4 emerging trends, collaboration ideas, or content experiments]

        Summary Insight: [Two sentences summarizing the key priority for next actions]

        *Important Restrictions:*
        - Never fabricate data, metrics, or demographics
        - Do not use vague, generic recommendations
        - Do not refer to AI models, system instructions, or internal processes
        - Do not cite unverified or user-generated content as evidence
        - Ensure all recommendations are specific and actionable
        - Explain the rationale briefly for major recommendations

        Now analyze the following profile data:"""
        
        # Variable data (changes per request) - this should NOT be cached
        variable_data = f"""
        Platform: {platform}
        Profile URL: {url}
        Name: {profile_name}
        Bio: {bio}
        Followers: {followers}
        Following: {following}
        Verified: {verified}
        Engagement Rate: {(engagement_rate or 0) * 100:.2f}%
        Hashtags Used: {', '.join(hashtags[:20]) if hashtags else 'None'}
        Content Themes: {', '.join(content_themes[:10]) if content_themes else 'None'}
        User Country: {user_country if user_country else 'Not specified'}
        """
        
        if return_split:
            return (static_template, variable_data)
        
        return f"""{static_template}

        {variable_data}"""
    
    def _create_competitor_instagram_prompt(self, profile_name: str, company_name: str, business_description: str, goal: str, bio: str, followers: int, following: int,
                                verified: bool, is_private: bool, website: str, engagement_rate: float,
                                hashtags: list, content_themes: list, posts_count: int, avg_likes: float,
                                avg_comments: float, url: str, user_country: str, return_split: bool = False) -> str | tuple[str, str]:
        """Create competitor Instagram analysis prompt matching normal format"""
        
        # Use the same template as normal Instagram but with competitor context
        static_template = f"""
        You are Transformellica's Executive Director of Instagram Growth, Social Intelligence, and Creative Strategy (2025). Your job is to generate an elite, agency-grade Instagram Intelligence Report equal to or superior to global agencies (Ogilvy, VaynerMedia, Social Chain) and premium analytics tools (Iconosquare, Later, Hootsuite Impact).

        IMPORTANT: You are analyzing a COMPETITOR Instagram profile. Focus on understanding their strengths and weaknesses to help the user identify competitive advantages and opportunities to outperform them.

        Your report MUST be:
        ✔ Expert-level  
        ✔ High ROI focused  
        ✔ Region-aware {user_country}  
        ✔ Algorithm-aligned (Instagram 2025 updates)  
        ✔ Detailed, actionable, and formatted cleanly  
        ✔ Ready for C-level decision making  
        ✔ NO generic advice, NO vague sentences  

        Do NOT mention internal reasoning or AI.

        ⸻
        TASK

        Using the data provided, create a complete Instagram Insight Report following the required output template.

        Within the 5 required sections, you MUST embed the following advanced intelligence:

        ────────────────────────────────────────
        🔥 CORE ADVANCED ANALYSIS REQUIREMENTS
        ────────────────────────────────────────

        ### 1. SCORE BREAKDOWN
        Inside Section 1:
        Provide a 5–7 part breakdown such as:
        • Bio Clarity  
        • Content Format Balance  
        • Engagement Health  
        • Discovery Optimization  
        • Audience Relevance  
        • Brand Positioning Strength  

        Each sub-score must include a short justification.

        ### 2. ALLOW SUBSECTIONS (A, B, C…)
        Inside sections 2–5, organize recommendations using subsections with titles:
        A. Reels Strategy  
        B. Carousel Strategy  
        C. Caption Strategy  
        D. Hashtag Strategy  
        E. Posting Windows  
        F. Collabs  
        G. Lead Funnels  
        H. Localization  
        I. Story Funnels  
        J. Content Formats  
        etc.

        ### 3. CAPTION RECOMMENDATIONS
        Provide:
        • 3–6 high-performing caption templates  
        • Arabic-English hybrid versions  
        • CTA-driven captions  
        • Hooks first, value second  

        ### 4. HASHTAG RECOMMENDATIONS
        Provide BOTH:
        • Cluster strategy (broad → mid → niche)  
        • AND ready copy/paste sets:

        Example format:
        **Hashtag Set 1 — Broad Reach**  
        #example #example #example  

        **Hashtag Set 2 — Mid-Competition**  
        ...

        **Hashtag Set 3 — Niche Targeting**  
        ...

        Hashtags MUST be niche-accurate and regionally relevant.

        ### 5. REELS HOOKS + SCRIPT IDEAS
        Provide:
        • 5–10 hook templates  
        • 3–5 full Reel scripts with scene breakdowns:
        Scene 1 (1s): Hook  
        Scene 2 (2s): Value  
        Scene 3 (3s): Proof  
        Scene 4 (1s): CTA  

        ### 6. "WHY IT WORKS" RATIONALE
        After any major recommendation, add a short explanation:
        "Why it works: …"  
        Tie it to IG 2025 behavior such as retention, saves, session time, interest mapping, DM engagement ranking, Explore Graph, etc.

        ### 7. INDUSTRY BENCHMARKS
        Allowed:
        • B2B ER averages (3–4%)  
        • Fashion ER ranges (1.8–4.5%)  
        • Reels discovery dominance (60–70% non-followers)  
        • Carousels save-rate multipliers (1.9×)  
        • Story completion rates  
        • Posting norms (3–5 Reels/week)  

        NEVER fabricate data about the profile — only use known industry norms.

        ### 8. AUDIENCE PERSONA INFERENCE
        Infer likely audience characteristics based on:
        • Niche  
        • Country  
        • Language mix  
        • Visual tone  
        • Content style  

        Without creating fake demographic percentages.

        ### 9. EMBEDDED SWOT
        Without creating a separate SWOT section:
        • Strengths → inside Score + Content Strategy  
        • Weaknesses → inside Score + Engagement  
        • Opportunities → inside Growth Opportunities  
        • Threats → inside Engagement + Best Practices  

        Threats must include:
        • Algorithmic decay  
        • Discoverability risks  
        • Competitor posting advantage  
        • Content fatigue  
        • Niche saturation  

        ### 10. COMPETITOR BENCHMARKING (QUALITATIVE)
        Compare the account to typical competitors in its niche:
        • Posting frequency  
        • Reels vs static ratio  
        • Creator usage  
        • Content quality  
        • Engagement patterns  

        NO brand names.

        ### 11. LEAD-GEN & CTA FRAMEWORKS
        Include:
        • DM Triggers ("DM 'AUDIT'", "DM 'LOOK'", "DM 'GUIDE'")  
        • Story funnels  
        • Lead magnet ideas  
        • Value-first CTAs  
        • Collab-driven lead-gen  

        ### 12. POSTING WINDOWS
        Include recommended times for:
        user country: {user_country}
        Based on behavioral trends.

        ### 13. CREATIVE FORMULAS
        Provide universal content formulas:
        • Hook → Value → CTA  
        • Problem → Myth → Truth  
        • 3 Ways To…  
        • Before/After  

        ### 14. 7-DAY CONTENT SCHEDULE
        Inside Section 2 or near the end, provide a **one-week content plan** tailored to the account:
        Mon → Reel  
        Tue → Carousel  
        Wed → Story funnel  
        Thu → Collab Reel  
        Fri → Hybrid caption Reel  
        Sat → Arabic-English carousel  
        Sun → Notes + Stories  

        ### 15. FULL 30-DAY ACTION PLAN
        Inside Summary Insight:
        • Week 1 → Foundation  
        • Week 2 → Volume Increase  
        • Week 3 → Lead Generation  
        • Week 4 → Optimization & Scaling  

        ────────────────────────────────────────
        🔹 ADDITIONAL INTELLIGENCE TO EMBED
        ────────────────────────────────────────

        - Perform qualitative competitor benchmarking (posting frequency, content depth, creator usage, niche saturation) with NO brand names.

        - Infer audience persona segments (e.g., young professionals, minimalist fashion lovers, tech-minded users, startup founders) based on niche, geography, and visual style.

        - Include SWOT logic within the 5 sections:
        Strengths → brand identity, product uniqueness  
        Weaknesses → low posting, weak bio, missing highlights  
        Opportunities → Reels, Guides, localized content, collabs  
        Threats → algorithmic decay, competitor advantage, niche saturation, content fatigue  

        - Add explicit threat analysis:
        • Low posting → algorithm suppression  
        • Generic hashtags → poor niche mapping  
        • Low comment depth → weak ranking signals  
        • Format repetition → content fatigue  
        • Missing highlights → conversion leak  

        - Evaluate full conversion flow:
        Bio → Highlights → Link → CTA → DMs

        - Identify best-performing content patterns (fit-tests, POV walkthroughs, expert breakdowns).

        - Identify weak patterns (static posts, low-motion videos).

        - Include 3–6 caption examples and 3 hashtag sets.

        - Mention visual identity strengths or inconsistencies.

        - Provide a full 30-day plan and a 7-day schedule.

        ────────────────────────────────────────
        CONTEXT & GUARDRAILS
        ────────────────────────────────────────

        • Never fabricate numbers or analytics for the profile.  
        • May use Instagram industry benchmarks.  
        • Must include culturally relevant suggestions (Egypt/KSA/UAE).  
        • No vague advice; everything must be actionable.  
        • Do NOT mention "AI", "system", or your process.  
        • Maintain a premium, authoritative tone.

        ────────────────────────────────────────
        REQUIRED OUTPUT TEMPLATE (DO NOT MODIFY)
        ────────────────────────────────────────

        **INSTAGRAM INSIGHT REPORT**
        **Platform:** Instagram
        **Profile URL:** {url}
        **Profile Name:** {profile_name}

        ---

        ## **1. PROFILE OPTIMIZATION SCORE**
        [Detailed justification + score breakdown] — [Score]/100

        ---

        ## **2. CONTENT STRATEGY RECOMMENDATIONS**
        [You may use A, B, C… subsections. Include hooks, caption templates, hashtag clusters, creative formulas, Reels scripts, posting windows, localization, content calendar.]

        ---

        ## **3. ENGAGEMENT IMPROVEMENT SUGGESTIONS**
        [DM triggers, comment-depth prompts, save triggers, story funnels, creator collabs, lead magnets.]

        ---

        ## **4. PLATFORM-SPECIFIC BEST PRACTICES**
        [2025 Instagram features: Remix, Add Yours, Notes, Broadcast Channel, AI hashtag tools, Professional Dashboard.]

        ---

        ## **5. GROWTH OPPORTUNITIES**
        [Localized content, micro-influencers, cross-platform reuse, niche expansion, campaign ideas, lead-gen systems.]

        ---

        ## **Summary Insight**
        [Executive summary + 30-day plan (Week 1 → Week 4).]

        ⸻

        Now analyze the following competitor profile data:

        """
        # Variable data (changes per request) - this should NOT be cached
        profile_data_xml = f"""
        <profile_data>
        Profile URL: {url}
        Profile Name: {profile_name}
        Company Name: {company_name}
        Business Description: {business_description}
        Goal: {goal}
        Bio: {bio}
        Followers: {followers}
        Following: {following}
        Verified: {verified}
        Private: {is_private}
        Website: {website}
        Posts Count: {posts_count}
        Engagement Rate: {(engagement_rate or 0) * 100:.2f}%
        Average Likes: {avg_likes:.0f}
        Average Comments: {avg_comments:.0f}
        Hashtags Used: {', '.join(hashtags[:20]) if hashtags else 'None'}
        Content Themes: {', '.join(content_themes[:10]) if content_themes else 'None'}
        User Country: {user_country if user_country else 'Not specified'}
        </profile_data>
        
        NOTE: This is a COMPETITOR Instagram profile analysis. Focus on identifying their strengths and weaknesses to help understand competitive positioning and opportunities.
        """
        if return_split:
            return (static_template, profile_data_xml)
        return f"{static_template}\n{profile_data_xml}"
    
    def _create_competitor_facebook_prompt(self, profile_name: str, company_name: str, business_description: str, goal: str, bio: str, 
                                followers: int, verified: bool, website: str, engagement_rate: float,
                                posts_count: int, avg_likes: float, avg_comments: float, avg_shares: float,
                                url: str, user_country: str, return_split: bool = False) -> str | tuple[str, str]:
        """Create competitor Facebook analysis prompt matching normal format"""
        
        # Use the same template as normal Facebook but with competitor context
        static_template = f"""
        You are Transformellica's Executive Director of Facebook Marketing, Community Building, and Organic Growth Strategy (2025). Your job is to generate an elite, agency-grade Facebook Page Intelligence Report equal to or superior to global agencies and premium analytics tools.

        IMPORTANT: You are analyzing a COMPETITOR Facebook page. Focus on understanding their strengths and weaknesses to help the user identify competitive advantages and opportunities to outperform them.

        Your report MUST be:
        ✔ Expert-level and data-driven
        ✔ High ROI focused with actionable recommendations
        ✔ Region-aware ({user_country})
        ✔ Algorithm-aligned (Facebook 2025 updates: News Feed ranking, engagement signals, video-first)
        ✔ Detailed, actionable, and formatted cleanly
        ✔ Ready for C-level decision making
        ✔ NO generic advice, NO vague sentences

        Do NOT mention internal reasoning or AI.

        ⸻
        TASK

        Using the data provided, create a complete Facebook Page Insight Report following the required output template.

        Within the 5 required sections, you MUST embed the following advanced intelligence:

        ────────────────────────────────────────
        🔥 CORE ADVANCED ANALYSIS REQUIREMENTS
        ────────────────────────────────────────

        ### 1. SCORE BREAKDOWN
        Inside Section 1:
        Provide a 5–7 part breakdown such as:
        • Page Optimization (About section, cover photo, profile picture)
        • Content Strategy & Format Balance
        • Engagement Health (likes, comments, shares ratio)
        • Video Performance (if applicable)
        • Community Building
        • Posting Consistency
        • Call-to-Action Effectiveness

        Each sub-score must include a short justification.

        ### 2. FACEBOOK-SPECIFIC METRICS ANALYSIS
        Analyze:
        • Likes vs Comments vs Shares ratio (shares are high-value signals)
        • Engagement rate benchmarks for the industry
        • Post frequency impact on reach
        • Video vs Image vs Text post performance
        • Best posting times for {user_country} audience

        ### 3. CONTENT STRATEGY RECOMMENDATIONS
        Provide:
        • Post type mix (Video 60%, Image 30%, Text 10% recommended)
        • Video content ideas (native Facebook videos perform best)
        • Carousel post strategies
        • Live video opportunities
        • Story/Reels integration (if applicable)
        • User-generated content campaigns

        ### 4. ENGAGEMENT TACTICS
        Provide:
        • Comment engagement strategies
        • Share-worthy content formats
        • Community building tactics
        • Facebook Groups integration
        • Messenger automation opportunities
        • Event promotion strategies

        ### 5. POSTING SCHEDULE
        Provide:
        • Optimal posting frequency (3-5x/week for pages)
        • Best times for {user_country} timezone
        • Content calendar template
        • Seasonal content opportunities

        ### 6. FACEBOOK AD INTEGRATION
        Include:
        • Organic-to-paid amplification strategies
        • Boost post recommendations
        • Audience targeting insights
        • Retargeting opportunities

        ### 7. "WHY IT WORKS" RATIONALE
        After any major recommendation, add a short explanation:
        "Why it works: …"
        Tie it to Facebook 2025 behavior such as:
        • News Feed ranking signals (engagement, recency, relationship)
        • Video watch time importance
        • Share value (highest ranking signal)
        • Comment depth and quality
        • Page authority signals

        ### 8. INDUSTRY BENCHMARKS
        Reference:
        • B2B Facebook ER averages (0.5–1.5%)
        • B2C Facebook ER ranges (1–3%)
        • E-commerce ER benchmarks (0.8–2%)
        • Local business ER (2–5%)
        • Adjust expectations based on industry

        ### 9. SWOT ANALYSIS
        Include within sections:
        Strengths → strong engagement, verified status, consistent posting
        Weaknesses → low share rate, infrequent posting, weak CTAs
        Opportunities → video content, Facebook Groups, Events, Live videos
        Threats → algorithm changes, declining organic reach, competitor advantage

        ### 10. CONVERSION OPTIMIZATION
        Evaluate:
        • Call-to-action button effectiveness
        • Link placement strategies
        • Messenger integration
        • Lead generation forms
        • Shop/Store integration (if applicable)

        ────────────────────────────────────────
        🔹 ADDITIONAL INTELLIGENCE TO EMBED
        ────────────────────────────────────────

        - Perform qualitative competitor benchmarking (posting frequency, content depth, engagement patterns) with NO brand names.

        - Infer audience persona segments based on engagement patterns, geography, and content preferences.

        - Include threat analysis:
        • Low share rate → weak viral potential
        • Infrequent posting → algorithm suppression
        • Low comment quality → weak ranking signals
        • Video underutilization → missed reach opportunity
        • Missing CTAs → conversion leak

        - Identify best-performing content patterns (videos, carousels, live content).

        - Identify weak patterns (text-only posts, low-engagement formats).

        - Provide 3–6 post copy examples optimized for Facebook.

        - Mention visual identity strengths or inconsistencies.

        - Provide a full 30-day action plan and weekly posting schedule.

        ────────────────────────────────────────
        📋 REQUIRED OUTPUT TEMPLATE
        ────────────────────────────────────────

        You MUST structure your response EXACTLY as follows:

        **Summary Insight:**
        [2-3 paragraph executive summary with overall score, key findings, and top 3 priorities]

        **Full Analysis:**
        [Comprehensive analysis covering all 5 sections with subsections as needed]

        **Recommendations:**
        [Actionable, prioritized recommendations with implementation steps]

        **Content Strategy:**
        [Specific content ideas, formats, and posting strategies]

        **30-Day Action Plan:**
        [Week-by-week breakdown of implementation steps]
        """

        # Variable data (changes per request) - this should NOT be cached
        variable_data = f"""
        ────────────────────────────────────────
        📊 FACEBOOK PAGE DATA
        ────────────────────────────────────────

        **Page Information:**
        - Page Name: {profile_name}
        - Company: {company_name}
        - Business Description: {business_description}
        - Goal: {goal}
        - Bio/About: {bio}
        - Verified: {'Yes' if verified else 'No'}
        - Website: {website or 'Not provided'}
        - Page URL: {url}
        - Target Region: {user_country}

        **Metrics:**
        - Followers: {followers:,}
        - Posts Analyzed: {posts_count}
        - Average Likes per Post: {avg_likes:.1f}
        - Average Comments per Post: {avg_comments:.1f}
        - Average Shares per Post: {avg_shares:.1f}
        - Engagement Rate: {engagement_rate:.2f}%

        **Engagement Breakdown:**
        - Total Engagement per Post: {avg_likes + avg_comments + avg_shares:.1f}
        - Likes: {avg_likes:.1f} ({((avg_likes / (avg_likes + avg_comments + avg_shares)) * 100) if (avg_likes + avg_comments + avg_shares) > 0 else 0:.1f}%)
        - Comments: {avg_comments:.1f} ({((avg_comments / (avg_likes + avg_comments + avg_shares)) * 100) if (avg_likes + avg_comments + avg_shares) > 0 else 0:.1f}%)
        - Shares: {avg_shares:.1f} ({((avg_shares / (avg_likes + avg_comments + avg_shares)) * 100) if (avg_likes + avg_comments + avg_shares) > 0 else 0:.1f}%)

        NOTE: This is a COMPETITOR Facebook page analysis. Focus on identifying their strengths and weaknesses to help understand competitive positioning and opportunities.

        Now generate the complete Facebook Intelligence Report following the template above.
        """

        if return_split:
            return (static_template, variable_data)
        
        return f"{static_template}\n{variable_data}"
    
    def _create_comprehensive_report_prompt(self, seo_data: Dict[str, Any], social_data: List[Dict[str, Any]], branding_data: Optional[Dict[str, Any]] = None) -> str:
        """Create prompt for comprehensive marketing report with detailed SEO and social data"""
        page_speed_scores = seo_data.get('page_speed_scores', {})
        performance = page_speed_scores.get('performance', 'N/A')
        accessibility = page_speed_scores.get('accessibility', 'N/A')
        best_practices = page_speed_scores.get('best_practices', 'N/A')
        seo_score = page_speed_scores.get('seo', 'N/A')
        overall = page_speed_scores.get('overall', 'N/A')
        print(page_speed_scores)
        # Format social profiles information
        social_profiles = []
        for profile in social_data:
            platform = profile.get('platform', 'unknown')
            url = profile.get('url', 'N/A')
            profile_data = profile.get('profile_data', {})
            content_analysis = profile.get('content_analysis', {})
            
            profile_info = f"\n    - Platform: {platform}\n"
            profile_info += f"      URL: {url}\n"
            profile_info += f"      Name: {profile_data.get('name', 'N/A')}\n"
            profile_info += f"      Bio: {profile_data.get('bio', 'N/A')}\n"
            profile_info += f"      Followers: {profile_data.get('follower_count', 'N/A')}\n"
            profile_info += f"      Following: {profile_data.get('following_count', 'N/A')}\n"
            profile_info += f"      Verified: {profile_data.get('verification_status', 'N/A')}\n"
            profile_info += f"      Content Themes: {content_analysis.get('content_themes', [])}\n"
            profile_info += f"      Hashtags: {content_analysis.get('hashtags', [])}\n"
            profile_info += f"      Engagement Rate: {content_analysis.get('engagement_rate', 'N/A')}\n"
            
            social_profiles.append(profile_info)
        
        # Format headings structure
        headings_structure = ""
        headings = seo_data.get('headings')

        if isinstance(headings, dict):
            for heading_type, heading_list in headings.items():
                if heading_list:
                    headings_structure += f"\n      {heading_type}: {len(heading_list)} headings"
                    for heading in heading_list[:3]:
                        headings_structure += f"\n        - {heading}"
                    if len(heading_list) > 3:
                        headings_structure += f"\n        - ... ({len(heading_list) - 3} more)"
        elif isinstance(headings, list):
            headings_structure += "\n      Headings (list format):"
            for heading in headings[:3]:
                headings_structure += f"\n        - {heading}"
            if len(headings) > 3:
                headings_structure += f"\n        - ... ({len(headings) - 3} more)"
        else:
            headings_structure += "\n      No heading data found."

        # Add branding data if available
        branding_summary = "Not analyzed."
        if branding_data and "branding_analysis" in branding_data:
            branding_summary = branding_data["branding_analysis"].get("executive_summary", "No summary available.")

        # Format schema markup
        schema_markup = ""
        schema_data = seo_data.get('schema_markup')
        if isinstance(schema_data, list):
            schema_markup = "\n      " + "\n      ".join([f"- {schema}" for schema in schema_data])
        elif isinstance(schema_data, dict):
            schema_markup = "\n      " + "\n      ".join([f"- {key}: {value}" for key, value in schema_data.items()])
        elif schema_data:
            schema_markup = f"\n      - {schema_data}"

        # Format Open Graph tags
        og_tags = ""
        og_data = seo_data.get('og_tags')
        if isinstance(og_data, dict):
            og_tags = "\n      " + "\n      ".join([f"- {tag}: {value}" for tag, value in og_data.items() if value])
        elif isinstance(og_data, list):
            og_tags = "\n      " + "\n      ".join([f"- {tag}" for tag in og_data])
        elif og_data:
            og_tags = f"\n      - {og_data}"

        # Format social links
        social_links = ""
        social_links_data = seo_data.get('social_links')
        if isinstance(social_links_data, dict):
            social_links = "\n      " + "\n      ".join([f"- {platform}: {url}" for platform, url in social_links_data.items()])
        elif isinstance(social_links_data, list):
            social_links = "\n      " + "\n      ".join([f"- {link}" for link in social_links_data])
        elif social_links_data:
            social_links = f"\n      - {social_links_data}"

        # Return final prompt
        return f"""
        Create a comprehensive digital marketing analysis report based on the following detailed data:

        WEBSITE SEO DATA:
        - URL: {seo_data.get('url')}
        - Performance: {performance}
        - Accessibility: {accessibility}
        - Best Practices: {best_practices}
        - SEO: {seo_score}
        - Page Speed Score: {overall}        
        - HTTPS Enabled: {seo_data.get('https', False)}
        - Title: {seo_data.get('title', 'N/A')}
        - Title Length: {seo_data.get('title_length', 0)} characters
        - Meta Description: {seo_data.get('meta_description', 'N/A')}
        - Meta Description Length: {seo_data.get('meta_description_length', 0)} characters
        - Canonical URL: {seo_data.get('canonical_url', 'N/A')}
        - Images Count: {seo_data.get('images_count', 0)}
        - Images Missing Alt Tags: {seo_data.get('alt_tags_missing', 0)}
        - Internal Links: {seo_data.get('internal_links', 0)}
        - External Links: {seo_data.get('external_links', 0)}
        - Technical Issues: {self._identify_technical_issues(seo_data)}
        - Content Gaps: (AI should infer this based on headings, etc.)
        - Headings Structure: {headings_structure}
        - Schema Markup: {schema_markup}
        - Open Graph Tags: {og_tags}
        - Social Links on Website: {social_links}

        SOCIAL MEDIA PRESENCE:
        - Platforms: {', '.join([p.get('platform', 'unknown') for p in social_data])}
        - Total Profiles: {len(social_data)}
        - Detailed Profile Information: {''.join(social_profiles)}

        **Branding Analysis Summary**:
        - {branding_summary}

        Please provide a comprehensive marketing report including:
        1.  **Executive Summary**: A high-level overview of the key findings and strategic direction.
        2.  **Key Findings**: Bulleted list of the most important insights from both SEO and social media analysis.
        3.  **Strategic Recommendations**: Prioritized list of strategies based on the analysis.
        4.  **Priority Actions**: Immediate next steps with timeline.
        5.  **Performance Benchmarks**: Quantitative assessment of current performance.
        6.  **Next Steps**: Long-term growth strategy and follow-up actions.
        
        Focus on cross-platform synergies, integrated marketing opportunities, and actionable insights that will improve both SEO performance and social media engagement. Provide specific, data-driven recommendations based on the detailed analysis provided.
        """
        
    def _parse_seo_insights(self, response: str) -> Dict[str, Any]:
        """Parse GPT response for SEO insights"""
        return {
            "summary": response[:200] + "..." if len(response) > 200 else response,
            "full_analysis": response
        }
    
    def _parse_social_insights(self, response: str) -> Dict[str, Any]:
        """Parse GPT response for social insights"""
        return {
            "summary": response[:200] + "..." if len(response) > 200 else response,
            "full_analysis": response
        }
    
    def _parse_comprehensive_insights(self, response: str) -> Dict[str, Any]:
        """Parse comprehensive report response"""
        lines = response.split('\n')
        
        insights = {
            "executive_summary": "",
            "key_findings": [],
            "strategic_recommendations": [],
            "priority_actions": [],
            "next_steps": []
        }
        
        current_section = None
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            if "executive summary" in line.lower():
                current_section = "executive_summary"
            elif "key findings" in line.lower():
                current_section = "key_findings"
            elif "strategic recommendations" in line.lower():
                current_section = "strategic_recommendations"
            elif "priority actions" in line.lower():
                current_section = "priority_actions"
            elif "next steps" in line.lower():
                current_section = "next_steps"
            else:
                if current_section and line:
                    if current_section == "executive_summary":
                        insights[current_section] += line + " "
                    else:
                        insights[current_section].append(line)
        
        return insights
    
    def _extract_recommendations(self, response: str) -> List[str]:
        """Extract recommendations from GPT response"""
        recommendations = []
        lines = response.split('\n')
        
        for line in lines:
            line = line.strip()
            if line.startswith(('•', '-', '*')) or line[0:2].isdigit():
                recommendations.append(line)
        
        return recommendations[:10]  # Limit to top 10
    
    def _calculate_priority_score(self, seo_data: Dict[str, Any]) -> int:
        """Calculate priority score based on SEO issues"""
        score = 100
        
        # Deduct points for various issues
        if not seo_data.get('https'):
            score -= 20
        if not seo_data.get('title'):
            score -= 15
        if not seo_data.get('meta_description'):
            score -= 10
        if seo_data.get('alt_tags_missing', 0) > 5:
            score -= 15
        
        page_speed = seo_data.get('page_speed_score')
        if page_speed and page_speed < 50:
            score -= 20
        elif page_speed and page_speed < 70:
            score -= 10
        
        return max(0, score)
    
    def _calculate_seo_score(self, seo_data: Dict[str, Any]) -> int:
        """Calculate overall SEO score"""
        return self._calculate_priority_score(seo_data)
    
    def _identify_improvement_areas(self, seo_data: Dict[str, Any]) -> List[str]:
        """Identify key improvement areas"""
        areas = []
        
        if not seo_data.get('https'):
            areas.append("HTTPS/SSL Certificate")
        if not seo_data.get('title') or len(seo_data.get('title', '')) < 30:
            areas.append("Title Tag Optimization")
        if not seo_data.get('meta_description'):
            areas.append("Meta Description")
        if seo_data.get('alt_tags_missing', 0) > 0:
            areas.append("Image Alt Tags")
        
        page_speed = seo_data.get('page_speed_score')
        if page_speed and page_speed < 70:
            areas.append("Page Speed Optimization")
        
        if not seo_data.get('social_links'):
            areas.append("Social Media Integration")
        
        return areas
    
    def _identify_technical_issues(self, seo_data: Dict[str, Any]) -> List[str]:
        """Identify technical SEO issues"""
        issues = []
        
        if not seo_data.get('https'):
            issues.append("Missing HTTPS")
        if seo_data.get('alt_tags_missing', 0) > 0:
            issues.append(f"{seo_data.get('alt_tags_missing')} missing alt tags")
        if seo_data.get('page_speed_score', 100) < 60:
            issues.append("Poor page speed performance")
        
        return issues
    
    def _extract_content_strategy(self, response: str) -> List[str]:
        lines = response.split("\n")
        strategies = []
        capture = False

        for line in lines:
            # Start capturing after section header
            if line.strip().startswith("2. CONTENT STRATEGY RECOMMENDATIONS"):
                capture = True
                continue

            # Stop when next section begins
            if capture and line.strip().startswith("3. "):
                break

            if capture:
                if line.strip().startswith("-") or line.strip().startswith("•"):
                    strategies.append(line.strip("•- ").strip())

        return strategies[:5]

    
    def _identify_engagement_opportunities(self, social_data: Dict[str, Any]) -> List[str]:
        """Identify engagement opportunities"""
        opportunities = []
        
        profile_data = social_data.get('profile_data', {})
        
        if not profile_data.get('bio', '').strip():
            opportunities.append("Add compelling bio/description")
        
        if not profile_data.get('verification_status'):
            opportunities.append("Apply for verification badge")
        
        hashtags = social_data.get('content_analysis', {}).get('hashtags', [])
        if len(hashtags) < 5:
            opportunities.append("Increase hashtag usage for better discoverability")
        
        return opportunities
    
    def _create_competitive_analysis_prompt(self, social_data: Dict[str, Any]) -> str:
        """Create prompt for competitive analysis suggestions"""
        profile_data = social_data.get('profile_data', {})
        content_analysis = social_data.get('content_analysis', {})
        platform = social_data.get('platform', 'unknown')
        user_country = social_data.get('user_country', '')
        
        # Create country-specific context
        country_context = ""
        if user_country:
            country_context = f"Target Market/Country: {user_country}\n        "
        
        return f"""
        Based on the following social media profile data, generate specific competitive analysis suggestions:

        Platform: {platform}
        Profile URL: {social_data.get('url')}
        {country_context}Name: {profile_data.get('name')}
        Bio: {profile_data.get('bio')}
        Followers: {profile_data.get('follower_count')}
        Following: {profile_data.get('following_count')}
        Verified: {profile_data.get('verification_status')}
        Content Themes: {content_analysis.get('content_themes', [])}
        Hashtags Used: {content_analysis.get('hashtags', [])}
        Engagement Rate: {content_analysis.get('engagement_rate', 'N/A')*100}

        Generate 4-6 specific, actionable competitive analysis suggestions. Return ONLY a valid JSON object with the following structure (no markdown, no extra text):

        {{
            "suggestions": [
                {{
                    "title": "Clear, actionable title",
                    "priority": "HIGH",
                    "category": "Competitor Research",
                    "specific_action": "Detailed step-by-step action to take",
                    "what_to_track": "Specific metrics and data points to monitor",
                    "expected_impact": "How this will benefit their strategy",
                    "timeline": "1-2 weeks",
                    "tools_needed": "Any tools or resources required"
                }}
            ]
        }}

        IMPORTANT: Return only valid JSON. Do not include markdown code blocks, explanations, or any text outside the JSON object.

        Focus on practical actions tailored to this profile's:
        1. Industry/niche (based on bio and content themes)
        2. Current follower size and engagement level
        3. Platform-specific opportunities
        4. Content strategy gaps that could be filled by studying competitors
        5. Target market/country-specific competitive landscape{f" (focus on {user_country} market)" if user_country else ""}

        Make each suggestion highly specific and actionable, not generic advice.{f" Include competitors and strategies specific to the {user_country} market when applicable." if user_country else ""}
        """
    
    def _repair_json_string(self, json_str: str) -> str:
        """Repair common JSON formatting issues"""
        try:
            # Check if JSON is already valid
            json.loads(json_str)
            return json_str
        except json.JSONDecodeError:
            pass
        
        # Fix unterminated strings
        if json_str.count('"') % 2 != 0:
            # Find the last quote and see if it's part of an unterminated string
            last_quote = json_str.rfind('"')
            if last_quote > 0:
                # Look for the pattern: "key": "value that got cut off
                before_quote = json_str[:last_quote]
                if before_quote.endswith(': '):
                    # This looks like an unterminated value, close it
                    json_str = before_quote + '""'
                else:
                    # Try to find the last complete key-value pair
                    last_complete = json_str.rfind('",', 0, last_quote)
                    if last_complete > 0:
                        json_str = json_str[:last_complete + 1]
                    else:
                        # Close the string
                        json_str = json_str[:last_quote] + '"'
        
        # Ensure proper JSON structure closure
        open_braces = json_str.count('{')
        close_braces = json_str.count('}')
        if open_braces > close_braces:
            json_str += '}' * (open_braces - close_braces)
        
        open_brackets = json_str.count('[')
        close_brackets = json_str.count(']')
        if open_brackets > close_brackets:
            json_str += ']' * (open_brackets - close_brackets)
        
        return json_str
    
    def _extract_competitive_suggestions(self, response: str) -> List[Dict[str, str]]:
        """Extract competitive suggestions from AI JSON response"""
        try:
            # Check if response is empty or None
            if not response or not response.strip():
                print("Empty response received from AI")
                return self._generate_mock_competitive_suggestions({})
            
            # Clean the response more thoroughly
            cleaned_response = response.strip()
            
            # Remove markdown code blocks more robustly
            if '```json' in cleaned_response:
                # Find the start after ```json
                start = cleaned_response.find('```json') + 7
                # Find the closing ```
                end = cleaned_response.find('```', start)
                if end != -1:
                    cleaned_response = cleaned_response[start:end].strip()
                else:
                    # If no closing ```, take everything after ```json
                    cleaned_response = cleaned_response[start:].strip()
            elif cleaned_response.startswith('```'):
                # Handle generic ``` blocks
                start = cleaned_response.find('```') + 3
                end = cleaned_response.find('```', start)
                if end != -1:
                    cleaned_response = cleaned_response[start:end].strip()
                else:
                    # If no closing ```, take everything after ```
                    cleaned_response = cleaned_response[start:].strip()
            
            # Additional cleaning for any remaining markdown artifacts
            cleaned_response = cleaned_response.replace('```json', '').replace('```', '').strip()
            
            # Check if we have any content after cleaning
            if not cleaned_response or len(cleaned_response.strip()) == 0:
                print("No content after cleaning markdown")
                return self._generate_mock_competitive_suggestions({})
            
            # Try to find JSON object in the response
            if '{' in cleaned_response and '}' in cleaned_response:
                start = cleaned_response.find('{')
                # Find the matching closing brace
                brace_count = 0
                end = start
                for i, char in enumerate(cleaned_response[start:], start):
                    if char == '{':
                        brace_count += 1
                    elif char == '}':
                        brace_count -= 1
                        if brace_count == 0:
                            end = i + 1
                            break
                
                if end > start:
                    cleaned_response = cleaned_response[start:end]
            else:
                print("No JSON structure found in response")
                return self._extract_suggestions_fallback(response)
            
            # Fix common JSON issues more aggressively
            # Escape any unescaped quotes within string values
            cleaned_response = re.sub(r'(?<!\\)"(?=[^:,\]}])', r'\\"', cleaned_response)
            # Fix newlines within JSON strings
            cleaned_response = re.sub(r':\s*"([^"]*)\n([^"]*)"', r': "\1 \2"', cleaned_response)
            # Remove problematic characters that break JSON strings
            cleaned_response = re.sub(r'[\x00-\x1f\x7f-\x9f]', ' ', cleaned_response)
            # Fix multiple spaces
            cleaned_response = re.sub(r'\s+', ' ', cleaned_response)
            
            # Debug: Show what we're trying to parse
            print(f"Attempting to parse JSON (length: {len(cleaned_response)}):")
            print(f"First 200 chars: {cleaned_response[:200]}")
            
            # Try a different approach - use a more lenient JSON parser
            try:
                # First attempt with the cleaned response
                data = json.loads(cleaned_response)
                suggestions = data.get('suggestions', [])
            except json.JSONDecodeError as e:
                print(f"First JSON parse failed: {e}")
                # If that fails, try to repair the JSON
                cleaned_response = self._repair_json_string(cleaned_response)
                print(f"Repaired JSON length: {len(cleaned_response)}")
                data = json.loads(cleaned_response)
                suggestions = data.get('suggestions', [])
            
            # Validate and clean suggestions
            validated_suggestions = []
            for suggestion in suggestions[:6]:  # Limit to 6 suggestions
                if isinstance(suggestion, dict) and suggestion.get('title'):
                    # Clean string values by removing problematic characters
                    def clean_string(s):
                        if not isinstance(s, str):
                            return str(s)
                        return re.sub(r'[\x00-\x1f\x7f-\x9f]', ' ', s).strip()
                    
                    # Ensure all required fields exist with defaults
                    validated_suggestion = {
                        'title': clean_string(suggestion.get('title', 'Untitled Suggestion')),
                        'priority': clean_string(suggestion.get('priority', 'MEDIUM')).upper(),
                        'category': clean_string(suggestion.get('category', 'Competitor Research')),
                        'specific_action': clean_string(suggestion.get('specific_action', 'No specific action provided')),
                        'what_to_track': clean_string(suggestion.get('what_to_track', 'Monitor engagement metrics')),
                        'expected_impact': clean_string(suggestion.get('expected_impact', 'Improved competitive positioning')),
                        'timeline': clean_string(suggestion.get('timeline', '2-4 weeks')),
                        'tools_needed': clean_string(suggestion.get('tools_needed', 'Social media analytics tools'))
                    }
                    validated_suggestions.append(validated_suggestion)
            
            # If no valid suggestions were found, use fallback
            if not validated_suggestions:
                print("No valid suggestions found in JSON response")
                return self._extract_suggestions_fallback(response)
            
            return validated_suggestions
            
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            print(f"Error parsing competitive suggestions JSON: {str(e)}")
            print(f"Cleaned response length: {len(cleaned_response) if 'cleaned_response' in locals() else 'N/A'}")
            print(f"Using fallback extraction method...")
            # Fallback to simple text extraction - this is working well!
            fallback_suggestions = self._extract_suggestions_fallback(response)
            if fallback_suggestions:
                print(f"Fallback method successfully extracted {len(fallback_suggestions)} suggestions")
                return fallback_suggestions
            else:
                print("Fallback method failed, returning empty suggestions")
                return []
    
    def _extract_suggestions_fallback(self, response: str) -> List[Dict[str, str]]:
        """Fallback method to extract suggestions from non-JSON response"""
        suggestions = []
        
        # If the response looks like it has JSON structure but failed to parse,
        # try to extract titles manually
        if '"title"' in response:
            title_matches = re.findall(r'"title":\s*"([^"]+)"', response)
            for i, title in enumerate(title_matches[:6]):
                suggestion = {
                    'title': title,
                    'priority': 'MEDIUM',
                    'category': 'Competitor Research',
                    'specific_action': title,
                    'what_to_track': 'Monitor engagement and reach metrics',
                    'expected_impact': 'Improved competitive positioning',
                    'timeline': '2-4 weeks',
                    'tools_needed': 'Social media analytics tools'
                }
                suggestions.append(suggestion)
        else:
            # Traditional line-by-line parsing
            lines = response.split('\n')
            
            for line in lines:
                line = line.strip()
                # Look for numbered items, bullet points, or lines with competitive keywords
                if (line.startswith(('•', '-', '*')) or 
                    line[0:2].isdigit() or 
                    any(keyword in line.lower() for keyword in ['competitor', 'benchmark', 'analyze', 'study', 'research', 'compare'])):
                    # Clean up the line
                    cleaned_line = line.lstrip('•-*0123456789. ')
                    if len(cleaned_line) > 10:  # Filter out very short lines
                        suggestion = {
                            'title': cleaned_line,
                            'priority': 'MEDIUM',
                            'category': 'Competitor Research',
                            'specific_action': cleaned_line,
                            'what_to_track': 'Monitor engagement and reach metrics',
                            'expected_impact': 'Improved competitive positioning',
                            'timeline': '2-4 weeks',
                            'tools_needed': 'Social media analytics tools'
                        }
                        suggestions.append(suggestion)
        
        # If we still don't have suggestions, return some defaults
        if not suggestions:
            suggestions = self._generate_mock_competitive_suggestions({})
        
        return suggestions[:6]  # Limit to top 6 suggestions
    
    def _generate_mock_competitive_suggestions(self, social_data: Dict[str, Any]) -> List[Dict[str, str]]:
        """Generate mock competitive suggestions when AI is unavailable"""
        platform = social_data.get('platform', 'social media')
        user_country = social_data.get('user_country', '')
        country_suffix = f" in {user_country}" if user_country else ""
        
        return [
            {
                'title': f"Map & Analyze Top 5 {platform.title()} Competitors{country_suffix}",
                'priority': 'HIGH',
                'category': 'Competitor Research',
                'specific_action': f"Create a spreadsheet tracking your top 5 direct competitors on {platform}{country_suffix}. Monitor their posting frequency, content types, engagement rates, and follower growth weekly.",
                'what_to_track': f'Post frequency (aim for 4-5 posts/week), content mix ratio (educational vs. promotional vs. case studies), engagement rates, follower growth{f", local market trends in {user_country}" if user_country else ""}',
                'expected_impact': f'Better understanding of competitive landscape{country_suffix} and identification of content gaps',
                'timeline': '1-2 weeks',
                'tools_needed': 'Spreadsheet software, social media analytics tools'
            },
            {
                'title': "Benchmark Posting Frequency Against Industry Standards",
                'priority': 'MEDIUM',
                'category': 'Posting Schedule',
                'specific_action': "Track competitor posting schedules for 2 weeks and compare to your current frequency. Identify optimal posting times and content consistency patterns.",
                'what_to_track': 'Posts per day/week, optimal posting times, content consistency, audience engagement patterns by time of day',
                'expected_impact': 'Optimized posting schedule for maximum reach and engagement',
                'timeline': '2-3 weeks',
                'tools_needed': 'Social media scheduling tools, analytics platforms'
            },
            {
                'title': "Study Successful Content Formats in Your Space",
                'priority': 'HIGH',
                'category': 'Content Strategy',
                'specific_action': "Analyze top-performing content types and formats from competitors. Document what works best for your industry and create templates.",
                'what_to_track': 'Content types (video, images, carousels), engagement rates, visual styles, caption lengths, hashtag usage',
                'expected_impact': 'Improved content strategy and higher engagement rates',
                'timeline': '1-2 weeks',
                'tools_needed': 'Content analysis tools, competitor monitoring platforms'
            },
            {
                'title': "Identify Trending Hashtags in Your Industry",
                'priority': 'MEDIUM',
                'category': 'Hashtags',
                'specific_action': "Research and compile a list of trending and niche-specific hashtags used by successful competitors. Test different hashtag combinations.",
                'what_to_track': 'Hashtag performance, reach, competition level, trending patterns, which hashtags drive most engagement',
                'expected_impact': 'Increased discoverability and reach through strategic hashtag usage',
                'timeline': '1 week',
                'tools_needed': 'Hashtag research tools, social media analytics'
            },
            {
                'title': "Research Competitor Engagement Strategies",
                'priority': 'MEDIUM',
                'category': 'Engagement',
                'specific_action': "Monitor when and how competitors engage with their audience. Document their response strategies and community management approaches.",
                'what_to_track': 'Response times, engagement tactics, community management approaches, audience interaction quality',
                'expected_impact': 'Enhanced audience engagement and stronger community building',
                'timeline': '2-4 weeks',
                'tools_needed': 'Social media monitoring tools, engagement tracking software'
            },
            {
                'title': "Compare Content Themes with Successful Competitors",
                'priority': 'LOW',
                'category': 'Brand Positioning',
                'specific_action': "Analyze the content themes and messaging strategies of top competitors to identify differentiation opportunities and unique positioning.",
                'what_to_track': 'Content themes, messaging tone, brand positioning, unique value propositions, audience response to different themes',
                'expected_impact': 'Clearer brand differentiation and unique positioning in the market',
                'timeline': '2-3 weeks',
                'tools_needed': 'Content analysis tools, brand monitoring platforms'
            }
        ]
    
    # async def _generate_competitive_suggestions(self, social_data: Dict[str, Any]) -> List[Dict[str, str]]:
    #     """Generate AI-powered competitive analysis suggestions"""
    #     if not self.api_key:
    #         print("No API key available, using mock competitive suggestions")
    #         return self._generate_mock_competitive_suggestions(social_data)
        
    #     prompt = self._create_competitive_analysis_prompt(social_data)
        
    #     try:
    #         print("Calling AI API for competitive suggestions...")
    #         response = await self._call_ai_api(prompt, max_tokens=2000)
    #         print(f"AI API response length: {len(response) if response else 0}")
            
    #         if not response:
    #             print("Empty response from AI API, using mock suggestions")
    #             return self._generate_mock_competitive_suggestions(social_data)
            
    #         suggestions = self._extract_competitive_suggestions(response)
    #         print(f"Extracted {len(suggestions)} competitive suggestions")
    #         return suggestions
            
    #     except Exception as e:
    #         print(f"Anthropic API error in competitive suggestions: {str(e)}")
    #         return self._generate_mock_competitive_suggestions(social_data)
    
    def format_competitive_suggestions_for_display(self, suggestions: List[Dict[str, str]]) -> str:
        """Format competitive suggestions for better display"""
        if not suggestions:
            return "No competitive suggestions available."
        
        formatted_output = "## 🎯 Competitive Analysis Strategy\n\n"
        
        # Group by priority
        high_priority = [s for s in suggestions if s.get('priority', '').upper() == 'HIGH']
        medium_priority = [s for s in suggestions if s.get('priority', '').upper() == 'MEDIUM']
        low_priority = [s for s in suggestions if s.get('priority', '').upper() == 'LOW']
        
        priority_groups = [
            ("🔴 HIGH PRIORITY", high_priority),
            ("🟡 MEDIUM PRIORITY", medium_priority),
            ("🟢 LOW PRIORITY", low_priority)
        ]
        
        for priority_label, group in priority_groups:
            if group:
                formatted_output += f"### {priority_label}\n\n"
                
                for i, suggestion in enumerate(group, 1):
                    formatted_output += f"**{i}. {suggestion.get('title', 'Untitled Suggestion')}**\n"
                    formatted_output += f"*Category: {suggestion.get('category', 'General')}*\n\n"
                    
                    formatted_output += f"**🎯 Specific Action:** {suggestion.get('specific_action', 'No action specified')}\n\n"
                    formatted_output += f"**📊 What to Track:** {suggestion.get('what_to_track', 'No tracking specified')}\n\n"
                    formatted_output += f"**💡 Expected Impact:** {suggestion.get('expected_impact', 'No impact specified')}\n\n"
                    formatted_output += f"**⏰ Timeline:** {suggestion.get('timeline', 'No timeline specified')}\n\n"
                    formatted_output += f"**🛠️ Tools Needed:** {suggestion.get('tools_needed', 'No tools specified')}\n\n"
                    
                    formatted_output += "---\n\n"
        
        return formatted_output
    
    def get_competitive_suggestions_summary(self, suggestions: List[Dict[str, str]]) -> Dict[str, Any]:
        """Get a summary of competitive suggestions"""
        if not suggestions:
            return {"total": 0, "by_priority": {}, "by_category": {}}
        
        # Count by priority
        priority_counts = {}
        for suggestion in suggestions:
            priority = suggestion.get('priority', 'MEDIUM').upper()
            priority_counts[priority] = priority_counts.get(priority, 0) + 1
        
        # Count by category
        category_counts = {}
        for suggestion in suggestions:
            category = suggestion.get('category', 'General')
            category_counts[category] = category_counts.get(category, 0) + 1
        
        return {
            "total": len(suggestions),
            "by_priority": priority_counts,
            "by_category": category_counts,
            "average_timeline": self._calculate_average_timeline(suggestions)
        }
    
    def _calculate_average_timeline(self, suggestions: List[Dict[str, str]]) -> str:
        """Calculate average timeline from suggestions"""
        timelines = []
        for suggestion in suggestions:
            timeline = suggestion.get('timeline', '2-4 weeks')
            # Extract numbers from timeline (e.g., "1-2 weeks" -> [1, 2])
            numbers = re.findall(r'\d+', timeline)
            if numbers:
                avg = sum(int(n) for n in numbers) / len(numbers)
                timelines.append(avg)
        
        if timelines:
            overall_avg = sum(timelines) / len(timelines)
            return f"{overall_avg:.0f} weeks average"
        return "2-3 weeks average"
    
    def convert_competitive_suggestions_to_strings(self, suggestions: List[Dict[str, str]]) -> List[str]:
        """Convert structured competitive suggestions to simple strings for frontend compatibility"""
        if not suggestions:
            return []
        
        converted_suggestions = []
        for suggestion in suggestions:
            if isinstance(suggestion, dict):
                # Just use the title as it's already descriptive and actionable
                title = suggestion.get('title', 'Competitive Analysis Suggestion')
                converted_suggestions.append(title)
            elif isinstance(suggestion, str):
                # Already a string, keep as is
                converted_suggestions.append(suggestion)
        
        return converted_suggestions
    
    def _generate_benchmarks(self, seo_data: Dict[str, Any], social_data: List[Dict[str, Any]], branding_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Generate performance benchmarks"""
        page_speed_scores = seo_data.get('page_speed_scores', {})
        seo_score = page_speed_scores.get('seo', 'N/A')
        overall = page_speed_scores.get('overall', 'N/A')

        branding_score = "N/A"
        if branding_data and "branding_analysis" in branding_data:
            scores = [item.get("score", 0) for item in branding_data["branding_analysis"].get("scorecard", [])]
            if scores:
                branding_score = f"{sum(scores) / len(scores):.1f}/10"

        return {
            "seo_score": seo_score,
            "page_speed":overall,
            "social_presence": len(social_data),
            "technical_health": "Good" if seo_data.get('https') and seo_data.get('title') else "Needs Improvement",
            "branding_consistency": branding_score
        }
    
    # Mock data generators for when GPT API is not available
    def _generate_mock_seo_insights(self, seo_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate mock SEO insights when GPT API is unavailable"""
        return {
            "url": seo_data.get("url"),
            "generated_at": datetime.now().isoformat(),
            "insights": {
                "summary": "Mock SEO analysis: Your website shows good fundamental SEO structure with opportunities for improvement in page speed and meta descriptions.",
                "full_analysis": "This is a mock analysis.call error"
            },
            "recommendations": [
                "Optimize page loading speed for better user experience",
                "Add meta descriptions to improve search engine visibility",
                "Implement proper image alt tags for accessibility",
                "Consider adding structured data markup"
            ],
            "priority_score": self._calculate_priority_score(seo_data),
            "improvement_areas": self._identify_improvement_areas(seo_data)
        }
    def _generate_mock_seo_insights_api(self, seo_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate mock SEO insights when GPT API is unavailable"""
        return {
            "url": seo_data.get("url"),
            "generated_at": datetime.now().isoformat(),
            "insights": {
                "summary": "Mock SEO analysis: Your website shows good fundamental SEO structure with opportunities for improvement in page speed and meta descriptions.",
                "full_analysis": "This is a mock analysis. Connect Azure OpenAI API for detailed insights."
            },
            "recommendations": [
                "Optimize page loading speed for better user experience",
                "Add meta descriptions to improve search engine visibility",
                "Implement proper image alt tags for accessibility",
                "Consider adding structured data markup"
            ],
            "priority_score": self._calculate_priority_score(seo_data),
            "improvement_areas": self._identify_improvement_areas(seo_data)
        }
    def _generate_mock_social_insights(self, social_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate mock social media insights"""
        return {
            "url": social_data.get("url"),
            "platform": social_data.get("platform"),
            "generated_at": datetime.now().isoformat(),
            "insights": {
                "summary": "Mock social analysis: Profile shows potential for increased engagement through consistent posting and community interaction.",
                "full_analysis": "This is a mock analysis. Connect Azure OpenAI API for detailed insights."
            },
            "content_strategy": [
                "Post consistently 3-5 times per week",
                "Use platform-specific hashtags",
                "Engage with your community regularly",
                "Share behind-the-scenes content"
            ],
            "engagement_opportunities": self._identify_engagement_opportunities(social_data),
            "competitive_analysis": self._generate_mock_competitive_suggestions(social_data)
        }
    
    def _generate_mock_comprehensive_insights(self, branding_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Generate mock comprehensive insights"""
        summary = "Your digital presence shows strong potential with opportunities for growth through improved SEO optimization and enhanced social media engagement."
        if branding_data:
            summary += " Branding is a key area for improvement."

        return {
            "executive_summary": summary,
            "key_findings": [
                "Website has solid technical foundation but needs speed optimization",
                "Social media presence exists but could benefit from more consistent posting",
                "Brand messaging is consistent across platforms",
                "There's untapped potential for cross-platform content promotion"
            ],
            "strategic_recommendations": [
                "Implement comprehensive SEO optimization strategy",
                "Develop content calendar for social media consistency",
                "Create integrated marketing campaigns across platforms",
                "Focus on community building and engagement"
            ],
            "priority_actions": [
                "Fix technical SEO issues immediately",
                "Optimize page loading speed",
                "Create weekly content posting schedule",
                "Set up social media monitoring and analytics"
            ],
            "next_steps": [
                "Conduct competitor analysis",
                "Set up tracking and measurement systems",
                "Plan quarterly marketing campaigns",
                "Review and optimize monthly performance"
            ]
        }
    
    def _generate_mock_comprehensive_report(self, seo_data: Dict[str, Any], social_data: List[Dict[str, Any]], branding_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Generate mock comprehensive report"""
        insights = self._generate_mock_comprehensive_insights(branding_data)
        return {
            "generated_at": datetime.now().isoformat(),
            "website_url": seo_data.get("url"),
            "social_profiles_analyzed": len(social_data),
            **insights,
            "performance_benchmarks": self._generate_benchmarks(seo_data, social_data, branding_data),
        }

    async def generate_branding_insights(self, screenshots: List[Dict[str, Any]], branding_profile: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Generate AI-powered branding insights from screenshots.
        
        Args:
            screenshots: A list of dictionaries, where each dictionary contains a URL and a base64-encoded screenshot.
            branding_profile: Optional company branding profile with logo and colors for comparison.
            
        Returns:
            A dictionary containing the branding analysis.
        """
        if not self.api_key:
            return self._generate_mock_branding_insights()

        # Prepare prompt with caching optimization
        static_template, variable_data = self._create_branding_analysis_prompt(branding_profile, return_split=True)
        
        try:
            # Prepare content with split prompts and images for Claude
            # Static template (cached) comes first, then variable data, then images
            content = [
                {
                    "type": "text", 
                    "text": static_template,
                    "cache_control": {"type": "ephemeral"}  # Cache the static template
                }
            ]
            
            # Add variable data if present (not cached)
            if variable_data:
                content.append({"type": "text", "text": variable_data})
            
            # Add images (not cached)
            for item in screenshots:
                image_format = item.get("format", "png")
                media_type = f"image/{image_format}"
                content.append({
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": media_type,
                        "data": item["screenshot"]
                    }
                })

            # Route through token monitor with cache control for static template
            # Note: For multi-part content, we cache the first text block (static_template)
            messages = [
                {
                    "role": "system", 
                    "content": "You are an expert in branding and visual design. Analyze the provided screenshots and provide comprehensive brand audit insights.",
                    "cache_control": {"type": "ephemeral"}
                },
                {
                    "role": "user",
                    "content": content
                }
            ]
            
            # For the first text block in content, we need to mark it for caching
            # Since content is a list, we'll handle caching at the message level
            # The static template is the first text block, so it will be cached
            tm_result = await token_monitor.track_openai_call(
                operation="branding_analysis",
                model=self.model_name,
                messages=messages,
                max_tokens=5000,
                experiment_name="branding_analysis",
                client=self.client
            )

            insights = self._parse_branding_insights(tm_result["response"])
            # Add token_usage to insights if it's a dict
            if isinstance(insights, dict):
                insights["token_usage"] = tm_result.get("token_usage", {})
            return insights

        except Exception as e:
            print(f"Azure OpenAI API error during branding analysis: {str(e)}")
            return self._generate_mock_branding_insights()

    async def generate_competitor_branding_insights(self, screenshots: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Generate AI-powered competitor branding insights from screenshots.
        
        Args:
            screenshots: A list of dictionaries, where each dictionary contains a URL and a base64-encoded screenshot.
            
        Returns:
            A dictionary containing the competitor branding analysis.
        """
        if not self.api_key:
            return self._generate_mock_branding_insights()

        # Prepare prompt with caching optimization
        static_template, variable_data = self._create_competitor_branding_analysis_prompt(return_split=True)
        
        try:
            # Prepare content with split prompts and images
            content = [
                {
                    "type": "text", 
                    "text": static_template,
                    "cache_control": {"type": "ephemeral"}  # Cache the static template
                }
            ]
            
            # Add variable data if present (not cached)
            if variable_data:
                content.append({"type": "text", "text": variable_data})
            
            # Add images (not cached)
            for item in screenshots:
                image_format = item.get("format", "png")
                media_type = f"image/{image_format}"
                content.append({
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": media_type,
                        "data": item["screenshot"]
                    }
                })

            messages = [
                {
                    "role": "system", 
                    "content": "You are Transformellica's Senior Brand Strategy & Competitive Positioning Consultant. You specialize in brand perception analysis, visual identity consistency, messaging clarity, and emotional positioning across digital touchpoints.",
                    "cache_control": {"type": "ephemeral"}
                },
                {
                    "role": "user",
                    "content": content
                }
            ]
            
            tm_result = await token_monitor.track_openai_call(
                operation="competitor_branding_analysis",
                model=self.model_name,
                messages=messages,
                max_tokens=5000,
                experiment_name="competitor_branding_analysis",
                client=self.client
            )

            insights = self._parse_branding_insights(tm_result["response"])
            # Add token_usage to insights if it's a dict
            if isinstance(insights, dict):
                insights["token_usage"] = tm_result.get("token_usage", {})
            return insights

        except Exception as e:
            print(f"Azure OpenAI API error during competitor branding analysis: {str(e)}")
            return self._generate_mock_branding_insights()

    def _create_branding_analysis_prompt(self, branding_profile: Optional[Dict[str, Any]] = None, return_split: bool = False) -> str | tuple[str, str]:
        """Creates a prompt for the branding analysis LLM using the new structured format with optional splitting for caching."""
        
        # Static template (instructions, format) - this can be cached
        static_template = """You are Transformellica's Senior Brand Identity and Visual Design Consultant. You specialize in evaluating digital brand presence across websites and social media using evidence-based design, UX, and marketing principles. Your goal is to deliver clear, actionable, and data-informed brand audit insights that help businesses improve consistency, clarity, and trust.

    You will be analyzing brand data to produce a structured brand audit in JSON format. Your task is to analyze the provided screenshots, visual captures, and associated data from the company's online presence. Base your analysis strictly on the visual evidence and text provided in the brand data.

    You must produce a JSON audit with the following exact structure and sections:

    **executive_summary** – A concise overview of overall brand health and strategic direction

    **overall_brand_impression** containing:
    - strengths – Bullet list of positive elements (clarity, tone, design unity)
    - room_for_improvement – Bullet list of issues (inconsistency, low contrast, weak identity)

    **messaging_and_content_style** containing:
    - content – Assessment of tone, clarity, and alignment with target audience
    - recommendations – 2-4 clear, actionable steps to refine messaging

    **visual_branding_elements** containing:
    - color_palette with:
    - analysis – Description of color use and brand emotion conveyed
    - recommendations – Specific improvements for palette balance and accessibility
    - typography with:
    - analysis – Font choices, hierarchy effectiveness, and readability assessment
    - recommendations – Suggestions for better hierarchy or font pairing

    **highlights_and_stories** (include only if social media data is present) containing:
    - analysis – Assessment of icon and label clarity
    - recommendations – Specific optimization ideas

    **grid_strategy** (include only if social media data is present) containing:
    - analysis – Evaluation of layout coherence and storytelling flow
    - recommendations – Specific layout or rhythm improvements

    **scorecard** – Array of objects, each containing "area" and "score" keys, where score is out of 10

    ## Context and Requirements

    Your analysis serves small to mid-size companies and agencies requiring professional brand audits to guide redesigns or consistency improvements. All recommendations must be:
    - Specific and realistic
    - Immediately applicable without major rebranding
    - Consider accessibility, clarity, emotional tone, and cultural relevance

    When analyzing, evaluate based on established design principles from authoritative sources like Nielsen Norman Group, W3C Accessibility Guidelines (WCAG 2.2), Google Material Design, and major brand style-guide repositories.

    ## Professional Standards

    Act as a senior brand consultant combining creative judgment with business reasoning. Use clear, professional language that designers, marketers, and executives can understand. Avoid subjective adjectives like "beautiful" or "modern" unless supported by concrete design principles. Each observation must link to a concrete impact on perception, usability, or consistency.

    ## Critical Guidelines

    **Always:**
    - Base insights only on the provided visuals and text in the brand data
    - Use neutral, evidence-based language
    - Mention clearly when an element cannot be evaluated due to limited visual data
    - Reference established design principles when making recommendations

    **Never:**
    - Invent unseen visuals, colors, or typography details
    - Add speculative data or internal company assumptions
    - Include opinions not grounded in observed evidence
    - Output any text outside the required JSON structure

    ## Output Format

    Return your response as a valid JSON object only. Do not include any commentary, explanations, or text outside the JSON structure. The JSON must match the exact structure specified above.

    Now analyze the provided screenshots and branding profile data:"""
        
        # Variable data (changes per request) - this should NOT be cached
        variable_data = ""
        if branding_profile:
            variable_data = "\n\n## OFFICIAL BRANDING PROFILE FOR COMPARISON\n\n"
            variable_data += "The company has provided their official branding profile. Compare the analyzed screenshots against these official brand standards:\n\n"
            
            if branding_profile.get('logo'):
                logo_info = branding_profile['logo']
                variable_data += f"**Official Logo:**\n"
                variable_data += f"- Filename: {logo_info.get('filename', 'Uploaded logo')}\n"
                variable_data += f"- Size: {logo_info.get('size', 'Unknown size')}\n\n"
            
            if branding_profile.get('colors'):
                colors = branding_profile['colors']
                variable_data += f"**Official Brand Colors:**\n"
                variable_data += f"- Dominant Color: {colors.get('dominant', 'Not specified')}\n"
                if colors.get('palette'):
                    variable_data += f"- Color Palette: {', '.join(colors.get('palette', []))}\n"
                variable_data += "\n"
            
            variable_data += """**Comparison Requirements:**

    When conducting your analysis, you MUST:
    1. Verify if the website/social media uses the official brand colors consistently
    2. Check if the logo appears correctly and matches the official version provided
    3. Assess whether visual elements align with the established brand identity
    4. In your recommendations, specifically address any deviations from the official branding
    5. Note any inconsistencies between the official brand profile and what's displayed in the screenshots
    6. Provide actionable steps to better align the digital presence with the official brand standards

    Base all color palette analysis on comparison with the official colors listed above. If colors in the screenshots deviate from the official palette, this should be explicitly noted in the "room_for_improvement" section and addressed in the color_palette recommendations."""
        
        if return_split:
            return (static_template, variable_data)
        
        return static_template + variable_data

    def _create_competitor_branding_analysis_prompt(self, return_split: bool = False) -> str | tuple[str, str]:
        """Creates a prompt for competitor branding analysis matching normal format."""
        
        # Use the same template as normal branding but with competitor context
        static_template = """You are Transformellica's Senior Brand Identity and Visual Design Consultant. You specialize in evaluating digital brand presence across websites and social media using evidence-based design, UX, and marketing principles. Your goal is to deliver clear, actionable, and data-informed brand audit insights that help businesses improve consistency, clarity, and trust.

    IMPORTANT: You are analyzing a COMPETITOR brand. Focus on understanding their brand strengths and weaknesses to help the user identify competitive advantages and opportunities to differentiate.

    You will be analyzing brand data to produce a structured brand audit in JSON format. Your task is to analyze the provided screenshots, visual captures, and associated data from the competitor's online presence. Base your analysis strictly on the visual evidence and text provided in the brand data.

    You must produce a JSON audit with the following exact structure and sections:

    **executive_summary** – A concise overview of overall brand health and strategic direction

    **overall_brand_impression** containing:
    - strengths – Bullet list of positive elements (clarity, tone, design unity)
    - room_for_improvement – Bullet list of issues (inconsistency, low contrast, weak identity)

    **messaging_and_content_style** containing:
    - content – Assessment of tone, clarity, and alignment with target audience
    - recommendations – 2-4 clear, actionable steps to refine messaging

    **visual_branding_elements** containing:
    - color_palette with:
    - analysis – Description of color use and brand emotion conveyed
    - recommendations – Specific improvements for palette balance and accessibility
    - typography with:
    - analysis – Font choices, hierarchy effectiveness, and readability assessment
    - recommendations – Suggestions for better hierarchy or font pairing

    **highlights_and_stories** (include only if social media data is present) containing:
    - analysis – Assessment of icon and label clarity
    - recommendations – Specific optimization ideas

    **grid_strategy** (include only if social media data is present) containing:
    - analysis – Evaluation of layout coherence and storytelling flow
    - recommendations – Specific layout or rhythm improvements

    **scorecard** – Array of objects, each containing "area" and "score" keys, where score is out of 10

    ## Context and Requirements

    Your analysis serves small to mid-size companies and agencies requiring professional brand audits to guide redesigns or consistency improvements. All recommendations must be:
    - Specific and realistic
    - Immediately applicable without major rebranding
    - Consider accessibility, clarity, emotional tone, and cultural relevance

    When analyzing, evaluate based on established design principles from authoritative sources like Nielsen Norman Group, W3C Accessibility Guidelines (WCAG 2.2), Google Material Design, and major brand style-guide repositories.

    ## Professional Standards

    Act as a senior brand consultant combining creative judgment with business reasoning. Use clear, professional language that designers, marketers, and executives can understand. Avoid subjective adjectives like "beautiful" or "modern" unless supported by concrete design principles. Each observation must link to a concrete impact on perception, usability, or consistency.

    ## Critical Guidelines

    **Always:**
    - Base insights only on the provided visuals and text in the brand data
    - Use neutral, evidence-based language
    - Mention clearly when an element cannot be evaluated due to limited visual data
    - Reference established design principles when making recommendations
    - Focus on competitive positioning and differentiation opportunities

    **Never:**
    - Invent unseen visuals, colors, or typography details
    - Add speculative data or internal company assumptions
    - Include opinions not grounded in observed evidence
    - Output any text outside the required JSON structure

    ## Output Format

    Return your response as a valid JSON object only. Do not include any commentary, explanations, or text outside the JSON structure. The JSON must match the exact structure specified above.

    Now analyze the provided competitor screenshots and branding data:"""
        
        # Variable data (changes per request) - this should NOT be cached
        variable_data = """
        
        NOTE: This is a COMPETITOR brand analysis. Focus on identifying their brand strengths and weaknesses to help understand competitive positioning and opportunities for differentiation.
        """
        
        if return_split:
            return (static_template, variable_data)
        
        return static_template + variable_data

    def _generate_mock_branding_insights(self) -> Dict[str, Any]:
        """
        Generates mock data for branding analysis, structured like the user's example.
        """
        return {
            "executive_summary": "This is a mock executive summary for the brand audit of Seayou Camp. The analysis reveals a friendly and adventure-oriented brand identity, but there are significant inconsistencies in visual branding and content strategy that need to be addressed.",
            "overall_brand_impression": {
                "strengths": [
                    "Friendly, family-oriented logo & tone",
                    "Real moments, community & adventure are well-represented"
                ],
                "room_for_improvement": [
                    "Lack of cohesive color, typography & layout",
                    "Fluctuating visual tone & style across posts",
                    "No clear brand guidelines seem to be followed"
                ]
            },
            "messaging_and_content_style": {
                "content": "The messaging is generally positive and family-friendly, but lacks a consistent tone of voice. There's an opportunity to introduce thematic series to structure content.",
                "recommendations": [
                    "Develop a consistent brand voice (e.g., adventurous, educational, friendly).",
                    "Introduce thematic content series (e.g., 'Tip Tuesday', 'Family Fridays').",
                    "For Arabic typography, ensure text is legible and consistently styled, using text blocks or overlays where necessary."
                ]
            },
            "visual_branding_elements": {
                "color_palette": {
                    "analysis": "Too many uncoordinated colors are used. A clear brand color system is missing.",
                    "recommendations": [
                        "Create a brand color system with 3-5 main colors and 2 accent colors.",
                        "Apply a visual rhythm (e.g., photo, graphic, reel pattern) for consistent post framing."
                    ]
                },
                "typography": {
                    "analysis": "Inconsistent fonts, sizes, and readability across posts.",
                    "recommendations": [
                        "Choose 1-2 primary fonts and standardize hierarchy (headings, body text) across all posts.",
                        "Design branded reel cover templates to use every time for a cohesive look."
                    ]
                }
            },
            "highlights_and_stories": {
                "analysis": "Good use of icons, but they are not consistently branded.",
                "recommendations": [
                    "Use branded designs with descriptive labels for all highlights.",
                    "Rename highlights clearly (e.g., 'Booking' to 'Activities')."
                ]
            },
            "grid_strategy": {
                "analysis": "The feed lacks a clear structure, with a random mix of reels, posts, and graphics.",
                "recommendations": [
                    "Use branded design templates for a more structured and visually appealing feed.",
                    "Plan the grid layout to create a better flow and visual narrative."
                ]
            },
            "scorecard": [
                {"area": "Visual Consistency", "score": 5},
                {"area": "Brand Identity Clarity", "score": 6},
                {"area": "Content Strategy", "score": 7},
                {"area": "Reel Presentation", "score": 5},
                {"area": "User Experience (UX)", "score": 6}
            ]
        }

    def _parse_branding_insights(self, response: str) -> Dict[str, Any]:
        """
        Parses the JSON response from the branding analysis LLM.
        """
        try:
            # The response might be wrapped in markdown JSON
            cleaned_response = response.strip().replace("```json", "").replace("```", "")
            return json.loads(cleaned_response)
        except json.JSONDecodeError:
            print("Error: Failed to decode JSON from branding analysis response.")
            # Fallback to returning the raw text in a structured way
            return {"executive_summary": "Could not parse the analysis.", "raw_response": response}

    async def generate_sentiment_insights(self, sentiment_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate AI-powered insights for sentiment analysis
        
        Args:
            sentiment_data: Dictionary containing sentiment analysis data and summary
            
        Returns:
            Dictionary with AI insights for sentiment analysis
        """
        if not self.api_key:
            return self._generate_mock_sentiment_insights(sentiment_data)
        
        # Prepare prompt with caching optimization
        static_template, variable_data = self._create_sentiment_analysis_prompt(sentiment_data, return_split=True)
        
        try:
            # Call Azure OpenAI API
            result = await self._call_ai_api(
                prompt="",  # Not used when static_template and variable_data are provided
                max_tokens=5000,
                operation="sentiment_analysis",
                static_template=static_template,
                variable_data=variable_data
            )
            
            response = result.get("response", "") if isinstance(result, dict) else result
            token_usage = result.get("token_usage", {}) if isinstance(result, dict) else {}
            
            return {
                "generated_at": datetime.now().isoformat(),
                "insights": self._parse_sentiment_insights(response),
                "recommendations": self._extract_sentiment_recommendations(response),
                "action_items": self._extract_sentiment_action_items(response),
                "token_usage": token_usage
            }
            
        except Exception as e:
            print(f"Azure OpenAI API error: {str(e)}")
            return self._generate_mock_sentiment_insights(sentiment_data)

    def _create_sentiment_analysis_prompt(self, sentiment_data: Dict[str, Any], return_split: bool = False) -> str | tuple[str, str]:
        """Create prompt for sentiment analysis insights using the new business-focused format with optional splitting for caching"""
        
        summary = sentiment_data.get("summary", {}) or {}
        sample_reviews = sentiment_data.get("sample_reviews", []) or []
        competitor_info = sentiment_data.get("competitor", {}) or {}
        sentiment_distribution = summary.get("sentiment_percentages", {}) or {}
        avg_star_rating = summary.get("average_star_rating", 0) or 0
        total_reviews = summary.get("total_reviews", 0) or len(sample_reviews) or 0
        avg_polarity = summary.get("average_polarity", 0) or 0
        avg_subjectivity = summary.get("average_subjectivity", 0) or 0
        
        # Extract competitor information (with fallbacks for backward compatibility)
        competitor_name = competitor_info.get("name") if competitor_info else None
        if not competitor_name:
            # Try to extract from industry/context if available, otherwise use generic
            competitor_name = sentiment_data.get("industry", sentiment_data.get("competitor_name", "Competitor"))
        
        competitor_rating = (competitor_info.get("rating") or 0) if competitor_info else avg_star_rating
        competitor_review_count = (competitor_info.get("review_count") or total_reviews) if competitor_info else total_reviews
        
        # Format sample reviews for the prompt
        reviews_text = ""
        if sample_reviews:
            for i, review in enumerate(sample_reviews[:10]):
                rating = review.get('Star Rating', review.get('rating', 'N/A'))
                sentiment = review.get('Sentiment', review.get('sentiment', 'N/A'))
                text = review.get('Review Text', review.get('text', review.get('review_text', 'N/A')))
                # Truncate long reviews
                if isinstance(text, str) and len(text) > 200:
                    text = text[:200] + "..."
                reviews_text += f"\n  - Rating: {rating}/5 | Sentiment: {sentiment} | Text: {text}"
        else:
            reviews_text = "\n  - No sample reviews provided"
        
        # Static template (instructions, format) - this can be cached
        static_template = f"""
        You are Transformellica's **Senior Business Insights & Sentiment Intelligence Consultant (2025)**.
        You specialize in:
        • Multilingual sentiment analysis  
        • Competitor intelligence  
        • Industry detection  
        • Customer-experience auditing  
        • Operational + marketing impact forecasting  
        • Turning unstructured customer voice into actionable strategy  

        Your audience:
        Marketing Directors, Brand Strategists, Growth Leaders, and Founders who expect *executive-grade insights*.

        -------------------------------------------
        YOUR CORE RESPONSIBILITIES
        -------------------------------------------

        When analyzing the dataset, your job is to:

        1. **Automatically detect the industry**  
        Use review language, keywords, service attributes, product hints, or context to infer whether the business is:
        - Tourism / hospitality  
        - Restaurants / food  
        - Clinics / healthcare  
        - E-commerce  
        - SaaS / apps  
        - Education / coaching  
        - Real estate  
        - Automotive  
        - Beauty / wellness  
        - B2B services / agencies  
        - Logistics / delivery  
        - Or any other domain  
        If detection is uncertain → state "Industry not clearly inferable from data."

        2. **Extract themes with evidence**  
        Identify emotional + functional drivers:
        - Service quality  
        - Speed  
        - Expertise  
        - Staff behavior  
        - Product quality  
        - Price/value  
        - Safety  
        - Trust  
        - Ease of use  
        - Pain points  

        3. **Distinguish sentiment layers**  
        - Polarity (positive/negative intensity)  
        - Subjectivity (emotional vs factual)  
        - Advocacy vs satisfaction  
        - Hidden risks (neutral 5-star reviews)  

        4. **Analyze competitor (if provided)**  
        Extract strengths/weaknesses but **never tell the user to copy features.**  
        You may use publicly verifiable, surface-level information (G2, Trustpilot, official product pages) only if needed.  
        If you use external sources → cite minimally (domain + year).

        5. **Translate insights to business impact**  
        Every recommendation must:  
        - Be actionable  
        - Tie to a business KPI (conversion, retention, NPS, referrals, CAC, churn)  
        - Be industry-relevant  
        - Avoid fluff or generalities  

        6. **Produce a structured, concise report following the REQUIRED OUTPUT TEMPLATE**  
        No extra sections.  
        No explanation of your internal reasoning.  
        No invented review content.  
        No fabricated competitor data.  

        -------------------------------------------
        REQUIRED OUTPUT TEMPLATE (DO NOT MODIFY)
        -------------------------------------------

        **SENTIMENT & COMPETITOR INSIGHT REPORT**

        ---

        ## **A. EXECUTIVE SNAPSHOT**
        - Detected industry: [industry or "Not clearly inferable"]
        - Primary objective: [1 short sentence]
        - Dataset summary: [review count, languages, average rating]

        ---

        ## **B. SENTIMENT HEALTH SCORE**
        **Score:** [score]/100  
        - Rationale: [short justification based on polarity, distribution, tone]

        ---

        ## **C. KEY SENTIMENT THEMES (Top 4)**
        - **Theme 1:** [phrase] — [evidence from reviews] — [business implication]
        - **Theme 2:** ...
        - **Theme 3:** ...
        - **Theme 4:** ...

        ---

        ## **D. TOP 5 COMPETITOR STRENGTHS**
        - {competitor_name}: [strength] — [evidence or brief citation]
        - Additional strengths:
        - [bullet]
        - [bullet]
        - [bullet]

        ---

        ## **E. TOP 5 COMPETITOR WEAKNESSES**
        - {competitor_name}: [weakness] — [evidence or citation]
        - Additional weaknesses:
        - [bullet]
        - [bullet]
        - [bullet]

        ---

        ## **F. COMPETITOR SWOT SUMMARY**
        - {competitor_name}: Strengths ✅ / Weaknesses ❌ / Opportunities ⚠ / Threats ✳

        ---

        ## **G. IMPACT ON YOUR BUSINESS (Priority Ranked)**
        1) [High-impact insight] — [why it matters] — [KPI]  
        2) [Medium-impact insight] — ...  
        3) [Low-impact insight] — ...  

        ---

        ## **H. ACTIONABLE RECOMMENDATIONS (3–6 items)**
        - [Action] — [expected outcome] — [metric]
        - [Action] — ...

        ---

        ## **I. QUICK WINS (Immediate)**
        - [Quick win] — [time required]
        - [Quick win] — ...

        ---

        ## **J. DATA LIMITATIONS**
        - [Biases, small samples, missing fields, etc.]

        ---

        ## **K. SOURCES (Only if external validation used)**
        - domain.com — [year]
        - g2.com — [year]

        ---

        ## **Summary Insight**
        [One-line highest priority takeaway]

        </report>

        -------------------------------------------
        RESTRICTIONS (MANDATORY)
        -------------------------------------------
        • NEVER fabricate review data, competitor features, fake statistics, or claims.  
        • NEVER suggest copying competitor features.  
        • ALWAYS base primary sentiment results on the provided dataset.  
        • ONLY cite external info if used, and keep citations minimal.  
        • KEEP report concise, executive-friendly, and bullet-based.  
        • NO long paragraphs.  
        • NO system/internal reasoning.  
        • NO generic “improve customer service”-type advice.

        -------------------------------------------
        Now analyze the following sentiment data:
        """
        # Extract optional user context for more targeted insights
        user_context = sentiment_data.get("user_context") or {}
        user_context_section = ""
        if any(user_context.get(k) for k in ("company_name", "business_description", "main_goal", "target_audience_country", "additional_context")):
            user_context_section = f"""
        User/Client Context (use this to tailor recommendations):
        - Client Company: {user_context.get('company_name') or 'Not provided'}
        - Business Description: {user_context.get('business_description') or 'Not provided'}
        - Analysis Goal: {user_context.get('main_goal') or 'Not provided'}
        - Target Audience Country: {user_context.get('target_audience_country') or 'Not provided'}
        - Additional Context: {user_context.get('additional_context') or 'Not provided'}
"""

        # Variable data (changes per request) - this should NOT be cached
        sentiment_data_xml = f"""
        <sentiment_data>
        Competitor Name: {competitor_name}
        Competitor Rating: {competitor_rating}/5
        Total Reviews Analyzed: {total_reviews}
        Average Star Rating: {avg_star_rating:.2f}/5
        Sentiment Distribution:
        - Positive: {sentiment_distribution.get('Positive', 0):.1f}%
        - Negative: {sentiment_distribution.get('Negative', 0):.1f}%
        - Neutral: {sentiment_distribution.get('Neutral', 0):.1f}%
        Average Sentiment Polarity: {avg_polarity:.3f}
        Average Subjectivity: {avg_subjectivity:.3f}
        {user_context_section}
        Sample Reviews:
        {reviews_text}
        </sentiment_data>
        """
        
        if return_split:
            return (static_template, sentiment_data_xml)

        return f"{static_template}\n{sentiment_data_xml}"

    def _parse_sentiment_insights(self, response: str) -> Dict[str, Any]:
        """Parse GPT response for sentiment insights"""
        return {
            "summary": response[:300] + "..." if len(response) > 300 else response,
            "full_analysis": response
        }

    def _extract_sentiment_recommendations(self, response: str) -> List[str]:
        """Extract recommendations from sentiment analysis response"""
        recommendations = []
        lines = response.split('\n')
        
        for line in lines:
            line = line.strip()
            if line.startswith(('•', '-', '*')) or line[0:2].isdigit():
                recommendations.append(line)
        
        return recommendations[:8]  # Limit to top 8

    def _extract_sentiment_action_items(self, response: str) -> List[str]:
        """Extract action items from sentiment analysis response"""
        action_items = []
        lines = response.split('\n')
        
        for line in lines:
            line = line.strip()
            if any(keyword in line.lower() for keyword in ['action', 'implement', 'address', 'fix', 'improve']):
                action_items.append(line)
        
        return action_items[:5]  # Limit to top 5

    def _generate_mock_sentiment_insights(self, sentiment_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate mock sentiment insights when GPT API is unavailable"""
        summary = sentiment_data.get("summary", {})
        sentiment_distribution = summary.get("sentiment_percentages", {})
        
        return {
            "generated_at": datetime.now().isoformat(),
            "insights": {
                "summary": f"Mock sentiment analysis: Customer sentiment shows {sentiment_distribution.get('Positive', 0):.1f}% positive feedback with opportunities for improvement in customer experience.",
                "full_analysis": "This is a mock analysis. Connect Azure OpenAI API for detailed sentiment insights."
            },
            "recommendations": [
                "Monitor customer feedback regularly to identify trends",
                "Address negative reviews promptly and professionally",
                "Leverage positive reviews for marketing and testimonials",
                "Implement customer satisfaction surveys",
                "Train staff on customer service best practices"
            ],
            "action_items": [
                "Set up automated review monitoring system",
                "Create response templates for common complaints",
                "Develop customer feedback collection process",
                "Implement customer service training program"
            ]
        }