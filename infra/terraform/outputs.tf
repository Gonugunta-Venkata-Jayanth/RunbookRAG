output "api_url" {
  description = "Base URL of the HTTP API; set it as apiBase in frontend/config.js."
  value       = aws_apigatewayv2_stage.default.invoke_url
}

output "index_bucket" {
  description = "S3 bucket holding the search index."
  value       = aws_s3_bucket.index.id
}

output "queries_table" {
  description = "DynamoDB table holding the query log and feedback."
  value       = aws_dynamodb_table.queries.name
}
