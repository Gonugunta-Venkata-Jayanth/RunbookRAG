variable "region" {
  description = "AWS region to deploy into."
  type        = string
  default     = "ap-south-1"
}

variable "stage" {
  description = "Deployment stage, used in resource names."
  type        = string
  default     = "dev"
  validation {
    condition     = contains(["dev", "prod"], var.stage)
    error_message = "stage must be dev or prod."
  }
}

variable "lambda_zip" {
  description = "Path to the bundle produced by scripts/package_lambda.sh."
  type        = string
  default     = "../../build/lambda.zip"
}

variable "index_file" {
  description = "Path to the search index uploaded to S3 (python -m runbookrag build)."
  type        = string
  default     = "../../build/index.json"
}

variable "allowed_origin" {
  description = "CORS origin allowed to call the API, for example the dashboard URL."
  type        = string
  default     = "*"
}

variable "throttle_rate" {
  description = "Steady-state requests per second allowed by API Gateway (keeps usage inside the free tier)."
  type        = number
  default     = 10
}
