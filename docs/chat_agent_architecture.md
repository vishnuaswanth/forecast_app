# Chat Agent - Technical Architecture

> **AI-Powered Conversational Interface for Workforce Forecasting**

---

## 1. High-Level Architecture

```mermaid
flowchart TB
    subgraph Client["Client Layer"]
        Browser["Web Browser"]
        ChatWidget["Chat Widget JS"]
    end

    subgraph ChatAgent["Chat Agent"]
        subgraph WebSocket["Real-Time Layer"]
            Consumer["WebSocket Consumer"]
            MsgRouter["Message Router"]
        end

        subgraph Processing["Processing Layer"]
            ChatService["Chat Service"]
            Preprocessor["Message Preprocessor"]
            EntityExtract["Entity Extraction"]
        end

        subgraph AI["AI Layer"]
            LLMService["LLM Service"]
            IntentClass["Intent Classifier"]
            ToolExec["Tool Executor"]
        end

        subgraph State["State Management"]
            ContextMgr["Context Manager"]
            LocalCache["Local Cache"]
            DBPersist["Database"]
        end
    end

    subgraph External["External Services"]
        LLM["LLM Provider"]
        BackendAPI["Forecast API"]
        Database[(Data Store)]
    end

    Browser --> ChatWidget
    ChatWidget -->|WebSocket| Consumer
    Consumer --> MsgRouter

    MsgRouter --> ChatService
    ChatService --> Preprocessor
    Preprocessor --> EntityExtract
    ChatService --> LLMService
    LLMService --> IntentClass
    LLMService --> ToolExec

    ChatService --> ContextMgr
    ContextMgr --> LocalCache
    ContextMgr --> DBPersist

    LLMService -->|API| LLM
    ToolExec -->|REST| BackendAPI
    BackendAPI --> Database
```

---

## 2. Message Processing Flow

```mermaid
sequenceDiagram
    participant U as User
    participant W as WebSocket
    participant C as ChatService
    participant P as Preprocessor
    participant L as LLM Service
    participant T as Tools
    participant A as Forecast API

    U->>W: Send Message
    W->>C: Route Message

    C->>P: Sanitize and Preprocess
    P->>P: Extract Entities
    P->>P: Tag Message
    P-->>C: Preprocessed Message

    C->>C: Update Context

    C->>L: Classify Intent
    L->>L: Analyze with Context
    L-->>C: Intent Category + Params

    C-->>W: Show Confirmation
    W-->>U: Confirm Intent?

    U->>W: Confirm
    W->>C: Execute Action

    C->>T: Call Tool
    T->>A: Fetch Data
    A-->>T: Results
    T-->>C: Formatted Response

    C-->>W: Send Results
    W-->>U: Display Data
```

---

## 3. Intent Classification System

```mermaid
flowchart LR
    subgraph Input["User Input"]
        Msg["User Message"]
    end

    subgraph Preprocess["Preprocessing"]
        Sanitize["Input Sanitization"]
        Spell["Spell Correction"]
        Extract["Entity Extraction"]
        Tag["Message Tagging"]
    end

    subgraph Classify["Intent Classification"]
        LLM["LLM Analysis"]
        Context["Context Aware"]
    end

    subgraph Intents["Intent Categories"]
        Forecast["Get Forecast Data"]
        Reports["List Reports"]
        Roster["Get Roster"]
        ModifyCPH["Modify CPH"]
        ClearCtx["Clear Context"]
        UpdateCtx["Update Filters"]
    end

    subgraph Execute["Execution"]
        Confirm["User Confirmation"]
        Tool["Tool Execution"]
        Response["Generate Response"]
    end

    Msg --> Sanitize
    Sanitize --> Spell
    Spell --> Extract
    Extract --> Tag
    Tag --> LLM
    LLM --> Context
    Context --> Intents
    Intents --> Confirm
    Confirm --> Tool
    Tool --> Response
```

---

## 4. Context Management

