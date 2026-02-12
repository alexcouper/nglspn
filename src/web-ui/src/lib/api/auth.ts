import type { components } from "../api-types";
import type { APIClient } from "./base";

export type TokenResponse = components["schemas"]["Token"];
export type User = components["schemas"]["UserResponse"];
export type UserUpdate = components["schemas"]["UserUpdate"];
export type VerifyEmailResponse = components["schemas"]["VerifyEmailResponse"];
export type ResendVerificationResponse = components["schemas"]["ResendVerificationResponse"];

export class AuthClient {
  constructor(private client: APIClient) {}

  async register(data: {
    email: string;
    password: string;
    kennitala: string;
  }): Promise<User> {
    return this.client.request<User>("/api/auth/register", {
      method: "POST",
      body: JSON.stringify({
        ...data,
        first_name: "",
        last_name: "",
      }),
    });
  }

  async login(email: string, password: string): Promise<TokenResponse> {
    const response = await this.client.request<TokenResponse>("/api/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    });
    this.client.setTokens(response.access_token, response.refresh_token);
    return response;
  }

  async getCurrentUser(): Promise<User> {
    return this.client.request<User>("/api/auth/me");
  }

  async updateCurrentUser(data: UserUpdate): Promise<User> {
    return this.client.request<User>("/api/auth/me", {
      method: "PUT",
      body: JSON.stringify(data),
    });
  }

  async verifyEmail(code: string): Promise<VerifyEmailResponse> {
    return this.client.request<VerifyEmailResponse>("/api/auth/verify-email", {
      method: "POST",
      body: JSON.stringify({ code }),
    });
  }

  async resendVerification(): Promise<ResendVerificationResponse> {
    return this.client.request<ResendVerificationResponse>("/api/auth/resend-verification", {
      method: "POST",
    });
  }
}
