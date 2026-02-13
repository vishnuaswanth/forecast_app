# Centene Forecasting - Technical Architecture

> **Testing**: Open `docs/diagrams/test_diagrams.html` in a browser to validate all diagrams render correctly.

---

## 1. High-Level System Architecture

```mermaid
flowchart TB
    subgraph Client["Client Layer"]
        Browser["Web Browser"]
        WS["WebSocket Client"]
    end

    subgraph Django["Django Frontend - ASGI"]
        subgraph Auth["Authentication"]
            LDAP["LDAP Backend"]
            Session["Session Manager"]
            Permissions["Permission System"]
        end

        subgraph WebLayer["Web Layer"]
            Views["Views"]
            Templates["Templates"]
            Static["Static Files"]
        end

        subgraph Business["Business Logic"]
            Services["Services"]
            Validators["Validators"]
            Serializers["Serializers"]
        end

        subgraph Integration["Integration Layer"]
            Repository["Repository Pattern"]
            WSConsumer["WebSocket Consumers"]
        end

        subgraph Background["Background Processing"]
            DjangoQ["Django-Q Workers"]
            Tasks["Async Tasks"]
        end

        subgraph CacheLayer["Caching Layer"]
            LocMem["In-Memory Cache"]
            FileCache["File-Based Cache"]
        end
    end

    subgraph External["External Services"]
        LDAPServer["Corporate LDAP Server"]
        FastAPI["FastAPI Backend"]
        Database[(Database)]
    end

    Browser -->|HTTP/HTTPS| Views
    Browser -->|Static Assets| Static
    WS -->|WebSocket| WSConsumer

    Views --> Auth
    LDAP -->|Validate| LDAPServer
    Auth --> Session
    Session --> Permissions

    Views --> Services
    Services --> Validators
    Validators --> Repository
    Services --> Serializers
    Serializers --> Views

    Repository -->|REST API| FastAPI
    FastAPI --> Database

    Views -->|Queue Task| DjangoQ
    DjangoQ --> Tasks
    Tasks --> Repository
    Tasks -->|Progress| WSConsumer

    Services --> CacheLayer
    Repository --> CacheLayer
```

---

## 2. Data Flow Architecture

```mermaid
flowchart LR
    subgraph Request["Request Flow"]
        User((User)) --> UI[Web UI]
        UI --> View[View Layer]
        View --> Service[Service Layer]
        Service --> Validator[Validation]
        Validator --> Repo[Repository]
        Repo --> API[Backend API]
    end

    subgraph Response["Response Flow"]
        API2[Backend API] --> Repo2[Repository]
        Repo2 --> Serial[Serializer]
        Serial --> View2[View Layer]
        View2 --> Template[Template or JSON]
        Template --> UI2[Web UI]
    end

    subgraph Cache["Cache Layer"]
        CacheCheck{Cache Check}
        CacheStore[(Cache Store)]
    end

    Service --> CacheCheck
    CacheCheck -->|Hit| Serial
    CacheCheck -->|Miss| Validator
    Repo2 --> CacheStore
```

---

## 3. Authentication and Authorization Flow

```mermaid
sequenceDiagram
    participant U as User
    participant D as Django
    participant L as LDAP Server
    participant S as Session
    participant P as Permissions

    U->>D: Login Request
    D->>L: Bind and Validate Credentials
    L-->>D: User Attributes
    D->>D: Create or Update User Record
    D->>D: Check Group Membership
    alt Has Valid Groups
        D->>S: Create Session
        S->>P: Load Permissions
        P-->>U: Redirect to Dashboard
    else No Groups
        D-->>U: Access Denied
    end

    Note over U,P: Subsequent Requests
    U->>D: Protected Resource
    D->>S: Validate Session
    S->>P: Check Permission
    alt Authorized
        P-->>U: Resource Content
    else Unauthorized
        P-->>U: 403 Forbidden
    end
```

---

## 4. File Upload and Background Processing

```mermaid
sequenceDiagram
    participant U as User
    participant V as View
    participant Q as Django-Q
    participant W as WebSocket
    participant R as Repository
    participant B as Backend API
    participant C as Cache

    U->>V: Upload File
    V->>V: Validate File Type
    V->>V: Store in Database
    V->>Q: Queue Processing Task
    V-->>U: Upload Accepted

    U->>W: Connect WebSocket

    loop Processing Chunks
        Q->>Q: Process Data Chunk
        Q->>W: Progress Update
        W-->>U: Real-time Progress
    end

    Q->>R: Send Processed Data
    R->>B: API Call
    B-->>R: Success
    Q->>C: Invalidate Related Caches
    Q->>W: Complete Notification
    W-->>U: Processing Complete
```

---

## 5. Caching Strategy

```mermaid
flowchart TB
    subgraph TTL["Cache TTL Configuration"]
        Fast["Fast: 5-30s"]
        Medium["Medium: 5 min"]
        Long["Long: 15 min"]
        Persist["Persistent: 1 hour"]
    end

    subgraph Types["Cache Types"]
        Exec["Execution List"]
        Progress["In-Progress Details"]
        Cascade["Filter Dropdowns"]
        Data["Data Tables"]
        Schema["Schema Metadata"]
        Complete["Completed Tasks"]
    end

    subgraph Backends["Cache Backends"]
        LocMem["In-Memory - Development"]
        File["File-Based - Staging"]
        Redis["Redis - Production"]
    end

    Fast --> Exec
    Fast --> Progress
    Medium --> Cascade
    Long --> Data
    Long --> Schema
    Persist --> Complete

    Types --> Backends

    subgraph Invalidation["Cache Invalidation"]
        Upload["File Upload"] --> Clear["Clear Related Caches"]
        Clear --> Forecast["Forecast Cache"]
        Clear --> Roster["Roster Cache"]
        Clear --> Summary["Summary Cache"]
        Clear --> CascadeC["Cascade Filters"]
    end
```

