'use client';

import { useState } from 'react';

export default function DebugPage() {
  const [results, setResults] = useState<string>('');
  const [token, setToken] = useState<string>('');

  const login = async () => {
    try {
      const response = await fetch('http://localhost:8000/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          email: 'admin@example.com',
          password: 'admin123'
        })
      });
      
      const data = await response.json();
      setToken(data.access_token);
      setResults(prev => prev + '\n✅ Login successful!');
    } catch (error: any) {
      setResults(prev => prev + '\n❌ Login failed: ' + error.message);
    }
  };

  const testAPIs = async () => {
    if (!token) {
      setResults(prev => prev + '\n❌ Please login first');
      return;
    }

    try {
      // Test APIs
      const [profileResponse, plansResponse, usageResponse] = await Promise.all([
        fetch('http://localhost:8000/api/v1/users/me/profile', {
          headers: { 'Authorization': `Bearer ${token}` }
        }),
        fetch('http://localhost:8000/api/v1/users/plans', {
          headers: { 'Authorization': `Bearer ${token}` }
        }),
        fetch('http://localhost:8000/api/v1/usage', {
          headers: { 'Authorization': `Bearer ${token}` }
        })
      ]);

      const profileData = await profileResponse.json();
      const plansData = await plansResponse.json();
      const usageData = await usageResponse.json();

      // Test plan matching
      let matchingResult = 'No matching logic';
      if (profileData.subscription && plansData.length > 0) {
        const userPlanId = profileData.subscription.plan_id;
        const foundPlan = plansData.find((plan: any) => plan.id === userPlanId);
        matchingResult = `User plan_id: ${userPlanId} (${typeof userPlanId}) -> Found: ${foundPlan ? foundPlan.name : 'NOT FOUND'}`;
      }

      const resultText = `
🔍 API RESULTS:
Profile: ${JSON.stringify(profileData, null, 2)}
Plans: ${JSON.stringify(plansData, null, 2)}
Usage: ${JSON.stringify(usageData, null, 2)}
Plan Matching: ${matchingResult}
      `;
      
      setResults(resultText);
    } catch (error: any) {
      setResults(prev => prev + '\n❌ API test failed: ' + error.message);
    }
  };

  return (
    <div style={{ padding: '20px', fontFamily: 'monospace' }}>
      <h1>Debug Dashboard Data</h1>
      <button onClick={login} style={{ margin: '10px', padding: '10px' }}>
        Login as Admin
      </button>
      <button onClick={testAPIs} style={{ margin: '10px', padding: '10px' }}>
        Test APIs
      </button>
      <pre style={{ 
        background: '#f5f5f5', 
        padding: '20px', 
        marginTop: '20px',
        whiteSpace: 'pre-wrap',
        fontSize: '12px'
      }}>
        {results}
      </pre>
    </div>
  );
}
