from typing import Optional, Union
import logging

try:
    import boto3
    from botocore.exceptions import ClientError
except ImportError:
    print("boto3 / botocore not installed, skipping import (might be a discovery call)")
    boto3 = None
    ClientError = None
    pass

logger = logging.getLogger(__name__)

def get_account_alias(session: Optional[Union[boto3.Session, None]]) -> Optional[str]:
    """Get AWS account alias if it exists."""
    if not session:
        return None
    try:
        iam = session.client('iam')
        response = iam.list_account_aliases()
        aliases = response.get('AccountAliases', [])
        return aliases[0] if aliases else None
    except Exception as e:
        logger.warning(f"Could not get account alias: {e}")
        return None

def get_permission_set_details(session: Optional[Union[boto3.Session, None]], instance_arn: str, permission_set_arn: str) -> Optional[dict]:
    """Get detailed information about a permission set."""
    if not session:
        return None
    try:
        sso_admin = session.client('sso-admin')
        response = sso_admin.describe_permission_set(
            InstanceArn=instance_arn,
            PermissionSetArn=permission_set_arn
        )
        return response.get('PermissionSet')
    except Exception as e:
        logger.warning(f"Could not get permission set details: {e}")
        return None