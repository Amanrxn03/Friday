"""Central Application Orchestrator for Project FRIDAY.

Coordinates conversation turns, executes fast deterministic multilingual intents (<5ms),
routes complex reasoning to AI providers, and handles sentence-streaming voice synthesis.
"""

import uuid
import logging
import threading
from typing import Dict, Any, List, Optional

from app.core.event_bus import event_bus, Events
from app.ai.provider_manager import provider_manager, AIResponse
from app.core.tool_registry import tool_registry
from app.core.execution_manager import execution_manager
from app.core.task_planner import task_planner
from app.voice.text_to_speech import tts_manager
from app.nlp.intent_matcher import intent_matcher, ParsedIntent
from app.nlp.language_detector import language_detector
from app.core.metrics import latency_tracker, TurnLatencyRecord
from app.core.permissions import permissions_engine

logger = logging.getLogger(__name__)


class Orchestrator:
    """Central coordinator for conversation, reasoning, tool execution, and voice output."""

    def __init__(self):
        self.conversation_history: List[Dict[str, str]] = []
        self._lock = threading.RLock()
        self._max_history = 20

        # Subscribe to user input events
        event_bus.subscribe(Events.USER_MESSAGE, self._on_user_message)

    def _on_user_message(self, data: Dict[str, Any]) -> None:
        """Handle incoming user message from text box or voice transcription."""
        text = data.get("text", "").strip()
        source = data.get("source", "text")
        latency_rec = data.get("latency_record")
        if not text:
            return

        # Process in a worker thread so the UI remains completely responsive
        threading.Thread(
            target=self.process_user_turn,
            args=(text, source, latency_rec),
            daemon=True,
            name="FridayTurnWorker",
        ).start()

    def process_user_turn(
        self,
        user_text: str,
        source: str = "text",
        turn_record: Optional[TurnLatencyRecord] = None,
    ) -> Dict[str, Any]:
        """Execute a conversational turn with fast deterministic bypass and AI reasoning."""
        logger.info("Processing user turn (%s): '%s'", source, user_text[:80])
        event_bus.publish(Events.STATE_CHANGED, "Thinking")

        # Create or continue latency tracking
        rec = turn_record or TurnLatencyRecord(turn_id=str(uuid.uuid4())[:8])
        detected_lang = language_detector.detect(user_text)
        rec.language = detected_lang

        # -------------------------------------------------------------
        # STEP 1: FAST DETERMINISTIC MULTILINGUAL INTENT BYPASS (<5ms)
        # -------------------------------------------------------------
        fast_intent: Optional[ParsedIntent] = intent_matcher.match_intent(user_text)
        if fast_intent:
            rec.fast_path_used = True
            rec.intent_type = fast_intent.tool_name

            # Special case: Stop / Cancellation Command
            if fast_intent.is_cancellation:
                tts_manager.stop_speaking()
                permissions_engine.trigger_emergency_stop("User issued cancellation command")
                reply = fast_intent.conversational_replies.get(detected_lang, "Action stopped.")
                with self._lock:
                    self.conversation_history.append({"role": "user", "content": user_text})
                    self.conversation_history.append({"role": "assistant", "content": reply})

                event_bus.publish(Events.ASSISTANT_MESSAGE, {"text": reply, "tool_results": None})
                event_bus.publish(Events.STATE_CHANGED, "Ready")
                rec.mark_first_audio_chunk()
                if source == "voice" or config.voice.enabled:
                    tts_manager.speak(reply, language=detected_lang)
                latency_tracker.record_turn(rec)
                return {"reply": reply, "fast_path": True, "tool_results": None}

            # Execute tool directly
            event_bus.publish(Events.STATE_CHANGED, "Executing")
            tool_outcome = execution_manager.execute_tool(
                fast_intent.tool_name, fast_intent.tool_args
            )
            rec.mark_tool_completion()

            reply = fast_intent.conversational_replies.get(
                detected_lang, "Action completed."
            )
            with self._lock:
                self.conversation_history.append({"role": "user", "content": user_text})
                self.conversation_history.append({"role": "assistant", "content": reply})

            tool_results = [{
                "name": fast_intent.tool_name,
                "arguments": fast_intent.tool_args,
                "outcome": tool_outcome,
            }]

            event_bus.publish(Events.ASSISTANT_MESSAGE, {"text": reply, "tool_results": tool_results})
            event_bus.publish(Events.STATE_CHANGED, "Speaking" if (source == "voice" or config.voice.enabled) else "Ready")
            rec.mark_first_audio_chunk()

            if source == "voice" or config.voice.enabled:
                tts_manager.speak(reply, language=detected_lang)

            latency_tracker.record_turn(rec)
            return {"reply": reply, "fast_path": True, "tool_results": tool_results}

        # -------------------------------------------------------------
        # STEP 2: AI PROVIDER REASONING (for multi-step/complex queries)
        # -------------------------------------------------------------
        with self._lock:
            self.conversation_history.append({"role": "user", "content": user_text})
            if len(self.conversation_history) > self._max_history:
                self.conversation_history = self.conversation_history[-self._max_history:]

            system_context = task_planner.build_system_context()
            messages = [{"role": "system", "content": system_context}] + self.conversation_history

        tools = tool_registry.get_openai_tool_schemas()
        rec.mark_first_model_token()

        ai_resp: AIResponse = provider_manager.generate(messages, tools=tools)

        if ai_resp.error:
            error_reply = f"I encountered an issue with the AI provider: {ai_resp.error}"
            event_bus.publish(Events.ASSISTANT_MESSAGE, {"text": error_reply, "error": True})
            event_bus.publish(Events.STATE_CHANGED, "Error")
            if source == "voice":
                tts_manager.speak(error_reply, language=detected_lang)
            latency_tracker.record_turn(rec)
            return {"reply": error_reply, "error": True}

        # Check for tool calls
        if ai_resp.tool_calls:
            event_bus.publish(Events.STATE_CHANGED, "Executing")
            tool_results = []
            for tc in ai_resp.tool_calls:
                exec_outcome = execution_manager.execute_tool(tc.name, tc.arguments)
                tool_results.append({
                    "name": tc.name,
                    "arguments": tc.arguments,
                    "outcome": exec_outcome,
                })
            rec.mark_tool_completion()

            waiting_approvals = [tr for tr in tool_results if tr["outcome"].get("approval_required")]
            if waiting_approvals:
                pending_msg = (
                    f"I've prepared the action '{waiting_approvals[0]['name']}'. "
                    "Because this is a high-impact operation, please review and approve it in the interface."
                )
                with self._lock:
                    self.conversation_history.append({"role": "assistant", "content": pending_msg})
                event_bus.publish(Events.ASSISTANT_MESSAGE, {"text": pending_msg, "tool_results": tool_results})
                event_bus.publish(Events.STATE_CHANGED, "Waiting for Approval")
                if source == "voice":
                    tts_manager.speak("I need your approval before executing this action.", language=detected_lang)
                latency_tracker.record_turn(rec)
                return {"reply": pending_msg, "tool_results": tool_results}

            synthesis_prompt = [
                {"role": "system", "content": system_context},
                {"role": "user", "content": user_text},
                {"role": "assistant", "content": f"Executed tools: {tool_results}. Synthesize a concise, verified response in {detected_lang}."},
            ]
            final_resp = provider_manager.generate(synthesis_prompt)
            assistant_reply = final_resp.content or "Action completed and verified successfully."
        else:
            assistant_reply = ai_resp.content

        with self._lock:
            self.conversation_history.append({"role": "assistant", "content": assistant_reply})

        event_bus.publish(Events.ASSISTANT_MESSAGE, {"text": assistant_reply, "tool_results": None})
        event_bus.publish(Events.STATE_CHANGED, "Speaking" if (source == "voice" or config.voice.enabled) else "Ready")
        rec.mark_first_audio_chunk()

        if source == "voice" or config.voice.enabled:
            tts_manager.speak(assistant_reply, language=detected_lang)

        latency_tracker.record_turn(rec)
        return {"reply": assistant_reply, "error": False, "fast_path": False}


# Global orchestrator singleton
orchestrator = Orchestrator()
