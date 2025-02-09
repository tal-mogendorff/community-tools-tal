from kubiya_sdk.tools import Tool, Arg
from kubiya_sdk.tools.registry import tool_registry

KUBIYA_ICON = "https://www.finsmes.com/wp-content/uploads/2022/10/Kubiya-logo-mark-color.png"
CLI_VERSION = "v0.0.6"
CLI_URL = f"https://github.com/kubiyabot/cli/releases/download/{CLI_VERSION}/kubiya-linux-amd64"
CLI_PATH = "/usr/local/bin/kubiya"

class KubiyaCliBase(Tool):
    """Base class for all Kubiya CLI tools"""
    
    def __init__(self, name, description, cli_command, args=None, mermaid=None):
        enhanced_command = f'''
#!/bin/sh
set -e

apk add curl --silent > /dev/null 2>&1

# Get CLI binary
curl -L {CLI_URL} -o /usr/local/bin/kubiya
chmod +x /usr/local/bin/kubiya

# Execute command with full path
/usr/local/bin/kubiya {cli_command}
'''

        super().__init__(
            name=name,
            description=description,
            icon_url=KUBIYA_ICON,
            type="docker",
            image="alpine:latest",
            content=enhanced_command,
            args=args or [],
            secrets=["KUBIYA_API_KEY"],
            mermaid=mermaid,
        )

    @classmethod
    def register(cls, tool):
        """Register a tool with the Kubiya registry"""
        tool_registry.register("kubiya", tool)
        return tool

def create_tool(name, description, cli_command, args=None, mermaid=None):
    """Factory function to create and register a new Kubiya CLI tool"""
    tool = KubiyaCliBase(
        name=f"kubiya_{name}",
        description=description,
        cli_command=cli_command,
        args=args or [],
        mermaid=mermaid,
    )
    return KubiyaCliBase.register(tool)

__all__ = ['KubiyaCliBase', 'create_tool']