"""
Brand Kit Orchestrator — Parallel AI generation with progressive results.
"""
import asyncio
import json
import time
import logging
import uuid
from datetime import datetime, timezone

from services.brand_kit.prompts import SYSTEM_PROMPT, PROMPTS, MODE_ARTIFACTS, brief_context

logger = logging.getLogger("creatorstudio.brand_kit")


class BrandKitOrchestrator:
    def __init__(self, db, llm_key: str):
        self.db = db
        self.llm_key = llm_key

    async def create_job(self, user_id: str, brief: dict, mode: str) -> str:
        job_id = str(uuid.uuid4())
        artifacts = MODE_ARTIFACTS.get(mode, MODE_ARTIFACTS["fast"])
        artifact_states = {a: {"status": "QUEUED", "data": None} for a in artifacts}

        job = {
            "id": job_id,
            "userId": user_id,
            "type": "brand_kit",
            "status": "CREATED",
            "mode": mode,
            "brief": brief,
            "artifacts": artifact_states,
            "progress": 0,
            "current_stage": "ENRICHING",
            "total_artifacts": len(artifacts),
            "completed_artifacts": 0,
            "credits_charged": 10 if mode == "fast" else 25,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        await self.db.brand_kit_jobs.insert_one(job)
        return job_id

    async def run_generation(self, job_id: str):
        """Run all artifact generation in parallel with progressive DB updates."""
        job = await self.db.brand_kit_jobs.find_one({"id": job_id}, {"_id": 0})
        if not job:
            return

        brief = job["brief"]
        mode = job["mode"]
        artifacts_to_gen = MODE_ARTIFACTS.get(mode, MODE_ARTIFACTS["fast"])
        context = brief_context(brief)

        await self.db.brand_kit_jobs.update_one(
            {"id": job_id},
            {"$set": {"status": "GENERATING", "current_stage": "TEXT_GENERATING",
                      "updated_at": datetime.now(timezone.utc).isoformat()}}
        )

        # Run all artifact generators in parallel
        tasks = [self._generate_artifact(job_id, art_type, context) for art_type in artifacts_to_gen]
        await asyncio.gather(*tasks, return_exceptions=True)

        # Final status check
        updated_job = await self.db.brand_kit_jobs.find_one({"id": job_id}, {"_id": 0})
        completed = sum(1 for a in updated_job["artifacts"].values() if a["status"] in ("READY", "FALLBACK_READY"))
        total = updated_job["total_artifacts"]

        if completed == total:
            final_status = "READY"
            stage = "COMPLETE"
        elif completed > 0:
            final_status = "PARTIAL_READY"
            stage = "PACKAGING"
        else:
            final_status = "FAILED"
            stage = "FAILED"

        await self.db.brand_kit_jobs.update_one(
            {"id": job_id},
            {"$set": {
                "status": final_status,
                "current_stage": stage,
                "progress": 100,
                "completed_artifacts": completed,
                "completed_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }}
        )

        logger.info(f"[BRAND_KIT] job={job_id} status={final_status} completed={completed}/{total}")

    async def _generate_artifact(self, job_id: str, artifact_type: str, context: str):
        """Generate a single artifact via LLM and persist result."""
        start = time.time()
        prompt_cfg = PROMPTS.get(artifact_type)
        if not prompt_cfg:
            return

        # Mark as processing
        await self.db.brand_kit_jobs.update_one(
            {"id": job_id},
            {"$set": {f"artifacts.{artifact_type}.status": "PROCESSING"}}
        )

        try:
            from emergentintegrations.llm.chat import LlmChat, UserMessage
            import os

            chat = LlmChat(
                api_key=self.llm_key,
                session_id=f"brand-kit-{job_id}-{artifact_type}",
                system_message=SYSTEM_PROMPT,
            )
            chat.with_model("openai", "gpt-4o-mini")

            prompt_text = prompt_cfg["template"].format(context=context)
            response = await asyncio.wait_for(
                chat.send_message(UserMessage(text=prompt_text)),
                timeout=30,
            )

            # Parse JSON response
            data = self._parse_json(response)
            if not data:
                raise ValueError("LLM returned non-JSON response")

            latency_ms = round((time.time() - start) * 1000)

            # Update artifact in DB
            job = await self.db.brand_kit_jobs.find_one({"id": job_id}, {"_id": 0, "completed_artifacts": 1, "total_artifacts": 1})
            completed = (job.get("completed_artifacts", 0) or 0) + 1
            progress = min(95, round((completed / max(job.get("total_artifacts", 1), 1)) * 95))

            await self.db.brand_kit_jobs.update_one(
                {"id": job_id},
                {"$set": {
                    f"artifacts.{artifact_type}.status": "READY",
                    f"artifacts.{artifact_type}.data": data,
                    f"artifacts.{artifact_type}.latency_ms": latency_ms,
                    "completed_artifacts": completed,
                    "progress": progress,
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                }}
            )

            logger.info(f"[BRAND_KIT] artifact={artifact_type} job={job_id} status=READY latency={latency_ms}ms")

        except Exception as e:
            latency_ms = round((time.time() - start) * 1000)
            logger.error(f"[BRAND_KIT] artifact={artifact_type} job={job_id} FAILED: {e}")

            # Try fallback
            fallback_data = self._get_fallback(artifact_type, context)
            if fallback_data:
                job = await self.db.brand_kit_jobs.find_one({"id": job_id}, {"_id": 0, "completed_artifacts": 1, "total_artifacts": 1})
                completed = (job.get("completed_artifacts", 0) or 0) + 1
                progress = min(95, round((completed / max(job.get("total_artifacts", 1), 1)) * 95))

                await self.db.brand_kit_jobs.update_one(
                    {"id": job_id},
                    {"$set": {
                        f"artifacts.{artifact_type}.status": "FALLBACK_READY",
                        f"artifacts.{artifact_type}.data": fallback_data,
                        f"artifacts.{artifact_type}.latency_ms": latency_ms,
                        f"artifacts.{artifact_type}.error": str(e)[:200],
                        "completed_artifacts": completed,
                        "progress": progress,
                        "updated_at": datetime.now(timezone.utc).isoformat(),
                    }}
                )
            else:
                await self.db.brand_kit_jobs.update_one(
                    {"id": job_id},
                    {"$set": {
                        f"artifacts.{artifact_type}.status": "FAILED",
                        f"artifacts.{artifact_type}.error": str(e)[:200],
                        f"artifacts.{artifact_type}.latency_ms": latency_ms,
                        "updated_at": datetime.now(timezone.utc).isoformat(),
                    }}
                )

    def _parse_json(self, text: str) -> dict:
        """Extract JSON from LLM response, handling markdown fences."""
        text = text.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            text = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            # Try to find JSON object in text
            start = text.find("{")
            end = text.rfind("}") + 1
            if start >= 0 and end > start:
                try:
                    return json.loads(text[start:end])
                except json.JSONDecodeError:
                    return None
        return None

    def _get_fallback(self, artifact_type: str, context: str) -> dict:
        """Deterministic fallback when AI fails — always return something useful."""
        biz = "Your Brand"
        for line in context.split("\n"):
            if line.startswith("Business: "):
                biz = line.replace("Business: ", "")
                break

        fallbacks = {
            "short_brand_story": {"short_brand_story": f"{biz} was founded to make a difference. With a clear mission and passionate team, we're building something that matters — for our customers, our community, and the future we believe in."},
            "long_brand_story": {"long_brand_story": f"The story of {biz} begins with a simple observation: the world needed something better. What started as an idea has grown into a mission-driven organization dedicated to creating real impact. Every day, our team works to deliver excellence, guided by the values that sparked our founding. We believe in transparency, innovation, and putting people first. As we grow, we remain committed to the principles that got us here — and the vision that keeps us moving forward."},
            "mission_vision_values": {"mission": "To empower our customers through innovative solutions.", "vision": f"A world where {biz} sets the standard for excellence.", "values": ["Innovation", "Integrity", "Impact", "Inclusivity", "Excellence"]},
            "taglines": {"taglines": [{"text": f"{biz}: Built Different", "style": "bold"}, {"text": "Excellence, Redefined", "style": "premium"}, {"text": "Your Future, Our Mission", "style": "emotional"}, {"text": "Simply Better", "style": "minimal"}, {"text": f"Welcome to {biz}", "style": "friendly"}]},
            "elevator_pitch": {"one_line": f"{biz} delivers innovative solutions for modern challenges.", "thirty_sec": f"{biz} is on a mission to transform how people experience our industry. We combine cutting-edge thinking with practical execution to deliver real results.", "sixty_sec": f"At {biz}, we saw a gap between what exists and what's possible. Our team brings together deep expertise and fresh thinking to create solutions that actually work. We're not just building a product — we're building a movement."},
            "website_hero": {"headline": f"Welcome to {biz}", "subheadline": "Innovation meets execution. Results you can count on.", "cta": "Get Started", "trust_bullets": ["Trusted by leading organizations", "Built for scale", "Dedicated support"]},
            "social_ad_copy": {"instagram": [f"Big things are happening at {biz}. Stay tuned."], "facebook": [f"Discover why people trust {biz}."], "google_ads": [f"{biz} - Innovation That Delivers"], "cta_lines": ["Learn More", "Get Started Today", "See the Difference"]},
            "color_palettes": {"palettes": [{"name": "Modern Professional", "primary": "#1D4ED8", "secondary": "#0F172A", "accent": "#F59E0B", "background": "#F8FAFC", "meaning": "Trust and innovation"}, {"name": "Bold Impact", "primary": "#DC2626", "secondary": "#1E1E1E", "accent": "#FBBF24", "background": "#FFFFFF", "meaning": "Energy and confidence"}, {"name": "Premium Calm", "primary": "#059669", "secondary": "#1E293B", "accent": "#8B5CF6", "background": "#F0FDF4", "meaning": "Growth and sophistication"}]},
            "typography": {"pairings": [{"name": "Modern Authority", "heading": "Bold geometric sans-serif (like Montserrat)", "body": "Clean humanist sans-serif (like Open Sans)", "personality": "Professional, trustworthy", "use_case": "Corporate websites, pitch decks"}, {"name": "Creative Edge", "heading": "Condensed display sans (like Oswald)", "body": "Rounded friendly sans (like Nunito)", "personality": "Dynamic, approachable", "use_case": "Startups, creative brands"}, {"name": "Timeless Elegance", "heading": "Serif with character (like Playfair Display)", "body": "Minimal sans-serif (like Lato)", "personality": "Sophisticated, premium", "use_case": "Luxury brands, editorial"}]},
            "logo_concepts": {"concepts": [{"name": "Lettermark", "symbol": f"Stylized initials of {biz}", "layout": "Centered, compact", "color_logic": "Primary brand color", "feel": "Professional, clean", "rationale": "Strong brand recognition"}, {"name": "Abstract Mark", "symbol": "Geometric shape representing growth", "layout": "Symbol + wordmark", "color_logic": "Gradient accent", "feel": "Modern, innovative", "rationale": "Memorable and versatile"}, {"name": "Wordmark", "symbol": "Custom typography", "layout": "Horizontal", "color_logic": "Monochrome with accent", "feel": "Elegant, confident", "rationale": "Name-first brand building"}]},
        }
        return fallbacks.get(artifact_type)