---

## 6. Component Architecture

```mermaid
flowchart TB
    subgraph Frontend["Django Application"]
        subgraph Views["View Modules"]
            CoreViews["Core Views"]
            ManagerView["Manager Dashboard"]
            ExecutionView["Execution Monitoring"]
            EditView["Edit and Allocation"]
            ConfigView["Configuration"]
            CacheView["Cache Management"]
        end

        subgraph Services["Service Layer"]
            DataSvc["DataView Service"]
            MgrSvc["Manager Service"]
            ExecSvc["Execution Service"]
            EditSvc["Edit Service"]
            ConfigSvc["Configuration Service"]
        end

        subgraph Utils["Utilities"]
            CacheUtil["Cache Utils"]
            AuthUtil["Auth Helpers"]
            FileUtil["File Validation"]
            TableUtil["Table Rendering"]
        end
    end

    subgraph Core["Core Module"]
        UserModel["Custom User Model"]
        FileModel["Upload Tracking"]
        LDAPAuth["LDAP Backend"]
        Config["Configuration Classes"]
    end

    subgraph Chat["Chat Module"]
        ChatConsumer["WebSocket Consumer"]
        ChatService["Chat Service"]
        ChatModels["Conversation Models"]
    end

    Views --> Services
    Services --> Utils
    Frontend --> Core
    Frontend --> Chat
```

---

## 7. Deployment Architecture

```mermaid
flowchart TB
    subgraph LoadBalancer["Load Balancer"]
        LB[LB]
    end

    subgraph AppServers["Application Tier"]
        App1["Django Instance 1"]
        App2["Django Instance 2"]
    end

    subgraph Workers["Background Workers"]
        W1["Django-Q Worker 1"]
        W2["Django-Q Worker 2"]
        W3["Django-Q Worker 3"]
        W4["Django-Q Worker 4"]
    end

    subgraph CacheTier["Cache Layer"]
        Redis[("Redis Cache")]
    end

    subgraph Backend["Data Backend"]
        FastAPI["FastAPI Service"]
        DB[("Database")]
    end

    subgraph External["External Services"]
        LDAP["Corporate LDAP"]
    end

    LB --> App1
    LB --> App2

    App1 --> Workers
    App2 --> Workers

    App1 --> Redis
    App2 --> Redis
    Workers --> Redis

    App1 --> FastAPI
    App2 --> FastAPI
    Workers --> FastAPI

    FastAPI --> DB

    App1 --> LDAP
    App2 --> LDAP
```

---

## 8. Technology Stack

```mermaid
flowchart TB
    subgraph App["Centene Forecasting Platform"]
        subgraph BackendStack["Backend"]
            Django["Django 4.x"]
            Channels["Django Channels"]
            DjangoQ["Django-Q"]
            Daphne["Daphne ASGI"]
        end

        subgraph FrontendStack["Frontend"]
            jQuery["jQuery"]
            DataTables["DataTables"]
            Select2["Select2"]
            SweetAlert["SweetAlert2"]
        end

        subgraph AuthStack["Authentication"]
            LDAPInt["LDAP Integration"]
            SessionMgmt["Session Management"]
            RBAC["Role-Based Access"]
        end

        subgraph DataStack["Data Layer"]
            RepoPattern["Repository Pattern"]
            FastAPIBackend["FastAPI Backend"]
            MultiCache["Multi-Tier Caching"]
        end

        subgraph RealTimeStack["Real-Time"]
            WebSocket["WebSocket"]
            ProgressStream["Progress Streaming"]
            LiveUpdates["Live Updates"]
        end

        subgraph DevOpsStack["DevOps"]
            WhiteNoise["WhiteNoise Static"]
            FileCache["File-Based Cache"]
            BGWorkers["Background Workers"]
        end
    end
```

---

## Key Design Patterns

| Pattern | Usage |
|---------|-------|
| **Repository** | APIClient abstracts all backend communication |
| **Layered Architecture** | Views - Services - Validators - Repository |
| **Decorator-Based Caching** | cache_with_ttl on expensive operations |
| **Configuration Classes** | Centralized validated business configuration |
| **Middleware Pipeline** | Authentication - Session - Permissions |
| **Async Processing** | Django-Q for long-running tasks |
| **Real-Time Updates** | WebSocket for progress streaming |
| **Retry Strategy** | Exponential backoff on API failures |

---

## Security Measures

- **Authentication**: Corporate LDAP integration
- **Authorization**: Role-based permission system (Admin, Manager, Viewer)
- **Session Management**: Django session framework with secure cookies
- **CSRF Protection**: Django middleware enabled
- **File Validation**: Type checking before processing
- **Input Validation**: Dedicated validator layer
- **Error Handling**: Custom middleware for graceful failures
