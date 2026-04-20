output "api_url" {
  description = "URL da API publica"
  value       = aws_api_gateway_stage.main.invoke_url
}

output "data_bucket_name" {
  description = "Nome do bucket S3 com os dados"
  value       = aws_s3_bucket.data.bucket
}

output "lambda_function_name" {
  description = "Nome da Lambda"
  value       = aws_lambda_function.party_builder.function_name
}
