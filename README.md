


















┌──────────────────────────────────────────────────────────────────────────────┐
│                                CLIENTS / USERS                               │
│  - Patients                                                                   │
│  - Doctors / Staff                                                            │
│  - Admins / Clinic Owners                                                     │
└──────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                           BROWSER / MOBILE APPS                              │
│  - Web Browser                                                                │
│  - Mobile Apps (iOS / Android)                                                │
└──────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                           FRONT-END LAYER (UI)                               │
│                     React + TypeScript + Vite (healthcare-ui)                │
│                                                                              │
│  Phase 1 (Current):                                                          │
│     - Direct synchronous REST calls to backend services                      │
│                                                                              │
│  Phase 2 (Future):                                                           │
│     - All traffic routed via API Gateway (Kong)                              │
└──────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                               API GATEWAY (Kong)                             │
│  - Routing to backend APIs                                                    │
│  - Centralized Authentication (OAuth2, JWT)                                   │
│  - Rate Limiting                                                              │
│  - Request/Response Transformation                                            │
│  - Logging / Tracing Injection                                                │
└──────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                        BACKEND SERVICES (API Layer)                          │
│                                                                              │
│  Python FastAPI Services:                                                    │
│     - appointment-service                                                    │
│     - patient-service                                                        │
│     - clinic-service                                                         │
│     - billing-service                                                        │
│     - helpdesk-service                                                       │
│                                                                              │
│  NodeJS Service:                                                             │
│     - notification-service (emails, SMS, push, async events)                 │
│                                                                              │
│  Phase 1 (Current):                                                          │
│     - Synchronous REST / gRPC between services                               │
│                                                                              │
│  Phase 2 (Future):                                                           │
│     - Event-driven architecture via RabbitMQ or Kafka                        │
│     - notification-service consumes events                                   │
└──────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                               DATABASE LAYER                                 │
│                                PostgreSQL                                     │
│                                                                              │
│  - Separate DBs / Schemas per service                                        │
│  - No cross-service DB calls                                                 │
│  - Strong domain boundaries                                                  │
│                                                                              │
│  Examples:                                                                   │
│     appointment_db                                                           │
│     patient_db                                                               │
│     clinic_db                                                                │
│     notification_db                                                          │
│     billing_db                                                               │
│     helpdesk_db                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                             OBSERVABILITY LAYER                              │
│                                                                              │
│  Logs:       Loki / Splunk                                                   │
│  Metrics:    Prometheus                                                      │
│  Dashboards: Grafana                                                         │
│  Tracing:    OpenTelemetry + Tempo                                           │
│  Alerting:   AlertManager                                                    │
└──────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                                PLATFORM LAYER                                │
│                                                                              │
│  - K3s Cluster (2 nodes + future 3rd node)                                   │
│  - Helm Charts                                                               │
│  - Docker Images                                                             │
│  - GitOps (ArgoCD — future)                                                  │
│  - API Gateway (Kong)                                                        │
│  - Observability Stack                                                       │
│  - Database Stack                                                            │
└──────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                           INFRASTRUCTURE LAYER                               │
│                                                                              │
│  - Terraform (future cloud migration)                                        │
│  - Ansible (node provisioning, config mgmt)                                  │
│  - Homelab Hardware                                                          │
└──────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                                   CLOUD                                      │
│                                                                              │
│  - AWS (future)                                                              │
│  - Azure (future)                                                            │
└──────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                                CI/CD WORKFLOW                                │
│                              GitHub Actions                                  │
│                                                                              │
│  - Lint → Test → Scan → Build → Push → Deploy                                │
│  - Deploy to K3s via Helm (future: GitOps)                                   │
│                                                                              │
│  Git Branching Strategy (Git Flow):                                          │
│     - main                                                                   │
│     - develop (integration)                                                  │
│     - feature/*                                                              │
│     - release/*                                                              │
│     - hotfix/*                                                               │
└──────────────────────────────────────────────────────────────────────────────┘
