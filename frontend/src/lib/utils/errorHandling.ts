/**
 * Standardized error handling utilities for the MoodList application
 */

import { logger } from './logger';

export interface AppError {
  message: string;
  code?: string;
  statusCode?: number;
  context?: Record<string, unknown>;
}

/**
 * Standard error codes used throughout the application
 */
export const ErrorCodes = {
  // Authentication errors
  AUTH_REQUIRED: 'AUTH_REQUIRED',
  AUTH_EXPIRED: 'AUTH_EXPIRED',
  AUTH_FAILED: 'AUTH_FAILED',
  
  // API errors
  NETWORK_ERROR: 'NETWORK_ERROR',
  API_ERROR: 'API_ERROR',
  TIMEOUT: 'TIMEOUT',
  
  // Workflow errors
  WORKFLOW_START_FAILED: 'WORKFLOW_START_FAILED',
  WORKFLOW_NOT_FOUND: 'WORKFLOW_NOT_FOUND',
  WORKFLOW_EDIT_FAILED: 'WORKFLOW_EDIT_FAILED',
  
  // Validation errors
  VALIDATION_ERROR: 'VALIDATION_ERROR',
  INVALID_INPUT: 'INVALID_INPUT',
  
  // Generic errors
  UNKNOWN_ERROR: 'UNKNOWN_ERROR',
} as const;

/**
 * User-friendly error messages mapped to error codes
 */
const ERROR_MESSAGES: Record<string, string> = {
  [ErrorCodes.AUTH_REQUIRED]: 'Please log in to continue',
  [ErrorCodes.AUTH_EXPIRED]: 'Your session has expired. Please log in again',
  [ErrorCodes.AUTH_FAILED]: 'Authentication failed. Please try again',
  [ErrorCodes.NETWORK_ERROR]: 'Network error. Please check your connection',
  [ErrorCodes.API_ERROR]: 'Something went wrong. Please try again',
  [ErrorCodes.TIMEOUT]: 'Request timed out. Please try again',
  [ErrorCodes.WORKFLOW_START_FAILED]: 'Failed to start playlist creation',
  [ErrorCodes.WORKFLOW_NOT_FOUND]: 'Playlist session not found',
  [ErrorCodes.WORKFLOW_EDIT_FAILED]: 'Failed to update playlist',
  [ErrorCodes.VALIDATION_ERROR]: 'Invalid input. Please check your data',
  [ErrorCodes.INVALID_INPUT]: 'Invalid input provided',
  [ErrorCodes.UNKNOWN_ERROR]: 'An unexpected error occurred',
};

/**
 * Parse an error into a standardized AppError format
 */
export function parseError(error: unknown): AppError {
  // If it's already an AppError, return it
  if (isAppError(error)) {
    return error;
  }

  // If it's a standard Error
  if (error instanceof Error) {
    return {
      message: error.message,
      code: ErrorCodes.UNKNOWN_ERROR,
    };
  }

  // If it's a fetch response error
  if (error && typeof error === 'object' && 'status' in error) {
    const statusCode = (error as { status: number }).status;
    return {
      message: getErrorMessageFromStatus(statusCode),
      statusCode,
      code: getErrorCodeFromStatus(statusCode),
    };
  }

  // Fallback for unknown error types
  return {
    message: 'An unexpected error occurred',
    code: ErrorCodes.UNKNOWN_ERROR,
  };
}

/**
 * Check if an object is an AppError
 */
function isAppError(error: unknown): error is AppError {
  return (
    error !== null &&
    typeof error === 'object' &&
    'message' in error &&
    typeof error.message === 'string'
  );
}

/**
 * Get user-friendly error message from HTTP status code
 */
function getErrorMessageFromStatus(statusCode: number): string {
  switch (statusCode) {
    case 400:
      return 'Invalid request. Please check your input';
    case 401:
      return 'Authentication required';
    case 403:
      return 'You do not have permission to perform this action';
    case 404:
      return 'The requested resource was not found';
    case 408:
      return 'Request timed out. Please try again';
    case 429:
      return 'Too many requests. Please slow down';
    case 500:
      return 'Server error. Please try again later';
    case 503:
      return 'Service temporarily unavailable';
    default:
      return 'An unexpected error occurred';
  }
}

/**
 * Get error code from HTTP status code
 */
function getErrorCodeFromStatus(statusCode: number): string {
  switch (statusCode) {
    case 401:
      return ErrorCodes.AUTH_REQUIRED;
    case 408:
      return ErrorCodes.TIMEOUT;
    default:
      return ErrorCodes.API_ERROR;
  }
}

/**
 * Get user-friendly message from error code
 */
export function getErrorMessage(code: string): string {
  return ERROR_MESSAGES[code] || ERROR_MESSAGES[ErrorCodes.UNKNOWN_ERROR];
}

/**
 * Handle an error with logging and optional user notification
 */
export function handleError(
  error: unknown,
  context: {
    component: string;
    action?: string;
    showToast?: boolean;
    onError?: (appError: AppError) => void;
  }
): AppError {
  const appError = parseError(error);
  
  // Log the error
  logger.error(
    `Error in ${context.component}${context.action ? ` - ${context.action}` : ''}`,
    error,
    {
      component: context.component,
      errorCode: appError.code,
      ...appError.context,
    }
  );

  // Call custom error handler if provided
  if (context.onError) {
    context.onError(appError);
  }

  return appError;
}

/**
 * Create a typed API error
 */
export function createApiError(
  message: string,
  statusCode?: number,
  code?: string
): AppError {
  return {
    message,
    statusCode,
    code: code || ErrorCodes.API_ERROR,
  };
}

/**
 * Check if an error should trigger a retry
 */
export function shouldRetry(error: AppError, retryCount: number, maxRetries = 3): boolean {
  // Don't retry if we've exceeded max retries
  if (retryCount >= maxRetries) {
    return false;
  }

  // Retry on network errors and timeouts
  if (
    error.code === ErrorCodes.NETWORK_ERROR ||
    error.code === ErrorCodes.TIMEOUT
  ) {
    return true;
  }

  // Retry on 5xx server errors
  if (error.statusCode && error.statusCode >= 500 && error.statusCode < 600) {
    return true;
  }

  return false;
}

/**
 * Calculate exponential backoff delay for retries
 */
export function getRetryDelay(retryCount: number, baseDelay = 300): number {
  return Math.min(baseDelay * Math.pow(2, retryCount), 10000);
}

