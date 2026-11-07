---
title: AWS Lambda function timing out
category: aws
tags: aws, lambda, serverless, vpc
---
## Symptoms
Invocations end with "Task timed out after 3.00 seconds", API Gateway returns 504 or 503, and CloudWatch shows durations equal to the configured timeout.

## Diagnosis
Read the CloudWatch log stream for the REPORT line, which gives duration, billed duration, memory used and init duration. A long init duration indicates slow cold starts from heavy imports. A Lambda attached to a VPC has no internet access unless its private subnets route through a NAT gateway, so calls to public APIs hang until the timeout. Downstream calls without client timeouts also consume the whole budget.

## Resolution
Increase the timeout and memory; more memory also allocates more CPU. Set explicit connect and read timeouts on HTTP and database clients. Use VPC endpoints for AWS services such as S3 and DynamoDB instead of a NAT gateway. Move heavy initialisation outside the handler so warm invocations reuse it. API Gateway has a 29 second integration limit, so long work should be moved to an asynchronous queue.

## Prevention
Alarm on duration approaching the timeout and on error rate, enable X-Ray tracing to see slow dependencies, and keep deployment packages small.
