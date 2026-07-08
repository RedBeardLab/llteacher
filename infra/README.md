# LLTeacher AWS infrastructure

This Pulumi TypeScript project creates the `llteacher-dev` AWS foundation in
`us-west-2`: ECR, a public App Runner service, and a private PostgreSQL RDS
instance. The App Runner service is disabled by default so the repository can
be created before its first image is pushed.

## Prerequisites

- AWS CLI authenticated to the target account
- Pulumi CLI
- Docker with Buildx
- Node.js 24 and npm

## Deploy

From the repository root:

```bash
./infra/scripts/bootstrap-state.sh
pulumi login "s3://llteacher-pulumi-state-$(aws sts get-caller-identity --query Account --output text)-us-west-2"
cd infra
pulumi stack init llteacher-dev \
  --secrets-provider="awskms://alias/llteacher-pulumi-state?region=us-west-2"
pulumi preview
pulumi up
cd ..
./infra/scripts/push-image.sh
pulumi -C infra config set deployService true
pulumi -C infra preview
pulumi -C infra up
```

If the stack already exists, select it with `pulumi -C infra stack select
llteacher-dev` instead of running `stack init`.

The push script uses an immutable 12-character Git SHA tag, builds an
`linux/amd64` image, pushes it to ECR, and updates `llteacher:imageTag`.
App Runner automatic deployments are disabled; run `pulumi up` to promote a
new image intentionally.

## Outputs

```bash
pulumi -C infra stack output appUrl
pulumi -C infra stack output ecrRepositoryUrl
pulumi -C infra stack output databaseEndpoint
pulumi -C infra stack output databaseSecretArn
```

The database is intentionally inaccessible from App Runner in this phase.
Do not make it public. Application database integration will add controlled
security-group ingress, an App Runner VPC connector, and outbound NAT.

## Local container smoke test

```bash
docker build -f Dockerfile.aws -t llteacher-aws:local .
docker run --rm -p 8080:8080 llteacher-aws:local
curl --fail http://localhost:8080/health
curl --fail http://localhost:8080/api/hello
```

Open `http://localhost:8080/` for the student app and
`http://localhost:8080/instructor/` for the instructor console.