```mermaid
flowchart TB
    subgraph Conversation["Conversation Context"]
        Report["Active Report Type"]
        TimeCtx["Month and Year"]
        Filters["Active Filters"]
        Prefs["User Preferences"]
    end

    subgraph Persistence["Persistence Chain"]
        Redis["Redis Cache"]
        Local["Local Memory"]
        DB["Database"]
    end

    subgraph Operations["Context Operations"]
        Get["Get Context"]
        Update["Update Context"]
        Clear["Clear Context"]
        Merge["Merge Entities"]
    end

    Conversation --> Operations

    Get --> Redis
    Redis -->|Miss| Local
    Local -->|Miss| DB
    DB -->|Miss| New["Create New"]

    Update --> Redis
    Update --> Local
    Update --> DB
```

---

## 5. WebSocket Communication

```mermaid
flowchart LR
    subgraph Client["Browser Client"]
        Widget["Chat Widget"]
        State["Connection State"]
        Queue["Message Queue"]
    end

    subgraph Messages["Message Types"]
        UserMsg["user_message"]
        Confirm["confirm_category"]
        Reject["reject_category"]
        NewConv["new_conversation"]
    end

    subgraph Responses["Response Types"]
        Assistant["assistant_response"]
        ToolResult["tool_result"]
        System["system_message"]
        Error["error_message"]
    end

    subgraph Features["Features"]
        Reconnect["Auto Reconnect"]
        Backoff["Exponential Backoff"]
        StatusInd["Connection Status"]
    end

    Widget --> Messages
    Messages -->|WebSocket| Responses
    Responses --> Widget

    State --> Reconnect
    Reconnect --> Backoff
    Widget --> StatusInd
```

---

## 6. Tool Execution Framework

```mermaid
flowchart TB
    subgraph Tools["Available Tools"]
        ForecastTool["Forecast Data Tool"]
        ReportsTool["Available Reports Tool"]
        ValidateTool["Validation Tool"]
        UITool["UI Generation Tool"]
    end

    subgraph Validation["Pre-Execution"]
        ValidateParams["Validate Parameters"]
        ValidateFilters["Validate Filters"]
        CheckReport["Check Report Exists"]
    end

    subgraph Execution["Tool Execution"]
        CallAPI["Call Backend API"]
        ProcessResult["Process Results"]
        GenUI["Generate UI Component"]
    end

    subgraph Logging["Audit Trail"]
        LogTool["Log Tool Call"]
        LogParams["Log Parameters"]
        LogResult["Log Results"]
        LogStatus["Log Status"]
    end

    Tools --> Validation
    Validation --> Execution
    Execution --> Logging

    CallAPI --> ProcessResult
    ProcessResult --> GenUI
```

---

## 7. Error Handling

```mermaid
flowchart TB
    subgraph Errors["Error Categories"]
        LLMErr["LLM Errors"]
        APIErr["API Errors"]
        ValErr["Validation Errors"]
        CtxErr["Context Errors"]
    end

    subgraph LLMTypes["LLM Error Types"]
        Timeout["Timeout"]
        RateLimit["Rate Limit"]
        AuthErr["Authentication"]
        ConnErr["Connection"]
    end

    subgraph APITypes["API Error Types"]
        ServerErr["Server Error 5xx"]
        ClientErr["Client Error 4xx"]
        NotFound["Not Found"]
        BadRequest["Bad Request"]
    end

    subgraph Response["Error Response"]
        UserMsg["User-Friendly Message"]
        ErrorCode["Error Code"]
        AdminFlag["Contact Admin Flag"]
        UIComp["Error UI Component"]
    end

    LLMErr --> LLMTypes
    APIErr --> APITypes

    Errors --> Response
    Response --> UserMsg
    Response --> UIComp
```

---

## 8. Component Architecture

