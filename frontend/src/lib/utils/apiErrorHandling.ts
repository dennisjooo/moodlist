/**
 * Extract user-friendly error message from API response
 */
export async function extractErrorMessage(response: Response): Promise<string> {
  const defaultMessage = `Request failed: ${response.status} ${response.statusText}`;

  try {
    const contentType = response.headers.get('content-type');
    if (!contentType?.includes('application/json')) {
      return defaultMessage;
    }

    const errorData = await response.json();

    // Backend returns error in detail.message for rate limits
    if (errorData.detail?.message) {
      return errorData.detail.message;
    }

    // FastAPI validation errors
    if (errorData.detail && typeof errorData.detail === 'string') {
      return errorData.detail;
    }

    // Generic message field
    if (errorData.message) {
      return errorData.message;
    }

    // Array of validation errors
    if (Array.isArray(errorData.detail)) {
      return errorData.detail.map((e: any) => e.msg).join(', ');
    }
  } catch {
    // If parsing fails, use default message
  }

  return defaultMessage;
}

/**
 * Standardized API error class
 */
export class APIError extends Error {
  constructor(
    public readonly status: number,
    message: string,
    public readonly endpoint?: string
  ) {
    super(message);
    this.name = 'APIError';
  }

  /**
   * Check if error is a specific HTTP status
   */
  isStatus(status: number): boolean {
    return this.status === status;
  }

  /**
   * Check if error is a client error (4xx)
   */
  isClientError(): boolean {
    return this.status >= 400 && this.status < 500;
  }

  /**
   * Check if error is a server error (5xx)
   */
  isServerError(): boolean {
    return this.status >= 500 && this.status < 600;
  }
}
