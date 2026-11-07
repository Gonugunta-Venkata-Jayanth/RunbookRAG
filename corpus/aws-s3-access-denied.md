---
title: S3 returns AccessDenied
category: aws
tags: aws, s3, iam, kms, bucket policy
---
## Symptoms
`aws s3 cp` or an SDK call fails with "An error occurred (AccessDenied)" or HTTP 403, while other principals can read the same bucket.

## Diagnosis
Identify the caller with `aws sts get-caller-identity`. Access requires an allow in the IAM identity policy and no explicit deny in the bucket policy, a service control policy or a VPC endpoint policy. Objects encrypted with a customer managed KMS key also require kms:Decrypt on that key. For cross-account uploads, Object Ownership settings determine who owns the object. Use the IAM policy simulator and CloudTrail events to find the denying statement.

## Resolution
Grant the missing s3:GetObject, s3:PutObject or s3:ListBucket action on the correct ARN; note that ListBucket applies to the bucket ARN and object actions apply to `bucket/*`. Add kms:Decrypt for encrypted objects. Remove or scope explicit deny statements. Keep Block Public Access enabled and share data through presigned URLs rather than public ACLs.

## Prevention
Define bucket and IAM policies in infrastructure as code, use IAM Access Analyzer to review access, and grant least-privilege roles per workload.