```mermaid
flowchart TB
    subgraph Consumer["WebSocket Layer"]
        ChatConsumer["ChatConsumer"]
        TestConsumer["TestConsumer"]
    end

    subgraph Services["Service Layer"]
        ChatSvc["ChatService"]
        LLMSvc["LLMService"]
        MockLLM["MockLLMService"]
        EntitySvc["EntityExtractionService"]
    end

    subgraph Utils["Utilities"]
        CtxMgr["ContextManager"]
        Logger["LLMLogger"]
        Sanitizer["InputSanitizer"]
        ErrHandler["ErrorHandler"]
    end

    subgraph Tools["Tool Layer"]
        ForecastTools["ForecastTools"]
        ValidationTools["ValidationTools"]
        UITools["UITools"]
    end

    subgraph Data["Data Layer"]
        Models["Django Models"]
        APIClient["ChatAPIClient"]
    end

    ChatConsumer --> ChatSvc
    ChatSvc --> LLMSvc
    ChatSvc --> MockLLM
    ChatSvc --> EntitySvc

    ChatSvc --> CtxMgr
    ChatSvc --> Logger
    ChatSvc --> Sanitizer
    ChatSvc --> ErrHandler

    LLMSvc --> Tools
    Tools --> APIClient
    CtxMgr --> Models
```

---

## 9. Data Models

```mermaid
erDiagram
    User ||--o{ ChatConversation : has
    ChatConversation ||--o{ ChatMessage : contains
    ChatConversation ||--o| ConversationContext : has
    ChatMessage ||--o{ ChatToolExecution : triggers

    ChatConversation {
        uuid id PK
        int user_id FK
        string title
        boolean is_active
        datetime created_at
        datetime updated_at
    }

    ChatMessage {
        uuid id PK
        uuid conversation_id FK
        string role
        text content
        json metadata
        datetime created_at
    }

    ConversationContext {
        uuid id PK
        uuid conversation_id FK
        string active_report_type
        int current_month
        int current_year
        json context_data
    }

    ChatToolExecution {
        uuid id PK
        uuid message_id FK
        string tool_name
        json parameters
        json result
        string status
        string error_message
    }
```

---

## 10. Technology Stack

```mermaid
flowchart TB
    subgraph Stack["Chat Agent Stack"]
        subgraph Backend["Backend"]
            Django["Django Channels"]
            Daphne["Daphne ASGI"]
            AsyncIO["AsyncIO"]
        end

        subgraph AI["AI Integration"]
            OpenAI["OpenAI GPT-4"]
            LangChain["LangChain"]
            Pydantic["Pydantic Validation"]
        end

        subgraph RealTime["Real-Time"]
            WS["WebSocket Protocol"]
            Channels["Django Channels"]
            ChannelLayers["Channel Layers"]
        end

        subgraph Frontend["Frontend"]
            JS["Vanilla JavaScript"]
            WSAPI["WebSocket API"]
            DOMManip["DOM Manipulation"]
        end

        subgraph Persistence["Persistence"]
            SQLite["SQLite"]
            Redis["Redis Optional"]
            InMemory["In-Memory Cache"]
        end
    end
```

---

## Key Features

| Feature | Description |
|---------|-------------|
| **Real-Time Chat** | WebSocket-based bidirectional communication |
| **Intent Classification** | LLM-powered understanding of user queries |
| **Context Awareness** | Maintains conversation state across turns |
| **Entity Extraction** | Identifies filters, dates, and parameters |
| **Confirmation Flow** | User confirms before data operations |
| **Auto Reconnect** | Handles connection drops gracefully |
| **Audit Trail** | Logs all tool executions and results |
| **Error Recovery** | User-friendly error messages |

---

## Security Measures

- **Input Sanitization**: XSS, SQL injection, command injection prevention
- **Authentication**: LDAP-integrated user validation
- **WebSocket Auth**: Rejects unauthenticated connections
- **Rate Limiting**: Configurable messages per minute
- **PII Redaction**: User data protected in logs
- **API Key Protection**: Keys never logged or exposed
