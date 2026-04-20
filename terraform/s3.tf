# --------------------------------------------------
# S3 — dados da aplicacao
# --------------------------------------------------

resource "aws_s3_bucket" "data" {
  bucket = "${var.project_name}-data-${var.environment}"
}

resource "aws_s3_bucket_versioning" "data" {
  bucket = aws_s3_bucket.data.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "data" {
  bucket = aws_s3_bucket.data.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "data" {
  bucket                  = aws_s3_bucket.data.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Upload dos JSONs de dados
resource "aws_s3_object" "companions" {
  bucket       = aws_s3_bucket.data.bucket
  key          = "companions.json"
  source       = "${path.module}/../data/companions.json"
  content_type = "application/json"
  etag         = filemd5("${path.module}/../data/companions.json")
}

resource "aws_s3_object" "approval_events" {
  bucket       = aws_s3_bucket.data.bucket
  key          = "approval_events.json"
  source       = "${path.module}/../data/approval_events.json"
  content_type = "application/json"
  etag         = filemd5("${path.module}/../data/approval_events.json")
}

resource "aws_s3_object" "pages" {
  bucket       = aws_s3_bucket.data.bucket
  key          = "pages.json"
  source       = "${path.module}/../data/pages.json"
  content_type = "application/json"
  etag         = filemd5("${path.module}/../data/pages.json")
}
