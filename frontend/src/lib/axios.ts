import axios, { AxiosError, InternalAxiosRequestConfig } from 'axios';
import { config } from '@/lib/config';
import { logger } from '@/lib/utils/logger';

const axiosInstance = axios.create({
  baseURL: config.api.baseUrl,
  withCredentials: true,
  headers: {
    'Content-Type': 'application/json',
  },
});

axiosInstance.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    logger.debug('API request', {
      component: 'AxiosClient',
      url: config.url,
      method: config.method,
    });
    return config;
  },
  (error: AxiosError) => {
    logger.error('Request error', error, { component: 'AxiosClient' });
    return Promise.reject(error);
  }
);

axiosInstance.interceptors.response.use(
  (response) => {
    logger.info('API response', {
      component: 'AxiosClient',
      status: response.status,
      url: response.config.url,
    });
    return response;
  },
  (error: AxiosError) => {
    if (error.response) {
      logger.error('API request failed', error, {
        component: 'AxiosClient',
        status: error.response.status,
        statusText: error.response.statusText,
        url: error.config?.url,
      });
    } else {
      logger.error('Network error', error, {
        component: 'AxiosClient',
        message: error.message,
      });
    }
    return Promise.reject(error);
  }
);

export default axiosInstance;
