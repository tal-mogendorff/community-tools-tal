import inspect
import sys
from pathlib import Path

# Add the project root to Python path
sys.path.append(str(Path(__file__).resolve().parents[2]))

from kubiya_sdk.tools import Arg, FileSpec, Volume
from kubiya_sdk.tools.registry import tool_registry

from src.tools.base import JustInTimeAccessTool
import scripts.describe_access_request as describe_access_request_script

describe_access_request_tool = JustInTimeAccessTool(
    name="describe_access_request",
    description="Describe a specific access request by its Request ID.",
    content="""
    set -e
    python /opt/scripts/describe_access_request.py "{{ .request_id }}"
    """,
    args=[
        Arg(
            name="request_id",
            description="The Request ID to describe. Example: 'req-12345'.",
            required=True
        ),
    ],
    with_files=[
        FileSpec(
            destination="/opt/scripts/describe_access_request.py",
            content=inspect.getsource(describe_access_request_script),
        ),
    ],
    with_volumes=[
        Volume(
            name="db_data",
            path="/var/lib/database"
        )
    ],
)

# Register the tool
tool_registry.register("just_in_time_access", describe_access_request_tool) 