'use client';

import React, { useEffect, useState } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Button,
  Chip,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  Alert,
  CircularProgress,
} from '@mui/material';
import {
  Check as CheckIcon,
  Star as StarIcon,
  Business as BusinessIcon,
  Person as PersonIcon,
} from '@mui/icons-material';
import Layout from '@/components/Layout';
import { useAuth } from '@/contexts/AuthContext';
import apiClient from '@/lib/api';

interface PlanData {
  id: string;
  name: string;
  description: string;
  monthly_price: number;
  yearly_price: number;
  requests_per_month: number;
  concurrent_requests: number;
  features: string[];
  is_active: boolean;
}

const PlansPage: React.FC = () => {
  const { user } = useAuth();
  const [plans, setPlans] = useState<PlanData[]>([]);
  const [loading, setLoading] = useState(true);
  const [subscribing, setSubscribing] = useState<string | null>(null);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  const fetchPlans = async () => {
    try {
      setLoading(true);
      const response = await apiClient.getPlans();
      setPlans(response.data || []);
      setError('');
    } catch (err: any) {
      setError('Failed to load plans');
      console.error('Plans error:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchPlans();
  }, []);

  const handleSubscribe = async (planId: string, planName: string) => {
    try {
      setSubscribing(planId);
      await apiClient.subscribe(planId);
      setSuccess(`Successfully subscribed to ${planName} plan!`);
      setError('');
      
      // Refresh user data to update current plan
      setTimeout(() => {
        window.location.reload();
      }, 1500);
    } catch (err: any) {
      setError(`Failed to subscribe to ${planName} plan`);
    } finally {
      setSubscribing(null);
    }
  };

  const getPlanIcon = (planName: string) => {
    switch (planName.toLowerCase()) {
      case 'free':
        return <PersonIcon />;
      case 'pro':
        return <StarIcon />;
      case 'enterprise':
        return <BusinessIcon />;
      default:
        return <PersonIcon />;
    }
  };

  const getPlanColor = (planName: string) => {
    switch (planName.toLowerCase()) {
      case 'free':
        return 'default';
      case 'pro':
        return 'primary';
      case 'enterprise':
        return 'secondary';
      default:
        return 'default';
    }
  };

  const isCurrentPlan = (planName: string) => {
    return planName.toLowerCase() === user?.subscription?.plan_name?.toLowerCase();
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
        <Typography variant="h4" component="h1" fontWeight="bold" gutterBottom align="center">
          Choose Your Plan
        </Typography>
        
        <Typography variant="h6" color="text.secondary" align="center" sx={{ mb: 4 }}>
          Select the perfect plan for your AI API needs
        </Typography>

        {error && (
          <Alert severity="error" sx={{ mb: 3 }}>
            {error}
          </Alert>
        )}

        {success && (
          <Alert severity="success" sx={{ mb: 3 }}>
            {success}
          </Alert>
        )}

        <Box 
          sx={{ 
            display: 'flex', 
            flexWrap: 'wrap', 
            gap: 3, 
            justifyContent: 'center',
            maxWidth: 1200,
            mx: 'auto',
            mt: 2
          }}
        >
          {plans.map((plan) => {
            const isCurrent = isCurrentPlan(plan.name);
            const planColor = getPlanColor(plan.name);
            
            return (
              <Box 
                key={plan.id}
                sx={{ 
                  width: { xs: '100%', sm: '100%', md: 'calc(33.333% - 16px)' },
                  minWidth: 300,
                  maxWidth: 400,
                  position: 'relative',
                  pt: plan.name.toLowerCase() === 'pro' ? 3 : 0
                }}
              >
                <Card 
                  sx={{ 
                    height: '100%',
                    display: 'flex',
                    flexDirection: 'column',
                    position: 'relative',
                    border: isCurrent ? 2 : 1,
                    borderColor: isCurrent ? 'primary.main' : 'divider',
                    ...(plan.name.toLowerCase() === 'pro' && {
                      boxShadow: 4,
                      transform: 'scale(1.05)',
                    })
                  }}
                >
                  {plan.name.toLowerCase() === 'pro' && (
                    <Box
                      sx={{
                        position: 'absolute',
                        top: 16,
                        left: '50%',
                        transform: 'translateX(-50%)',
                        bgcolor: 'primary.main',
                        color: 'white',
                        px: 2,
                        py: 0.5,
                        borderRadius: 1,
                        fontSize: '0.75rem',
                        fontWeight: 'bold',
                        zIndex: 1,
                        whiteSpace: 'nowrap'
                      }}
                    >
                      MOST POPULAR
                    </Box>
                  )}
                  
                  <CardContent sx={{ flexGrow: 1, textAlign: 'center' }}>
                    {/* Plan Header */}
                    <Box sx={{ mb: 3 }}>
                      <Box sx={{ display: 'flex', justifyContent: 'center', mb: 1 }}>
                        {getPlanIcon(plan.name)}
                      </Box>
                      <Typography variant="h5" fontWeight="bold" gutterBottom>
                        {plan.name}
                        {isCurrent && (
                          <Chip 
                            label="Current" 
                            color="primary" 
                            size="small" 
                            sx={{ ml: 1 }}
                          />
                        )}
                      </Typography>
                      <Typography variant="body2" color="text.secondary">
                        {plan.description}
                      </Typography>
                    </Box>

                    {/* Pricing */}
                    <Box sx={{ mb: 3 }}>
                      <Typography variant="h3" fontWeight="bold" color="primary">
                        ${plan.monthly_price}
                      </Typography>
                      <Typography variant="body2" color="text.secondary">
                        per month
                      </Typography>
                      {plan.yearly_price > 0 && (
                        <Typography variant="body2" color="text.secondary">
                          ${plan.yearly_price}/year (save ${(plan.monthly_price * 12 - plan.yearly_price).toFixed(0)})
                        </Typography>
                      )}
                    </Box>

                    {/* Key Stats */}
                    <Box sx={{ mb: 3 }}>
                      <Typography variant="h6" color="primary">
                        {plan.requests_per_month.toLocaleString()}
                      </Typography>
                      <Typography variant="body2" color="text.secondary">
                        API requests per month
                      </Typography>
                      
                      <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                        Up to {plan.concurrent_requests} concurrent requests
                      </Typography>
                    </Box>

                    {/* Features */}
                    <List dense sx={{ mb: 3 }}>
                      {plan.features.map((feature, index) => (
                        <ListItem key={index} sx={{ px: 0 }}>
                          <ListItemIcon sx={{ minWidth: 32 }}>
                            <CheckIcon color="primary" fontSize="small" />
                          </ListItemIcon>
                          <ListItemText 
                            primary={feature}
                            primaryTypographyProps={{ variant: 'body2' }}
                          />
                        </ListItem>
                      ))}
                    </List>

                    {/* Action Button */}
                    <Box sx={{ mt: 'auto' }}>
                      {isCurrent ? (
                        <Button
                          variant="outlined"
                          fullWidth
                          disabled
                          size="large"
                        >
                          Current Plan
                        </Button>
                      ) : (
                        <Button
                          variant={plan.name.toLowerCase() === 'pro' ? 'contained' : 'outlined'}
                          color={planColor as any}
                          fullWidth
                          size="large"
                          onClick={() => handleSubscribe(plan.id, plan.name)}
                          disabled={subscribing === plan.id}
                        >
                          {subscribing === plan.id ? (
                            <CircularProgress size={24} />
                          ) : (
                            `Choose ${plan.name}`
                          )}
                        </Button>
                      )}
                    </Box>
                  </CardContent>
                </Card>
              </Box>
            );
          })}
        </Box>

        {/* FAQ or Additional Info */}
        <Box sx={{ mt: 6, textAlign: 'center' }}>
          <Typography variant="h6" gutterBottom>
            Need help choosing?
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            All plans include access to our AI models and email support.
            You can upgrade or downgrade at any time.
          </Typography>
          <Button variant="text" color="primary">
            Contact Sales
          </Button>
        </Box>
      </Box>
    </Layout>
  );
};

export default PlansPage;
