import * as aws from "@pulumi/aws";
import * as pulumi from "@pulumi/pulumi";
import * as random from "@pulumi/random";

const config = new pulumi.Config();
const stack = pulumi.getStack();
const project = pulumi.getProject();
const prefix = stack.startsWith(project) ? stack : `${project}-${stack}`;
const deployService = config.getBoolean("deployService") ?? false;
const imageTag = config.get("imageTag") ?? "dev";

const tags = {
  Project: "llteacher",
  Environment: stack,
  ManagedBy: "pulumi",
};

const repository = new aws.ecr.Repository("app", {
  name: `${prefix}-app`,
  imageTagMutability: "IMMUTABLE",
  imageScanningConfiguration: { scanOnPush: true },
  forceDelete: stack !== "production",
  tags,
});

new aws.ecr.LifecyclePolicy("app", {
  repository: repository.name,
  policy: JSON.stringify({
    rules: [{
      rulePriority: 1,
      description: "Keep the 20 most recent images",
      selection: { tagStatus: "any", countType: "imageCountMoreThan", countNumber: 20 },
      action: { type: "expire" },
    }],
  }),
});

const vpc = new aws.ec2.Vpc("database", {
  cidrBlock: "10.42.0.0/16",
  enableDnsHostnames: true,
  enableDnsSupport: true,
  tags: { ...tags, Name: `${prefix}-database` },
});

const availabilityZones = aws.getAvailabilityZonesOutput({ state: "available" });
const databaseSubnets = [0, 1].map((index) => new aws.ec2.Subnet(`database-${index + 1}`, {
  vpcId: vpc.id,
  availabilityZone: availabilityZones.names.apply((names) => names[index]),
  cidrBlock: `10.42.${index + 1}.0/24`,
  mapPublicIpOnLaunch: false,
  tags: { ...tags, Name: `${prefix}-database-${index + 1}` },
}));

const databaseRouteTable = new aws.ec2.RouteTable("database", {
  vpcId: vpc.id,
  tags: { ...tags, Name: `${prefix}-database-isolated` },
});

databaseSubnets.forEach((subnet, index) => {
  new aws.ec2.RouteTableAssociation(`database-${index + 1}`, {
    subnetId: subnet.id,
    routeTableId: databaseRouteTable.id,
  });
});

const databaseSecurityGroup = new aws.ec2.SecurityGroup("database", {
  namePrefix: `${prefix}-database-`,
  description: "PostgreSQL ingress is intentionally disabled until application integration",
  vpcId: vpc.id,
  ingress: [],
  egress: [],
  tags,
});

const subnetGroup = new aws.rds.SubnetGroup("database", {
  name: `${prefix}-database`,
  subnetIds: databaseSubnets.map((subnet) => subnet.id),
  tags,
});

const databasePassword = new random.RandomPassword("database", {
  length: 32,
  special: true,
  overrideSpecial: "!#$%&*+-=?^_",
});

const database = new aws.rds.Instance("database", {
  identifier: `${prefix}-postgres`,
  engine: "postgres",
  engineVersion: "16",
  instanceClass: "db.t4g.micro",
  allocatedStorage: 20,
  maxAllocatedStorage: 100,
  storageType: "gp3",
  storageEncrypted: true,
  dbName: "llteacher",
  username: "llteacher_admin",
  password: databasePassword.result,
  port: 5432,
  dbSubnetGroupName: subnetGroup.name,
  vpcSecurityGroupIds: [databaseSecurityGroup.id],
  publiclyAccessible: false,
  multiAz: false,
  backupRetentionPeriod: 7,
  backupWindow: "10:00-11:00",
  maintenanceWindow: "sun:11:00-sun:12:00",
  autoMinorVersionUpgrade: true,
  deletionProtection: false,
  skipFinalSnapshot: true,
  applyImmediately: true,
  tags,
});

const databaseSecret = new aws.secretsmanager.Secret("database", {
  namePrefix: `${prefix}/database-`,
  description: "LLTeacher PostgreSQL connection details",
  recoveryWindowInDays: 0,
  tags,
});

new aws.secretsmanager.SecretVersion("database", {
  secretId: databaseSecret.id,
  secretString: pulumi.secret(pulumi.all([
    database.address,
    database.port,
    databasePassword.result,
  ]).apply(([host, port, password]) => JSON.stringify({
    engine: "postgres",
    host,
    port,
    dbname: "llteacher",
    username: "llteacher_admin",
    password,
  }))),
});

const ecrAccessRole = new aws.iam.Role("app-runner-ecr", {
  namePrefix: `${prefix}-ecr-`,
  assumeRolePolicy: aws.iam.assumeRolePolicyForPrincipal({
    Service: "build.apprunner.amazonaws.com",
  }),
  tags,
});

new aws.iam.RolePolicyAttachment("app-runner-ecr", {
  role: ecrAccessRole.name,
  policyArn: "arn:aws:iam::aws:policy/service-role/AWSAppRunnerServicePolicyForECRAccess",
});

const autoScaling = new aws.apprunner.AutoScalingConfigurationVersion("app", {
  autoScalingConfigurationName: `${prefix}-app`,
  maxConcurrency: 50,
  minSize: 1,
  maxSize: 2,
  tags,
});

const service = deployService ? new aws.apprunner.Service("app", {
  serviceName: `${prefix}-app`,
  sourceConfiguration: {
    autoDeploymentsEnabled: false,
    authenticationConfiguration: { accessRoleArn: ecrAccessRole.arn },
    imageRepository: {
      imageIdentifier: pulumi.interpolate`${repository.repositoryUrl}:${imageTag}`,
      imageRepositoryType: "ECR",
      imageConfiguration: {
        port: "8080",
        runtimeEnvironmentVariables: {
          NODE_ENV: "production",
        },
      },
    },
  },
  instanceConfiguration: {
    cpu: "1 vCPU",
    memory: "2 GB",
  },
  autoScalingConfigurationArn: autoScaling.arn,
  healthCheckConfiguration: {
    protocol: "HTTP",
    path: "/health",
    interval: 10,
    timeout: 5,
    healthyThreshold: 1,
    unhealthyThreshold: 5,
  },
  networkConfiguration: {
    egressConfiguration: { egressType: "DEFAULT" },
    ingressConfiguration: { isPubliclyAccessible: true },
    ipAddressType: "IPV4",
  },
  tags,
}) : undefined;

export const ecrRepositoryUrl = repository.repositoryUrl;
export const appUrl = service ? pulumi.interpolate`https://${service.serviceUrl}` : "service-disabled";
export const databaseEndpoint = database.address;
export const databaseName = database.dbName;
export const databaseSecretArn = databaseSecret.arn;
export const databasePubliclyAccessible = database.publiclyAccessible;
