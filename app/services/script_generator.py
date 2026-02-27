"""
Script generator service for audio briefing generation.

Uses GPT-4o to generate podcast-style narration scripts from classified articles,
with role-specific tone, priority-ordered content, and source attribution.
"""
from datetime import datetime
from typing import List, Dict

import structlog
from openai import AzureOpenAI, OpenAI, APITimeoutError, APIConnectionError
from tenacity import (
    retry,
    stop_after_attempt,
    wait_random_exponential,
    retry_if_exception_type,
)

from app.config import get_settings


logger = structlog.get_logger(__name__)


class ScriptGenerator:
    """
    Service for generating podcast-style narration scripts from classified articles.

    Uses GPT-4o to create 300-540 word scripts with branded intro/outro,
    priority-ordered content, and role-specific tone.
    """

    def __init__(self):
        """
        Initialize script generator with Azure OpenAI client.

        Follows the same pattern as reporter.py for client initialization.
        """
        settings = get_settings()

        # Azure OpenAI client (same pattern as reporter.py)
        if settings.is_azure_openai_configured():
            endpoint = settings.azure_openai_endpoint
            if '/deployments/' in endpoint:
                # Corporate proxy — endpoint is the full URL, use standard client
                base_url = endpoint.rstrip('/')
                if base_url.endswith('/chat/completions'):
                    base_url = base_url[:-len('/chat/completions')]
                self.client = OpenAI(base_url=base_url, api_key=settings.azure_openai_api_key)
            else:
                # Standard Azure OpenAI endpoint
                self.client = AzureOpenAI(
                    azure_endpoint=endpoint,
                    api_key=settings.azure_openai_api_key,
                    api_version=settings.azure_openai_api_version
                )
            self.deployment = settings.azure_openai_deployment
        else:
            self.client = None
            self.deployment = None

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_random_exponential(multiplier=1, min=2, max=15),
        retry=retry_if_exception_type((ConnectionError, TimeoutError, APITimeoutError, APIConnectionError)),
        reraise=True
    )
    def generate_script(self, role: str, articles: List[dict], report_date: datetime) -> str:
        """
        Generate podcast-style narration script for a specific role.

        Args:
            role: Role name (Brokers, Leadership, Compliance, Underwriting)
            articles: List of classified article dictionaries (pre-filtered for role)
            report_date: Date of the report

        Returns:
            Generated script text (300-540 words)
        """
        # Check if Azure OpenAI is configured
        if self.client is None:
            logger.warning("azure_openai_not_configured_for_script_generation", role=role)
            return "Audio briefing unavailable. Azure OpenAI not configured."

        # Handle empty article list
        if not articles:
            date_str = report_date.strftime("%B %d, %Y")
            logger.info("no_articles_for_script", role=role, date=date_str)
            return self._generate_empty_script(role, date_str)

        # Generate script
        try:
            system_prompt = self._build_system_prompt(role)
            user_prompt = self._build_user_prompt(articles, report_date, role)

            logger.info(
                "generating_script",
                role=role,
                article_count=len(articles),
                date=report_date.strftime("%Y-%m-%d")
            )

            response = self.client.chat.completions.create(
                model=self.deployment,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.7,  # Moderate creativity for natural narration
                max_tokens=800    # ~540 words with safety margin
            )

            script = response.choices[0].message.content
            word_count = len(script.split())

            logger.info(
                "script_generated",
                role=role,
                article_count=len(articles),
                word_count=word_count
            )

            return script

        except Exception as e:
            logger.error(
                "script_generation_failed",
                role=role,
                article_count=len(articles),
                error=str(e)
            )
            # Return fallback on error
            date_str = report_date.strftime("%B %d, %Y")
            return self._generate_fallback_script(role, date_str, len(articles))

    def _build_system_prompt(self, role: str) -> str:
        """
        Build role-specific system prompt for podcast narrator persona.

        Args:
            role: Role name (Brokers, Leadership, Compliance, Underwriting)

        Returns:
            System prompt text
        """
        # Role-specific tone guidance
        role_tone = {
            "Brokers": "Action-oriented, market-focused, competitive intelligence. Use language that helps brokers advise clients and position against competitors.",
            "Leadership": "Strategic, big-picture, market trends and implications. Focus on business impact and strategic decisions.",
            "Compliance": "Risk-focused, regulatory emphasis, clear guidance. Explain compliance implications and regulatory requirements clearly.",
            "Underwriting": "Technical, exposure-focused, data-driven insights. Use technical insurance terminology appropriately."
        }

        tone_guidance = role_tone.get(role, "Professional, informative, and relevant to the role.")

        return f"""You are a professional intelligence briefing narrator creating audio scripts for Marsh {role}.

**Audio Character:**
- Voice: Female, authoritative, clear, confident, professional broadcast quality
- Style: Bloomberg/Reuters morning briefing - conversational but credible
- Pacing: Brisk but clear, natural speaking rhythm (150 words per minute)

**Script Structure:**
1. Branded intro: "Good morning, this is your Marsh {role} intelligence brief for [date]..."
2. Priority-ordered content:
   - Critical priority stories first
   - High priority stories second
   - Medium priority stories last
3. Content synthesis: Group related articles by theme, weave into flowing narrative (not individual article summaries)
4. Source attribution: Include source names for credibility ("Reuters reports...", "According to the Financial Times...")
5. Clean sign-off: "That's your {role} brief for today. Stay informed."

**Writing Guidelines:**
- Target 300-540 words (2-5 minute audio duration)
- Write for listening, not reading: short sentences, contractions acceptable, conversational flow
- Use natural language for ALL numbers and figures (write out "one point two million dollars", not "$1.2M")
- Avoid jargon without context; explain industry terms briefly
- Role-specific tone: {tone_guidance}

**Important:**
- This is for AUDIO narration, so write how you would SPEAK it
- Group articles by theme, don't list them individually
- Make it sound like a professional news briefing, not a list of headlines
"""

    def _build_user_prompt(self, articles: List[dict], report_date: datetime, role: str) -> str:
        """
        Build user prompt with classified articles grouped by priority.

        Args:
            articles: List of article dictionaries (keys: title, summary, source_name, priority, etc.)
            report_date: Date of the report
            role: Role name

        Returns:
            User prompt text with article data
        """
        date_str = report_date.strftime("%B %d, %Y")

        # Group articles by priority
        critical = [a for a in articles if a.get("priority") == "Critical"]
        high = [a for a in articles if a.get("priority") == "High"]
        medium = [a for a in articles if a.get("priority") == "Medium"]

        # Build prompt
        prompt = f"Create podcast-style narration script for {date_str}.\n\n"

        if critical:
            prompt += f"**CRITICAL PRIORITY** ({len(critical)} articles):\n"
            for article in critical:
                title = article.get('title', 'No title')
                source = article.get('source_name', 'Unknown source')
                summary = article.get('summary', article.get('description', 'No summary'))
                prompt += f"- {title} ({source})\n  {summary}\n\n"

        if high:
            prompt += f"**HIGH PRIORITY** ({len(high)} articles):\n"
            for article in high:
                title = article.get('title', 'No title')
                source = article.get('source_name', 'Unknown source')
                summary = article.get('summary', article.get('description', 'No summary'))
                prompt += f"- {title} ({source})\n  {summary}\n\n"

        if medium:
            prompt += f"**MEDIUM PRIORITY** ({len(medium)} articles):\n"
            for article in medium:
                title = article.get('title', 'No title')
                source = article.get('source_name', 'Unknown source')
                summary = article.get('summary', article.get('description', 'No summary'))
                prompt += f"- {title} ({source})\n  {summary}\n\n"

        prompt += f"\nGenerate a natural-sounding audio script for the {role} audience."

        return prompt

    def _generate_empty_script(self, role: str, date_str: str) -> str:
        """
        Generate script when no articles are available.

        Args:
            role: Role name
            date_str: Formatted date string

        Returns:
            Short "no articles" script
        """
        return f"Good morning, this is your Marsh {role} intelligence brief for {date_str}. There are no significant developments to report today. That's your {role} brief for today. Stay informed."

    def _generate_fallback_script(self, role: str, date_str: str, article_count: int) -> str:
        """
        Generate fallback script when script generation fails.

        Args:
            role: Role name
            date_str: Formatted date string
            article_count: Number of articles that were supposed to be processed

        Returns:
            Fallback script text
        """
        return f"Good morning, this is your Marsh {role} intelligence brief for {date_str}. We have {article_count} articles to review today, but script generation encountered a technical issue. Please check the HTML brief for full details. That's your {role} brief for today. Stay informed."
