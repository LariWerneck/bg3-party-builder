# --------------------------------------------------
# API Gateway — expoe a Lambda publicamente
# --------------------------------------------------

resource "aws_api_gateway_rest_api" "main" {
  name        = "${var.project_name}-${var.environment}"
  description = "BG3 Party Builder API"
}

# Recurso /party
resource "aws_api_gateway_resource" "party" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  parent_id   = aws_api_gateway_rest_api.main.root_resource_id
  path_part   = "party"
}

resource "aws_api_gateway_method" "party_get" {
  rest_api_id   = aws_api_gateway_rest_api.main.id
  resource_id   = aws_api_gateway_resource.party.id
  http_method   = "GET"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "party" {
  rest_api_id             = aws_api_gateway_rest_api.main.id
  resource_id             = aws_api_gateway_resource.party.id
  http_method             = aws_api_gateway_method.party_get.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.party_builder.invoke_arn
}

# Recurso /companion
resource "aws_api_gateway_resource" "companion" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  parent_id   = aws_api_gateway_rest_api.main.root_resource_id
  path_part   = "companion"
}

resource "aws_api_gateway_method" "companion_get" {
  rest_api_id   = aws_api_gateway_rest_api.main.id
  resource_id   = aws_api_gateway_resource.companion.id
  http_method   = "GET"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "companion" {
  rest_api_id             = aws_api_gateway_rest_api.main.id
  resource_id             = aws_api_gateway_resource.companion.id
  http_method             = aws_api_gateway_method.companion_get.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.party_builder.invoke_arn
}

# Recurso /playstyles
resource "aws_api_gateway_resource" "playstyles" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  parent_id   = aws_api_gateway_rest_api.main.root_resource_id
  path_part   = "playstyles"
}

resource "aws_api_gateway_method" "playstyles_get" {
  rest_api_id   = aws_api_gateway_rest_api.main.id
  resource_id   = aws_api_gateway_resource.playstyles.id
  http_method   = "GET"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "playstyles" {
  rest_api_id             = aws_api_gateway_rest_api.main.id
  resource_id             = aws_api_gateway_resource.playstyles.id
  http_method             = aws_api_gateway_method.playstyles_get.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.party_builder.invoke_arn
}

# Deploy
resource "aws_api_gateway_deployment" "main" {
  rest_api_id = aws_api_gateway_rest_api.main.id

  triggers = {
    redeployment = sha1(jsonencode([
      aws_api_gateway_resource.party.id,
      aws_api_gateway_resource.companion.id,
      aws_api_gateway_resource.playstyles.id,
      aws_api_gateway_method.party_get.id,
      aws_api_gateway_method.companion_get.id,
      aws_api_gateway_method.playstyles_get.id,
      aws_api_gateway_integration.party.id,
      aws_api_gateway_integration.companion.id,
      aws_api_gateway_integration.playstyles.id,
    ]))
  }

  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_api_gateway_stage" "main" {
  deployment_id = aws_api_gateway_deployment.main.id
  rest_api_id   = aws_api_gateway_rest_api.main.id
  stage_name    = var.environment
}
