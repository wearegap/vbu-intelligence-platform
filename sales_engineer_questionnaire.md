# Sales Engineer Discovery Questionnaire (Pipeline Complete)

Use this script during discovery/technical qualification calls to collect everything needed to populate the VBU Intelligence pipeline end-to-end.

## 1) Call And Account Context

1. What is the exact account/client name as it should appear in the report?
2. What date range should we include for analyzed calls/transcripts?
3. Which specific calls should be included in the analysis (titles/dates/participants)?
4. Who attended this call (name, title, role in deal)?

## 2) Core Modernization Inputs (Required)

1. What is your primary legacy/source technology stack today? (VB6, VB.NET, Access, PowerBuilder, WebForms, WinForms, Clarion, Silverlight, ASP Classic, Informix, Delphi, other)
2. What is your target platform/target architecture? (example: .NET 8 on Azure)
3. Approximately how many total lines of code are in scope for modernization?
4. How would you rate current code complexity? (Clean, Conventional, Complex, Spaghetti)
5. How many customer-side developers are currently assigned to modernization?
6. In one or two sentences, how would you summarize the current state and migration goal?

## 3) Architecture And Hosting Decision (Estimator)

1. Will the database be hosted in Azure or remain on-premises/hybrid?
2. Which Azure region should we price for? (default East US)
3. What availability/SLA expectations do you have for production?
4. Are there any data residency or compliance constraints that affect region choice?

## 4) App Service Inputs

1. Which App Service plan SKU should we assume for sizing? (for example P2v3)
2. How many App Service instances do you expect at steady state?
3. Do you need separate sizing assumptions for peak traffic periods?

## 5) SignalR Inputs

1. Which SignalR tier should we assume? (Free, Standard, Premium)
2. How many SignalR units do you need initially?
3. What is your expected concurrent user/connection profile?

## 6) Database Inputs (Ask Based On DB Mode)

### If Azure SQL

1. Should Azure SQL be enabled for this estimate? (yes/no)
2. Which Azure SQL tier/vCore size should we assume? (example: 4 vCore)
3. How much SQL storage (GB) is needed initially?
4. Which compute model is preferred? (Provisioned or Serverless)

### If On-Prem/Hybrid DB

1. Should hybrid/on-prem connectivity be enabled for this estimate? (yes/no)
2. Which VPN Gateway tier should we assume? (example: VpnGw1)
3. How much outbound egress to on-prem is expected per month (GB)?
4. Which Key Vault tier should we assume? (Standard or Premium)
5. How many Key Vault secret operations per month (in thousands)?

## 7) Monitoring Inputs

1. Which Azure Monitor/App Insights tier should we use? (Basic or Analytics)
2. How much monthly log ingestion do you expect (GB/month)?
3. Are there retention or observability requirements that may increase monitoring volume/cost?

## 8) Cost Dashboard Assumptions

1. How many engineers should we model for a DIY modernization scenario?
2. What annual fully loaded cost per engineer should we use?
3. Do you want sensitivity ranges (best case, likely, worst case) for staffing and cost?

## 9) Sales Strategy And Qualification Inputs

1. What is the business impact if this legacy system fails or is delayed? (dollars/hour or business KPI impact)
2. How urgent is the migration timeline? (Immediate, This quarter, This year, No fixed date)
3. What is driving the deal most? (risk reduction, speed, cost, compliance, innovation)
4. Who is the economic buyer and who signs the final approval?
5. Who is the technical champion and day-to-day owner?
6. What internal blockers do you expect? (procurement, security review, architecture review, resourcing, change resistance)
7. Which objections are most likely from stakeholders?
8. Have you attempted modernization before? If yes, what stalled it?
9. What does success look like in 6-12 months?
10. What concrete next step can we commit to now? (deep dive, pilot scope, SOW draft, exec review)
11. What timeline should we target for pilot approval and full project start?

## 10) Evidence Capture Prompts (For Transcript-Backed Strategy)

1. Can you share direct quotes that indicate urgency?
2. Can you share direct quotes that describe risk and complexity?
3. Can you share direct quotes that reveal buyer persona and decision dynamics?
4. Can you share direct quotes that support ROI/value messaging?

## 11) Completion Checklist (Before Ending Call)

- Source technology captured
- Target platform captured
- Lines of code captured
- Complexity level captured
- Customer dev count captured
- DB mode selected (Azure SQL or On-Prem)
- Estimator sizing captured (App, SignalR, DB/Hybrid, Monitor)
- DIY staffing/cost assumptions captured
- Buyer/champion/blockers/urgency captured
- Next action and timeline agreed

## Field Mapping (Questionnaire -> Pipeline)

- state.clientName <- Section 1
- state.extracted.sourceTech <- Section 2
- state.extracted.targetTech <- Section 2
- state.extracted.linesOfCode <- Section 2
- state.extracted.complexityLevel <- Section 2
- state.extracted.customersDevCount <- Section 2
- state.extracted.summary <- Section 2
- state.blazorEstimatorPrefill.dbMode <- Section 3
- state.blazorEstimatorPrefill.region <- Section 3
- state.blazorEstimatorPrefill.app.sku <- Section 4
- state.blazorEstimatorPrefill.app.instances <- Section 4
- state.blazorEstimatorPrefill.signalr.tier <- Section 5
- state.blazorEstimatorPrefill.signalr.units <- Section 5
- state.blazorEstimatorPrefill.azureSql.* <- Section 6 (Azure SQL)
- state.blazorEstimatorPrefill.onPrem.* <- Section 6 (On-Prem/Hybrid)
- state.blazorEstimatorPrefill.monitor.* <- Section 7
- state.engineerCount/state.engineerCost <- Section 8
- state.salesStrategy/state.salesEvidence <- Sections 9 and 10
