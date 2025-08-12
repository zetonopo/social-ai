# Phase 2 Documentation: User Management & Admin

## Completed Features

### 2.1 User Management Endpoints

#### User Profile Management
- **PATCH /api/v1/users/me** - Update user profile (email)
- **POST /api/v1/users/me/deactivate** - Deactivate user account

#### Subscription Management
- **GET /api/v1/users/plans** - List all available plans
- **POST /api/v1/users/subscribe** - Subscribe to a plan
- **GET /api/v1/users/my-subscription** - Get current subscription
- **GET /api/v1/users/usage** - Get usage statistics
- **POST /api/v1/users/cancel-subscription** - Cancel subscription

### 2.2 Admin Endpoints (Superuser Only)

#### User Management
- **GET /api/v1/admin/users** - List all users with pagination
- **GET /api/v1/admin/users/{id}** - Get user details by ID
- **PATCH /api/v1/admin/users/{id}** - Update user (email, active status, superuser)
- **DELETE /api/v1/admin/users/{id}** - Deactivate user

#### Subscription Management
- **GET /api/v1/admin/subscriptions** - List all subscriptions
- **POST /api/v1/admin/subscriptions/{id}/cancel** - Cancel subscription

#### Plan Management
- **POST /api/v1/admin/plans** - Create new plan
- **PATCH /api/v1/admin/plans/{id}** - Update existing plan

#### Analytics
- **GET /api/v1/admin/usage** - System-wide usage statistics

## API Usage Examples

### User Endpoints

#### Get Available Plans
```bash
curl -X GET "http://localhost:8000/api/v1/users/plans"
```

#### Login and Get Token
```bash
curl -X POST "http://localhost:8000/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "password123"}'
```

#### Subscribe to Pro Plan
```bash
curl -X POST "http://localhost:8000/api/v1/users/subscribe" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -d '{"plan_id": 2, "billing_cycle": "monthly"}'
```

#### Get Usage Statistics
```bash
curl -X GET "http://localhost:8000/api/v1/users/usage" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### Admin Endpoints

#### Login as Admin
```bash
curl -X POST "http://localhost:8000/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@example.com", "password": "admin123"}'
```

#### List All Users
```bash
curl -X GET "http://localhost:8000/api/v1/admin/users?skip=0&limit=10" \
  -H "Authorization: Bearer ADMIN_ACCESS_TOKEN"
```

#### Get System Statistics
```bash
curl -X GET "http://localhost:8000/api/v1/admin/usage" \
  -H "Authorization: Bearer ADMIN_ACCESS_TOKEN"
```

#### Update User
```bash
curl -X PATCH "http://localhost:8000/api/v1/admin/users/1" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ADMIN_ACCESS_TOKEN" \
  -d '{"is_active": false}'
```

## Database Schema Updates

### New Business Logic
- **Subscription Management**: Users can subscribe to different plans
- **Usage Tracking**: Track API usage per user per billing period
- **Plan Management**: Flexible plan system with features and pricing
- **Admin Controls**: Full admin management of users and subscriptions

### Features Implemented
1. **Plan System**: Free, Pro, Enterprise tiers
2. **Subscription Management**: Monthly/yearly billing cycles
3. **Usage Tracking**: Request counting and limits
4. **Role-Based Access**: User vs Admin permissions
5. **User Profile Management**: Email updates, account deactivation
6. **Admin Dashboard Data**: System-wide analytics

## Security Features
- **Role-based access control**: Superuser middleware for admin endpoints
- **Token-based authentication**: JWT tokens for all protected endpoints
- **Input validation**: Pydantic schemas for all requests
- **Permission checks**: Users can only access their own data
- **Admin restrictions**: Cannot delete superuser accounts

## Available Plans

### Free Plan
- 100 API requests per month
- 1 concurrent request
- Basic AI models
- Email support
- Price: $0/month

### Pro Plan
- 10,000 API requests per month
- 5 concurrent requests
- Advanced AI models
- Priority support
- Analytics dashboard
- Price: $29/month or $290/year

### Enterprise Plan
- 100,000 API requests per month
- 20 concurrent requests
- All AI models
- 24/7 phone support
- Custom integrations
- SLA guarantee
- Price: $99/month or $990/year

## Next Steps (Phase 3)
- Redis integration for caching
- Rate limiting middleware
- Real-time usage tracking
- Performance optimization
