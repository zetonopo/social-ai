'use client';

import React, { useEffect, useState } from 'react';
import { Box, Typography, Card, CardContent, Button } from '@mui/material';
import apiClient from '@/lib/api';

const DebugPlansPage: React.FC = () => {
  const [plansData, setPlansData] = useState<any>(null);
  const [usageData, setUsageData] = useState<any>(null);
  const [error, setError] = useState<string>('');

  const testAPI = async () => {
    try {
      console.log('Testing plans API...');
      const plansResponse = await apiClient.getPlans();
      console.log('Plans response:', plansResponse);
      setPlansData(plansResponse);

      console.log('Testing usage API...');
      const usageResponse = await apiClient.getUsage();
      console.log('Usage response:', usageResponse);
      setUsageData(usageResponse);

      setError('');
    } catch (err: any) {
      console.error('API Error:', err);
      setError(err.message || 'Unknown error');
    }
  };

  useEffect(() => {
    testAPI();
  }, []);

  return (
    <Box sx={{ p: 4 }}>
      <Typography variant="h4" gutterBottom>
        Debug Plans & Usage API
      </Typography>

      <Button variant="contained" onClick={testAPI} sx={{ mb: 3 }}>
        Refresh APIs
      </Button>

      {error && (
        <Card sx={{ mb: 3, bgcolor: 'error.light' }}>
          <CardContent>
            <Typography color="error">Error: {error}</Typography>
          </CardContent>
        </Card>
      )}

      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            Plans API Response:
          </Typography>
          <pre style={{ whiteSpace: 'pre-wrap', fontSize: '12px' }}>
            {JSON.stringify(plansData, null, 2)}
          </pre>
        </CardContent>
      </Card>

      <Card>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            Usage API Response:
          </Typography>
          <pre style={{ whiteSpace: 'pre-wrap', fontSize: '12px' }}>
            {JSON.stringify(usageData, null, 2)}
          </pre>
        </CardContent>
      </Card>
    </Box>
  );
};

export default DebugPlansPage;
