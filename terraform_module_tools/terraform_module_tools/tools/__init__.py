import logging
from typing import List, Any, Dict, Optional
from kubiya_sdk.tools import Tool
from kubiya_sdk.tools.registry import tool_registry
from .terraform_module_tool import TerraformModuleTool
from .terraformer_tool import TerraformerTool, _initialize_provider_tools
from ..parser import TerraformModuleParser
from ..scripts.config_loader import get_module_configs, get_reverse_terraform_config, ConfigurationError
import re

logger = logging.getLogger(__name__)

def parse_module_urls(urls_input: Any) -> List[Dict[str, Any]]:
    """
    Parse module URLs and metadata from configuration.
    
    Supports multiple formats:
    1. Simple string: "url1,url2"
    2. List of strings: ["url1", "url2"]
    3. List of dicts: [{"url": "url1", "name": "custom_name", "ref": "main"}, ...]
    4. Dict with metadata: {"url1": {"name": "custom_name", "ref": "main"}, ...}
    
    Returns:
        List[Dict[str, Any]]: List of module configurations
    """
    if not urls_input:
        return []
    
    modules = []
    
    try:
        if isinstance(urls_input, str):
            # Handle comma-separated string
            modules = [{"url": url.strip()} for url in urls_input.split(',') if url.strip()]
            
        elif isinstance(urls_input, (list, tuple)):
            # Handle list of strings or dicts
            for item in urls_input:
                if isinstance(item, str):
                    modules.append({"url": item.strip()})
                elif isinstance(item, dict):
                    if 'url' not in item:
                        logger.warning(f"Skipping module config missing URL: {item}")
                        continue
                    modules.append(item)
                else:
                    logger.warning(f"Skipping invalid module config: {item}")
                    
        elif isinstance(urls_input, dict):
            # Handle new configuration format
            for module_name, module_config in urls_input.items():
                if isinstance(module_config, dict):
                    # Convert registry format to URL format
                    if '/' in module_config.get('source', ''):
                        source_parts = module_config['source'].split('/')
                        if len(source_parts) == 3:  # namespace/name/provider format
                            url = f"registry.terraform.io/{module_config['source']}"
                        else:
                            url = module_config['source']
                    else:
                        url = module_config['source']

                    modules.append({
                        'url': url,
                        'name': module_name,
                        'version': module_config.get('version'),
                        'auto_discover': module_config.get('auto_discover', True),
                        'instructions': module_config.get('instructions'),
                        'variables': module_config.get('variables', {})
                    })

        else:
            logger.warning(f"Unexpected type for module URLs: {type(urls_input)}")
            return []
            
        # Validate and normalize each module config
        normalized_modules = []
        for module in modules:
            if normalized := _normalize_module_config(module):
                normalized_modules.append(normalized)
                
        return normalized_modules
        
    except Exception as e:
        logger.error(f"Error parsing module configurations: {str(e)}")
        return []

