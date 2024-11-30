import os
import json
from typing import Dict, Any, List
from kubiya_sdk.tools import Arg
from kubiya_sdk.tools.registry import tool_registry
from ..parser import TerraformModuleParser, TerraformVariable

CONFIG_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'configs')

def _create_arg_from_variable(var: TerraformVariable) -> Arg:
    """Create a Kubiya tool argument from a Terraform variable."""
    description = (
        f"{var.description or f'Variable: {var.name}'}\n\n"
        f"Type: {var.type.base_type}\n"
    )
    
    if var.type.base_type in ['object', 'map', 'list', 'set']:
        description += f"\nExample Input:\n```json\n{var.get_example_value()}\n```"
    
    if var.validation_rules:
        description += "\nValidation Rules:\n"
        for rule in var.validation_rules:
            description += f"- {rule.get('error_message', rule.get('condition'))}\n"
    
    if var.default is not None:
        description += f"\nDefault: {json.dumps(var.default)}"

    return Arg(
        name=var.name,
        description=description,
        required=var.required,
        type="string",  # All inputs will be JSON strings for consistency
        default=json.dumps(var.default) if var.default is not None else None,
    )

def register_terraform_tools(module_name: str, config: Dict[str, Any], variables: Dict[str, TerraformVariable]) -> None:
    """Register all tools for a Terraform module."""
    
    # Create variable arguments
    variable_args = [
        _create_arg_from_variable(var)
        for var in variables.values()
    ]
    
    # Register plan tool
    plan_tool = {
        "name": f"terraform_{module_name}_plan",
        "description": f"Plan changes for {config['description']}",
        "content": """
            # Run Terraform plan
            python /opt/scripts/terraform_plan.py '{{ .source_config | toJson }}' '{{ .variables | toJson }}'
        """,
        "args": variable_args + [
            Arg(
                name="source_config",
                description="Module source configuration",
                type="object",
                required=True,
                default=config['source']
            )
        ],
        "env": config.get('env', []),
        "secrets": config.get('secrets', [])
    }
    tool_registry.register("terraform", plan_tool)
    
    # Register apply tool
    apply_tool = {
        "name": f"terraform_{module_name}_apply",
        "description": f"Apply changes for {config['description']}",
        "content": """
            # Run Terraform apply
            python /opt/scripts/terraform_apply.py '{{ .source_config | toJson }}' '{{ .variables | toJson }}'
        """,
        "args": variable_args + [
            Arg(
                name="source_config",
                description="Module source configuration",
                type="object",
                required=True,
                default=config['source']
            )
        ],
        "env": config.get('env', []),
        "secrets": config.get('secrets', [])
    }
    tool_registry.register("terraform", apply_tool)
    
    # Register variables tool
    vars_tool = {
        "name": f"terraform_{module_name}_vars",
        "description": f"Show variables for {config['description']}",
        "content": """
            # Show variables
            python /opt/scripts/get_module_vars.py '{{ .source_config | toJson }}'
        """,
        "args": [
            Arg(
                name="source_config",
                description="Module source configuration",
                type="object",
                required=True,
                default=config['source']
            )
        ],
        "env": config.get('env', []),
        "secrets": config.get('secrets', [])
    }
    tool_registry.register("terraform", vars_tool)

def load_terraform_tools():
    """Load and register all Terraform tools from configuration files."""
    for filename in os.listdir(CONFIG_DIR):
        if filename.endswith('.json'):
            config_path = os.path.join(CONFIG_DIR, filename)
            try:
                with open(config_path, 'r') as f:
                    config = json.load(f)
                
                module_name = config['name']
                print(f"📦 Loading module: {module_name}")
                
                # Parse module variables
                parser = TerraformModuleParser(
                    source_url=config['source']['location'],
                    ref=config['source'].get('git_config', {}).get('ref'),
                    subfolder=config['source'].get('git_config', {}).get('subfolder')
                )
                
                variables, warnings, errors = parser.get_variables()
                
                # Log any warnings or errors
                for warning in warnings:
                    print(f"⚠️ Warning for {module_name}: {warning}")
                for error in errors:
                    print(f"❌ Error for {module_name}: {error}")
                
                if not variables:
                    print(f"⚠️ No variables found for module {module_name}")
                    continue
                
                # Register tools for this module
                register_terraform_tools(module_name, config, variables)
                print(f"✅ Successfully registered tools for {module_name}")
                
            except Exception as e:
                print(f"❌ Failed to load module from {filename}: {str(e)}")
                continue

# Export the loader function
__all__ = ['load_terraform_tools'] 