export interface LoginCredentials {
  username: string;
  password: string;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  expires_at: string;
}

export interface AuthStatusResponse {
  required: boolean;
}

export interface ApiErrorResponse {
  detail?: string;
  code?: string;
}
