# Deployment

Checkmate deploys to AWS via Terraform. The stack is intentionally boring: ECS Fargate for stateless services, RDS for Postgres, ElastiCache for Redis, ALB for HTTPS termination.

## Architecture

```
                    ┌──────────────────────────┐
Internet ───▶ Route53 ───▶ ALB (ACM cert) ─────┤
                                                │
                                                ▼
                                   ECS Fargate (checkmate-api)
                                                │
                                   ┌────────────┼────────────┐
                                   ▼            ▼            ▼
                                  RDS      ElastiCache     Fargate
                                Postgres      Redis      (worker, qdrant,
                                                           langfuse)
```

## Prerequisites

- AWS account with admin IAM (for first deploy; tighten later)
- Domain name (Route53 hosted zone)
- Anthropic API key
- GitHub App created + private key PEM

## First Deploy

```bash
cd terraform/
cp terraform.tfvars.example terraform.tfvars
# Fill in domain, AWS region, secrets (or use AWS Secrets Manager refs)

terraform init
terraform plan
terraform apply
```

Expect ~15 minutes for first apply (RDS provisioning dominates).

## Cost Estimate (single-region, low traffic)

| Resource | Monthly |
|---|---|
| ECS Fargate (2x 0.25 vCPU / 0.5 GB, 24/7) | ~$15 |
| RDS Postgres (db.t4g.micro) | ~$13 |
| ElastiCache Redis (cache.t4g.micro) | ~$12 |
| ALB | ~$17 |
| Data transfer / misc | ~$5 |
| **Total baseline** | **~$60/mo** |

LLM costs scale with PR volume (~$0.03-0.05 per PR).

## Cheaper Alternative

For a portfolio/demo deploy, skip ECS and run everything on a single **Lightsail** or **EC2 t4g.small** ($10/mo) with docker-compose. Less impressive on the resume but fine for showing it working.

## CI/CD

`.github/workflows/deploy.yml` builds Docker images, pushes to ECR, and triggers ECS service updates on pushes to `main`.
