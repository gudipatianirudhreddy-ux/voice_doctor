
import os
from datetime import datetime
from zoneinfo import ZoneInfo

from dotenv import load_dotenv
from loguru import logger

from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.frames.frames import TTSSpeakFrame
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.worker import PipelineParams, PipelineWorker

from pipecat.processors.aggregators.llm_context import LLMContext

from app.voice.tools import (
    find_doctors,
    check_doctor_availability,
    book_appointment,
    cancel_appointment,
    reschedule_appointment,
    get_appointment_for_reschedule,
)
from pipecat.processors.aggregators.llm_response_universal import (
    LLMContextAggregatorPair,
    LLMUserAggregatorParams,
)

from pipecat.runner.types import RunnerArguments
from pipecat.services.groq.llm import GroqLLMService
from pipecat.services.elevenlabs.stt import (
    ElevenLabsRealtimeSTTService,
)
from pipecat.services.elevenlabs.tts import ElevenLabsTTSService

from pipecat.transports.base_transport import TransportParams
from pipecat.transports.smallwebrtc.transport import (
    SmallWebRTCTransport,
)
from pipecat.transports.smallwebrtc.connection import (
    SmallWebRTCConnection,
)

from pipecat.workers.runner import WorkerRunner

load_dotenv()


async def run_bot(
    transport: SmallWebRTCTransport,
    runner_args: RunnerArguments,
):
    logger.info("Starting Voice Doctor bot")

    # 1. Speech-to-text
    stt = ElevenLabsRealtimeSTTService(
        api_key=os.environ["ELEVENLABS_API_KEY"],
    )

    # 2. Language model
    today_ist = datetime.now(ZoneInfo("Asia/Kolkata")).date().isoformat()
    llm = GroqLLMService(
        api_key=os.environ["GROQ_API_KEY"],
        settings=GroqLLMService.Settings(
            model=os.getenv(
                "GROQ_MODEL",
                "openai/gpt-oss-20b",
            ),
            system_instruction=(
                f"Today's date is {today_ist}; caller timezone is Asia/Kolkata (IST). "
                "Interpret relative dates like tomorrow and the 25th using this date. "
                "For availability, pass requested_date in YYYY-MM-DD format. "
                "For rescheduling, first collect the existing appointment ID and registered phone number, "
                "call get_appointment_for_reschedule to verify them and obtain the original doctor_id, "
                "then call check_doctor_availability for the requested date using that doctor_id, "
                "offer only returned slot IDs, and call reschedule_appointment only after the caller "
                "confirms the new slot. Never cancel the original appointment before rescheduling. "
                "After successful rescheduling, tell the caller the appointment ID and new date/time. "
                "You are Voice Doctor, a polite and helpful "
                "medical appointment booking voice assistant. "
                "You help callers check doctor availability, "
                "book appointments, and cancel appointments. "
                "Speak like a calm, friendly human receptionist, not like a form or checklist. "
                "Keep each spoken turn short and conversational. Ask exactly ONE question "
                "per turn, then stop speaking and wait for the caller's answer before "
                "asking the next question. Never read a numbered list, bullet list, field "
                "labels, or the entire appointment form aloud. Do not announce all required "
                "details at once. For booking, collect missing details naturally in this "
                "order: caller's full name, phone number, preferred doctor or specialty, "
                "date, then available time slot. If the caller already gave a detail, do "
                "not ask for it again. Search doctors or check availability when needed; "
                "offer only real doctors and slots returned by tools. Before booking, "
                "briefly summarize the details in one natural sentence and ask whether "
                "the caller confirms. Call the booking tool only after explicit confirmation. "
                "Never invent doctor IDs, slot IDs, appointment IDs, or available times. "
                "For cancellation, ask conversationally for the appointment ID and registered "
                "phone number, one at a time. For rescheduling, verify the existing appointment "
                "and phone number, check availability for the same doctor, offer returned slots, "
                "and confirm the new slot before changing it. Never cancel the original before "
                "rescheduling. Never claim success unless a tool returns success=true. "
                "If a tool fails, explain briefly and honestly. Avoid Markdown formatting "
                "because your response is spoken aloud. Do not say labels such as 'Name' "
                "or 'Step one'; phrase every question as natural speech."
            ),
        ),
    )

    # 3. Text-to-speech
    tts = ElevenLabsTTSService(
        api_key=os.environ["ELEVENLABS_API_KEY"],
        settings=ElevenLabsTTSService.Settings(
            voice=os.environ["ELEVENLABS_VOICE_ID"],
        ),
    )

    # 4. Conversation memory
    context = LLMContext(
        tools=[
            find_doctors,
            check_doctor_availability,
            book_appointment,
            cancel_appointment,
            reschedule_appointment,
            get_appointment_for_reschedule,
        ]
    )

    user_aggregator, assistant_aggregator = (
        LLMContextAggregatorPair(
            context,
            user_params=LLMUserAggregatorParams(
                vad_analyzer=SileroVADAnalyzer(),
            ),
        )
    )

    # 5. Connect all processors into one pipeline
    pipeline = Pipeline(
        [
            transport.input(),
            stt,
            user_aggregator,
            llm,
            tts,
            transport.output(),
            assistant_aggregator,
        ]
    )

    worker = PipelineWorker(
        pipeline,
        params=PipelineParams(
            enable_metrics=True,
            enable_usage_metrics=True,
        ),
        idle_timeout_secs=(
            runner_args.pipeline_idle_timeout_secs
        ),
    )

    runner = WorkerRunner(
        handle_sigint=runner_args.handle_sigint,
    )

    await runner.add_workers(worker)

    @transport.event_handler("on_client_connected")
    async def on_client_connected(transport, client):
        logger.info("Browser connected")

        # Speak a fixed greeting without calling the LLM on an empty context.
        # The spoken text is appended to context for the caller's first turn.
        await worker.queue_frames(
            [
                TTSSpeakFrame(
                    text="Welcome to Voice Doctor! How can I help you today?",
                    append_to_context=True,
                )
            ]
        )

    @transport.event_handler("on_client_disconnected")
    async def on_client_disconnected(transport, client):
        logger.info("Browser disconnected")
        await runner.cancel()

    await runner.run()


async def bot(runner_args: RunnerArguments):
    webrtc_connection: SmallWebRTCConnection = (
        runner_args.webrtc_connection
    )

    transport = SmallWebRTCTransport(
        webrtc_connection=webrtc_connection,
        params=TransportParams(
            audio_in_enabled=True,
            audio_out_enabled=True,
        ),
    )

    await run_bot(transport, runner_args)


if __name__ == "__main__":
    from pipecat.runner.run import main

    main()
