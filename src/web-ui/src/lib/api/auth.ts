import type { components } from "../api-types";
import { ApiRequestError, type APIClient } from "./base";

export type TokenResponse = components["schemas"]["Token"];
export type User = components["schemas"]["UserResponse"];
export type UserUpdate = components["schemas"]["UserUpdate"];
export type VerifyEmailResponse = components["schemas"]["VerifyEmailResponse"];
export type ResendVerificationResponse = components["schemas"]["ResendVerificationResponse"];
export type ForgotPasswordResponse = components["schemas"]["ForgotPasswordResponse"];
export type ForgotPasswordVerifyResponse = components["schemas"]["ForgotPasswordVerifyResponse"];
export type ForgotPasswordVerifyError = components["schemas"]["ForgotPasswordVerifyError"];
export type ResetPasswordResponse = components["schemas"]["ResetPasswordResponse"];

export class VerifyCodeError extends Error {
  constructor(
    message: string,
    public attemptsRemaining: number,
  ) {
    super(message);
  }
}

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

  async forgotPassword(email: string): Promise<ForgotPasswordResponse> {
    return this.client.request<ForgotPasswordResponse>("/api/auth/forgot-password", {
      method: "POST",
      body: JSON.stringify({ email }),
    });
  }

  async forgotPasswordVerify(email: string, code: string): Promise<ForgotPasswordVerifyResponse> {
    try {
      return await this.client.request<ForgotPasswordVerifyResponse>("/api/auth/forgot-password/verify", {
        method: "POST",
        body: JSON.stringify({ email, code }),
      });
    } catch (err) {
      if (err instanceof ApiRequestError) {
        const body = err.body as ForgotPasswordVerifyError;
        throw new VerifyCodeError(err.message, body.attempts_remaining);
      }
      throw err;
    }
  }

  async resetPassword(resetToken: string, newPassword: string): Promise<ResetPasswordResponse> {
    return this.client.request<ResetPasswordResponse>("/api/auth/reset-password", {
      method: "POST",
      body: JSON.stringify({ reset_token: resetToken, new_password: newPassword }),
    });
  }
}
