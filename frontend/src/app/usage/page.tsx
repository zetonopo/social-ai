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
  Button,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
} from '@mui/material';
import {
  TrendingUp as TrendingUpIcon,
  Upgrade as UpgradeIcon,
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
  id: string;
  name: string;
  description: string;
  price?: number;
  features: string[];
  request_limit?: number;
}

const UsagePage: React.FC = () => {
  const { user } = useAuth();
  const [usage, setUsage] = useState<UsageData | null>(null);
  const [plans, setPlans] = useState<PlanData[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const fetchData = async () => {
    try {
      setLoading(true);
      const [usageResponse, plansResponse] = await Promise.all([
        apiClient.getUsage(),
        apiClient.getPlans(),
      ]);
      
      setUsage(usageResponse.data);
      setPlans(plansResponse.data);
      setError('');
    } catch (err: any) {
      setError('Failed to load usage data');
      console.error('Usage error:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const getUsageColor = (percentage: number) => {
    if (percentage >= 90) return 'error';
    if (percentage >= 75) return 'warning';
    return 'primary';
  };

  const formatDate = (dateString?: string) => {
    if (!dateString) return 'N/A';
    return new Date(dateString).toLocaleDateString();
  };

  const handleSubscribe = async (planId: string) => {
    try {
      await apiClient.subscribe(planId);
      await fetchData(); // Refresh data
    } catch (err: any) {
      setError('Failed to subscribe to plan');
    }
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

  return (
    <Layout>
      <Box sx={{ mb: 4 }}>
        <Typography variant="h4" component="h1" fontWeight="bold" gutterBottom>
          Usage & Billing
        </Typography>

        {error && (
          <Alert severity="error" sx={{ mb: 3 }}>
            {error}
          </Alert>
        )}

        {/* Current Usage */}
        <Card sx={{ mb: 3 }}>
          <CardContent>
            <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
              <TrendingUpIcon sx={{ mr: 1 }} />
              <Typography variant="h6">Current Usage</Typography>
            </Box>
            
            {usage ? (
              <>
                <Box sx={{ mb: 2 }}>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                    <Typography variant="body2" color="text.secondary">
                      {usage.current_usage || 0} / {usage.limit || 0} requests this month
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      {usage.percentage != null ? usage.percentage.toFixed(1) : '0.0'}%
                    </Typography>
                  </Box>
                  <LinearProgress
                    variant="determinate"
                    value={usage.percentage || 0}
                    color={getUsageColor(usage.percentage || 0)}
                    sx={{ height: 10, borderRadius: 5 }}
                  />
                </Box>
                
                <Box sx={{ display: 'flex', gap: 3, mt: 3 }}>
                  <Box>
                    <Typography variant="h4" color="primary">
                      {usage.remaining ? usage.remaining.toLocaleString() : '0'}
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      Requests Remaining
                    </Typography>
                  </Box>
                  <Box>
                    <Typography variant="h6" color="secondary">
                      {formatDate(usage.reset_date)}
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      Next Reset
                    </Typography>
                  </Box>
                </Box>
              </>
            ) : (
              <Typography>No usage data available</Typography>
            )}
          </CardContent>
        </Card>

        {/* Available Plans */}
        <Card>
          <CardContent>
            <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
              <UpgradeIcon sx={{ mr: 1 }} />
              <Typography variant="h6">Available Plans</Typography>
            </Box>

            <TableContainer component={Paper} sx={{ mt: 2 }}>
              <Table>
                <TableHead>
                  <TableRow>
                    <TableCell>Plan</TableCell>
                    <TableCell>Price</TableCell>
                    <TableCell>Requests/Month</TableCell>
                    <TableCell>Description</TableCell>
                    <TableCell>Action</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {plans && plans.length > 0 ? plans.map((plan) => {
                    const isCurrentPlan = plan.name.toLowerCase() === user?.subscription?.plan_name?.toLowerCase();
                    
                    return (
                      <TableRow key={plan.id}>
                        <TableCell>
                          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                            <Typography variant="subtitle1" fontWeight="bold">
                              {plan.name}
                            </Typography>
                            {isCurrentPlan && (
                              <Chip label="Current" color="primary" size="small" />
                            )}
                          </Box>
                        </TableCell>
                        <TableCell>
                          <Typography variant="h6" color="primary">
                            ${plan.price || 0}/month
                          </Typography>
                        </TableCell>
                        <TableCell>
                          <Typography>
                            {plan.request_limit ? plan.request_limit.toLocaleString() : 'N/A'}
                          </Typography>
                        </TableCell>
                        <TableCell>
                          <Typography variant="body2" color="text.secondary">
                            {plan.description}
                          </Typography>
                        </TableCell>
                        <TableCell>
                          {isCurrentPlan ? (
                            <Chip label="Active" color="success" />
                          ) : (
                            <Button
                              variant="contained"
                              size="small"
                              onClick={() => handleSubscribe(plan.id)}
                              disabled={loading}
                            >
                              Upgrade
                            </Button>
                          )}
                        </TableCell>
                      </TableRow>
                    );
                  }) : (
                    <TableRow>
                      <TableCell colSpan={5} align="center">
                        <Typography variant="body2" color="text.secondary">
                          No plans available
                        </Typography>
                      </TableCell>
                    </TableRow>
                  )}
                </TableBody>
              </Table>
            </TableContainer>
          </CardContent>
        </Card>
      </Box>
    </Layout>
  );
};

export default UsagePage;
