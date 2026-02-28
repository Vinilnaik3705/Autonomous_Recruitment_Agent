import React from 'react';
import { useAuth } from '../context/AuthContext';

/**
 * ProtectedRoute - Conditionally render component based on role and permissions.
 * 
 * Usage:
 *   <ProtectedRoute role="recruiter">
 *     <YourComponent />
 *   </ProtectedRoute>
 * 
 *   <ProtectedRoute role={["recruiter", "super_admin"]}>
 *     <YourComponent />
 *   </ProtectedRoute>
 * 
 *   <ProtectedRoute permission="upload_resumes">
 *     <YourComponent />
 *   </ProtectedRoute>
 * 
 *   <ProtectedRoute permissions={["upload_resumes", "run_screening"]} all>
 *     <YourComponent />
 *   </ProtectedRoute>
 */
export const ProtectedRoute = ({
  children,
  role,
  permission,
  permissions,
  all = false,
  fallback = null,
  requiredAll = false
}) => {
  const auth = useAuth();

  if (auth.loading) {
    return <div className="flex items-center justify-center p-4 text-gray-500">Loading...</div>;
  }

  if (!auth.isAuthenticated) {
    return fallback || <div className="flex items-center justify-center p-4 text-red-500">Please log in</div>;
  }

  // Check role-based access
  if (role) {
    if (!auth.hasRole(role)) {
      return fallback || (
        <div className="flex items-center justify-center p-4 text-red-500">
          Access denied. Required role: {Array.isArray(role) ? role.join(', ') : role}
        </div>
      );
    }
  }

  // Check single permission
  if (permission) {
    if (!auth.hasPermission(permission)) {
      return fallback || (
        <div className="flex items-center justify-center p-4 text-red-500">
          Access denied. Permission required: {permission}
        </div>
      );
    }
  }

  // Check multiple permissions
  if (permissions && permissions.length > 0) {
    if (requiredAll || all) {
      if (!auth.hasAllPermissions(permissions)) {
        return fallback || (
          <div className="flex items-center justify-center p-4 text-red-500">
            Access denied. All permissions required: {permissions.join(', ')}
          </div>
        );
      }
    } else {
      if (!auth.hasAnyPermission(permissions)) {
        return fallback || (
          <div className="flex items-center justify-center p-4 text-red-500">
            Access denied. One of these permissions required: {permissions.join(', ')}
          </div>
        );
      }
    }
  }

  return children;
};

/**
 * Show component only if user has role
 */
export const ShowIfRole = ({ children, role }) => {
  const auth = useAuth();
  if (!auth.isAuthenticated) return null;
  if (!auth.hasRole(role)) return null;
  return children;
};

/**
 * Show component only if user has permission
 */
export const ShowIfPermission = ({ children, permission }) => {
  const auth = useAuth();
  if (!auth.isAuthenticated) return null;
  if (!auth.hasPermission(permission)) return null;
  return children;
};

/**
 * Show component only if user has any of the permissions
 */
export const ShowIfAnyPermission = ({ children, permissions = [] }) => {
  const auth = useAuth();
  if (!auth.isAuthenticated) return null;
  if (!auth.hasAnyPermission(permissions)) return null;
  return children;
};

/**
 * Show component only if user has all of the permissions
 */
export const ShowIfAllPermissions = ({ children, permissions = [] }) => {
  const auth = useAuth();
  if (!auth.isAuthenticated) return null;
  if (!auth.hasAllPermissions(permissions)) return null;
  return children;
};

/**
 * Hide component if user has role
 */
export const HideIfRole = ({ children, role }) => {
  const auth = useAuth();
  if (!auth.isAuthenticated) return children;
  if (auth.hasRole(role)) return null;
  return children;
};

/**
 * Hide component if user does NOT have permission
 */
export const HideIfMissingPermission = ({ children, permission }) => {
  const auth = useAuth();
  if (!auth.isAuthenticated) return null;
  if (!auth.hasPermission(permission)) return null;
  return children;
};
