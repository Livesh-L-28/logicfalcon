"""
Server-Sent Events (SSE) Streaming Adapter for LogicFalcon Engine
Provides async chunk formatting and real-time reasoning telemetry emission.
"""
import json
from typing import Any, AsyncGenerator, Dict

async def format_sse_stream(
    generator: AsyncGenerator[Dict[str, Any], None]
) -> AsyncGenerator[str, None]:
    """
    Converts raw dictionary chunks into formatted Server-Sent Event strings.
    Protocol: data: <json_payload>\n\n
    """
    async for item in generator:
        yield f"data: {json.dumps(item)}\n\n"
    yield "data: [DONE]\n\n"
