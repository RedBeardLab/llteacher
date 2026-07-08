#!/usr/bin/env bash
set -euo pipefail

REGION="${AWS_REGION:-us-west-2}"
ACCOUNT_ID="$(aws sts get-caller-identity --query Account --output text)"
BUCKET="llteacher-pulumi-state-${ACCOUNT_ID}-${REGION}"
ALIAS="alias/llteacher-pulumi-state"

if ! aws kms describe-key --region "$REGION" --key-id "$ALIAS" >/dev/null 2>&1; then
  KEY_ID="$(aws kms create-key \
    --region "$REGION" \
    --description "LLTeacher Pulumi state and secrets" \
    --query KeyMetadata.KeyId \
    --output text)"
  aws kms create-alias --region "$REGION" --alias-name "$ALIAS" --target-key-id "$KEY_ID"
fi

KEY_ARN="$(aws kms describe-key --region "$REGION" --key-id "$ALIAS" --query KeyMetadata.Arn --output text)"

if ! aws s3api head-bucket --bucket "$BUCKET" 2>/dev/null; then
  aws s3api create-bucket \
    --region "$REGION" \
    --bucket "$BUCKET" \
    --create-bucket-configuration "LocationConstraint=${REGION}"
fi

aws s3api put-public-access-block --bucket "$BUCKET" --public-access-block-configuration \
  BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true
aws s3api put-bucket-versioning --bucket "$BUCKET" --versioning-configuration Status=Enabled
aws s3api put-bucket-encryption --bucket "$BUCKET" --server-side-encryption-configuration \
  "{\"Rules\":[{\"ApplyServerSideEncryptionByDefault\":{\"SSEAlgorithm\":\"aws:kms\",\"KMSMasterKeyID\":\"${KEY_ARN}\"},\"BucketKeyEnabled\":true}]}"

echo "Pulumi backend: s3://${BUCKET}"
echo "Secrets provider: awskms://${ALIAS}?region=${REGION}"
echo "Run: pulumi login s3://${BUCKET}"
