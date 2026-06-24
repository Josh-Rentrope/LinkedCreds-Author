
variable "do_token" { type = string }
variable "spaces_access_id" { type = string }
variable "spaces_secret_key" { type = string }


variable "google_client_id" {
  description = "Google OAuth Client ID"
  type        = string
}

variable "google_client_secret" {
  description = "Google OAuth Client Secret"
  type        = string
  sensitive   = true
}

variable "firebase_api_key" {
  description = "Firebase API Key"
  type        = string
  sensitive   = true
}

variable "firebase_auth_domain" {
  description = "Firebase Auth Domain"
  type        = string
}

variable "firebase_project_id" {
  description = "Firebase Project ID"
  type        = string
}

variable "firebase_storage_bucket" {
  description = "Firebase Storage Bucket"
  type        = string
}

variable "firebase_messaging_sender_id" {
  description = "Firebase Messaging Sender ID"
  type        = string
}

variable "firebase_app_id" {
  description = "Firebase App ID"
  type        = string
}

variable "nextauth_secret" {
  description = "NextAuth Secret string"
  type        = string
  sensitive   = true
}


variable "aws_region" {
  description = "AWS Region"
  type        = string
}


variable "backend_api_url" {
  description = "Backend API URL"
  type        = string
}


variable "NEXT_PUBLIC_SKILLS_API_URL" {
  description = "Skills API URL"
  type        = string
}


variable "NEXTAUTH_URL" {
  description = "NextAuth URL"
  type        = string
}
