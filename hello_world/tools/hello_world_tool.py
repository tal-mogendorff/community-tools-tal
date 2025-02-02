from kubiya_sdk.tools.models import Tool, Arg
from kubiya_sdk.tools.registry import tool_registry

hello_world = ServiceSpec(
            name="world",
            image="kubiya/tal-jfrog:latest",
            exposed_ports=[80]
        )

say_hello_tool = Tool(
    name="say_hello",
    type="docker",
    image="python:3.12-slim-bullseye",
    description="Prints hello with name",
    args=[Arg(name="name", description="name to say hello to", required=True)],
    env=[],
    secrets=[],
    with_services=[hello_world]
    content="""
python -c "print(f'Hello, {{ .name }}!')"
""",
)

tool_registry.register_tool("hello_world", say_hello_tool)