def _normalize_module_config(config: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Normalize and validate module configuration."""
    try:
        url = config['url'].strip()
        if not url:
            return None
            
        normalized = {
            'url': url,
            'ref': config.get('ref') or config.get('version') or config.get('branch'),
            'path': config.get('path'),
            'name': config.get('name'),
            'description': config.get('description'),
            'provider': config.get('provider'),
            'resource_type': config.get('resource_type'),
            'metadata': config.get('metadata', {})
        }
        
        # Clean up None values
        return {k: v for k, v in normalized.items() if v is not None}
        
    except Exception as e:
        logger.warning(f"Failed to normalize module config: {str(e)}")
        return None

def _get_clean_module_name(module_config: Dict[str, Any]) -> str:
    """
    Extract a clean module name from configuration.
    
    Priority:
    1. Explicit name from config
    2. Provider/resource combination
    3. Parsed from URL
    """
    # Use explicit name if provided
    if name := module_config.get('name'):
        return name.lower().replace('-', '_')
    
    url = module_config['url']
    provider = module_config.get('provider')
    resource_type = module_config.get('resource_type')
    
    # Use provider/resource if both are specified
    if provider and resource_type:
        return f"{provider}_{resource_type}".lower()
    
    # Parse from URL
    if '/tree/' in url:
        url = url.split('/tree/')[0]
    
    # Handle different URL formats
    if url.startswith(('http://', 'https://', 'git@')):
        # GitHub/GitLab URLs
        if 'github.com' in url or 'gitlab.com' in url:
            parts = url.rstrip('/').rstrip('.git').split('/')
            repo_name = parts[-1]
            
            # Handle terraform-provider-name format
            if repo_name.startswith('terraform-'):
                name_parts = repo_name.split('-')
                if len(name_parts) >= 3:
                    provider = name_parts[1]
                    resource = '_'.join(name_parts[2:])
                    return f"{provider}_{resource}".lower()
            
            return repo_name.replace('-', '_').lower()
            
    elif url.count('/') == 2:  # registry format
        namespace, name, provider = url.split('/')
        return f"{provider}_{name}".lower()
    
    # Fallback: clean up whatever we have
    name = url.split('/')[-1].replace('-', '_')
    name = re.sub(r'[^\w_]', '', name)
    return name.lower()

def create_terraform_module_tool(module_config: Dict[str, Any], action: str, with_pr: bool = False):
    """Create a Terraform module tool from module configuration."""
    try:
        # Parse module information from URL
        parser = TerraformModuleParser(
            source_url=module_config['url'],
            ref=module_config.get('ref'),
            path=module_config.get('path')
        )
        
        variables, warnings, errors = parser.get_variables()
        
        if errors:
            logger.error(f"Failed to parse module {module_config['url']}: {errors}")
            return None
            
        for warning in warnings:
            logger.warning(f"Warning for {module_config['url']}: {warning}")

        # Get clean module name
        module_name = _get_clean_module_name(module_config)
        
        # Create module configuration
        tool_config = {
            'name': module_name,
            'description': module_config.get('description') or f"Terraform module for {module_name}",
            'source': {
                'location': module_config['url'],
                'version': module_config.get('ref') or parser.source.get_ref() or 'latest',
                'path': module_config.get('path')
            },
            'metadata': module_config.get('metadata', {})
        }

        # Generate tool name
        action_suffix = '_plan_pr' if action == 'plan' and with_pr else f'_{action}'
        tool_name = f"tf_{module_name}{action_suffix}"

        return TerraformModuleTool(
            name=tool_name,
            description=tool_config['description'],
            module_config=tool_config,
            action=action,
            with_pr=with_pr
        )

    except Exception as e:
        logger.error(f"Failed to create tool for {module_config['url']}: {str(e)}")
        return None

def initialize_tools(config: Dict[str, Any]) -> List[Tool]:
    """Initialize all Terraform tools from configuration."""
    tools = []
    try:
        if not config:
            raise ConfigurationError("No configuration provided")

        terraform_config = config.get('terraform', {})

        # Initialize module tools if modules are configured
        if terraform_config.get('modules'):
            logger.info("Initializing Terraform module tools")
            module_tools = _initialize_module_tools(terraform_config['modules'])
            if module_tools:
                tools.extend(module_tools)

        # Initialize reverse terraform tools if enabled
        if terraform_config.get('enable_reverse_terraform'):
            logger.info("Initializing reverse Terraform engineering tools")
            reverse_tools = _initialize_reverse_terraform_tools(config)
            if reverse_tools:
                tools.extend(reverse_tools)

        if not tools:
            raise ConfigurationError("No tools were created from configuration")

        logger.info(f"Successfully initialized all Terraform tools")
        return tools
        
    except ConfigurationError as e:
        logger.error(f"Configuration error: {str(e)}")
        raise
    except Exception as e:
        error_msg = f"Failed to initialize tools: {str(e)}"
        logger.error(error_msg)
        raise ConfigurationError(error_msg)

def _initialize_module_tools(module_configs: Dict[str, Dict[str, Any]]) -> List[TerraformModuleTool]:
    """Initialize Terraform module tools from validated module configurations."""
    tools = []
    errors = []
    
    for module_name, module_config in module_configs.items():
        try:
            logger.info(f"Creating tools for module: {module_name}")
            
            # Create tools for each action
            for action in ['plan', 'apply']:
                tool = create_terraform_module_tool(module_config, action)
                if tool:
                    tools.append(tool)
                    tool_registry.register("terraform", tool)
                    logger.info(f"Created {action} tool for {module_name}")
                else:
                    errors.append(f"Failed to create {action} tool for {module_name}")
                    
        except Exception as e:
            error_msg = f"Failed to create tools for module {module_name}: {str(e)}"
            logger.error(error_msg)
            errors.append(error_msg)
            continue
    
    if errors and not tools:
        raise ConfigurationError(f"Failed to initialize any module tools: {'; '.join(errors)}")
            
    return tools

def _initialize_reverse_terraform_tools(config: Dict[str, Any]) -> List[Tool]:
    """Initialize reverse Terraform engineering tools."""
    tools: List[Tool] = []
    enabled_providers = TerraformerTool.get_enabled_providers(config)
    
    for provider in enabled_providers:
        try:
            provider_tools = _initialize_provider_tools(provider, tool_registry)
            if provider_tools:
                tools.extend(provider_tools)
        except Exception as e:
            logger.error(f"Failed to initialize tools for provider {provider}: {str(e)}")
            continue
            
    return tools

__all__ = [
    'initialize_tools',
    'create_terraform_module_tool',
    'TerraformModuleTool',
    'TerraformerTool'
]