from kubiya_sdk.tools import Tool, Arg
from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

class TerraformerTool(Tool):
    """Tool for reverse engineering existing infrastructure into Terraform code."""
    
    # Define supported providers and their configurations
    SUPPORTED_PROVIDERS = {
        'aws': {
            'name': 'AWS',
            'resources': ['vpc', 'subnet', 'security-group', 'elb', 'rds', 'iam'],
            'env_vars': ['AWS_ACCESS_KEY_ID', 'AWS_SECRET_ACCESS_KEY', 'AWS_REGION']
        },
        'gcp': {
            'name': 'Google Cloud',
            'resources': ['compute', 'storage', 'sql', 'iam'],
            'env_vars': ['GOOGLE_CREDENTIALS', 'GOOGLE_PROJECT']
        },
        'azure': {
            'name': 'Azure',
            'resources': ['compute', 'network', 'storage', 'database'],
            'env_vars': ['AZURE_SUBSCRIPTION_ID', 'AZURE_CLIENT_ID', 'AZURE_CLIENT_SECRET', 'AZURE_TENANT_ID']
        }
    }

    @classmethod
    def get_enabled_providers(cls, config: Dict[str, Any]) -> List[str]:
        """Get list of enabled providers from configuration."""
        if 'terraform' not in config and any(
            key in config for key in ['enable_reverse_terraform', 'reverse_terraform_providers']
        ):
            config = {'terraform': config}
            
        terraform_config = config.get('terraform', {})
        if not terraform_config.get('enable_reverse_terraform'):
            return []
            
        providers = terraform_config.get('reverse_terraform_providers', [])
        if isinstance(providers, str):
            providers = [providers]
            
        if not providers:
            logger.warning("Reverse Terraform engineering is enabled but no providers specified")
            return []
            
        # Validate providers
        valid_providers = []
        for provider in providers:
            if provider in cls.SUPPORTED_PROVIDERS:
                valid_providers.append(provider)
            else:
                logger.warning(f"Unsupported provider: {provider}. Supported providers: {list(cls.SUPPORTED_PROVIDERS.keys())}")
                
        return valid_providers

def _initialize_provider_tools(provider: str, tool_registry) -> List[Tool]:
    """Initialize tools for a specific provider."""
    tools = []
    try:
        if provider not in TerraformerTool.SUPPORTED_PROVIDERS:
            logger.warning(f"Unsupported provider: {provider}")
            return tools

        provider_config = TerraformerTool.SUPPORTED_PROVIDERS[provider]
        
        # Create import tool
        import_tool = TerraformerTool(
            name=f"terraform_import_{provider}",
            description=f"Import existing {provider_config['name']} infrastructure into Terraform",
            args=[
                Arg(
                    name="resource_type",
                    description=f"Type of resource to import. Available: {', '.join(provider_config['resources'])}",
                    type="str"
                ),
                Arg(
                    name="resource_id",
                    description="ID or name of the resource to import",
                    type="str"
                ),
                Arg(
                    name="output_dir",
                    description="Directory to save the generated Terraform code",
                    type="str",
                    required=False,
                    default="terraform_imported"
                )
            ],
            env=provider_config['env_vars']
        )
        tools.append(import_tool)
        
        # Create scan tool
        scan_tool = TerraformerTool(
            name=f"terraform_scan_{provider}",
            description=f"Scan and discover {provider_config['name']} infrastructure for Terraform import",
            args=[
                Arg(
                    name="resource_types",
                    description=f"Types of resources to scan. Available: {', '.join(provider_config['resources'])}",
                    type="str",
                    required=False,
                    default="all"
                ),
                Arg(
                    name="output_format",
                    description="Output format (json, yaml, or hcl)",
                    type="str",
                    required=False,
                    default="hcl"
                )
            ],
            env=provider_config['env_vars']
        )
        tools.append(scan_tool)
        
        logger.info(f"Created tools for provider: {provider}")
        return tools
        
    except Exception as e:
        logger.error(f"Failed to initialize tools for provider {provider}: {str(e)}")
        return []

__all__ = ['TerraformerTool', '_initialize_provider_tools'] 