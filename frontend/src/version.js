/**
 * Version information for the frontend.
 */

export const VERSION = '1.0.5';
export const BUILD_DATE = '2025-11-15';

export const getVersionInfo = () => {
  return {
    version: VERSION,
    buildDate: BUILD_DATE,
    component: 'frontend'
  };
};
