# Deployment Guide

## Overview

homeapp uses **GitHub Actions** for CI/CD with direct zip-and-upload deployment to AWS Lambda. Dependencies are pre-packaged in separate Lambda Layers for API and Batch functions.

---

## Prerequisites

### AWS Resources (Manual Setup)

| Resource | Name | Description |
|----------|------|-------------|
| **Lambda Layer (API)** | `homeapp-api-layer` | powertools, pydantic, pymongo |
| **Lambda Layer (Batch)** | `homeapp-batch-layer` | + polars for Parquet export |
| **Lambda Function** | `HomeApp-LambdaFunction-APIs` | API handler |
| **Lambda Function** | `HomeApp-LambdaFunction-Batch` | Batch handler |
| **API Gateway** | `homeapp-http-api` | HTTP API (rate: 5/sec, quota: 100/day) |
| **S3 Bucket** | `homeapp-archive` | Transaction archives |
| **EventBridge Rule** | `homeapp-monthly-batch` | Monthly trigger (Toronto ET) |
| **IAM Role** | `homeapp-lambda-role` | Lambda execution role |
| **IAM Role** | `GitHubActions-HomeApp` | GitHub Actions deployment role (OIDC) |

### IAM Permissions for Lambda

| Service | Actions |
|---------|---------|
| **CloudWatch Logs** | CreateLogGroup, CreateLogStream, PutLogEvents |
| **S3** | PutObject, GetObject (on `homeapp-archive/*`) |

### IAM Permissions for GitHub Actions

| Action | Resource |
|--------|----------|
| `lambda:GetFunction` | `HomeApp-LambdaFunction-*` |
| `lambda:GetFunctionConfiguration` | `HomeApp-LambdaFunction-*` |
| `lambda:UpdateFunctionCode` | `HomeApp-LambdaFunction-*` |

### GitHub Secrets

| Secret | Description |
|--------|-------------|
| `AWS_ROLE_ARN` | IAM role ARN for OIDC authentication |

---

## Lambda Layers

### API Layer (`homeapp-api-layer`)

| Package | Purpose |
|---------|---------|
| `aws-lambda-powertools[tracer]` | Logging, tracing |
| `pydantic` | Data validation |
| `pydantic-settings` | Settings management |
| `pymongo` | MongoDB driver |

### Batch Layer (`homeapp-batch-layer`)

Includes everything in API layer plus:

| Package | Purpose |
|---------|---------|
| `polars` | DataFrame and Parquet export |

### Build Commands

```bash
# Build both layers
./build_lambda_layer.sh

# Output:
# - lambda-layer-api.zip   (~21MB)
# - lambda-layer-batch.zip (~80MB)
```

### Upload Layers to AWS

```bash
# API layer
aws lambda publish-layer-version \
  --layer-name homeapp-api-layer \
  --zip-file fileb://lambda-layer-api.zip \
  --compatible-runtimes python3.14

# Batch layer
aws lambda publish-layer-version \
  --layer-name homeapp-batch-layer \
  --zip-file fileb://lambda-layer-batch.zip \
  --compatible-runtimes python3.14
```

> **Note:** Layers only need updating when dependencies change.

---

## GitHub Actions Setup (OIDC)

### 1. Create OIDC Identity Provider

1. IAM → Identity providers → Add provider
2. Provider type: **OpenID Connect**
3. Provider URL: `https://token.actions.githubusercontent.com`
4. Audience: `sts.amazonaws.com`

### 2. Create IAM Role

1. IAM → Roles → Create role
2. Trusted entity: **Custom trust policy**

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {
      "Federated": "arn:aws:iam::ACCOUNT_ID:oidc-provider/token.actions.githubusercontent.com"
    },
    "Action": "sts:AssumeRoleWithWebIdentity",
    "Condition": {
      "StringEquals": {
        "token.actions.githubusercontent.com:aud": "sts.amazonaws.com"
      },
      "StringLike": {
        "token.actions.githubusercontent.com:sub": "repo:YOUR_GITHUB_USERNAME/LambdaApps:*"
      }
    }
  }]
}
```

3. Add inline policy for Lambda deployment:

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Action": [
      "lambda:GetFunction",
      "lambda:GetFunctionConfiguration",
      "lambda:UpdateFunctionCode"
    ],
    "Resource": [
      "arn:aws:lambda:*:*:function:HomeApp-LambdaFunction-*"
    ]
  }]
}
```

### 3. Add GitHub Secret

- Name: `AWS_ROLE_ARN`
- Value: `arn:aws:iam::ACCOUNT_ID:role/GitHubActions-HomeApp`

---

## GitHub Actions Workflow

### Trigger

- Push to `main` branch
- Manual dispatch

### Jobs

1. **test**: Run pytest unit tests
2. **deploy**: Package and deploy both Lambda functions

### Workflow File

`.github/workflows/deploy.yml`

---

## Environment Variables

### API Lambda (`HomeApp-LambdaFunction-APIs`)

| Variable | Required | Description |
|----------|----------|-------------|
| `MONGODB_URI` | ✅ | MongoDB connection string |
| `MONGODB_DATABASE` | ✅ | Database name (`homeapp`) |

### Batch Lambda (`HomeApp-LambdaFunction-Batch`)

| Variable | Required | Description |
|----------|----------|-------------|
| `MONGODB_URI` | ✅ | MongoDB connection string |
| `MONGODB_DATABASE` | ✅ | Database name (`homeapp`) |
| `S3_BUCKET_NAME` | ✅ | Archive bucket (`homeapp-archive`) |

---

## Local Development

### Setup

```bash
# Clone repository
git clone <repo-url>
cd LambdaApps

# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install dependencies
uv sync --all-extras

# Set environment variables
export MONGODB_URI="mongodb+srv://..."
export MONGODB_DATABASE="homeapp"
export S3_BUCKET_NAME="homeapp-archive"
```

### Running Tests

```bash
uv run pytest tests/unit/ -v
```

### Running Linter

```bash
uv run ruff check service/
```

---

## Deployment Checklist

### First-Time Setup

- [ ] Create MongoDB Atlas cluster and get connection string
- [ ] Create S3 bucket for archives
- [ ] Create IAM role for Lambda execution
- [ ] Create OIDC provider and GitHub Actions IAM role
- [ ] Build and upload Lambda Layers (API and Batch)
- [ ] Create Lambda functions
- [ ] Attach appropriate layers to each function
- [ ] Create HTTP API Gateway
- [ ] Create EventBridge rule for batch job
- [ ] Configure GitHub secret (`AWS_ROLE_ARN`)
- [ ] Push to main branch to trigger deployment

### Regular Deployment

- [ ] Push to main branch
- [ ] Verify GitHub Actions pass
- [ ] Check Lambda logs in CloudWatch

### Dependency Updates

- [ ] Update `pyproject.toml`
- [ ] Run `uv lock`
- [ ] Rebuild Lambda Layers: `./build_lambda_layer.sh`
- [ ] Upload new Layer versions to AWS
- [ ] Update Lambda functions to use new Layer versions

---

## Monitoring & Troubleshooting

### CloudWatch Log Groups

- `/aws/lambda/HomeApp-LambdaFunction-APIs`
- `/aws/lambda/HomeApp-LambdaFunction-Batch`

### Common Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| Import error | Missing dependency in Layer | Rebuild and redeploy Layer |
| Timeout | Long-running operation | Increase Lambda timeout |
| MongoDB connection error | Network/credentials | Check VPC config, verify URI |
| Permission denied (S3) | IAM role missing permissions | Update IAM policy |
| GitHub Actions auth failure | OIDC misconfigured | Check trust policy and secret |
