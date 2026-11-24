
import os

from dotenv import load_dotenv
from loguru import logger

from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.frames.frames import LLMRunFrame
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.worker import PipelineParams, PipelineWorker

from pipecat.processors.aggregators.llm_context import LLMContext
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
    llm = GroqLLMService(
        api_key=os.environ["GROQ_API_KEY"],
        settings=GroqLLMService.Settings(
            model=os.getenv(
                "GROQ_MODEL",
                "llama-3.1-8b-instant",
            ),
            system_instruction=(
                "You are Voice Doctor, a polite and helpful "
                "medical appointment booking voice assistant. "
                "You help callers check doctor availability, "
                "book appointments, and cancel appointments. "
                "Speak naturally and keep responses concise. "
                "Never claim an appointment is booked or "
                "cancelled unless the backend confirms it."
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
    context = LLMContext()

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

        context.add_message(
            {
                "role": "developer",
                "content": (
                    "Welcome the caller to Voice Doctor "
                    "and ask how you can help."
                ),
            }
        )

        await worker.queue_frames([LLMRunFrame()])

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
