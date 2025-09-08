``` mermaid
graph TB
    subgraph "Data Sources"
        DS1[Customer Data Files]
        DS2[Sales Data Files]
        DS3[External APIs]
    end
    
    subgraph "AWS S3 Data Lake"
        S3Raw[S3 Raw Data Bucket<br/>Raw CSV/JSON files]
        S3Processed[S3 Processed Data Bucket<br/>Parquet files partitioned]
        S3Scripts[S3 Scripts Bucket<br/>Glue ETL scripts]
        S3Temp[S3 Temp Bucket<br/>Temporary processing files]
    end
    
    subgraph "AWS Glue"
        GlueCrawler[Glue Crawler<br/>Schema Discovery]
        GlueDB[(Glue Data Catalog<br/>Metadata Repository)]
        
        subgraph "ETL Jobs"
            Job1[Customer Data ETL<br/>- Data validation<br/>- Transformation<br/>- Quality checks]
            Job2[Sales Data ETL<br/>- Business metrics<br/>- Customer segmentation<br/>- Aggregations]
            Job3[Data Quality Job<br/>- Validation rules<br/>- Quality scoring<br/>- Report generation]
        end
        
        GlueWorkflow[Glue Workflow<br/>Job orchestration]
    end
    
    subgraph "AWS EventBridge"
        EventBus[Custom Event Bus]
        
        subgraph "Event Rules"
            Rule1[S3 Object Created Rule]
            Rule2[Glue Job State Change Rule]
            Rule3[Scheduled ETL Rule]
            Rule4[Quality Check Rule]
        end
    end
    
    subgraph "AWS Lambda"
        Lambda1[Glue Job Orchestrator<br/>- Job triggering<br/>- State management<br/>- Error handling]
        Lambda2[Data Validation<br/>- Custom validations<br/>- Business rules]
    end
    
    subgraph "Monitoring & Notifications"
        CW[CloudWatch<br/>Metrics & Logs]
        SNS[SNS Topic<br/>Notifications]
        Email[Email Notifications]
    end
    
    subgraph "Analytics & BI"
        Athena[Amazon Athena<br/>SQL Analytics]
        QuickSight[Amazon QuickSight<br/>Dashboards]
        BI[External BI Tools<br/>Tableau, PowerBI]
    end
    
    %% Data Flow
    DS1 --> S3Raw
    DS2 --> S3Raw
    DS3 --> S3Raw
    
    S3Raw -->|File arrival event| Rule1
    Rule1 --> Lambda1
    Lambda1 --> Job1
    Lambda1 --> Job2
    
    Job1 -->|Process customer data| S3Processed
    Job2 -->|Process sales data| S3Processed
    
    Job1 -->|State change| Rule2
    Job2 -->|State change| Rule2
    Rule2 --> Lambda1
    
    Lambda1 -->|Trigger quality job| Job3
    Job3 --> S3Processed
    
    Rule3 -->|Daily schedule| Lambda1
    GlueCrawler --> GlueDB
    S3Raw --> GlueCrawler
    S3Processed --> GlueCrawler
    
    Job1 --> CW
    Job2 --> CW
    Job3 --> CW
    Lambda1 --> CW
    
    Rule2 --> SNS
    SNS --> Email
    
    S3Processed --> Athena
    Athena --> QuickSight
    S3Processed --> BI
    
    EventBus --> Rule1
    EventBus --> Rule2
    EventBus --> Rule3
    EventBus --> Rule4
    
    %% Styling
    classDef awsService fill:#FF9900,stroke:#232F3E,stroke-width:2px,color:white
    classDef dataStore fill:#3F48CC,stroke:#232F3E,stroke-width:2px,color:white
    classDef etlJob fill:#7AA116,stroke:#232F3E,stroke-width:2px,color:white
    classDef eventService fill:#FF4B4B,stroke:#232F3E,stroke-width:2px,color:white
    
    class S3Raw,S3Processed,S3Scripts,S3Temp dataStore
    class Job1,Job2,Job3 etlJob
    class EventBus,Rule1,Rule2,Rule3,Rule4 eventService
    class Lambda1,Lambda2,CW,SNS,Athena,QuickSight awsService
    ```