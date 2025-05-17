
# OpenStack Command Center

A modern web application that allows users to control their OpenStack environment using natural language commands. This project simplifies cloud infrastructure management by translating plain English instructions into OpenStack API calls.

## Features

- **Natural Language Command Interface**: Control your OpenStack environment using simple, conversational commands
- **Terminal Emulator**: Interactive terminal with command history and syntax highlighting
- **Dashboard**: Visual representation of your OpenStack resources with metrics and management tools
- **Code Testing**: Built-in testing panel for trying commands before executing them on your infrastructure
- **User Management**: Authentication, user profiles, and collaboration features
- **Real-time Monitoring**: Monitor instance health, usage statistics, and system status

## Routes

The application includes the following routes:

| Route | Description |
|-------|-------------|
| `/` | Home page with product information and interactive demo |
| `/login` | User authentication page |
| `/signup` | New user registration page |
| `/dashboard` | Main dashboard with OpenStack resource metrics and management |
| `/terminal` | Interactive natural language command terminal |
| `/profile` | User profile management |

## File Structure

### Components

- `Terminal.tsx` - The main terminal interface for executing commands
- `CommandInput.tsx` - Input component for entering natural language commands
- `CommandHistory.tsx` - Component to display and navigate through command history
- `OutputDisplay.tsx` - Component to render command execution results
- `StatusIndicator.tsx` - Shows the current connection status to the OpenStack API
- `ParticleBackground.tsx` - Interactive 3D particle animation background
- `CodeTester.tsx` - Interactive code testing environment for users to try commands
- `ActiveUsers.tsx` - Shows currently active users collaborating on projects
- `InstancesOverview.tsx` - Displays status and metrics for OpenStack instances

### Pages

- `Home.tsx` - Landing page with product information and interactive demos
- `Login.tsx` - User authentication page
- `Signup.tsx` - New user registration page
- `Dashboard.tsx` - Main dashboard with metrics, charts, and management tools
- `Terminal.tsx` - Page that hosts the terminal component
- `NotFound.tsx` - 404 error page

### UI Components

The project uses shadcn/ui components:
- Button
- Dropdown
- Form
- Tabs
- Progress
- Toast
- Dialog
- Avatar
- Badge
- etc.

## Implementing Database Integration

To add database functionality to this project, you can follow these steps:

1. **Set up Supabase Integration**:
   - Click on the green Supabase button on the top right of the Lovable interface
   - Connect to your Supabase project or create a new one
   - This will provide authentication, database, and storage capabilities

2. **Authentication**:
   - Use Supabase Auth for user management:
   ```typescript
   import { createClient } from '@supabase/supabase-js'
   
   const supabase = createClient('YOUR_SUPABASE_URL', 'YOUR_SUPABASE_KEY')
   
   // Sign up
   const { data, error } = await supabase.auth.signUp({
     email: 'user@example.com',
     password: 'password123'
   })
   
   // Log in
   const { data, error } = await supabase.auth.signInWithPassword({
     email: 'user@example.com',
     password: 'password123'
   })
   ```

3. **Database Tables**:
   Create the following tables in your Supabase project:

   - `users` - Extended user profile information
   ```sql
   CREATE TABLE users (
     id UUID REFERENCES auth.users PRIMARY KEY,
     name TEXT,
     avatar_url TEXT,
     created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
   );
   ```

   - `instances` - OpenStack VM instances
   ```sql
   CREATE TABLE instances (
     id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
     user_id UUID REFERENCES users(id),
     name TEXT NOT NULL,
     status TEXT NOT NULL,
     image TEXT NOT NULL,
     flavor TEXT NOT NULL,
     ip TEXT,
     created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
   );
   ```

   - `commands` - Command history
   ```sql
   CREATE TABLE commands (
     id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
     user_id UUID REFERENCES users(id),
     command TEXT NOT NULL,
     output TEXT,
     executed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
   );
   ```

4. **API Integration**:
   - Create a service for interacting with the OpenStack API
   - Store API credentials securely using Supabase environment variables
   - Create Edge Functions in Supabase for secure API calls

5. **State Management**:
   - Use React Context or libraries like @tanstack/react-query to manage state
   - Set up data fetching hooks that interact with your Supabase database

## Development

1. Clone the repository
2. Install dependencies: `npm install`
3. Start the development server: `npm run dev`
4. Access the application at `http://localhost:5173`

## Deployment

The application can be deployed using Lovable:
1. Open [Lovable](https://lovable.dev/projects/76678e0a-5408-4f8e-ae9b-8b808ebea5d0)
2. Click on Share -> Publish
3. Follow the deployment instructions

To connect a custom domain:
1. Navigate to Project > Settings > Domains
2. Click Connect Domain
3. Follow the instructions to set up DNS records
