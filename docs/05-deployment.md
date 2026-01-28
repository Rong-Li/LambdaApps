# Deployment Guide

## Overview

homeapp uses **GitHub Actions** for CI/CD with direct zip-and-upload deployment to AWS Lambda. Dependencies are pre-packaged in a Lambda Layer.

---

## Prerequisites

### AWS Resources (Manual Setup)

| Resource | Name | Description |
|----------|------|-------------|
| **Lambda Layer** | `homeapp-dependencies` | Contains powertools, pydantic, pymongo |
| **Lambda Function** | `lambda-home-api` | API handler |
| **Lambda Function** | `lambda-home-batch` | Batch handler |
| **API Gateway** | `homeapp-http-api` | HTTP API (rate: 5/sec, quota: 100/day) |
| **S3 Bucket** | `homeapp-archive` | Transaction archives |
| **EventBridge Rule** | `homeapp-monthly-batch` | Monthly trigger (Toronto ET) |
| **IAM Role** | `homeapp-lambda-role` | Lambda execution role |

### IAM Permissions Required

| Service | Actions |
|---------|---------|
| **CloudWatch Logs** | CreateLogGroup, CreateLogStream, PutLogEvents |
| **S3** | PutObject, GetObject (on `homeapp-archive/*`) |

### GitHub Secrets

| Secret | Description |
|--------|-------------|
| `AWS_ACCESS_KEY_ID` | AWS IAM access key |
| `AWS_SECRET_ACCESS_KEY` | AWS IAM secret key |
| `AWS_REGION` | AWS region (e.g., `us-east-1`) |
| `MONGODB_URI` | MongoDB Atlas connection string |

---

## Lambda Layer

### Contents

- `aws-lambda-powertools`
- `pydantic`
- `pymongo`

### Build Command

```bash
./build_lambda_layer.sh
```

Creates `lambda-uv.zip` for upload.

> **Note:** Layer only needs updating when dependencies change.

---

## GitHub Actions Workflow

### Trigger

- Push to `main` branch (paths: `service/**`, `.github/workflows/deploy.yml`)
- Manual dispatch

### Jobs

1. **test**: Run pytest and ruff linter
2. **deploy-api**: Package and deploy `lambda-home-api`
3. **deploy-batch**: Package and deploy `lambda-home-batch`

### Workflow File Location

`.github/workflows/deploy.yml`

---

## Environment Variables

### API Lambda (`lambda-home-api`)

| Variable | Required | Description |
|----------|----------|-------------|
| `MONGODB_URI` | ✅ | MongoDB connection string |
| `MONGODB_DATABASE` | ✅ | Database name (`homeapp`) |
| `LOG_LEVEL` | ❌ | Logging level (default: INFO) |

### Batch Lambda (`lambda-home-batch`)

| Variable | Required | Description |
|----------|----------|-------------|
| `MONGODB_URI` | ✅ | MongoDB connection string |
| `MONGODB_DATABASE` | ✅ | Database name (`homeapp`) |
| `S3_BUCKET_NAME` | ✅ | Archive bucket (`homeapp-archive`) |
| `LOG_LEVEL` | ❌ | Logging level (default: INFO) |

---

## Local Development

### Setup

1. Clone repository
2. Install uv: `curl -LsSf https://astral.sh/uv/install.sh | sh`
3. Install dependencies: `uv sync --dev`
4. Set environment variables:
   - `MONGODB_URI`
   - `MONGODB_DATABASE=homeapp`
   - `S3_BUCKET_NAME=homeapp-archive`

### Running Tests

```bash
uv run pytest
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
- [ ] Create IAM role for Lambda
- [ ] Create Lambda Layer with dependencies
- [ ] Create Lambda functions (API and Batch)
- [ ] Create HTTP API Gateway
- [ ] Create EventBridge rule for batch job
- [ ] Configure GitHub secrets
- [ ] Deploy initial code

### Regular Deployment

- [ ] Run tests locally
- [ ] Push to main branch
- [ ] Verify GitHub Actions pass
- [ ] Check Lambda logs in CloudWatch
- [ ] Test API endpoints

### Dependency Updates

- [ ] Update `pyproject.toml`
- [ ] Run `uv lock`
- [ ] Rebuild Lambda Layer
- [ ] Upload new Layer version
- [ ] Update Lambda functions to use new Layer

---

## Rollback Procedure

1. List Lambda versions for the function
2. Update alias to point to previous working version

---

## Monitoring & Troubleshooting

### CloudWatch Log Groups

- `/aws/lambda/lambda-home-api`
- `/aws/lambda/lambda-home-batch`

### Common Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| Import error | Missing dependency in Layer | Rebuild and redeploy Layer |
| Timeout | Long-running operation | Increase Lambda timeout |
| MongoDB connection error | Network/credentials | Check VPC config, verify URI |
| Permission denied (S3) | IAM role missing permissions | Update IAM policy |
