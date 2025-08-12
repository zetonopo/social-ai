'use client';

import React, { useEffect, useState } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  LinearProgress,
  Chip,
  Alert,
  CircularProgress,
  Paper,
  IconButton,
  Tooltip,
} from '@mui/material';
import {
  TrendingUp as TrendingUpIcon,
  AccessTime as AccessTimeIcon,
  Star as StarIcon,
  Refresh as RefreshIcon,
} from '@mui/icons-material';
import Layout from '@/components/Layout';
import { useAuth } from '@/contexts/AuthContext';
import apiClient from '@/lib/api';

interface UsageData {
  current_usage?: number;
  limit?: number;
  percentage?: number;
  remaining?: number;
  reset_date?: string;
}

interface PlanData {
  id: number;
  name: string;
  description: string;
  monthly_price: number;
  yearly_price: number;
  requests_per_month: number;
  concurrent_requests: number;
  features: string[];
  is_active: boolean;
  created_at: string;
}

const DashboardPage: React.FC = () => {
  const { user, refreshUser } = useAuth();
  const [usage, setUsage] = useState<UsageData | null>(null);
  const [plans, setPlans] = useState<PlanData[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const fetchData = async () => {
    try {
      setLoading(true);
      setError('');
      
      console.log('Fetching data, authenticated:', apiClient.isAuthenticated());
      
      if (!apiClient.isAuthenticated()) {
        setError('Not authenticated. Please login first.');
        return;
      }
      
      const [usageResponse, plansResponse, userResponse] = await Promise.all([
        apiClient.getUsage(),
        apiClient.getPlans(),
        apiClient.getCurrentUser() // Get fresh user data with subscription
      ]);
      
      console.log('Raw API Responses:');
      console.log('Usage Response:', usageResponse);
      console.log('Plans Response:', plansResponse);
      console.log('User Response:', userResponse);
      
      // Handle response format - API might return {data: ...} or direct data
      const usageData = usageResponse?.data || usageResponse;
      const plansData = plansResponse?.data || plansResponse;
      const userData = userResponse?.data || userResponse;
      
      console.log('Processed Data:');
      console.log('Usage Data:', usageData);
      console.log('Plans Data:', plansData);
      console.log('User Data:', userData);
      
      setUsage(usageData);
      setPlans(Array.isArray(plansData) ? plansData : []);
      
      // Update user in auth context if needed
      if (userData && !user?.subscription && userData.subscription) {
        await refreshUser();
      }
      
      setError('');
    } catch (err: any) {
      console.error('Dashboard error:', err);
      setError(`Failed to load dashboard data: ${err.response?.data?.detail || err.message}`);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    const initDashboard = async () => {
      // Force refresh user data first
      await refreshUser();
      // Then fetch dashboard data
      await fetchData();
    };
    
    initDashboard();
  }, []);

  // Re-fetch when user changes
  useEffect(() => {
    if (user) {
      fetchData();
    }
  }, [user]);

  const currentPlan = (() => {
    // Nếu có plans và user có subscription
    if (plans?.length > 0 && user?.subscription) {
      // Tìm plan theo plan_id với type conversion
      const planId = user.subscription.plan_id;
      const foundPlan = plans.find(plan => 
        plan.id === planId || 
        plan.id === Number(planId) || 
        String(plan.id) === String(planId)
      );
      
      if (foundPlan) {
        console.log('Found plan by ID:', foundPlan);
        return foundPlan;
      }
      
      // Fallback: tìm plan theo tên
      const planByName = plans.find(plan => 
        plan.name.toLowerCase() === user.subscription?.plan_name?.toLowerCase()
      );
      
      if (planByName) {
        console.log('Found plan by name:', planByName);
        return planByName;
      }
    }
    
    // Fallback cuối: tìm Free plan
    const freePlan = plans?.find(plan => 
      plan.name.toLowerCase() === 'free'
    );
    
    console.log('Using free plan fallback:', freePlan);
    return freePlan || null;
  })();

  // Debug logs
  console.log('Dashboard Debug:', {
    plansLength: plans?.length,
    hasUserSubscription: !!user?.subscription,
    userSubscription: user?.subscription,
    plans: plans,
    currentPlan: currentPlan,
    planIdType: typeof plans?.[0]?.id,
    subscriptionPlanIdType: typeof user?.subscription?.plan_id,
    userFromAuth: user,
    authLoading: loading,
    isAuthenticated: !!user
  });

  const getUsageColor = (percentage: number) => {
    if (percentage >= 90) return 'error';
    if (percentage >= 75) return 'warning';
    return 'primary';
  };

  const formatDate = (dateString?: string) => {
    if (!dateString) return 'N/A';
    return new Date(dateString).toLocaleDateString();
  };

  if (loading) {
    return (
      <Layout>
        <Box sx={{ display: 'flex', justifyContent: 'center', mt: 4 }}>
          <CircularProgress />
        </Box>
      </Layout>
    );
  }

  if (!user) {
    return (
      <Layout>
        <Box sx={{ mt: 4 }}>
          <Alert severity="warning">
            Please log in to access the dashboard.
          </Alert>
        </Box>
      </Layout>
    );
  }

  return (
    <Layout>
      <Box sx={{ mb: 4 }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
          <Typography variant="h4" component="h1" fontWeight="bold">
            Dashboard
          </Typography>
          <Tooltip title="Refresh data">
            <IconButton onClick={fetchData} disabled={loading}>
              <RefreshIcon />
            </IconButton>
          </Tooltip>
        </Box>

        {error && (
          <Alert severity="error" sx={{ mb: 3 }}>
            {error}
          </Alert>
        )}

        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
          {/* Welcome Card */}
          <Card>
            <CardContent>
              <Typography variant="h5" gutterBottom>
                Welcome back, {user?.name || user?.email}!
              </Typography>
              <Typography variant="body1" color="text.secondary">
                Here&apos;s an overview of your account activity and usage.
              </Typography>
            </CardContent>
          </Card>

          <Box sx={{ display: 'flex', flexDirection: { xs: 'column', md: 'row' }, gap: 3 }}>
            {/* Usage Statistics */}
            <Box sx={{ flex: 2 }}>
              <Card>
                <CardContent>
                  <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                    <TrendingUpIcon sx={{ mr: 1 }} />
                    <Typography variant="h6">API Usage</Typography>
                  </Box>
                  
                  {usage ? (
                    <>
                      <Box sx={{ mb: 2 }}>
                        <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                          <Typography variant="body2" color="text.secondary">
                            {usage.current_usage || 0} / {usage.limit || 0} requests
                          </Typography>
                          <Typography variant="body2" color="text.secondary">
                            {usage.percentage != null ? usage.percentage.toFixed(1) : '0.0'}%
                          </Typography>
                        </Box>
                        <LinearProgress
                          variant="determinate"
                          value={usage.percentage || 0}
                          color={getUsageColor(usage.percentage || 0)}
                          sx={{ height: 8, borderRadius: 4 }}
                        />
                      </Box>
                      
                      <Box sx={{ display: 'flex', gap: 2 }}>
                        <Paper sx={{ p: 2, textAlign: 'center', flex: 1 }}>
                          <Typography variant="h4" color="primary">
                            {usage.remaining || 0}
                          </Typography>
                          <Typography variant="body2" color="text.secondary">
                            Requests Remaining
                          </Typography>
                        </Paper>
                        <Paper sx={{ p: 2, textAlign: 'center', flex: 1 }}>
                          <Typography variant="h4" color="secondary">
                            {formatDate(usage.reset_date)}
                          </Typography>
                          <Typography variant="body2" color="text.secondary">
                            Reset Date
                          </Typography>
                        </Paper>
                      </Box>
                    </>
                  ) : (
                    <Typography>No usage data available</Typography>
                  )}
                </CardContent>
              </Card>
            </Box>

            {/* Current Plan */}
            <Box sx={{ flex: 1 }}>
              <Card>
                <CardContent>
                  <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                    <StarIcon sx={{ mr: 1 }} />
                    <Typography variant="h6">Current Plan</Typography>
                  </Box>
                  
                  {currentPlan ? (
                    <>
                      <Typography variant="h5" gutterBottom>
                        {currentPlan.name}
                      </Typography>
                      <Typography variant="body2" color="text.secondary" gutterBottom>
                        {currentPlan.description}
                      </Typography>
                      <Typography variant="h6" color="primary" gutterBottom>
                        ${currentPlan.monthly_price || 0}/month
                      </Typography>
                      <Typography variant="body2" color="text.secondary">
                        {currentPlan.requests_per_month ? currentPlan.requests_per_month.toLocaleString() : 'N/A'} requests/month
                      </Typography>
                      
                      <Chip 
                        label={user?.subscription?.status || 'Active'} 
                        color="success" 
                        size="small" 
                        sx={{ mt: 1 }}
                      />
                    </>
                  ) : loading ? (
                    <Typography>Loading plan information...</Typography>
                  ) : (
                    <>
                      <Typography>No plan information available</Typography>
                      <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                        Debug: Plans count: {plans?.length || 0}, Has subscription: {user?.subscription ? 'Yes' : 'No'}
                      </Typography>
                    </>
                  )}
                </CardContent>
              </Card>
            </Box>
          </Box>

          <Box sx={{ display: 'flex', flexDirection: { xs: 'column', md: 'row' }, gap: 3 }}>
            {/* Account Information */}
            <Box sx={{ flex: 1 }}>
              <Card>
                <CardContent>
                  <Typography variant="h6" gutterBottom>
                    Account Information
                  </Typography>
                  <Box sx={{ mt: 2 }}>
                    <Typography variant="body2" color="text.secondary">
                      Email
                    </Typography>
                    <Typography variant="body1" gutterBottom>
                      {user?.email}
                    </Typography>
                    
                    <Typography variant="body2" color="text.secondary">
                      Member Since
                    </Typography>
                    <Typography variant="body1" gutterBottom>
                      {formatDate(user?.created_at)}
                    </Typography>
                    
                    <Typography variant="body2" color="text.secondary">
                      Account Status
                    </Typography>
                    <Chip 
                      label={user?.is_active ? 'Active' : 'Inactive'} 
                      color={user?.is_active ? 'success' : 'error'} 
                      size="small"
                    />
                  </Box>
                </CardContent>
              </Card>
            </Box>

            {/* Quick Actions */}
            <Box sx={{ flex: 1 }}>
              <Card>
                <CardContent>
                  <Typography variant="h6" gutterBottom>
                    Quick Actions
                  </Typography>
                  <Box sx={{ mt: 2 }}>
                    <Typography variant="body2" color="text.secondary" gutterBottom>
                      • View detailed usage analytics
                    </Typography>
                    <Typography variant="body2" color="text.secondary" gutterBottom>
                      • Upgrade your plan
                    </Typography>
                    <Typography variant="body2" color="text.secondary" gutterBottom>
                      • Update profile settings
                    </Typography>
                    <Typography variant="body2" color="text.secondary" gutterBottom>
                      • Manage API keys
                    </Typography>
                  </Box>
                </CardContent>
              </Card>
            </Box>
          </Box>
        </Box>
      </Box>
    </Layout>
  );
};

export default DashboardPage;
